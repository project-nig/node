import copy
import logging
import json

import requests

from common.block import Block
from common.io_mem_pool import MemPool
from node.transaction_validation.script import StackScript
from common.io_known_nodes import KnownNodesMemory
from common.values import ROUND_VALUE_DIGIT
from common.utils import normal_round,calculate_hash,check_marketplace_step2,check_marketplace_step1,check_carriage_request
from common.io_leader_node_schedule import LeaderNodeScheduleMemory
from common.smart_contract import SmartContract,load_smart_contract_from_master_state



class TransactionException(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class Transaction:
    """
    Class to validate a transaction.
    """
    def __init__(self, blockchain: Block, hostname: str):
        self.blockchain = blockchain
        self.transaction_data = {}
        self.inputs = []
        self.outputs = []
        self.is_valid = False
        self.is_funds_sufficient = False
        self.is_smart_contract_valid = True
        self.mempool = MemPool()
        self.known_node_memory = KnownNodesMemory()
        self.leader_node_schedule_memory = LeaderNodeScheduleMemory()
        self.sender = ""
        self.hostname = hostname
        self.api_readonly_flag=False

    def receive(self, transaction: dict):
        self.transaction_data = transaction
        self.timestamp = transaction["timestamp"]
        self.inputs = transaction["inputs"]
        self.outputs = transaction["outputs"]

    def validate_output_not_empty(self):
        #check that output is not empty to avoid overloading leadernode with wrong transaction
        if self.outputs==[]:return False
        else:return True

    @property
    def is_new(self):
        current_transactions = self.mempool.get_transactions_from_memory()
        if self.transaction_data in current_transactions:
            return False
        return True

    def execute_script(self, unlocking_script, locking_script):
        unlocking_script_list = unlocking_script.split(" ")
        locking_script_list = locking_script.split(" ")
        transaction_data = copy.deepcopy(self.transaction_data)
        if "transaction_hash" in transaction_data:
            transaction_data.pop("transaction_hash")
        stack_script = StackScript(transaction_data)
        for element in unlocking_script_list:
            if element.startswith("OP"):
                class_method = getattr(StackScript, element.lower())
                class_method(stack_script)
            else:
                stack_script.push(element)
        for element in locking_script_list:
            if element.startswith("OP") or element.startswith("MP"):
                class_method = getattr(StackScript, element.lower())
                class_method(stack_script)
            else:
                stack_script.push(element)

    def validate(self,*args, **kwargs):
        NIGthreading_flag=kwargs.get('NIGthreading_flag',False)
        logging.info("Validating inputs")
        #specific case of self.inputs
        if self.inputs==[]:self.is_valid = True
        for tx_input in self.inputs:
            #Step 1 for new User of Marketplace is not Checked as we're always using the same UTXO
            if check_marketplace_step1(self.outputs) is False and check_carriage_request(self.outputs) is False:
                try:
                    #logging.info(f"tx_input: {tx_input}")
                    transaction_hash = tx_input["transaction_hash"]
                    output_index = tx_input["output_index"]
                    unlocking_public_key_hash = tx_input["unlocking_public_key_hash"]
                    if "SC " in unlocking_public_key_hash:
                        #This is a marketplace transaction, let's extract the SmartContract account
                        unlocking_public_key_hash_list=unlocking_public_key_hash.split(" ")
                        unlocking_public_key_hash=unlocking_public_key_hash_list[2]
                    try:
                        logging.info(f"transaction_hash: {transaction_hash} ")
                        locking_script = self.blockchain.get_locking_script_from_utxo(unlocking_public_key_hash,transaction_hash,output_index,NIGthreading_flag=NIGthreading_flag)
                        logging.info(f"locking_script: {locking_script}")
                    except Exception as e:
                        #self.is_valid = True
                        logging.info(f"Transaction script validation failed 0. Exception: {e}")
                        raise TransactionException(f"{transaction_hash}:{output_index}", "Could not find locking script for utxo")
                    try:
                        self.execute_script(tx_input["unlocking_script"], locking_script)
                        self.is_valid = True
                    except Exception as e:
                        logging.info(f"Transaction script validation failed 1. Exception: {e}")
                        #self.is_valid = True
                        raise TransactionException(f"UTXO ({transaction_hash}:{output_index})", "Transaction script validation failed")
                except Exception as e:
                    logging.info(f"Transaction script validation failed 2. Exception: {e}")
                    #self.is_valid = True
            else:
                #Step 1 of Marketplace is not Checked as we're always using the same UTXO
                self.is_valid = True

    def get_total_amount_in_inputs(self, **kwargs):
        NIGthreading_flag=kwargs.get('NIGthreading_flag',False)
        total_in = 0
        #Step 1 for new User of Marketplace is not Checked as we're always using the same UTXO
        if check_marketplace_step1(self.outputs) is False:
            for tx_input in self.inputs:
                unlocking_public_key_hash = tx_input["unlocking_public_key_hash"]
                if "SC " in unlocking_public_key_hash:
                    #This is a marketplace transaction, let's extract the SmartContract account
                    unlocking_public_key_hash_list=unlocking_public_key_hash.split(" ")
                    unlocking_public_key_hash=unlocking_public_key_hash_list[2]
                transaction_data = self.blockchain.get_transaction_from_utxo(unlocking_public_key_hash,tx_input["transaction_hash"],tx_input["output_index"],NIGthreading_flag=NIGthreading_flag)
                if transaction_data is not None:
                    utxo_amount = transaction_data["output"]["amount"]
                    fee_interface = transaction_data["output"]["fee_interface"]
                    fee_node = transaction_data["output"]["fee_node"]
                    fee_miner = transaction_data["output"]["fee_miner"]
                    #total_in = total_in + normal_round(utxo_amount,ROUND_VALUE_DIGIT)+ fee_interface + fee_node + fee_miner
                    total_in = total_in + normal_round(utxo_amount,ROUND_VALUE_DIGIT)
        return total_in

    def get_total_amount_in_outputs(self) -> int:
        total_out = 0
        for tx_output in self.outputs:
            amount = tx_output["amount"]
            fee_interface = tx_output["fee_interface"]
            fee_node = tx_output["fee_node"]
            fee_miner = tx_output["fee_miner"]
            total_out = total_out + amount + fee_interface + fee_node + fee_miner
            #logging.info(f"inputs:{self.inputs} total_out: {total_out}, amount {amount}, fee_interface {fee_interface}, fee_node {fee_node}, fee_miner {fee_miner}")
        return total_out

    def get_total_fee_in_outputs(self) -> int:
        total_fee = 0
        for tx_output in self.outputs:
            fee_interface = tx_output["fee_interface"]
            fee_node = tx_output["fee_node"]
            fee_miner = tx_output["fee_miner"]
            total_fee = total_fee + fee_interface + fee_node + fee_miner
        return total_fee

    def validate_funds(self, **kwargs):
        NIGthreading_flag=kwargs.get('NIGthreading_flag',False)
        logging.info("Validating funds")
        inputs_total = normal_round(self.get_total_amount_in_inputs(NIGthreading_flag=NIGthreading_flag),ROUND_VALUE_DIGIT)
        outputs_total = normal_round(self.get_total_amount_in_outputs(),ROUND_VALUE_DIGIT)
        try:
            assert inputs_total == outputs_total
            self.is_funds_sufficient = True
            logging.info("Funds are sufficient")
        except AssertionError:

            logging.info(f"Transaction inputs and outputs did not match: inputs ({inputs_total}), outputs ({outputs_total})")
            logging.info(f"Transaction data: ({self.transaction_data})")
            raise TransactionException(f"inputs ({inputs_total}), outputs ({outputs_total})",
                                       "Transaction inputs and outputs did not match")

    def broadcast_to_leader_node(self):
        logging.info("Broadcasting to leader nodes")
        #node_list = self.known_node_memory.known_nodes
        leader_node_schedule = self.leader_node_schedule_memory.leader_node_schedule
        #only the first epoch (leader_node_schedule[0]) is taken into account
        epoch=leader_node_schedule[0]
        #the transaction is sent in advance to other leader node to ensure a smooth transition between leader node
        leader_node_flag=False
        leader_node_count=0
        hostname_list=[]
        for node_dic in epoch['LeaderNodeList']:
            if node_dic['already_processed']==False:
                leader_node_flag=True
                leader_node_count+=1
                logging.info(f"###leader_node_count: {leader_node_count}")
                if node_dic['node'].hostname != self.hostname and node_dic['node'].hostname != self.sender and node_dic['node'].hostname not in hostname_list:
                    hostname_list.append(node_dic['node'].hostname)
                    if leader_node_count==1:
                        #this is the leader node
                        try:
                            logging.info(f"Broadcasting to leader node {node_dic['node'].hostname}")
                            node_dic['node'].send_transaction_to_leader_node({"transaction": self.transaction_data})
                            #the transaction is sent only to the leader node
                        except requests.ConnectionError:
                            logging.info(f"Failed broadcasting to leader node {node_dic['node'].hostname}")

                    else:
                        #this is the leader node in advance
                        try:
                            logging.info(f"Broadcasting to leader node in advance {node_dic['node'].hostname}")
                            #node_dic['node'].send_transaction_to_leader_node_advance({"transaction": self.transaction_data})
                            #the transaction is sent to the leader node in advance
                        except requests.ConnectionError:
                            logging.info(f"Failed broadcasting to leader node in advance {node_dic['node'].hostname}")
                if leader_node_count==2:break

    def store(self):
        if self.is_valid and self.is_funds_sufficient:
            logging.info("Storing transaction data in memory")
            #logging.info(f"###INFO Transaction data: {self.transaction_data}")
            current_transactions = self.mempool.get_transactions_from_memory()
            current_transactions.append(self.transaction_data)
            self.mempool.store_transactions_in_memory(current_transactions)

    def add_to_PoH(self,PoH):
        if self.is_valid and self.is_funds_sufficient:
            logging.info("Adding transaction to PoH")
            transaction_bytes = json.dumps(self.transaction_data, indent=2)
            PoH.input(calculate_hash(transaction_bytes))

    def validate_smart_contract(self,smart_contract_index_list,*args, **kwargs):
        leader_node_flag=kwargs.get('leader_node_flag',False)
        #if self.is_valid and self.is_funds_sufficient:
        logging.info("Validating Smart Contract")
        #logging.info(f"smart_contract_index_list: {smart_contract_index_list}")
        index=0
        input_list=[]
        output_list=[]
        for i in range(len(self.outputs)):
            transaction_out_temp=None
            #logging.info("Validating Smart Contract 1")
            if index in smart_contract_index_list:
                #logging.info("Validating Smart Contract 2")
                smart_contract_account=self.outputs[i]['smart_contract_account']
                smart_contract_previous_transaction=self.outputs[i]['smart_contract_previous_transaction']

                try:marketplace_transaction_flag=self.outputs[i]['marketplace_transaction_flag']
                except:marketplace_transaction_flag=False
                if marketplace_transaction_flag=="false" or marketplace_transaction_flag=="False":marketplace_transaction_flag=False
                try:
                    smart_contract_account=self.outputs[i]['smart_contract_account']
                    NIGthreading_flag=False
                    if leader_node_flag is True:
                        #if 5==5:
                        if smart_contract_account=="31f2ac8088005412c7b031a6e342b17a65a48d01" and marketplace_transaction_flag is False and check_marketplace_step2(self.outputs[i]) is False or "BlockVote" in str(self.outputs[i]):
                            logging.info("====> BlockVote transaction input update")
                            #smart_contract_previous_transaction is loaded dynamically to keep chaining with high volume
                            #if smart_contract_account=="31f2ac8088005412c7b031a6e342b17a65a48d01":
                            old_smart_contract_previous_transaction,smart_contract_previous_transaction,smart_contract_transaction_output_index=load_smart_contract_from_master_state(smart_contract_account,leader_node_flag=leader_node_flag,NIGthreading_flag=True)
                            if smart_contract_previous_transaction is not None:
                                self.outputs[i]['smart_contract_previous_transaction']=smart_contract_previous_transaction
                                logging.info(f"###########Validating Smart Contract account: {smart_contract_account} previous_transaction:{smart_contract_previous_transaction} old_previous_transaction:{old_smart_contract_previous_transaction}")
                                #only for the marketplace
                            
                                from common.transaction_input import TransactionInput
                                from common.transaction_output import TransactionOutput
                                from common.transaction import Transaction as NewTransaction
                                from node.main import marketplace_owner
                            
                                if "BlockVote" in str(self.outputs[i]):
                                    input_list.append(TransactionInput(transaction_hash=smart_contract_previous_transaction[0:64],
                                                                    output_index=smart_contract_transaction_output_index,
                                                                    unlocking_public_key_hash=marketplace_owner.public_key_hash+" SC "+smart_contract_account))
                                    transaction_out_temp=TransactionOutput(list_public_key_hash=[smart_contract_account],
                                                                        amount=self.outputs[i]['amount'])
                                else:
                                    input_list.append(TransactionInput(transaction_hash=smart_contract_previous_transaction[0:64],
                                                                    output_index=smart_contract_transaction_output_index,
                                                                    unlocking_public_key_hash=marketplace_owner.public_key_hash))
                                    transaction_out_temp=TransactionOutput(list_public_key_hash=[marketplace_owner.public_key_hash],
                                                                            amount=self.outputs[i]['amount'])
                                
                                #logging.info(f"====> self.outputs[i].keys(): {self.outputs[i].keys()}")
                                for attribut in self.outputs[i].keys():
                                    setattr(transaction_out_temp,attribut,self.outputs[i][attribut])

                                setattr(transaction_out_temp,'smart_contract_previous_transaction',smart_contract_previous_transaction)

                                output_list.append(transaction_out_temp)

                                NIGthreading_flag=True

                            else:
                                self.is_smart_contract_valid = False
                                #raise TransactionException(f"Smart Contract validation failed during load_smart_contract_from_master_state: {smart_contract_account}")
                                logging.info(f"Smart Contract validation failed during load_smart_contract_from_master_state: {smart_contract_account}")
        
                    smart_contract_sender=self.outputs[i]['smart_contract_sender']
                    smart_contract_new=self.outputs[i]['smart_contract_new']
                    smart_contract_gas=self.outputs[i]['smart_contract_gas']
                    smart_contract_memory=self.outputs[i]['smart_contract_memory']
                    smart_contract_memory_size=self.outputs[i]['smart_contract_memory_size']
                    smart_contract_type=self.outputs[i]['smart_contract_type']
                    smart_contract_payload=self.outputs[i]['smart_contract_payload']
                    smart_contract_result=self.outputs[i]['smart_contract_result']
                    #smart_contract_transaction_hash is not provided as it's not store on the Blockchain at the SmartContract Level
                    smart_contract=SmartContract(smart_contract_account,
                                                    smart_contract_sender=smart_contract_sender,
                                                    smart_contract_new=smart_contract_new,
                                                    smart_contract_gas=smart_contract_gas,
                                                    smart_contract_memory=smart_contract_memory,
                                                    smart_contract_memory_size=smart_contract_memory_size,
                                                    smart_contract_type=smart_contract_type,
                                                    payload=smart_contract_payload,
                                                    smart_contract_previous_transaction=smart_contract_previous_transaction,
                                                    leader_node_flag=leader_node_flag,
                                                    NIGthreading_flag=NIGthreading_flag)
                    #logging.info(f"smart_contract_sender: {smart_contract_sender}")
                    #logging.info(f"smart_contract_new: {smart_contract_new}")
                    #logging.info(f"smart_contract_account: {smart_contract_account}")
                    logging.info(f"smart_contract_gas: {smart_contract_gas}")
                    logging.info(f"smart_contract_memory_size: {smart_contract_memory_size}")
                    logging.info(f"smart_contract_type: {smart_contract_type}")
                    logging.info(f"check smart_contract_previous_transaction: {smart_contract_previous_transaction}")
                    smart_contract.process()
                    if smart_contract.error_flag is False:
                        if smart_contract.smart_contract_memory==[] or smart_contract.smart_contract_memory is None:
                            logging.info(f"smart_contract_memory: {smart_contract_memory}")
                            logging.info(f"smart_contract_payload: {smart_contract_payload}")
                            self.is_smart_contract_valid = False
                            raise TransactionException(f"smart_contract.result ({smart_contract.result})",
                                                            "Smart Contract validation failed due to smart_contract_memory issue")

                        #if "NIGthreading" in str(self.outputs[i]):
                        #if 5==5:
                        if leader_node_flag is True and "BlockVote" in str(self.outputs[i]):
                            self.outputs[i]['smart_contract_memory']=smart_contract.smart_contract_memory
                            if transaction_out_temp is not None:setattr(transaction_out_temp,'smart_contract_memory',smart_contract.smart_contract_memory)
                            pass

                        #check if the API call needs to be stored on the blockain
                        self.api_readonly_flag=smart_contract.api_readonly_flag
                        logging.info(f"smart_contract_result: {smart_contract_result}")
                        if smart_contract_result is not None:
                            try:
                                assert smart_contract_result == smart_contract.result
                                logging.info("Smart Contract is validated")
                            except AssertionError:
                                logging.info(f"Smart Contract validation did not match: ({smart_contract_result}), smart_contract.result ({smart_contract.result})")
                                self.is_smart_contract_valid = False
                                raise TransactionException(f"smart_contract_result ({smart_contract_result}), smart_contract.result ({smart_contract.result})",
                                                        "Smart Contract validation failed")
                    else:
                        logging.info(f"**** ISSUE validate_smart_contract1: {smart_contract_account}")
                        logging.info(f"**** ISSUE: {smart_contract.error_code}")
                        self.is_smart_contract_valid = False
                                
                except Exception as e:
                    logging.info(f"**** ISSUE validate_smart_contract2: {smart_contract_account} => {e}")
                    logging.exception(e)
                    self.is_smart_contract_valid = False

            index+=1
                
        if input_list!=[]:
            #the input list needs to be revised (ex: BlockVote,..)
            #smart_contract_timestamp needs to be considered to avoid signature issue
            new_transaction = NewTransaction(input_list, output_list,smart_contract_timestamp=self.timestamp)
            new_transaction.sign(marketplace_owner)
            self.inputs=[]
            for i in range(len(new_transaction.inputs)):
                self.inputs.append(new_transaction.inputs[i].to_dict())
            self.outputs=[]
            for i in range(len(new_transaction.outputs)):
                self.outputs.append(new_transaction.outputs[i].to_dict())
            self.transaction_data["inputs"]=self.inputs
            self.transaction_data["outputs"]=self.outputs

