import json
import logging
from datetime import datetime
import random

import requests

from blockchain_users.miner import public_key_hash as miner_public_key_hash
from common.block import Block, BlockHeader, BlockPoH
from common.io_blockchain import BlockchainMemory
from common.io_mem_pool import MemPool
from common.io_known_nodes import KnownNodesMemory
from common.merkle_tree import get_merkle_root
from common.owner import Owner
from common.transaction_output import TransactionOutput
from common.utils import calculate_hash,normal_round,check_marketplace_step1_sell,check_marketplace_step1_buy,check_marketplace_step2,check_marketplace_reputation_refresh
from common.values import NUMBER_OF_LEADING_ZEROS, BLOCK_REWARD, INTERFACE_BLOCK_REWARD_PERCENTAGE, NODE_BLOCK_REWARD_PERCENTAGE, MINER_BLOCK_REWARD_PERCENTAGE,ROUND_VALUE_DIGIT
from common.io_leader_node_schedule import LeaderNodeScheduleMemory
from common.node import Node
from node.transaction_validation.transaction_validation import Transaction
from common.smart_contract import SmartContract,check_smart_contract
from common.smart_contract_script import block_script
from common.master_state import MasterState
from common.master_state_readiness import master_state_readiness
from common.master_state_threading import master_state_threading
from blockchain_users.node import private_key as node_private_key



