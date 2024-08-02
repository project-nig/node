from ast import Pass
import os
import logging
import json
import time
import requests
import json
import binascii

from Crypto.Signature import pkcs1_15
import Crypto.PublicKey.RSA as RSA

from common.block import Block, BlockHeader, BlockPoH
from common.io_mem_pool import MemPool
from common.master_state import MasterState
from common.io_known_nodes import KnownNodesMemory
from common.io_blockchain import BlockchainMemory
from common.values import NUMBER_OF_LEADING_ZEROS, BLOCK_REWARD,ROUND_VALUE_DIGIT
from node.transaction_validation.transaction_validation import Transaction
from common.utils import normal_round,check_contest_refresh_score
from common.io_leader_node_schedule import LeaderNodeScheduleMemory
from common.smart_contract import SmartContract,check_smart_contract, load_smart_contract_from_master_state
from common.smart_contract_script import block_script

from common.transaction_input import TransactionInput
from common.transaction_output import TransactionOutput
from blockchain_users.interface import public_key_hash as interface_public_key_hash
from blockchain_users.marketplace import public_key_hash as marketplace_public_key_hash

from common.master_state_readiness import master_state_readiness
from common.proof_of_history import ProofOfHistory
from blockchain_users.node import public_key_hex as node_public_key_hex


