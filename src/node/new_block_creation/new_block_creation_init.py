import json
import logging
from datetime import datetime
import random

import requests

from blockchain_users.miner import public_key_hash as miner_public_key_hash
from common.block import Block, BlockHeader
from common.io_blockchain import BlockchainMemory
from common.io_mem_pool import MemPool
from common.io_known_nodes import KnownNodesMemory
from common.merkle_tree import get_merkle_root
from common.owner import Owner
from common.transaction_output import TransactionOutput
from common.utils import calculate_hash,normal_round,check_marketplace_step1,check_marketplace_step2
from common.values import NUMBER_OF_LEADING_ZEROS, BLOCK_REWARD, INTERFACE_BLOCK_REWARD_PERCENTAGE, NODE_BLOCK_REWARD_PERCENTAGE, MINER_BLOCK_REWARD_PERCENTAGE,ROUND_VALUE_DIGIT
from common.io_leader_node_schedule import LeaderNodeScheduleMemory
from common.node import Node
from node.transaction_validation.transaction_validation import Transaction
from common.smart_contract import check_smart_contract


class BlockException(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class ProofOfWork:
    def __init__(self, hostname: str):
        logging.info("Starting Proof of Work")
        self.known_nodes_memory = KnownNodesMemory()
        blockchain_memory = BlockchainMemory()
        self.leader_node_schedule_memory=LeaderNodeScheduleMemory()
        self.hostname = hostname
        self.mempool = MemPool()
        self.blockchain = blockchain_memory.get_blockchain_from_memory()
        self.new_block = None
        self.PoH_memory = None

    @staticmethod
    def get_noonce(block_header: BlockHeader) -> int:
        logging.info("Trying to find noonce")
        block_header_hash = ""
        noonce = block_header.noonce
        starting_zeros = "".join([str(0) for _ in range(NUMBER_OF_LEADING_ZEROS)])
        while not block_header_hash.startswith(starting_zeros):
            noonce = noonce + 1
            block_header_content = {
                "previous_block_hash": block_header.previous_block_hash,
                "current_PoH_hash": block_header.current_PoH_hash,
                "current_PoH_timestamp": block_header.current_PoH_timestamp,
                "previous_PoH_hash": block_header.previous_PoH_hash,
                "merkle_root": block_header.merkle_root,
                "timestamp": block_header.timestamp,
                "noonce": noonce
            }
            block_header_hash = calculate_hash(json.dumps(block_header_content))
        logging.info("Found the noonce!")
        return noonce

    def reload_blockchain(self):
        blockchain_memory = BlockchainMemory()
        self.blockchain = blockchain_memory.get_blockchain_from_memory()


    def launch_new_block_creation(self):
        logging.info("Launch of new block creation")
        #Launch Leader node Rotation
        self.leader_node_schedule_memory.next_leader_node_schedule(self.known_nodes_memory.known_nodes)
        self.PoH_memory.PoH_start_flag=False
        self.broadcast_leader_node_schedule()
        #Check if there are valid transactions
        transactions = self.mempool.get_transactions_from_memory()
        logging.info(f"nb of transactions: {len(transactions)}")
        #self.PoH_memory.stop()
        check_new_block_creation=self.create_new_block()
        logging.info(f"check1")
        if check_new_block_creation is True:
            logging.info(f"check ok")
            #a new block needs to be created
            self.broadcast()
            self.mempool.clear_transactions_from_memory()
            self.PoH_memory.reset("None","None",datetime.timestamp(datetime.utcnow()))
        return check_new_block_creation

    def next_leader_node_schedule(self):
        known_nodes_of_known_nodes=self.ask_known_nodes_for_their_known_nodes()
        self.leader_node_schedule_memory.next_leader_node_schedule(known_nodes_of_known_nodes)
        
    def ask_known_nodes_for_their_known_nodes(self) -> list:
        logging.info("Asking known nodes for their own known nodes")
        known_nodes_of_known_nodes = []
        for currently_known_node in self.known_nodes_memory.known_nodes:
            if currently_known_node.hostname != self.hostname:
                try:
                    known_nodes_of_known_node = currently_known_node.known_node_request()
                    for node in known_nodes_of_known_node:
                        if node["hostname"] != self.hostname:
                            known_nodes_of_known_nodes.append(Node(node["hostname"]))
                except requests.exceptions.ConnectionError:
                    logging.info(f"Node not answering: {currently_known_node.hostname}")
        return known_nodes_of_known_nodes

    def create_new_block(self):
        logging.info(f"Creating new block by {self.hostname}")
        transactions = self.mempool.get_transactions_from_memory()

        #STEP 0 Remove all the transactions with the same inputs to avoid conflict
        #For Marketplace 2, Remove all the transactions with duplicate same smart_contract_account
        #as the seller can have multiple available UTXO which can be used in the same block which is an issue
        #as it will create several UTXO for the Same SmartContract which is not possible
        transactions=sorted(transactions, key=lambda x: x['timestamp'])
        transactions_input_list=[]
        step2_smart_contract_account_list=[]
        transactions_2_remove_list=[]
        for i in range(0,len(transactions)):
            if check_marketplace_step1(transactions[i]['outputs']) is False:
                for j in range(0,len(transactions[i]['inputs'])):
                    transactions_input_str=transactions[i]['inputs'][j]['transaction_hash']+'_'+str(transactions[i]['inputs'][j]['output_index'])
                    if transactions_input_str not in transactions_input_list:transactions_input_list.append(transactions_input_str)
                    else:
                        #ISSUE: this transactions is using an input already in the Block
                        #we need to remove this transaction
                        transactions_2_remove_list.append(transactions[i])
                        logging.info(f"#WARNING transactions_2_remove_list INPUT DUPLICATE: {transactions[i]}")

            if check_marketplace_step2(transactions[i]['outputs']) is True:
                for j in range(0,len(transactions[i]['outputs'])):
                    try:
                        step2_smart_contract_account=transactions[i]['outputs'][j]['smart_contract_account']
                        if step2_smart_contract_account not in step2_smart_contract_account_list:step2_smart_contract_account_list.append(step2_smart_contract_account)
                        else:
                            #ISSUE: this transactions is using a smart_contract_account already in the Block for Marketplace Step 2
                            #we need to remove this transaction as it's a duplicate
                            transactions_2_remove_list.append(transactions[i])
                            logging.info(f"#WARNING transactions_2_remove_list STEP 2 smart_contract_account DUPLICATE: {transactions[i]}")
                    except:
                        pass
        for transactions_2_remove in transactions_2_remove_list:transactions.remove(transactions_2_remove)
        logging.info(f"nb of transactions: {len(transactions)}")

        
        if 5==6:
            if len(transactions)>0:
                #STEP 1 Validation of all the transaction
                input_amount = 0
                output_amount = 0
                transactions_to_check_list=transactions
                for transaction in transactions_to_check_list:
                    transaction_validation = Transaction(self.blockchain, self.hostname)
                    transaction_validation.receive(transaction=transaction)
                    transaction_validation.validate()
                    if transaction_validation.is_valid is True:
                        smart_contract_flag,smart_contract_index_list=check_smart_contract(transaction_validation)
                        if smart_contract_flag:
                            #there are smart contract in the transaction, let's validate them
                            transaction_validation.validate_smart_contract(smart_contract_index_list)
                        if transaction_validation.is_valid is True:
                            input_amount = input_amount + transaction_validation.get_total_amount_in_inputs()
                            output_amount = output_amount + transaction_validation.get_total_amount_in_outputs()
                            output_amount = output_amount - transaction_validation.get_total_fee_in_outputs()
                    
                            #logging.info(f"##### output_amount {output_amount} input:{transaction_validation.inputs} ouput:{transaction_validation.outputs} transaction_data:{transaction_validation.transaction_data} output:{transaction_validation.outputs}")
                    if transaction_validation.is_valid is False:
                        #the transaction is not valid, let's remove it from the block
                        logging.info(f"####transaction removal: {transaction}")
                        transactions.remove(transaction)
            else:
                #There is No transaction after cleanning
                #no need to create a new block
                #raise BlockException("", "No transaction in mem_pool")
                return False

            
        if len(transactions)>0:
            interface_transaction_fees_dic,node_transaction_fees_dic,miner_transaction_fees = self.get_transaction_fees(transactions)
            #STEP 1 Interface
            for interface_transaction_fees_public_key_hash in interface_transaction_fees_dic.keys():
                interface_coinbase_transaction = self.get_coinbase_transaction(interface_transaction_fees_dic[interface_transaction_fees_public_key_hash],
                                                                               INTERFACE_BLOCK_REWARD_PERCENTAGE,
                                                                               interface_transaction_fees_public_key_hash,
                                                                               "interface")
                transactions.append(interface_coinbase_transaction)
            #STEP 2 Node
            for node_transaction_fees_public_key_hash in node_transaction_fees_dic.keys():
                node_coinbase_transaction = self.get_coinbase_transaction(node_transaction_fees_dic[node_transaction_fees_public_key_hash],
                                                                               NODE_BLOCK_REWARD_PERCENTAGE,
                                                                               node_transaction_fees_public_key_hash,
                                                                               "node")
                transactions.append(node_coinbase_transaction)
            #STEP 3 Miner
            miner_coinbase_transaction = self.get_coinbase_transaction(miner_transaction_fees,
                                                                       MINER_BLOCK_REWARD_PERCENTAGE,
                                                                       miner_public_key_hash,
                                                                       "miner")
            transactions.append(miner_coinbase_transaction)

            block_header = BlockHeader(
                merkle_root=get_merkle_root(transactions),
                previous_block_hash=self.blockchain.block_header.hash,
                current_PoH_hash=self.PoH_memory.next_PoH_hash,
                current_PoH_timestamp=self.PoH_memory.next_PoH_timestamp,
                previous_PoH_hash=self.PoH_memory.previous_PoH_hash,
                timestamp=datetime.timestamp(datetime.now()),
                noonce=0
            )
            block_header.noonce = self.get_noonce(block_header)
            block_header.hash = block_header.get_hash()
            self.new_block = Block(transactions=transactions, block_header=block_header)
            return True
        else:
            #There is No transaction in mem_pool
            #no need to create a new block
            #raise BlockException("", "No transaction in mem_pool")
            return False
       

    def get_transaction_fees(self, transactions: list) -> int:
        node_transaction_fees_dic = {}
        interface_transaction_fees_dic = {}
        miner_transaction_fees = 0
        for transaction in transactions:
            for transaction_output in transaction["outputs"]:
                #fee for the interface
                interface_public_key_hash=transaction_output["interface_public_key_hash"]
                if interface_public_key_hash is not None:
                    try:interface_transaction_fees_dic[interface_public_key_hash]
                    except:interface_transaction_fees_dic[interface_public_key_hash]=0
                    interface_transaction_fees_dic[interface_public_key_hash]+=transaction_output["fee_interface"]

                #fee for the node
                node_public_key_hash=transaction_output["node_public_key_hash"]
                if node_public_key_hash is not None:
                    try:node_transaction_fees_dic[node_public_key_hash]
                    except:node_transaction_fees_dic[node_public_key_hash]=0
                    node_transaction_fees_dic[node_public_key_hash]+=transaction_output["fee_node"]

                #fee for the miner
                miner_transaction_fees+=transaction_output["fee_miner"]

        logging.info(f"$$$$$$$$$$$ interface_transaction_fees_dic: {interface_transaction_fees_dic} node_transaction_fees_dic: {node_transaction_fees_dic} miner_transaction_fees:{miner_transaction_fees}")
        return interface_transaction_fees_dic,node_transaction_fees_dic,miner_transaction_fees

    @staticmethod
    def get_coinbase_transaction(transaction_fees: float, block_reward_percentage: float, public_key_hash: str, type: str) -> dict:
        transaction_output = TransactionOutput(
            amount=normal_round(transaction_fees + BLOCK_REWARD*(block_reward_percentage/100),ROUND_VALUE_DIGIT),
            public_key_hash=public_key_hash,
            coinbase_transaction=True
        )
        return {"inputs": [],
                "outputs": [transaction_output.to_dict()],
                "transaction_hash":calculate_hash(str(random.randint(10000000, 9999999999999999999999))+str(transaction_output.to_dict())),
                "timestamp": datetime.timestamp(datetime.utcnow())}

    def broadcast(self) -> bool:
        logging.info("Broadcasting block to other nodes by leader node")
        PoH_registry_input_data=self.PoH_memory.registry_input_data
        PoH_registry_intermediary=self.PoH_memory.registry_intermediary
        node_list = self.known_nodes_memory.known_nodes
        broadcasted_node = False
        saving_flag=False
        #Step 0 saving the block on the blockchain
        for node in node_list:
            if node.hostname == self.hostname:
                block_content = {
                        "block": {
                            "header": self.new_block.block_header.to_dict,
                            "transactions": self.new_block.transactions
                        },
                        "sender": self.hostname
                    }
                try:
                    logging.info(f"saving the block on the blockchain {self.hostname}")
                    node.saving_new_block_leader_node(block_content)
                    #broadcasted_node = True
                    saving_flag=True
                except requests.exceptions.ConnectionError as e:
                    logging.info(f"Failed saving block by leaderNode {self.hostname}: {e}")
                except requests.exceptions.HTTPError as e:
                    logging.info(f"Failed saving block by leaderNode {self.hostname}: {e}")

        if saving_flag is True:
            for node in node_list:
                block_content = {
                        "block": {
                            "header": self.new_block.block_header.to_dict,
                            "transactions": self.new_block.transactions
                        },
                        "sender": self.hostname
                    }
                if node.hostname != self.hostname:
                    if 5==6:
                        #Step 1 broadcasting PoH_registry_input_data
                        try:
                            logging.info(f"Broadcasting PoH_registry_input_data to {node.hostname}")
                            node.send_new_block_PoH_registry_input_data(PoH_registry_input_data)
                            broadcasted_node = True
                        except requests.exceptions.ConnectionError as e:
                            logging.info(f"Failed broadcasting PoH_registry_input_data to {node.hostname}: {e}")
                        except requests.exceptions.HTTPError as e:
                            logging.info(f"Failed broadcasting PoH_registry_input_data to {node.hostname}: {e}")
                
                            #Step 2 broadcasting PoH_registry_intermediary
                        try:
                            logging.info(f"Broadcasting PoH_registry_intermediary to {node.hostname}")
                            node.send_new_block_PoH_registry_intermediary(PoH_registry_intermediary)
                            broadcasted_node = True
                        except requests.exceptions.ConnectionError as e:
                            logging.info(f"Failed broadcasting PoH_registry_intermediary to {node.hostname}: {e}")
                        except requests.exceptions.HTTPError as e:
                            logging.info(f"Failed broadcasting PoH_registry_intermediary to {node.hostname}: {e}")
               
                    #Step 3 broadcasting block
                    try:
                        logging.info(f"Broadcasting block to {node.hostname}")
                        node.send_new_block(block_content)
                        broadcasted_node = True
                    except requests.exceptions.ConnectionError as e:
                        logging.info(f"Failed broadcasting block to {node.hostname}: {e}")
                    except requests.exceptions.HTTPError as e:
                        logging.info(f"Failed broadcasting block to {node.hostname}: {e}")

        return broadcasted_node

    def broadcast_leader_node_schedule(self) -> bool:
        logging.info("Broadcasting LeaderNodeSchedule to other nodes")
        node_list = self.known_nodes_memory.known_nodes
        broadcasted_node = False
        for node in node_list:
            if node.hostname != self.hostname:
                leader_node_schedule = self.leader_node_schedule_memory.leader_node_schedule
                try:
                    logging.info(f"Broadcasting LeaderNodeSchedule to {node.hostname}")
                    node.advertise_leader_node_schedule(leader_node_schedule)
                    broadcasted_node = True
                except requests.exceptions.ConnectionError as e:
                    logging.info(f"Failed broadcasting LeaderNodeSchedule to {node.hostname}: {e}")
                except requests.exceptions.HTTPError as e:
                    logging.info(f"Failed broadcasting LeaderNodeSchedule to {node.hostname}: {e}")
        return broadcasted_node