class BlockException(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class ProofOfWork:
    """
    Class to create a new block.
    """
    def __init__(self, hostname: str):
        self.hostname = hostname
        self.PoH_memory = None
        self.known_nodes_memory = KnownNodesMemory()
        self.leader_node_schedule_memory=LeaderNodeScheduleMemory()
        self.mempool = MemPool()
        self.testing_flag=False

    def start(self):
        logging.info("Starting Proof of Work")
        #load of the best block in the backlog and if not exiting use the standard blockchain
        blockchain_memory = BlockchainMemory()
        blockchain=blockchain_memory.get_best_block_pointer_in_backlog()
        if blockchain is None:self.blockchain = blockchain_memory.get_blockchain_from_memory()
        else:self.blockchain = blockchain
        self.new_block = None
        

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
                "noonce": noonce,
                "slot": block_header.slot,
                "leader_node_public_key_hash": block_header.leader_node_public_key_hash,
            }
            block_header_hash = calculate_hash(json.dumps(block_header_content))
        logging.info(f"Found the noonce!: {noonce} block_header_hash:{block_header_hash}")
        return noonce

    def reload_blockchain(self):
        blockchain_memory = BlockchainMemory()
        #load of the best block in the backlog and if not exiting use the standard blockchain
        from common.consensus_blockchain import consensus_blockchain
        consensus_blockchain.refresh()
        blockchain=blockchain_memory.get_best_block_pointer_in_backlog()
        if blockchain is None:self.blockchain = blockchain_memory.get_blockchain_from_memory()
        else:self.blockchain = blockchain


    def launch_new_block_creation(self, *args, **kwargs):
        logging.info("Launch of new block creation")
        self.testing_flag=kwargs.get('testing_flag',False)
        #Launch Leader node Rotation

        current_leader_node_public_key_hash=self.leader_node_schedule_memory.current_leader_node_public_key_hash
        self.leader_node_schedule_memory.next_leader_node_schedule(self.known_nodes_memory.known_nodes)
        self.PoH_memory.PoH_start_flag=False
        self.broadcast_leader_node_schedule()
        #Check if there are valid transactions
        transactions = self.mempool.get_transactions_from_memory()
        logging.info(f"nb of transactions: {len(transactions)}")
        #self.PoH_memory.stop()
        check_new_block_creation=self.create_new_block(current_leader_node_public_key_hash)
        if check_new_block_creation is True:
            #a new block needs to be created
            self.broadcast()
            self.mempool.clear_transactions_from_memory()
            self.PoH_memory.reset("None","None",datetime.timestamp(datetime.utcnow()))

        #let's release to allow the block receiving
        #master_state_threading.receiving_reset()
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

    def create_new_block(self,current_leader_node_public_key_hash):
        logging.info(f"Creating new block by {self.hostname}")
        transactions = self.mempool.get_transactions_from_memory()
        #transactions=sorted(transactions, key=lambda x: x['timestamp'])
        
        master_state=MasterState()
        #master_state_readiness=MasterStateReadiness()

        #STEP 0 Remove all the transactions with the same inputs to avoid conflict
        #For Marketplace 2, Remove all the transactions with duplicate same smart_contract_account
        #as the seller can have multiple available UTXO which can be used in the same block which is an issue
        #as it will create several UTXO for the Same SmartContract which is not possible
        transactions_input_list=[]
        step2_smart_contract_account_list=[]
        transactions_2_remove_list=[]
        for i in range(0,len(transactions)):
            if check_marketplace_step1_buy(transactions[i]['outputs']) is False and check_marketplace_step1_sell(transactions[i]['outputs']) is False:
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
                    #1st check
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
                    #2nd check
                    try:
                        step2_smart_contract_account=transactions[i]['outputs'][j]['smart_contract_account']
                        blockchain_memory = BlockchainMemory()
                        blockchain_base = blockchain_memory.get_blockchain_from_memory()
                        step2_smart_contract_account_utxos=blockchain_base.get_user_utxos(step2_smart_contract_account)
                        if len(step2_smart_contract_account_utxos["utxos"])>1:
                            #ISSUE: this transactions has been already confirmed in STEP 2 probably in another Block
                            #we need to remove this transaction 
                            transactions_2_remove_list.append(transactions[i])
                            logging.info(f"#WARNING transactions_2_remove_list STEP 2 smart_contract_account ALREADY SOLD: {transactions[i]}")
                    except:
                        pass
            try:
                reputation_refresh_flag,account_list_2_refresh=check_marketplace_reputation_refresh(transactions[i]['outputs'])
                if reputation_refresh_flag is True:
                    #The reputation needs to be refresh (Step 4, 45 Partial payment or 66 payment default or Step 98 expiration, not Step 99 cancellation)
                    from node.main import refresh_reputation,participant_refresh_score
                    for account_2_refresh in account_list_2_refresh:
                        #STEP 1 refresh of reputation
                        try:
                            transaction_reputation=refresh_reputation(account_public_key_hash=account_2_refresh,block_creation_flag=True)
                            logging.info(f"transaction_reputation=>:{transaction_reputation}")
                            if transaction_reputation is not None:transactions.append(transaction_reputation.transaction_data)
                        except Exception as e:
                            #issue with reputation refresh
                            logging.info(f"###ERROR block creation reputation refresh issue. account_2_refresh: {account_2_refresh}")
                            logging.exception(e)
                        #STEP 2 refresh of score
                        try:
                            transaction_refresh_score=participant_refresh_score(participant_public_key_hash=account_2_refresh,block_creation_flag=True)
                            logging.info(f"transaction_refresh_score=>:{transaction_refresh_score}")
                            if transaction_refresh_score is not None:transactions.append(transaction_refresh_score.transaction_data)
                        except Exception as e:
                            #issue with reputation refresh
                            logging.info(f"###ERROR block creation score refresh issue. account_2_refresh: {account_2_refresh}")
                            logging.exception(e)
            except Exception as e:
                #issue with reputation refresh
                logging.info(f"###ERROR block creation reputation/score refresh issue. Transaction output: {transactions[i]['outputs']}")
                logging.exception(e)


        for transactions_2_remove in transactions_2_remove_list:
            try:
                transactions.remove(transactions_2_remove)
            except Exception as e:
                logging.info(f"ERROR with transactions_2_remove: {transactions_2_remove}")
                logging.exception(e)
        logging.info(f"nb of transactions: {len(transactions)}")


        
            
        if len(transactions)>0:
            interface_transaction_fees_dic,node_transaction_fees_dic,miner_transaction_fees = self.get_transaction_fees(transactions)
            #STEP 1 Interface
            for interface_transaction_fees_public_key_hash in interface_transaction_fees_dic.keys():
                interface_coinbase_transaction = self.get_coinbase_transaction(interface_transaction_fees_dic[interface_transaction_fees_public_key_hash],
                                                                                INTERFACE_BLOCK_REWARD_PERCENTAGE,
                                                                                interface_transaction_fees_public_key_hash,
                                                                                "interface",
                                                                                self.testing_flag)
                transactions.append(interface_coinbase_transaction)
            #STEP 2 Node
            for node_transaction_fees_public_key_hash in node_transaction_fees_dic.keys():
                node_coinbase_transaction = self.get_coinbase_transaction(node_transaction_fees_dic[node_transaction_fees_public_key_hash],
                                                                                NODE_BLOCK_REWARD_PERCENTAGE,
                                                                                node_transaction_fees_public_key_hash,
                                                                                "node",
                                                                                self.testing_flag)
                transactions.append(node_coinbase_transaction)
            #STEP 3 Miner
            miner_coinbase_transaction = self.get_coinbase_transaction(miner_transaction_fees,
                                                                        MINER_BLOCK_REWARD_PERCENTAGE,
                                                                        miner_public_key_hash,
                                                                        "miner",
                                                                        self.testing_flag)
            transactions.append(miner_coinbase_transaction)

            #STEP 4 Creation of the block
            block_header = BlockHeader(
                merkle_root=get_merkle_root(transactions),
                previous_block_hash=self.blockchain.block_header.hash,
                current_PoH_hash=self.PoH_memory.next_PoH_hash,
                current_PoH_timestamp=self.PoH_memory.next_PoH_timestamp,
                previous_PoH_hash=self.PoH_memory.previous_PoH_hash,
                timestamp=datetime.timestamp(datetime.now()),
                noonce=0,
                slot=self.leader_node_schedule_memory.current_leader_node_slot,
                leader_node_public_key_hash=current_leader_node_public_key_hash
            )

          
            block_header.noonce = self.get_noonce(block_header)
            block_header.hash = block_header.get_hash()

            block_PoH=BlockPoH(PoH_registry_input_data=self.PoH_memory.registry_input_data,
                               PoH_registry_intermediary=self.PoH_memory.registry_intermediary,)
            
            
            vote_transaction = self.get_vote_transaction()
            transactions.append(vote_transaction)

            logging.info(f"###BlockVote addition in temporay master state ")
            #this is the initial BlockVote transaction, let's store it in a temporay master state

            self.new_block = Block(transactions=transactions, block_header=block_header, block_PoH=block_PoH, block_signature=None)
            
            #STEP 5 Sign the Block
            from common.values import MY_NODE
            if MY_NODE=="server_node3":
                from blockchain_users.node3_server import private_key as node_private_key
            if MY_NODE=="server_node2":
                from blockchain_users.node2_server import private_key as node_private_key
            if MY_NODE=="local_node3":
                from blockchain_users.node3_local import private_key as node_private_key
            if MY_NODE=="local_node2":
                from blockchain_users.node2_local import private_key as node_private_key
            node_owner=Owner(private_key=node_private_key)
            self.new_block.sign_block(node_owner)

            #let's block MasterState
            while master_state_readiness.block() is False:
                #let's wait until MasterState is release by another thread
                pass
            
            #STEP 6 SmartContract to vote on block
            master_state_temp=MasterState(temporary_save_flag=True)
            
            master_state_temp.update_master_state(vote_transaction,self.new_block.block_header.current_PoH_hash,previous_PoH_hash=self.new_block.block_header.previous_PoH_hash,leader_node_flag=True)
            master_state_temp.store_master_state_in_memory(self.new_block.block_header.current_PoH_hash)

            #STEP 7 Delete TempBlockPoH
            master_state=MasterState()
            for transaction in transactions:
                #logging.info(f"###delete_TempBlockPoH:{self.new_block.block_header.current_PoH_hash}")
                #logging.info(f"###delete_TempBlockPoH transaction:{transaction}")
                master_state.delete_TempBlockPoH(transaction)

            #let's release MasterState
            master_state_readiness.release()
            
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

        #logging.info(f"$$$$$$$$$$$ interface_transaction_fees_dic: {interface_transaction_fees_dic} node_transaction_fees_dic: {node_transaction_fees_dic} miner_transaction_fees:{miner_transaction_fees}")
        return interface_transaction_fees_dic,node_transaction_fees_dic,miner_transaction_fees

    @staticmethod
    def get_coinbase_transaction(transaction_fees: float, block_reward_percentage: float, public_key_hash: str, type: str , testing_flag:bool) -> dict:
        transaction_output = TransactionOutput(
            amount=normal_round(transaction_fees + BLOCK_REWARD*(block_reward_percentage/100),ROUND_VALUE_DIGIT),
            list_public_key_hash=[public_key_hash],
            coinbase_transaction=True
        )
        if testing_flag is True:
            timestamp_value='timestamp'
            transaction_hash_value=calculate_hash(str(transaction_output.to_dict()))
        else:
            timestamp_value =datetime.timestamp(datetime.utcnow())
            transaction_hash_value=calculate_hash(str(random.randint(10000000, 9999999999999999999999))+str(transaction_output.to_dict()))
        return {"inputs": [],
                "outputs": [transaction_output.to_dict()],
                "transaction_hash":transaction_hash_value,
                "timestamp": timestamp_value}

    def get_vote_transaction(self) -> dict:
        #SmartContract use to vote on the block to insert it on the BlockChain
        from node.main import marketplace_owner
        block_PoH=self.PoH_memory.next_PoH_hash
        payload=f'''block_PoH="{block_PoH}"
'''+block_script
        smart_contract_block=SmartContract(block_PoH,
                                 smart_contract_sender=marketplace_owner.public_key_hash,
                                 smart_contract_new=True,
                                 smart_contract_gas=1000000,
                                 smart_contract_type="source",
                                 payload=payload)
        smart_contract_block.process()

        transaction_output = TransactionOutput(list_public_key_hash=[block_PoH], 
                                               amount=0,
                                               account_temp=True,
                                               smart_contract_transaction_flag=True,
                                             smart_contract_account=smart_contract_block.smart_contract_account,
                                             smart_contract_sender=smart_contract_block.smart_contract_sender,
                                             smart_contract_new=smart_contract_block.smart_contract_new,
                                             smart_contract_flag=True,
                                             smart_contract_gas=smart_contract_block.gas,
                                             smart_contract_memory=smart_contract_block.smart_contract_memory,
                                             smart_contract_memory_size=smart_contract_block.smart_contract_memory_size,
                                             smart_contract_type=smart_contract_block.smart_contract_type,
                                             smart_contract_payload=smart_contract_block.payload,
                                             smart_contract_result=smart_contract_block.result,
                                             smart_contract_previous_transaction=smart_contract_block.smart_contract_previous_transaction,
                                             coinbase_transaction=True)
        return {"inputs": [],
                "outputs": [transaction_output.to_dict()],
                "transaction_hash":calculate_hash(str(random.randint(10000000, 9999999999999999999999))+str(transaction_output.to_dict())),
                "timestamp": datetime.timestamp(datetime.utcnow())}

    def broadcast(self) -> bool:
        logging.info("Broadcasting block to other nodes by leader node")
        node_list = self.known_nodes_memory.known_nodes
        broadcasted_node = False
        saving_flag=False
        #Step 0 saving the block on the blockchain
        node_list_check=[]
        for node in node_list:
            if node.hostname == self.hostname and node.hostname not in node_list_check:
                node_list_check.append(node.hostname)
                block_content = {
                        "block": {
                            "header": self.new_block.block_header.to_dict,
                            "PoH": self.new_block.block_PoH.to_dict,
                            "signature": self.new_block.block_signature,
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
                            "PoH": self.new_block.block_PoH.to_dict,
                            "signature": self.new_block.block_signature,
                            "transactions": self.new_block.transactions
                        },
                        "sender": self.hostname
                    }
                if node.hostname != self.hostname and node.hostname not in node_list_check:
                    node_list_check.append(node.hostname)
                    # broadcasting block
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
        node_list_check=[]
        for node in node_list:
            if node.hostname != self.hostname and node.hostname not in node_list_check:
                node_list_check.append(node.hostname)
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