class NewBlockException(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class NewBlock:
    """
    Class to validate a new block.
    """
    def __init__(self, blockchain: Block,  hostname: str):
        from common.values import STORAGE_DIR,NEW_BLOCKCHAIN_DIR_BACKLOG
        self.STORAGE_DIR=STORAGE_DIR
        self.NEW_BLOCKCHAIN_DIR_BACKLOG=NEW_BLOCKCHAIN_DIR_BACKLOG
        self.blockchain = blockchain
        self.new_block = None
        self.sender = ""
        self.mempool = MemPool()
        self.known_nodes_memory = KnownNodesMemory()
        self.blockchain_memory = BlockchainMemory()
        self.leader_node_schedule_memory=LeaderNodeScheduleMemory()
        self.master_state=MasterState()
        self.hostname = hostname
        self.is_valid = True
        self.refresh_score_list=[]

    def receive(self, new_block: dict, sender: str):
        """
        Validation of the block hash and Hash of PoH of the previous block
        raise an Error in case of issue
        Otherwise nothing.
        """
        block_header = BlockHeader(**new_block["header"])
        block_PoH = BlockPoH(**new_block["PoH"])
        
        self.new_block = Block(transactions=new_block["transactions"], block_header=block_header, block_PoH=block_PoH, block_signature=new_block["signature"])
        self.sender = sender
        previous_block_PoH_hash=None
        previous_block_hash=None
        try:
            previous_block_PoH_hash=self.new_block.block_header.previous_PoH_hash
            previous_block_filename,previous_block=self.retrieve_block_detail(previous_block_PoH_hash)
            if previous_block is not None:
                previous_block_hash=previous_block.block_header.hash
                assert previous_block_hash == self.new_block.block_header.previous_block_hash
        except AssertionError:
            logging.info(f"###ERROR: Previous block hash:{previous_block_hash} in block_PoH:{previous_block_PoH_hash} provided is not valid: {self.new_block.block_header.previous_block_hash} in the most recent block_PoH: {self.new_block.block_header.current_PoH_hash}")
            raise NewBlockException("", f"Previous block hash:{previous_block_hash} in block_PoH:{previous_block_PoH_hash} provided is not valid: {self.new_block.block_header.previous_block_hash} in the most recent block_PoH: {self.new_block.block_header.current_PoH_hash}")
        except Exception as e:
            logging.info(f"###ERROR during validation of Hash. Previous block hash:{previous_block_hash} in block_PoH:{previous_block_PoH_hash} provided is not valid: {self.new_block.block_header.previous_block_hash} in the most recent block_PoH: {self.new_block.block_header.current_PoH_hash}")
            logging.exception(e)
            raise NewBlockException("", f"###ERROR during validation of Hash of block_PoH: {self.new_block.block_header.current_PoH_hash}")
        

    def validate(self,master_state_readiness):
        '''Launch several validations (hash, signature, PoH & Transactions) of the block
        return self.is_valid = False if issue
        Otherwise nothing
        '''
        self._validate_hash()
        self._validate_signature()
        self._validate_PoH()
        self._validate_transactions(master_state_readiness)

    def _validate_hash(self):
        '''Validate the hash of the block
        return self.is_valid = False if issue
        Otherwise nothing
        '''
        new_block_hash = self.new_block.block_header.get_hash()
        number_of_zeros_string = "".join([str(0) for _ in range(NUMBER_OF_LEADING_ZEROS)])
        print(f'new_block_hash:{new_block_hash},{number_of_zeros_string}')
        try:
            assert new_block_hash.startswith(number_of_zeros_string)
        except AssertionError:
            logging.info('Proof of work validation failed')
            self.is_valid=False
            #raise NewBlockException("", "Proof of work validation failed")

    def _validate_signature(self):
        '''Validate the signature of the leader
        return self.is_valid = False if issue
        Otherwise nothing
        '''
        new_block_signature = self.new_block.block_signature
        block_signature_hash=self.new_block.signature_hash()
        from node.main import network
        node_network_account=network.node_network_account
        
        smart_contract_previous_transaction,smart_contract_transaction_hash,smart_contract_transaction_output_index=load_smart_contract_from_master_state(node_network_account.public_key_hash)
        if smart_contract_transaction_hash is not None:
            #logging.info(f"self.new_block.block_header.leader_node_public_key_hash:{self.new_block.block_header.leader_node_public_key_hash}")
            payload=f'''
node_public_key_hash="{self.new_block.block_header.leader_node_public_key_hash}"
memory_obj_2_load=['node_network']
node_network.get_public_key_hex(node_public_key_hash)
'''
            #logging.info(f"###:node_network_account.public_key_hash:{node_network_account.public_key_hash}")
            #logging.info(f"###:payload:{payload}")
            node_public_key_hex=self.process_smart_contract(node_network_account.public_key_hash,payload,smart_contract_transaction_hash,False)
            #logging.info(f"###:node_public_key_hex:{node_public_key_hex}")
            node_public_key_bytes=node_public_key_hex.encode("utf-8")
            node_public_key_object = RSA.import_key(binascii.unhexlify(node_public_key_bytes))
            #logging.info(f"###:block_signature_hash:{block_signature_hash.hexdigest()}")
            #logging.info(f"###:new_block_signature:{new_block_signature}")
            try:
                pkcs1_15.new(node_public_key_object).verify(block_signature_hash, binascii.unhexlify(new_block_signature.encode("utf-8")))
                logging.info(f"Validation of block signature with success !!")
            except Exception as e:
                logging.info(f'#ISSUE : block signature verification failed. block PoH: {self.new_block.block_header.current_PoH_hash} ')
                logging.exception(e)
                self.is_valid=False

        else:
            logging.info(f'#ISSUE : block signature verification failed. Impossible to retrive node_public_key_hex. block PoH: {self.new_block.block_header.current_PoH_hash} ')
            self.is_valid=False



    def _validate_PoH(self):
        """
        Validate the PoH of the block
        return self.is_valid = False if issue
        Otherwise nothing.
        """
        #STEP 1 - Validation of PoH_registry_input_data
        PoH_registry_input_data = self.new_block.block_PoH.PoH_registry_input_data
        start = time.time()
        PoH_validation=ProofOfHistory()
        #logging.info(f"registry_input_data {PoH_validation.registry_input_data}")
        PoH_validation.validate_PoH_registry(PoH_registry_input_data)
        check=PoH_validation.get_validation_status()
        if check==False:
            logging.info(f"###ERROR: Validation block_PoH_registry_input_data without success !!")
            self.is_valid=False
        else:logging.info(f"Validation block_PoH_registry_input_data with success")
        #logging.info(f"registry_intermediary {PoH_validation.registry_intermediary}")
        #PoH_validation.stop()
        end = time.time()
        logging.info(f"Validation block_PoH_registry_input_data operation:{end-start} sec")
        
        #STEP 2 - Validation of PoH_registry_intermediary
        PoH_registry_intermediary = self.new_block.block_PoH.PoH_registry_intermediary
        start = time.time()
        PoH_validation=ProofOfHistory()
        #logging.info(f"registry_input_data {PoH_validation.registry_input_data}")
        PoH_validation.validate_PoH_registry_intermediary(PoH_registry_intermediary)
        check=PoH_validation.get_validation_status()
        if check==False:
            logging.info(f"###ERROR: Validation block_PoH_registry_intermediary without success !!")
            self.is_valid=False
        else:logging.info(f"Validation block_PoH_registry_intermediary with success")
        #logging.info(f"registry_intermediary {PoH_validation.registry_intermediary}")
        #PoH_validation.stop()
        end = time.time()
        logging.info(f"Validation block_PoH_registry_intermediary operation:{end-start} sec")

    

    def _validate_transactions(self,master_state_readiness):
        """
        validate the total input & total output amount of all transactions
        return self.is_valid = False if issue
        Otherwise nothing.
        """
        input_amount = 0
        output_amount = 0
        

        #sorting of Transaction per timestamp
        self.new_block.transactions==sorted(self.new_block.transactions, key=lambda x: x['timestamp'])

        for transaction in self.new_block.transactions:
            transaction_validation = Transaction(self.blockchain, self.hostname)
            transaction_validation.receive(transaction=transaction)
            #Check that transaction output is not empty
            if transaction_validation.validate_output_not_empty() == True:
                import logging
                #logging.info(f"####transaction_data: {transaction_validation.transaction_data}")
                #logging.info(f"####transaction _validate_funds: {transaction}")
            
                smart_contract_flag,smart_contract_index_list=check_smart_contract(transaction_validation)
                if smart_contract_flag:
                    #there are smart contract in the transaction, let's validate them
                    #input UTXO can be change so transaction_validation.validate() can only happen after 
                    transaction_validation.validate_smart_contract(smart_contract_index_list,leader_node_flag=False)

                transaction_validation.validate()

                if transaction_validation.is_valid is False or transaction_validation.is_smart_contract_valid is False:
                    #Error with the validation of the transaction
                    #The block cannot be validated
                    self.is_valid=False
                    transaction_hash=transaction_validation.transaction_data["transaction_hash"]
                    if transaction_validation.is_valid is False:logging.info(f"###ERROR BLOCK RECEIVING with Transaction validation {transaction_hash}")
                    if transaction_validation.is_smart_contract_valid is False:logging.info(f"###ERROR BLOCK RECEIVING with Transaction SmartContract validation {transaction_hash}")
                else:
                    if 5==6:
                        #check if the Contest Score need to be refreshed
                        new_refresh_score_list=check_contest_refresh_score(transaction_validation.transaction_data)
                        for account in new_refresh_score_list:
                            if account not in self.refresh_score_list:self.refresh_score_list.append(account)

                input_amount = input_amount + transaction_validation.get_total_amount_in_inputs()
                output_amount = output_amount + transaction_validation.get_total_amount_in_outputs()
                output_amount = output_amount - transaction_validation.get_total_fee_in_outputs()
                import logging
                #logging.info(f"##### output_amount {output_amount} input:{transaction_validation.inputs} ouput:{transaction_validation.outputs} transaction_data:{transaction_validation.transaction_data} output:{transaction_validation.outputs}")
            
                #storing in a temporay master state
                master_state_temp=MasterState(temporary_save_flag=True)
                #let's block MasterState
                #while master_state_readiness.block() is False:
                #    #let's wait until MasterState is released by another thread
                #    pass

                try:
                    master_state_temp.update_master_state(transaction_validation.transaction_data,self.new_block.block_header.current_PoH_hash,previous_PoH_hash=self.new_block.block_header.previous_PoH_hash)
                    master_state_temp.store_master_state_in_memory(self.new_block.block_header.current_PoH_hash)
                except Exception as e:
                    #issue with the SmartContract
                    self.is_valid=False
                    logging.info(f"###ERROR BLOCK RECEIVING with update_master_state of SmartContract. Exception: {e}")
                    logging.exception(e)

                #let's release MasterState
                #master_state_readiness.release()

            
        if self._validate_funds(input_amount, output_amount) is False:
            self.is_valid=False
            logging.info(f"###ERROR BLOCK RECEIVING with funds validation")


    @staticmethod
    def _validate_funds(input_amount: float, output_amount: float):
        import logging
        #logging.info(f"input_amount: {input_amount} {type(input_amount)}+ BLOCK_REWARD:{BLOCK_REWARD} {type(BLOCK_REWARD)} == output_amount:{output_amount} {type(output_amount)}")
        #assert round(1.01000000,2) + round(1,2) == round(2,2)
        test1=normal_round(float(normal_round(float(input_amount),ROUND_VALUE_DIGIT) + normal_round(float(BLOCK_REWARD),ROUND_VALUE_DIGIT)),ROUND_VALUE_DIGIT)
        test2=normal_round(float(output_amount),ROUND_VALUE_DIGIT)
        test3=test1==test2
        logging.info(f"test1: {test1} test2: {test2} test3: {test3}")
        validate_funds_check=True
        if normal_round(float(normal_round(float(input_amount),ROUND_VALUE_DIGIT) + normal_round(float(BLOCK_REWARD),ROUND_VALUE_DIGIT)),ROUND_VALUE_DIGIT) != normal_round(float(output_amount),ROUND_VALUE_DIGIT):
            validate_funds_check=False
        return validate_funds_check
            
        

    def add_in_backlog(self,master_state_readiness):
        """
        store the block in a file in blockchain_backlog folder.
        """
        self.new_block.previous_block = self.blockchain
        self.blockchain_memory.store_block_in_blockchain_in_backlog(self.new_block,master_state_readiness)

    def clear_block_transactions_from_mempool(self):
        current_transactions = self.mempool.get_transactions_from_memory()
        transactions_cleared = [i for i in current_transactions if not (i in self.new_block.transactions)]
        self.mempool.store_transactions_in_memory(transactions_cleared)
        

    def vote(self,smart_contract_account,leader_node_flag):
        payload=f'''
#NIGthreading
node="{self.hostname}"
memory_obj_2_load=['block_vote']
block_vote.vote(node)
memory_list.add([block_vote,'block_vote',['block_PoH','vote_list','slash_list','validated']])
123456
'''
        self.raw_transaction(payload,smart_contract_account,leader_node_flag)

    def slash(self,smart_contract_account,leader_node_flag):
        payload=f'''
#NIGthreading
node="{self.hostname}"
memory_obj_2_load=['block_vote']
block_vote.slash(node)
memory_list.add([block_vote,'block_vote',['block_PoH','vote_list','slash_list','validated']])
123456
'''
        self.raw_transaction(payload,smart_contract_account,leader_node_flag)

    def validate_block_in_blockchain(self,smart_contract_account,leader_node_flag):
        payload=f'''
#NIGthreading
node="{self.hostname}"
memory_obj_2_load=['block_vote']
block_vote.validated=True
memory_list.add([block_vote,'block_vote',['block_PoH','vote_list','slash_list','validated']])
123456
'''
        self.raw_transaction(payload,smart_contract_account,leader_node_flag)

    def slash_block_in_blockchain(self,smart_contract_account,leader_node_flag):
        payload=f'''
#NIGthreading
node="{self.hostname}"
memory_obj_2_load=['block_vote']
block_vote.validated=False
memory_list.add([block_vote,'block_vote',['block_PoH','vote_list','slash_list','validated']])
123456
'''
        self.raw_transaction(payload,smart_contract_account,leader_node_flag)

    def raw_transaction(self,payload,smart_contract_account,leader_node_flag):
        try:
            #from node.main import smart_contract_wallet
            from node.main import smart_contract_owner
            from common.values import FIRST_KNOWN_NODE_HOSTNAME_LIST
            from wallet.wallet import Owner, Wallet
            from common.node import Node
            smart_contract_wallet_node=FIRST_KNOWN_NODE_HOSTNAME_LIST[0]

            smart_contract_wallet = Wallet(smart_contract_owner,Node(smart_contract_wallet_node))
            #retrieval of previous block_vote SmartContract information
            smart_contract_public_key_hash=smart_contract_account
            smart_contract_previous_transaction,smart_contract_transaction_hash,smart_contract_transaction_output_index=load_smart_contract_from_master_state(smart_contract_public_key_hash,
                                                                                                                                                              leader_node_flag=leader_node_flag,
                                                                                                                                                              block_PoH=smart_contract_public_key_hash)
            if smart_contract_transaction_hash is not None:
                blockchain_base = self.blockchain_memory.get_blockchain_from_memory()
                utxo_dict=blockchain_base.get_user_utxos_balance(smart_contract_public_key_hash)
                from common.smart_contract import load_smart_contract_from_master_state_leader_node

                utxo=load_smart_contract_from_master_state_leader_node(smart_contract_public_key_hash,smart_contract_transaction_hash=smart_contract_transaction_hash,leader_node_flag=leader_node_flag)

                #logging.info(f'===> raw_vote utxo_dict:{utxo}')
                input_list=[]
                output_list=[]
                smart_contract=SmartContract(smart_contract_public_key_hash,
                                                smart_contract_sender='sender_public_key_hash2',
                                                smart_contract_type="source",
                                                payload=payload,
                                                smart_contract_previous_transaction=smart_contract_transaction_hash,
                                                smart_contract_transaction_hash=smart_contract_transaction_hash,
                                                block_PoH=smart_contract_public_key_hash)

                check_vote=smart_contract.process()
                if smart_contract.error_flag is False:
                    input_list.append(TransactionInput(transaction_hash=smart_contract_transaction_hash, output_index=utxo['output_index'],
                                                        unlocking_public_key_hash=marketplace_public_key_hash+" SC "+smart_contract_public_key_hash))
                    output_list.append(TransactionOutput(list_public_key_hash=[smart_contract_public_key_hash], 
                                                            amount=0,
                                                            interface_public_key_hash=interface_public_key_hash,
                                                            smart_contract_account=smart_contract.smart_contract_account,
                                                            smart_contract_sender=smart_contract.smart_contract_sender,
                                                            smart_contract_new=smart_contract.smart_contract_new,
                                                            smart_contract_flag=True,
                                                            smart_contract_gas=smart_contract.gas,
                                                            smart_contract_memory=smart_contract.smart_contract_memory,
                                                            smart_contract_memory_size=smart_contract.smart_contract_memory_size,
                                                            smart_contract_type=smart_contract.smart_contract_type,
                                                            smart_contract_payload=smart_contract.payload,
                                                            smart_contract_result=smart_contract.result,
                                                            smart_contract_previous_transaction=smart_contract.smart_contract_previous_transaction,
                                                            smart_contract_transaction_hash=smart_contract.smart_contract_transaction_hash,
                                                            account_temp=True))
                    smart_contract_wallet.process_transaction(inputs=input_list, outputs=output_list)
                else:
                    logging.info(f"**** ISSUE raw_transaction failure1: {smart_contract_account}")
                    logging.info(f"**** ISSUE: {smart_contract.error_code}")
            else:
                raise ValueError(f"**** ISSUE raw_transaction failure2: {smart_contract_account} smart_contract_previous_transaction: {smart_contract_previous_transaction}")
        except Exception as e:
                logging.info(f"**** ISSUE vote/slash block_vote: {smart_contract_account}")
                logging.info(f"**** ISSUE vote/slash leader_node_flag: {leader_node_flag}")
                logging.info(f"**** ISSUE vote/slash smart_contract_previous_transaction: {smart_contract_previous_transaction}")
                logging.info(f"**** ISSUE vote/slash payload: {payload}")
                logging.exception(e)
                self.is_smart_contract_valid = False

    def manage_vote_book(self,action,block_PoH):
        #this function is saving the vote per block_PoH
        #action => vote : to vote on a block_PoH
        #action => slash : to slash a block_PoH
        #action => delete : to delete the vote of a block_PoH
        #action => read : to read the vote of a block_PoH
        filename='vote_book'
        vote_book_filename=self.STORAGE_DIR+self.NEW_BLOCKCHAIN_DIR_BACKLOG+f"/{filename}"
        try:
            with open(vote_book_filename, "rb") as file_obj:
                vote_book_str = file_obj.read()
                vote_book_data = json.loads(vote_book_str)
        except:
            vote_book_data={}
        if action=="delete":
            #deletion of the vote in vote book 
            vote_book_data.pop(block_PoH, None)
        elif action=="read":
            #reading of the vote in vote book 
            vote_value=None
            try:vote_value=vote_book_data[block_PoH]
            except:pass
            return vote_value
        else:
            #saving of the vote in vote book
            vote_book_data[block_PoH]=action
        
        text = json.dumps(vote_book_data).encode("utf-8")
        with open(vote_book_filename, "wb") as file_obj:
            file_obj.write(text)



      
    def check_vote_and_backlog(self,master_state_readiness,*args, **kwargs):
        """
        vote and check the backlog of block 
        to include them if needed on the blockchain
        """
        leader_node_flag = kwargs.get('leader_node_flag',False)
        new_block_2_exclude = kwargs.get('new_block_2_exclude',None)
        latest_received_block = kwargs.get('latest_received_block',None)
        received_block_2_slash = kwargs.get('received_block_2_slash',None)
        from common.values import NEW_BLOCKCHAIN_DIR_SLASHED_NB_SLOT_BEFORE_ARCHIVE,NEW_BLOCKCHAIN_DIR_NB_SLOT_BEFORE_BLOCKCHAIN,NEW_BLOCKCHAIN_DIR_NB_SLOT_BEFORE_REVOTE
        from common.consensus_blockchain import consensus_blockchain

        #STEP 1
        if received_block_2_slash is not None:
            #a new received block is invalid and needs to be Slashed
            logging.info(f"WARNING block {received_block_2_slash} is slashed !!!")
            self.manage_vote_book("slash",received_block_2_slash)
            #self.slash(received_block_2_slash,leader_node_flag)
        else:
            #a new received block is valid and needs to be voted
            logging.info(f"INFO block {latest_received_block} is vote !!!")
            self.manage_vote_book("vote",latest_received_block)
            #self.vote(latest_received_block,leader_node_flag)
            #self.vote(latest_received_block,leader_node_flag)
        
        #STEP 2
        #this function check the vote for each block in backlog
        #if vote is not yet done, then it vote for the block
        #if vote_ratio is accepted, then it inserts it in the final BlockChain
        directory = os.fsencode(self.STORAGE_DIR+self.NEW_BLOCKCHAIN_DIR_BACKLOG)
        leader_node_schedule=LeaderNodeScheduleMemory()
        current_leader_node_slot=leader_node_schedule.current_leader_node_slot
        backlog_block_list=[]
        backlog_block_list_updated=[]
        backlog_block_list_removed=[]
        block_list_to_archive_ASAP=[]
        
        #STEP 3 list all the block in the backlog
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if filename!="last_block_pointer" and filename!="vote_book" and filename!=received_block_2_slash:
                backlog_block_list.append(filename)
                backlog_block_list_updated.append(filename)

        #STEP 4 management of VALIDATOR Node
        if leader_node_flag is False:
            for filename in backlog_block_list:
                block_PoH=filename
                if block_PoH in backlog_block_list_updated:
                    #the filename is the block PoH hash
                    smart_contract_previous_transaction,smart_contract_transaction_hash,smart_contract_transaction_output_index=load_smart_contract_from_master_state(block_PoH,
                                                                                                                                                                      leader_node_flag=leader_node_flag,
                                                                                                                                                                      block_PoH=block_PoH)
                    if smart_contract_transaction_hash is not None:
                        payload=f'''
node="{self.hostname}"
memory_obj_2_load=['block_vote']
block_vote.is_validated(node)
'''
                        block_is_validated=self.process_smart_contract(block_PoH,payload,smart_contract_transaction_hash,leader_node_flag)
                        if block_is_validated=="True": block_is_validated=True
                        if block_is_validated=="False": block_is_validated=False
                        if block_is_validated=="None": block_is_validated=None
                        logging.info(f'===> block {block_PoH} validation by validator node:{block_is_validated}')
                
                        #STEP 4-1 check if a block needs to be added
                        block_filename,block_to_save=self.retrieve_block_detail(block_PoH)
                        if block_to_save is not None:
                            block_slot=block_to_save.block_header.slot
                            logging.info(f'===> current_leader_node_slot:{current_leader_node_slot} block_slot {block_slot} NEW_BLOCKCHAIN_DIR_NB_SLOT_BEFORE_BLOCKCHAIN:{NEW_BLOCKCHAIN_DIR_NB_SLOT_BEFORE_BLOCKCHAIN}')
                            logging.info(f'===> block_is_validated is:{block_is_validated is True} current_leader_node_slot:{current_leader_node_slot} test2 {block_slot+NEW_BLOCKCHAIN_DIR_NB_SLOT_BEFORE_BLOCKCHAIN} test3:{current_leader_node_slot>block_slot+NEW_BLOCKCHAIN_DIR_NB_SLOT_BEFORE_BLOCKCHAIN} ')
                            if block_is_validated is True and current_leader_node_slot>block_slot+NEW_BLOCKCHAIN_DIR_NB_SLOT_BEFORE_BLOCKCHAIN:
                                logging.info(f'===> check1')
                                for backlog_chain_list_counter in consensus_blockchain.backlog_chain_list.keys():
                                    try:
                                        backlog_chain_list=consensus_blockchain.backlog_chain_list[backlog_chain_list_counter]['list']
                                        #remove the 1st element as the block is not in the Backlog
                                        #but already in the BlockChain
                                        backlog_chain_list.pop(0)
                                        logging.info(f'===> block_PoH:{block_PoH} backlog_chain_list {backlog_chain_list} backlog_block_list_updated:{backlog_block_list_updated} ')
                                        if block_PoH in backlog_chain_list and block_PoH in backlog_block_list_updated:
                                            logging.info(f'===> check2')
                                            #all the block_PoH prior to the current block_PoH needs to be validated and added to the BlockChain
                                            for i in range(0,len(backlog_chain_list)):
                                                logging.info(f'===> check 3:{i}')
                                                block_PoH_2_check=backlog_chain_list[i]
                                                if block_PoH_2_check==block_PoH:
                                                    backlog_block_list_updated.remove(block_PoH_2_check)
                                                    break
                                                #retrieve block detail
                                                block_filename,block_to_save=self.retrieve_block_detail(block_PoH_2_check)
                                                if block_to_save is not None:
                                                    #the block is added to the blockchain
                                                    #self.add_block_in_blockchain(filename,block_filename,block_to_save,latest_received_block)
                                                    self.add_block_in_blockchain(filename,block_filename,block_to_save,block_PoH_2_check)
                                    except Exception as e:
                                        logging.info(f"INFO consensus_blockchain.backlog_chain_list1: {e}")
                                        logging.exception(e)
                                    
                                #add the received block in last to ensure that the last_block_pointer is pointing to it
                                block_filename,block_to_save=self.retrieve_block_detail(block_PoH)
                                #if block_to_save is not None:self.add_block_in_blockchain(filename,block_filename,block_to_save,latest_received_block)
                                if block_to_save is not None:self.add_block_in_blockchain(filename,block_filename,block_to_save,block_PoH)
                        
                                
                                
                #STEP 4-2 management of vote after several slots to avoid overloading of vote
                #if block_is_validated is False and filename!=new_block_2_exclude and current_leader_node_slot>block_slot+NEW_BLOCKCHAIN_DIR_NB_SLOT_BEFORE_REVOTE:
                if block_is_validated is None and filename!=latest_received_block and filename!=new_block_2_exclude:
                    smart_contract_previous_transaction,smart_contract_transaction_hash,smart_contract_transaction_output_index=load_smart_contract_from_master_state(block_PoH,
                                                                                                                                                                      leader_node_flag=leader_node_flag,
                                                                                                                                                                      block_PoH=block_PoH)
                    if smart_contract_transaction_hash is not None:
                        payload=f'''
node="{self.hostname}"
memory_obj_2_load=['block_vote']
block_vote.check_vote(node)
'''
                        check_vote=self.process_smart_contract(block_PoH,payload,smart_contract_transaction_hash,leader_node_flag)
                        logging.info(f'===> check_vote:{check_vote} block_PoH:{block_PoH}')
                        if check_vote is True or check_vote=="True":
                            vote_value=self.manage_vote_book("read",block_PoH)
                            logging.info(f'===> vote_value:{vote_value} block_PoH:{block_PoH}')
                            if vote_value=="vote":self.vote(block_PoH,leader_node_flag)
                            if vote_value=="slash":self.slash(block_PoH,leader_node_flag)


                #STEP 4-3 management of block that needs to be archived ASAP
                if block_is_validated is False and filename!=latest_received_block and filename!=new_block_2_exclude:
                    block_list_to_archive_ASAP.append(block_PoH)

         #STEP 5 management of LEADER Node
        if leader_node_flag is True:
            for filename in backlog_block_list:
                block_PoH=filename
                #the filename is the block PoH hash
                smart_contract_previous_transaction,smart_contract_transaction_hash,smart_contract_transaction_output_index=load_smart_contract_from_master_state(block_PoH,
                                                                                                                                                                  leader_node_flag=leader_node_flag,
                                                                                                                                                                  block_PoH=block_PoH)
                if smart_contract_transaction_hash is not None:
                    payload=f'''
node="{self.hostname}"
memory_obj_2_load=['block_vote']
block_vote.validate(node)
'''
                    block_is_validated=self.process_smart_contract(block_PoH,payload,smart_contract_transaction_hash,leader_node_flag)
                    if block_is_validated=="True": block_is_validated=True
                    if block_is_validated=="False": block_is_validated=False
                    logging.info(f'===> block {block_PoH} validation by leader node:{block_is_validated}')
                    if block_is_validated is True and filename!=new_block_2_exclude:
                        #for leaderNode only, validate the block in the blockchain
                        #not applicable for the Block which is just added
                        self.validate_block_in_blockchain(block_PoH,leader_node_flag)
                    if block_is_validated is False and filename!=new_block_2_exclude:
                        #for leaderNode only, Slash the block in the blockchain
                        #not applicable for the Block which is just added
                        self.slash_block_in_blockchain(block_PoH,leader_node_flag)

                
        #STEP 7 archiving of old block
        for filename in backlog_block_list_updated:
            block_PoH_2_check=filename
            #the filename is the block PoH hash
            #check if the block need to be archived as it's too old >NEW_BLOCKCHAIN_DIR_SLASHED_NB_SLOT_BEFORE_ARCHIVE slot
            block_filename,block_to_save=self.retrieve_block_detail(block_PoH_2_check)
            if block_to_save is not None:
                block_slot=block_to_save.block_header.slot
                check_option1=block_PoH_2_check in block_list_to_archive_ASAP
                check_option2=current_leader_node_slot>block_slot+NEW_BLOCKCHAIN_DIR_SLASHED_NB_SLOT_BEFORE_ARCHIVE
                if check_option1 is True or check_option2 is True:
                    #OPTION 1 this block has been rejected, let's archived it
                    #OPTION 2 this block is too old, it should be already validated, let's archived it
                    logging.info(f'###ARCHIVING of :{block_PoH_2_check} block_slot:{block_slot} rejected:{check_option1} too old:{check_option2}')

                    #1St round to avoid archiving a block which is in the backlog_chain_list of the best block
                    best_block=consensus_blockchain.best_block
                    archiving_flag=True
                    backlog_chain_list_counter=0
                    for backlog_chain_list_counter in consensus_blockchain.backlog_chain_list.keys():
                        try:
                            backlog_chain_list=consensus_blockchain.backlog_chain_list[backlog_chain_list_counter]['list']
                            if block_PoH_2_check in backlog_chain_list:
                                backlog_chain_list_counter+=1
                                if best_block.block_header.current_PoH_hash in backlog_chain_list:
                                    #this block is in the chain list of the best block so we cannot archive it
                                    #no need to check further
                                    archiving_flag=False
                                    break
                        except Exception as e:
                            logging.info(f"INFO consensus_blockchain.backlog_chain_list2: {e}")
                            logging.exception(e)
                    
                    if archiving_flag is True:
                        logging.info(f'###ARCHIVING check')
                        #2nd let's remove all the block after this block which are associated ot it
                        for backlog_chain_list_counter in consensus_blockchain.backlog_chain_list.keys():
                            try:
                                backlog_chain_list=consensus_blockchain.backlog_chain_list[backlog_chain_list_counter]['list']
                                if block_PoH_2_check in backlog_chain_list and block_PoH_2_check not in backlog_block_list_removed:
                        
                                    #all the block_PoH prior to the current block_PoH needs to be validated and added to the BlockChain
                                    removing_flag=False
                                    for i in range(0,len(backlog_chain_list)):
                                        if removing_flag is True:
                                            self.archive_block(backlog_chain_list[i])
                                            backlog_block_list_removed.append(backlog_chain_list[i])
                                
                                        if backlog_chain_list[i]==block_PoH_2_check:
                                            #starting now all the block needs to be removed:
                                            removing_flag=True
                                    removing_flag=False
                            except Exception as e:
                                logging.info(f"INFO consensus_blockchain.backlog_chain_list3: {e}")
                                logging.exception(e)
                
                        #let's remove the initial block
                        if block_PoH_2_check not in backlog_block_list_removed:
                            self.archive_block(block_PoH_2_check)
                            backlog_block_list_removed.append(block_PoH_2_check)

                    
            #except Exception as e:
            #    logging.info(f"**** ISSUE check_vote_and_backlog block_vote: {smart_contract_public_key_hash}")
            #    logging.info(f"**** ISSUE check_vote_and_backlog leader_node_flag: {leader_node_flag}")
            #    logging.exception(e)

    def process_smart_contract(self,block_PoH,payload,smart_contract_transaction_hash,leader_node_flag):
        smart_contract=SmartContract(block_PoH,
                                     smart_contract_sender='sender_public_key_hash3',
                                     smart_contract_type="api",
                                     payload=payload,
                                     smart_contract_previous_transaction=smart_contract_transaction_hash,
                                     smart_contract_transaction_hash=smart_contract_transaction_hash,
                                     leader_node_flag=leader_node_flag,
                                     block_PoH=block_PoH)

        smart_contract.process()
        return smart_contract.result

    def add_block_in_blockchain(self,filename,block_filename,block_to_save,latest_received_block):
        block_PoH=block_to_save.block_header.current_PoH_hash
        block_header_to_save=block_to_save.block_header
        #deletion of the file of the block in backlog
        os.remove(block_filename)

        #deletion of the vote in the vote book
        self.manage_vote_book("delete",block_PoH)

        #add block in blockChain
        #while master_state_readiness.block() is False:
        #    #let's wait until MasterState is released by another thread
        #    pass
        self.blockchain_memory.store_block_in_blockchain_in_memory(block_to_save,latest_received_block)
        #let's release MasterState
        #master_state_readiness.release()
                    

        #deletion of the file in MasterState_temp
        master_state_temp=MasterState(temporary_save_flag=True)
        master_state_temp.temporary_storage_sharding.delete(filename,master_state_readiness)

        #cleaning of the data associated to each transaction of this block on MasterState_temp
        for transaction in block_to_save.data["transactions"]:
            #add block in blockChain
            #while master_state_readiness.block() is False:
            #    #let's wait until MasterState is released by another thread
            #    pass
            master_state_temp.clean_temporary_file_master_state(transaction,block_header_to_save.current_PoH_hash,master_state_readiness)
            #let's release MasterState
            #master_state_readiness.release()

    def retrieve_block_detail(self,block_PoH):
        block_filename=self.STORAGE_DIR+self.NEW_BLOCKCHAIN_DIR_BACKLOG+f"/{block_PoH.lower()}".replace("'","")
        block=None
        try:
            with open(block_filename, "rb") as file_obj:
                block_str = file_obj.read()
                block_data = json.loads(block_str)
                
            block_header_to_save = BlockHeader(previous_block_hash=block_data["header"]['previous_block_hash'],
                                current_PoH_hash=block_data["header"]['current_PoH_hash'],
                                current_PoH_timestamp=block_data["header"]['current_PoH_timestamp'],
                                previous_PoH_hash=block_data["header"]['previous_PoH_hash'],
                                merkle_root=block_data["header"]['merkle_root'],
                                timestamp=block_data["header"]['timestamp'],
                                noonce=block_data["header"]['noonce'],
                                slot=block_data["header"]['slot'],
                                leader_node_public_key_hash=block_data["header"]['leader_node_public_key_hash'])
            
            block_PoH_to_save=BlockPoH(PoH_registry_input_data=block_data["PoH"]['PoH_registry_input_data'],
                                PoH_registry_intermediary=block_data["PoH"]['PoH_registry_intermediary'],)
            block = Block(
                transactions=block_data["transactions"],
                block_header=block_header_to_save,
                block_PoH=block_PoH_to_save,
                block_signature=block_data["signature"]
            )
        except:
            #block can be already in the BlockChain
            pass
        return block_filename,block

    def archive_block(self,block_PoH):
        block_filename_2_archive,block_2_archive=self.retrieve_block_detail(block_PoH)
        if block_2_archive is not None:
            logging.info(f'###Block is archived in slash archive:{block_filename_2_archive}')
            #deletion of the file of the block in backlog
            os.remove(block_filename_2_archive)

            #deletion of the vote in the vote book
            self.manage_vote_book("delete",block_PoH)

            #add block in slashed archive
            self.blockchain_memory.store_block_in_blockchain_in_slashed(block_2_archive)

            #deletion of the file in MasterState_temp
            master_state_temp=MasterState(temporary_save_flag=True)
            master_state_temp.temporary_storage_sharding.delete(block_PoH,master_state_readiness)

            #cleaning of the data associated to each transaction of this block on MasterState_temp
            for transaction in block_2_archive.data["transactions"]:
                #add block in blockChain
                #while master_state_readiness.block() is False:
                #    #let's wait until MasterState is released by another thread
                #    pass
                master_state_temp.clean_temporary_file_master_state(transaction,block_2_archive.block_header.current_PoH_hash,master_state_readiness)
                #let's release MasterState
                #master_state_readiness.release()