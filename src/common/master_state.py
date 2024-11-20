import json
import logging
import os
import copy
from common.utils import normal_round,check_marketplace_step1_sell,check_marketplace_step1_buy,check_smart_contract_consistency,check_marketplace_step2,extract_marketplace_account,check_marketplace_step,check_carriage_request
from common.values import ROUND_VALUE_DIGIT, DEFAULT_TRANSACTION_FEE_PERCENTAGE,MARKETPLACE_BUY,MARKETPLACE_SELL
from common.io_storage_sharding import StorageSharding



        


class MasterState:
    """
    Class to manage the state of each NIG account including SmartContract. 
    Each state of account is stored in an unique file.
    It's faster than reading all the transactions associated to an account in the blockchain.
    """
    def __init__(self,*args, **kwargs):
        from common.values import MASTER_STATE_DIR,MASTER_STATE_DEEPTH,MASTER_STATE_DIR_TEMP
        self.current_master_state={}
        self.temporary_save_flag=kwargs.get('temporary_save_flag',False)
        self.advance_save_flag=kwargs.get('advance_save_flag',False)
        self.store_block_in_blockchain_in_memory_flag=kwargs.get('store_block_in_blockchain_in_memory_flag',False)
        self.storage_sharding=StorageSharding(MASTER_STATE_DIR,deepth=MASTER_STATE_DEEPTH)
        self.temporary_storage_sharding=StorageSharding(MASTER_STATE_DIR_TEMP,deepth=0)

    def get_master_state_from_memory_from_transaction(self,transactions,*args, **kwargs) -> list:
        block_PoH = kwargs.get('block_PoH',None)
        leader_node_flag=kwargs.get('leader_node_flag',False)
        #logging.info(f"==>block_PoH1:{block_PoH}")
        previous_PoH_hash = kwargs.get('previous_PoH_hash',None)
        NIGthreading_flag=kwargs.get('NIGthreading_flag',False)
        #logging.info("Getting master state from memory for a transaction")
        account_list=self.get_account_list_transaction(transactions)
        #logging.info(f"==>account_list:{account_list}")
        logging.info(f"==>transactions:{transactions}")
        self.get_master_state_from_memory_from_account_list(account_list,block_PoH=block_PoH,previous_PoH_hash=previous_PoH_hash,leader_node_flag=leader_node_flag,NIGthreading_flag=NIGthreading_flag)

    def get_account_list_transaction(self,transactions):
        account_list=[]
        #logging.info(f"####transactions55:{transactions}")
        try:
            #account_list.append(transactions['inputs'][0]['transaction_hash']+'_'+str(transactions['inputs'][0]['output_index']))
            for utxo in transactions['outputs']:
                #test1=self.extract_account_list_from_locking_script("OP_SC",utxo)
                #test2=self.extract_account_list_from_locking_script("OP_DEL_SC",utxo)
                #logging.info(f"####OP_SC:{test1}")
                #logging.info(f"####OP_DEL_SC:{test2}")
                account_list.extend(self.extract_account_list_from_locking_script("OP_SC",utxo))
                account_list.extend(self.extract_account_list_from_locking_script("OP_DEL_SC",utxo))
            for inputs in transactions['inputs']:
                new_account=self.extract_account_list_from_unlocking_public_key_hash(inputs['unlocking_public_key_hash'])
                if new_account not in account_list:account_list.append(new_account)
        except Exception as e:
            logging.info(f"**** Transaction2: {e}")
            logging.exception(e)
        return account_list

    def get_master_state_from_memory_from_user(self,user,*args, **kwargs) -> list:
        block_PoH = kwargs.get('block_PoH',None)
        leader_node_flag=kwargs.get('leader_node_flag',False)
        NIGthreading_flag=kwargs.get('NIGthreading_flag',False)
        self.get_master_state_from_memory_from_account_list([user],block_PoH=block_PoH,leader_node_flag=leader_node_flag,NIGthreading_flag=NIGthreading_flag)
        
    def get_master_state_from_memory_from_account_list(self,account_list,*args, **kwargs) -> list:
        block_PoH = kwargs.get('block_PoH',None)
        leader_node_flag=kwargs.get('leader_node_flag',False)
        NIGthreading_flag=kwargs.get('NIGthreading_flag',False)
        previous_PoH_hash = kwargs.get('previous_PoH_hash',None)
        #previous_PoH_hash is used by leaderNode to reference the previous block which is stored in the memory
        #as the new block is not yet saved in the memory
        
        #logging.info(f"==>account_list:{account_list}")
        #STEP 1 retrieval of the last_block_pointer block_PoH
        from common.io_blockchain import BlockchainMemory
        blockchain_memory = BlockchainMemory()

        #STEP 2 Retrievel of the last block_PoH in consensus_blockchain ONLY for temporary_storage_sharding
        if block_PoH is not None and block_PoH!="TempBlockPoH" and block_PoH!="add_in_blockchain":
            #let's retrieve the last received block of the blockchain belonging to that block_PoH
            #to ensure that the MasterState is up to date
            #ONLY for temporary_storage_sharding (self.temporary_save_flag=True)
            from common.consensus_blockchain import consensus_blockchain
            #logging.info(f"### CHANGE OF block_PoH:w{block_PoH}")
            for backlog_chain_list_counter in consensus_blockchain.backlog_chain_list.keys():
                if block_PoH in consensus_blockchain.backlog_chain_list[backlog_chain_list_counter]['list']:
                    block_PoH=consensus_blockchain.backlog_chain_list[backlog_chain_list_counter]['last']
                    break
            #logging.info(f"### NEW block_PoH:{block_PoH}")

        #STEP 2 retrieval of the block with the block_PoH
        if block_PoH is None or block_PoH=="TempBlockPoH" and block_PoH!="add_in_blockchain":
            block_PoH=blockchain_memory.backlog_storage_sharding.read("last_block_pointer")
            if block_PoH is None:block_PoH=blockchain_memory.storage_sharding.read("last_block_pointer")
        elif block_PoH=="add_in_blockchain":
            #specific process when adding a new block in the BlockChain
            block_PoH=blockchain_memory.storage_sharding.read("last_block_pointer")
        blockchain_block_PoH=blockchain_memory.storage_sharding.read("last_block_pointer")
        block_PoH_chain_list=[block_PoH]

        if blockchain_block_PoH is None:blockchain_block_PoH=block_PoH
        #else:block_PoH_chain_list.append(blockchain_block_PoH)
        

        #STEP 2 retrieval of all the block_PoH until blockchain_block_PoH
        #logging.info(f"### block_PoH:{block_PoH}")
        #logging.info(f"### previous_PoH_hash:{previous_PoH_hash}")
        #logging.info(f"### blockchain_block_PoH:{blockchain_block_PoH}")
        while block_PoH!=blockchain_block_PoH:
            
            if previous_PoH_hash is None:
                block_dict=blockchain_memory.backlog_storage_sharding.read(block_PoH)
                if block_dict is None:block_dict=blockchain_memory.storage_sharding.read(block_PoH)
            else:
                #Specific process only for LeaderNode when saving the Temporay Block
                block_dict=blockchain_memory.backlog_storage_sharding.read(previous_PoH_hash)
                if block_dict is None:block_dict=blockchain_memory.storage_sharding.read(previous_PoH_hash)
                block_PoH_chain_list.append(previous_PoH_hash)
                previous_PoH_hash=None

            if block_dict is None:break
            #logging.info(f"###=> block_PoH_chain_list:{block_PoH_chain_list}")
            #logging.info(f"###=> block_dict:{block_dict}")
            previous_block_PoH=block_dict['header']['previous_PoH_hash']
            block_PoH_chain_list.append(previous_block_PoH)
            block_PoH=previous_block_PoH
            if block_PoH=='111':break


        block_PoH_chain_list.reverse()

        #if block_PoH=="TempBlockPoH":block_PoH_chain_list.insert(0,"TempBlockPoH")

        #if block_PoH=="TempBlockPoH":block_PoH_chain_list.append("TempBlockPoH")
        #if leader_node_flag is True:block_PoH_chain_list.append("TempBlockPoH")
        if NIGthreading_flag is True:block_PoH_chain_list.append("TempBlockPoH")

        #logging.info(f"### block_PoH_chain_list:{block_PoH_chain_list}")

        for account in account_list:
            #read the file
            file_master_state=self.storage_sharding.read(account)
            if file_master_state is not None:
                self.current_master_state[account]={}
                self.current_master_state[account].update(file_master_state)
                #logging.info(f"########### current_master_state: {account} {self.current_master_state[account]}")
            
            #read the temporary file for LeaderNode
            #if self.store_block_in_blockchain_in_memory_flag is False:
            temporary_file_master_state_raw=self.temporary_storage_sharding.read(account)
            if temporary_file_master_state_raw is not None:
                #Sanity check to ensure that old TempBlockPoH is well deleted
                block_PoH_list = list(temporary_file_master_state_raw)
                try:
                    TempBlockPoH_index=block_PoH_list.index('TempBlockPoH')
                    if TempBlockPoH_index<len(block_PoH_list)-1:
                        #a previousTempBlockPoH needs to be deleted
                        # because a most recent BlockPoH is existing
                        try:
                            temporary_file_master_state_raw.pop("TempBlockPoH")
                            logging.info(f"****INFO issue with removal of old TempBlockPoH for account: {account}")
                        except:pass
                except:pass

                for block_PoH in block_PoH_chain_list:
                    self.update_master_state_memory(account,temporary_file_master_state_raw,block_PoH)

    def update_master_state_memory(self,account,file_master_state_raw,block_PoH):
        try:
            file_master_state=file_master_state_raw[block_PoH]
            try:
                self.current_master_state[account].update(file_master_state)
            except Exception as e:
                self.current_master_state[account]=file_master_state
        except:
            pass

    def get_buy_mp_account_from_memory(self,requested_gap):
        return self.get_raw_mp_account_from_memory("buy",requested_gap)

    def get_sell_mp_account_from_memory(self,requested_gap):
        return self.get_raw_mp_account_from_memory("sell",requested_gap)


    def get_raw_mp_account_from_memory(self,action,requested_gap):
        if action=="buy":mp_account=MARKETPLACE_BUY
        if action=="sell":mp_account=MARKETPLACE_SELL
        mp_amount=None
        mp_gap=None
        next_mp=None
        sc=None
        last_flag=False

        while True:
            try:
                try:
                    self.get_master_state_from_memory_from_account_list([mp_account],leader_node_flag=True,NIGthreading_flag=True)
                    mp_account_utxo=self.current_master_state[mp_account]
                    mp_account_data=mp_account_utxo['marketplace']
                except:
                    #there is not value, this is the last transaction
                    last_flag=True
                    break
                
                mp_amount=mp_account_data['amount']
                mp_gap=mp_account_data['gap']
                next_mp=mp_account_data['next_mp']
                sc=mp_account_data['sc']

                if mp_gap is None:
                    #this is the last transaction following a carriage request reset
                    last_flag=True
                    break
                
                if action=="buy" and float(requested_gap)>float(mp_account_data['gap']):
                    break
                if action=="sell" and float(requested_gap)<float(mp_account_data['gap']):
                    break

                mp_account=mp_account_data['next_mp']
                
            except Exception as e:
                break
        if mp_account is None:
            if action=="buy":mp_account=MARKETPLACE_BUY
            if action=="sell":mp_account=MARKETPLACE_SELL
        return mp_account,mp_amount,mp_gap,next_mp,sc,last_flag

    def get_delete_mp_account_from_memory(self,action,sc_to_delete) -> list:
        if action=="buy":
            mp_account=MARKETPLACE_BUY
            mp_account_to_update=MARKETPLACE_BUY
            default_marketplace_transaction=MARKETPLACE_BUY
        if action=="sell":
            mp_account=MARKETPLACE_SELL
            mp_account_to_update=MARKETPLACE_SELL
            default_marketplace_transaction=MARKETPLACE_SELL
        
        new_next_mp=None
        nb_transactions=0
        mp_account_to_update_data=None
        mp_first_account_to_update_data_flag=False
        mp_2_delete_flag=False

        
        #1st loop to ensure that there is more than 1 transaction
        while True:
            try:
                self.get_master_state_from_memory_from_account_list([mp_account],leader_node_flag=True,NIGthreading_flag=True)
                mp_account_utxo=self.current_master_state[mp_account]
                mp_account_data=mp_account_utxo['marketplace']
                nb_transactions+=1
                mp_account=mp_account_data['next_mp']
                if nb_transactions>1:break
            except:
                #there is not value, this is the last transaction
                break

        #2nd loop to retrieve the right carriage request
        mp_account=default_marketplace_transaction
        while True:
            try:
                try:
                    self.get_master_state_from_memory_from_account_list([mp_account],leader_node_flag=True,NIGthreading_flag=True)
                    mp_account_utxo=self.current_master_state[mp_account]
                    mp_account_data=mp_account_utxo['marketplace']
                    mp_account_to_update_data=mp_account_data

                except:
                    #there is no value, this is the last transaction
                    break
                
                if sc_to_delete==mp_account_data['sc']:
                    #this is the carriage request to delete
                    new_next_mp=mp_account_data['next_mp']
                    mp_2_delete_flag=True
                    if mp_account==default_marketplace_transaction:
                        #specific process as it's the first carriage request
                        mp_account=mp_account_data['next_mp']

                        self.get_master_state_from_memory_from_account_list([mp_account],leader_node_flag=True,NIGthreading_flag=True)
                        mp_account_utxo=self.current_master_state[mp_account]
                        mp_account_data=mp_account_utxo['marketplace']

                        mp_account_to_update=default_marketplace_transaction
                        mp_account_to_update_data=mp_account_data
                        mp_first_account_to_update_data_flag=True
                            
                    break

                mp_account_to_update=mp_account
                mp_account=mp_account_data['next_mp']

                if mp_account=="None":break
                
            except Exception as e:
                break
        return mp_2_delete_flag,mp_account_to_update,new_next_mp,nb_transactions,mp_account_to_update_data,mp_first_account_to_update_data_flag

    def update_master_state(self, transaction: list,block_PoH,*args, **kwargs):
        previous_PoH_hash = kwargs.get('previous_PoH_hash',None)
        leader_node_flag = kwargs.get('leader_node_flag',None)
        #logging.info(f"==>block_PoH2:{block_PoH}")
        NIGthreading_flag=kwargs.get('NIGthreading_flag',False)
        #previous_PoH_hash is used by leaderNode to reference the previous block which is stored in the memory
        #as the new block is not yet saved in the memory

        #logging.info("Update master state with transaction")
        
        #Step 1 uploading of previous master state for that transaction
        self.get_master_state_from_memory_from_transaction(transaction,block_PoH=block_PoH,previous_PoH_hash=previous_PoH_hash,leader_node_flag=leader_node_flag,NIGthreading_flag=NIGthreading_flag)

        #Step 2 in case of SmartContract, ensure that the consistency of the SmartContract:
        #only 1 input, only 1 output except for marketplace
        #transaction_hash of input of new transaxction = UTXO of SmartContrat
        smart_contract_flag,smart_contract_error_list=check_smart_contract_consistency(transaction)
        if smart_contract_flag is True:
            smart_contract_transaction_hash=transaction["transaction_hash"]
            check_input_flag=False
            for i in range(0,len(transaction['inputs'])):
                smart_contract_input_transaction_hash=transaction['inputs'][i]['transaction_hash']
                smart_contract_output_index=transaction['inputs'][i]['output_index']
                unlocking_public_key_hash=transaction['inputs'][i]['unlocking_public_key_hash']
                smart_contract_account=self.extract_account_list_from_unlocking_public_key_hash(unlocking_public_key_hash)
                if smart_contract_account!='':
                    #smart_contract_account='' when initializing BlockChain
                    logging.info(f'#smart_contract_account:{smart_contract_account}')
                    try:
                        smart_contract_account_account_dic=self.current_master_state[smart_contract_account]
                    except:
                        smart_contract_account_account_dic=None
                    if smart_contract_account_account_dic is not None:
                        if smart_contract_input_transaction_hash+'_'+str(smart_contract_output_index) in smart_contract_account_account_dic['utxos']: check_input_flag=True
                           
            if check_input_flag is False:
                #any input_transaction_hash doesn't equal of the UTXO of the SmartContract which is not possible
                #let's raise an issue
                logging.info(f'#transaction:{transaction}')
                raise ValueError(f'###ERROR UPDATE MASTER STATE of SmartContract with transaction_hash: {smart_contract_transaction_hash} INPUT of new transaction is not in current SmartContract UTXO')


        if smart_contract_flag=="error":
            #there is an issue with the SmartContrat
            smart_contract_transaction_hash=transaction["transaction_hash"]
            logging.info(f'#transaction:{transaction}')
            raise ValueError(f'###ERROR UPDATE MASTER STATE of SmartContract with transaction_hash: {smart_contract_transaction_hash} ERROR:{smart_contract_error_list}')
        
        
        #Step 3 deletion of older UTXO
        deleted_utxo=None
        old_utxo_key=None
        old_utxo_account=None

        #if check_marketplace_step1(transaction['outputs']) is False and "BlockVote" not in str(transaction['outputs']):
        #if check_marketplace_step1(transaction['outputs']) is False and check_marketplace_step(98,transaction['outputs']) is False and check_marketplace_step(99,transaction['outputs']) is False:
        if check_marketplace_step1_buy(transaction['outputs']) is False and check_marketplace_step1_sell(transaction['outputs']) is False:
            try:
                for i in range(0, len(transaction['inputs'])):
                    if "_" in transaction['inputs'][i]['transaction_hash']:old_utxo_key=transaction['inputs'][i]['transaction_hash']
                    else:old_utxo_key=transaction['inputs'][i]['transaction_hash']+'_'+str(transaction['inputs'][i]['output_index'])
                    #special process Smart Contract
                    #when there is "SC" in unlocking_public_key_hash ex: "31f2ac8088005412c7b031a6e342b17a65a48d01 SC f998212b2adc762f114c9ec2b0b2d9bd6c811688
                    old_utxo_account=self.extract_account_list_from_unlocking_public_key_hash(transaction['inputs'][i]['unlocking_public_key_hash'])

                    #extract of the data
                    if old_utxo_account!='' and old_utxo_account!='abcd1234_0':
                        #logging.info(f"###### current_master_state:{self.current_master_state}")
                        account_dic=self.current_master_state[old_utxo_account]
                        if account_dic!={}:
                            deleted_utxo=copy.deepcopy(account_dic['utxos_data'][old_utxo_key])
                            #logging.info(f"###### deleted_utxo['output']1:{deleted_utxo['output']}")
                            account_dic['total']-=normal_round(deleted_utxo['output']['amount'],ROUND_VALUE_DIGIT)
                            account_dic['utxos']=list(filter(lambda a: a != old_utxo_key, account_dic['utxos']))
                            account_dic['utxos_data'].pop(old_utxo_key)
                            self.current_master_state[old_utxo_account]=account_dic

            except Exception as e:
                logging.info(f"**** Transaction5: {e}")
                logging.exception(e)

        if check_marketplace_step2(transaction['outputs']) is True:
            #check that there is not more than 2 utxos for marketplace_step2
            smart_contract_account=extract_marketplace_account(transaction['outputs'])
            if smart_contract_account is not None:
                account_dic=self.current_master_state[smart_contract_account]
                if len(account_dic['utxos'])>2:
                    raise ValueError(f'###ERROR UPDATE MASTER STATE of SmartContract: {smart_contract_account} with transaction_hash: {smart_contract_transaction_hash} More than 2 UTXO for marketplace_step2')
            

        #Step 3 update of new UTXO
        try:
            output_index=0
            transaction_hash=transaction['transaction_hash']
            timestamp=transaction['timestamp']
            new_utxo_value_input_list=[]
            account_credit_list=[]
            reputation_acount=None
            for utxo in transaction['inputs']:
                new_utxo_value_input={}
                new_utxo_value_input['unlocking_public_key_hash']=utxo['unlocking_public_key_hash']
                #special process Smart Contract
                #when there is "SC" in unlocking_public_key_hash ex: "31f2ac8088005412c7b031a6e342b17a65a48d01 SC f998212b2adc762f114c9ec2b0b2d9bd6c811688
                account_credit_list.append(self.extract_account_list_from_unlocking_public_key_hash(utxo['unlocking_public_key_hash']))
                new_utxo_value_input['network']=utxo['network']
                new_utxo_value_input['transaction_hash']=utxo['transaction_hash']
                new_utxo_value_input['output_index']=utxo['output_index']
                new_utxo_value_input_list.append(new_utxo_value_input)


            for utxo in transaction['outputs']:
                #removal of amount in account
                new_utxo_key=transaction_hash+'_'+str(output_index)
                new_utxo_value_output={}
                new_utxo_value_output['amount']=utxo['amount']
                new_utxo_value_output['locking_script']=utxo['locking_script']
                new_utxo_value_output['network']=utxo['network']
                new_utxo_value_output['transaction_hash']=transaction_hash
                new_utxo_value_output['timestamp']=timestamp
                new_utxo_value_output['output_index']=output_index
                new_utxo_value_output['fee_interface']=utxo['fee_interface']
                new_utxo_value_output['fee_miner']=utxo['fee_miner']
                new_utxo_value_output['fee_node']=utxo['fee_node']
                try:marketplace_transaction_flag=utxo['marketplace_transaction_flag']
                except:marketplace_transaction_flag=False
                try:smart_contract_transaction_flag=utxo['smart_contract_transaction_flag']
                except:smart_contract_transaction_flag=False
                account_list=self.extract_account_list_from_locking_script("OP_SC",utxo)
                #logging.info(f"====>account_list1:{account_list}")
                
                #reputation account management
                if "OP_RE" in utxo['locking_script']:
                    reputation_acount=self.extract_account_list_from_locking_script("OP_SC",utxo)
                    #logging.info(f"====>reputation_acount1:{reputation_acount}")

                new_utxo_value_output['account_list']=account_list
                marketplace_place_step4_flag=False
                marketplace_place_step4_buyer=None
                marketplace_place_step4_seller=None
                marketplace_place_step4_requested_amount=None
                marketplace_place_step4_requested_currency=None
                marketplace_place_step4=0
                marketplace_place_step4_requested_nig=0
                marketplace_place_archiving_flag=False
                try:
                    new_utxo_value_output['smart_contract_sender']=utxo['smart_contract_sender']
                    new_utxo_value_output['smart_contract_new']=utxo['smart_contract_new']
                    new_utxo_value_output['smart_contract_account']=utxo['smart_contract_account']
                    new_utxo_value_output['smart_contract_flag']=utxo['smart_contract_flag']
                    new_utxo_value_output['smart_contract_gas']=utxo['smart_contract_gas']
                    new_utxo_value_output['smart_contract_memory']=utxo['smart_contract_memory']
                    #check if the transaction is in step 4 or 45 (partial payment) or 66 (payment default) or 98 (expiration) or 99 (cancellation) to put in Marketplace_archive if needed
                    smart_contract_memory=utxo['smart_contract_memory']
                    for j in range(0,len(smart_contract_memory[0][2])):
                        if smart_contract_memory[0][2][j]=='step':
                            if smart_contract_memory[0][3][j]==4 or smart_contract_memory[0][3][j]==45 or smart_contract_memory[0][3][j]==66 or smart_contract_memory[0][3][j]==98 or smart_contract_memory[0][3][j]==99:
                                marketplace_place_step4=smart_contract_memory[0][3][j]
                                marketplace_place_step4_flag=True
                                #step = 99 is used to archive the cancelled marketplace request 
                                if smart_contract_memory[0][3][j]==99:marketplace_place_archiving_flag=True
                                #step = 98 is used to archive the expired marketplace request 
                                if smart_contract_memory[0][3][j]==98:marketplace_place_archiving_flag=True
                                #logging.info(f"======> MarketPlace {smart_contract_memory[0][3][j]}: {transaction_hash}")

                        if smart_contract_memory[0][2][j]=='requested_amount':marketplace_place_step4_requested_amount=smart_contract_memory[0][3][j]
                        if smart_contract_memory[0][2][j]=='requested_currency':marketplace_place_step4_requested_currency=smart_contract_memory[0][3][j]
                        if smart_contract_memory[0][2][j]=='buyer_public_key_hash':marketplace_place_step4_buyer=smart_contract_memory[0][3][j]
                        if smart_contract_memory[0][2][j]=='seller_public_key_hash':marketplace_place_step4_seller=smart_contract_memory[0][3][j]
                        if smart_contract_memory[0][2][j]=='requested_nig':marketplace_place_step4_requested_nig=smart_contract_memory[0][3][j]
                        
                        

                    new_utxo_value_output['smart_contract_memory_size']=utxo['smart_contract_memory_size']
                    new_utxo_value_output['smart_contract_type']=utxo['smart_contract_type']
                    new_utxo_value_output['smart_contract_payload']=utxo['smart_contract_payload']
                    new_utxo_value_output['smart_contract_result']=utxo['smart_contract_result']
                    new_utxo_value_output['smart_contract_transaction_hash']=new_utxo_key
                    if utxo['smart_contract_type']=="source":
                        #smart_contract_previous_transaction is only updated with source call
                        if new_utxo_value_output['smart_contract_new'] is True:new_utxo_value_output['smart_contract_previous_transaction']=None
                        else:new_utxo_value_output['smart_contract_previous_transaction']=utxo['smart_contract_previous_transaction']
                    else:
                        #smart_contract_previous_transaction is not updated with API call
                        new_utxo_value_output['smart_contract_previous_transaction']=utxo['smart_contract_previous_transaction']
                except:
                    pass

                from common.smart_contract import SmartContract
                #Step 1 : retrieve the needed information per account
                mp_account_data=None
                requested_amount=None
                requested_gap=0
                marketplace_data={}
                #if marketplace_transaction_flag is True:
                if check_carriage_request(transaction['outputs']) is True:
                    try:
                        from common.smart_contract import load_smart_contract_from_master_state
                        smart_contract_previous_transaction,smart_contract_transaction_hash,smart_contract_transaction_output_index=load_smart_contract_from_master_state(account_list[0])
                        payload=utxo['smart_contract_payload']+f'''
return carriage_request.get_mp_info()
'''
                        smart_contract=SmartContract(account_list[0],
                                                     smart_contract_sender='sender_public_key_hash',
                                                     smart_contract_type="source",
                                                     smart_contract_new=False,
                                                     payload=payload,
                                                     smart_contract_previous_transaction=smart_contract_previous_transaction)
                        smart_contract.process()
                        locals()['smart_contract']
                        if smart_contract.result is not None :mp_account_data=smart_contract.result
                        if mp_account_data is not None:
                            requested_amount=mp_account_data['requested_amount']
                            requested_gap=mp_account_data['requested_gap']
                    except Exception as e:
                        logging.info(f"### ISSUE master_state get mp_account_data account:{account_list[0]} {e}")
                        logging.exception(e)
                        
                    #Step 2 : retrieve the marketplace_data
                    marketplace_data['next_mp']=mp_account_data['next_mp']
                    marketplace_data['gap']=requested_gap
                    marketplace_data['amount']=requested_amount
                    marketplace_data['sc']=mp_account_data['sc']

                for account in account_list:
                    #Step 3 : update master state
                    try:
                        #there are values for this account, let's update them
                        account_dic=self.current_master_state[account]
                        if account_dic=={}:
                            account_dic['total']=0
                            account_dic['utxos']=[]
                            account_dic['marketplace_profit_details']={}
                            account_dic['utxos_data']={}
                            account_dic['marketplace']=[]
                            account_dic['marketplace_archive']=[]
                            account_dic['reputation']=[]
                            account_dic['smart_contract']=[]
                            account_dic['balance']={}
                            account_dic['balance']['credit']={}
                            account_dic['balance']['debit']={}

                    except:
                        #there is no value for this account, let's create them
                        self.current_master_state[account]={}
                        account_dic={}
                        account_dic['total']=0
                        account_dic['marketplace_profit_details']={}
                        account_dic['utxos']=[]
                        account_dic['utxos_data']={}
                        account_dic['marketplace']=[]
                        account_dic['marketplace_archive']=[]
                        account_dic['reputation']=[]
                        account_dic['smart_contract']=[]
                        account_dic['balance']={}
                        account_dic['balance']['credit']={}
                        account_dic['balance']['debit']={}
                    
                    if marketplace_transaction_flag is False and smart_contract_transaction_flag is False or account==account_list[0]:
                        #account==account_list[0] means that it's the datas of the SmartContract so we need to update the data of the Smart Contract
                        if account_dic!={}:
                            if check_carriage_request(transaction['outputs']) is True:
                                #process for carriage request of marketplace step 1
                                account_dic['marketplace']=marketplace_data

                            if new_utxo_key not in account_dic['utxos']:
                                account_dic['total']+=normal_round(new_utxo_value_output['amount'],ROUND_VALUE_DIGIT)
                                account_dic['utxos'].append(new_utxo_key)
                                account_dic['utxos_data'][new_utxo_key]={}
                                account_dic['utxos_data'][new_utxo_key]['output']=new_utxo_value_output
                                account_dic['utxos_data'][new_utxo_key]['input']=new_utxo_value_input_list
                                #update of balance
                                if old_utxo_key==account:
                                    #try:account_dic['balance']['credit'].pop(old_utxo_key)
                                    #except:pass
                                    pass
                                new_utxo_value_output['account_credit_list']=account_credit_list
                                #if old_utxo_account is not None and old_utxo_account!=account:account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                                #if old_utxo_account is not None and old_utxo_account!=account:self.update_old_utxo_key(old_utxo_account,old_utxo_key,account,new_utxo_value_output)
                                #if old_utxo_account!=account:account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output

                                try:
                                    new_utxo_value_output['smart_contract_flag']=utxo['smart_contract_flag']
                                    account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                                    account_dic['balance']['credit'][new_utxo_key]['inputs']=transaction['inputs']
                                except:
                                    if old_utxo_account!=account:account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                        
                                if old_utxo_account!=account:self.update_old_utxo_key(old_utxo_account,old_utxo_key,new_utxo_key,new_utxo_value_output)
                            
                                account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                                account_dic['balance']['credit'][new_utxo_key]['inputs']=transaction['inputs']
                                self.current_master_state[account]=account_dic

                            if marketplace_place_step4_flag is True:
                                #this is transaction fully validated (step 4, 45, 66, 98 or 99)
                                #let's archive it in the associated account to increase speed
                                if marketplace_place_archiving_flag is False:associated_account_dic_step4_list=[marketplace_place_step4_buyer,marketplace_place_step4_seller]
                                else:
                                    #this is an expired request which needs to be archived
                                    #marketplace_place_step4_seller can be None ('') in step = 1
                                    #marketplace_place_step4_buyer can be None ('') in step = -1
                                    associated_account_dic_step4_list=[marketplace_place_step4_buyer,marketplace_place_step4_seller]
                                    try:associated_account_dic_step4_list.remove('')
                                    except:pass
                                    try:associated_account_dic_step4_list.remove(None)
                                    except:pass
                                logging.info(f"INFO ### associated_account_dic_step4_list:{associated_account_dic_step4_list}")
                                step=0
                                for associated_account_dic_step4 in associated_account_dic_step4_list:
                                    step+=1
                                    associated_account_dic_step4_to_update=self.current_master_state[associated_account_dic_step4]
                                    if account_list[0] not in associated_account_dic_step4_to_update['marketplace_archive']:associated_account_dic_step4_to_update['marketplace_archive'].append(account_list[0])
                                    try:
                                        try:
                                            associated_account_dic_step4_to_update['marketplace'].remove(account_list[0])
                                        except:pass
                                        #update of added value/gain
                                        if marketplace_place_step4==4 or marketplace_place_step4==45:
                                            logging.info(f"INFO ### marketplace_place added value")
                                            try:associated_account_dic_step4_to_update['marketplace_profit_details']
                                            except:associated_account_dic_step4_to_update['marketplace_profit_details']={}
                                            try:associated_account_dic_step4_to_update['marketplace_profit_details'][marketplace_place_step4_requested_currency]
                                            except:associated_account_dic_step4_to_update['marketplace_profit_details'][marketplace_place_step4_requested_currency]={}
                                            if step==1:
                                                logging.info(f"INFO ### marketplace_place added value buyer")
                                                #this is the buyer
                                                try:
                                                    associated_account_dic_step4_to_update['marketplace_profit_details'][marketplace_place_step4_requested_currency]['credit']+=marketplace_place_step4_requested_amount
                                                    associated_account_dic_step4_to_update['marketplace_profit_details'][marketplace_place_step4_requested_currency]['credit_nig']+=normal_round(marketplace_place_step4_requested_nig*(1-float(DEFAULT_TRANSACTION_FEE_PERCENTAGE)/100),ROUND_VALUE_DIGIT)
                                                except Exception as e:
                                                    logging.info(f"####CHECK1###")
                                                    associated_account_dic_step4_to_update['marketplace_profit_details'][marketplace_place_step4_requested_currency]['credit']=marketplace_place_step4_requested_amount
                                                    associated_account_dic_step4_to_update['marketplace_profit_details'][marketplace_place_step4_requested_currency]['credit_nig']=normal_round(marketplace_place_step4_requested_nig*(1-float(DEFAULT_TRANSACTION_FEE_PERCENTAGE)/100),ROUND_VALUE_DIGIT)

                                            if step==2:
                                                logging.info(f"INFO ### marketplace_place added value seller")
                                                #this is the seller
                                                try:
                                                    associated_account_dic_step4_to_update['marketplace_profit_details'][marketplace_place_step4_requested_currency]['debit']+=marketplace_place_step4_requested_amount
                                                    associated_account_dic_step4_to_update['marketplace_profit_details'][marketplace_place_step4_requested_currency]['debit_nig']+=marketplace_place_step4_requested_nig
                                                except Exception as e:
                                                    logging.info(f"####CHECK2###")
                                                    associated_account_dic_step4_to_update['marketplace_profit_details'][marketplace_place_step4_requested_currency]['debit']=marketplace_place_step4_requested_amount
                                                    associated_account_dic_step4_to_update['marketplace_profit_details'][marketplace_place_step4_requested_currency]['debit_nig']=marketplace_place_step4_requested_nig

                                            try:
                                                associated_account_dic_step4_to_update['marketplace'].remove(account_list[0])
                                            except Exception as e:
                                                logging.info(f"marketplace_place_step4 removal issue with account: {account_list[0]}")
                                                logging.exception(e)


                                    except Exception as e:
                                        logging.info(f"marketplace_place_step4 removal issue with account: {account_list[0]}")
                                        logging.exception(e)
                                    

                                    data1=associated_account_dic_step4_to_update['marketplace']
                                    data2=associated_account_dic_step4_to_update['marketplace_archive']
                                    logging.info(f"======> associated_account_dic_step4: {associated_account_dic_step4} account_dic['marketplace']: {data1} account_dic['marketplace_archive'] :{data2}")
                                    self.current_master_state[associated_account_dic_step4]=associated_account_dic_step4_to_update
                                    
                                    
                        else:
                            account_dic['total']+=normal_round(new_utxo_value_output['amount'],ROUND_VALUE_DIGIT)
                            account_dic['utxos'].append(new_utxo_key)
                            account_dic['utxos_data'][new_utxo_key]={}
                            account_dic['utxos_data'][new_utxo_key]['output']=new_utxo_value_output
                            account_dic['utxos_data'][new_utxo_key]['input']=new_utxo_value_input_list
                            #update of balance
                            if old_utxo_key==account:
                                #try:account_dic['balance']['credit'].pop(old_utxo_key)
                                #except:pass
                                pass
                            new_utxo_value_output['account_credit_list']=account_credit_list
                            #if old_utxo_account is not None and old_utxo_account!=account:account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                            #if old_utxo_account is not None and old_utxo_account!=account:self.update_old_utxo_key(old_utxo_account,old_utxo_key,new_utxo_key,new_utxo_value_output)
                            #if old_utxo_account!=account:account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                        
                            try:
                                new_utxo_value_output['smart_contract_flag']=utxo['smart_contract_flag']
                                account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                                account_dic['balance']['credit'][new_utxo_key]['inputs']=transaction['inputs']
                            except:
                                if old_utxo_account!=account:account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                        
                            if old_utxo_account!=account:self.update_old_utxo_key(old_utxo_account,old_utxo_key,new_utxo_key,new_utxo_value_output)
                            account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                            account_dic['balance']['credit'][new_utxo_key]['inputs']=transaction['inputs']
                            self.current_master_state[account]=account_dic
                    else:
                        #account_list[0] is the Smart Contract account
                        #account_list[1 and + ] are the other account associated to that Smart Contrat
                        from node.main import marketplace_owner
                        if account!=marketplace_owner.public_key_hash:
                            #the marketplace dict of marketplace is not updated.
                            if check_carriage_request(transaction['outputs']) is True:
                                #this is a carriage request of a marketplace step 1 transaction
                                account_dic['marketplace']=marketplace_data
                            elif marketplace_transaction_flag is True and marketplace_place_step4_flag is False:
                                #this is a marketplace transaction
                                if account_list[0] not in account_dic['marketplace']:account_dic['marketplace'].append(account_list[0])
                            elif smart_contract_transaction_flag is True:
                                #this is a smart contract transaction
                                if account_list[0] not in account_dic['smart_contract']:account_dic['smart_contract'].append(account_list[0])
                        #reputation_acount management
                        #logging.info(f"====>reputation_acount2:{reputation_acount}")
                        if reputation_acount is not None:
                            account_dic['reputation']=reputation_acount[0]
                            try:account_dic['smart_contract'].remove(reputation_acount[0])
                            except:pass
                        self.current_master_state[account]=account_dic
                        
                #Removal of association between some account and this SmartContract
                account_list=self.extract_account_list_from_locking_script("OP_DEL_SC",utxo)
                for account in account_list:
                    smart_contract_account=utxo["smart_contract_account"]
                    account_2_remove_dic=self.current_master_state[account]
                    if smart_contract_account in account_2_remove_dic['marketplace']:
                        account_2_remove_dic['marketplace'].remove(smart_contract_account)
                        self.current_master_state[account]=account_2_remove_dic
                    #FYI, transaction are never removed from marketplace_archive to keep tracked
                    
                output_index+=1
            
        except Exception as e:
            logging.info(f"**** Transaction6: {e}")
            logging.exception(e)

        #Step 4 update of balance

    def update_old_utxo_key(self,old_utxo_account,old_utxo_key,new_utxo_key,new_utxo_value_output):
        if old_utxo_account is not None and old_utxo_account!='':
            try:
                self.current_master_state[old_utxo_account]['balance']['debit'][new_utxo_key]=new_utxo_value_output
            except Exception as e:
                if new_utxo_key!='abcd1234_0':
                    logging.info(f"**** Transaction7: {e}")
                    logging.exception(e)

    

    def store_master_state_in_memory(self,BlockPoH):
        '''to store the transaction in a file =>store_master_state_in_memory
        '''
        try:
            #logging.info(f"**** self.current_master_state.keys(): {self.current_master_state.keys():}")
            for account in self.current_master_state.keys():
                new_master_state={}
                current_master_state = {}
                new_master_state[account]=self.current_master_state[account]
                #saving the file
                if self.temporary_save_flag is True:
                    #on a temporary file for LeaderNode
                    temporary_file_master_state_raw=self.temporary_storage_sharding.read(account)
                    if temporary_file_master_state_raw is not None:
                        try:
                            temporary_file_master_state_raw[BlockPoH] = new_master_state[account]
                        except:
                            temporary_file_master_state_raw={}
                            temporary_file_master_state_raw[BlockPoH] = new_master_state[account]
                    else:
                        temporary_file_master_state_raw={}
                        temporary_file_master_state_raw[BlockPoH] = new_master_state[account]
                    self.temporary_storage_sharding.store(account,temporary_file_master_state_raw)
                    #logging.info(f"**** account: {account} ==> new_master_state:{new_master_state[account]}")
                else:
                    self.storage_sharding.store(account,new_master_state[account])
        except Exception as e:
            logging.info(f"**** Transaction8: {e}")


    def delete_TempBlockPoH(self,transaction):
        '''to delete TempBlockPoH associated to the Transaction 
        at the end of the block creation
        '''
        account_list=self.get_account_list_transaction(transaction)
        #logging.info(f"**** account_list: {account_list}")
        for account in account_list:
            temporary_file_master_state_raw=self.temporary_storage_sharding.read(account)
            if temporary_file_master_state_raw is not None:
                try:
                    #logging.info(f"**** temporary_file_master_state_raw: {type(temporary_file_master_state_raw)} {temporary_file_master_state_raw}")
                    temporary_file_master_state_raw.pop("TempBlockPoH")
                    self.temporary_storage_sharding.store(account,temporary_file_master_state_raw)
                except Exception as e:
                    logging.info(f"**** Transaction9: {e}")
                    logging.exception(e)

    def clean_temporary_file_master_state(self,transaction,BlockPoH,master_state_readiness):
        '''to delete the transaction in the temporary_file_master
        '''
        account_list=self.get_account_list_transaction(transaction)
        for account in account_list:
            temporary_file_master_state_raw=self.temporary_storage_sharding.read(account)
            if temporary_file_master_state_raw is not None:
                try:
                    temporary_file_master_state_raw.pop(BlockPoH)
                except Exception as e:
                    logging.info(f"**** Transaction10: {e}")
                    logging.exception(e)
                if temporary_file_master_state_raw=={}:
                    #the file is empty, let's delete it
                    self.temporary_storage_sharding.delete(account,master_state_readiness)
                else:
                    self.temporary_storage_sharding.store(account,temporary_file_master_state_raw)

    def extract_account_list_from_locking_script(self,op_elem,utxo):
        account_list=[]
        op_elem_account_list=[]
        locking_script=utxo['locking_script']
        locking_script_list = locking_script.split(" ")
        #list of op_elem
        # =>OP_SC is used to associate an account to a SmartContract
        # =>OP_DEL_SC is used to deassociate an account from a SmartContract
        #ex: OP_DUP OP_HASH160 31f2ac8088005412c7b031a6e342b17a65a48d01 OP_EQUAL_VERIFY OP_CHECKSIG OP_SC 47866ef83717f16c24cb246deeef1f75f798b8e5 
        ##OP_SC 531c2e528bd177866f7213b192833846018686e5 OP_DEL_SC 3243223324GFDG
        flag_for_adding=False
        for element in locking_script_list:
            #Step 1 list of account when there is no specific OP like OP_SC, OP_DEL_SC
            if element.startswith("OP"):
                pass
            else:
                if element not in account_list:account_list.append(element)
            #Step 2 list for specific OP like OP_SC, OP_DEL_SC
            if element.startswith(op_elem):flag_for_adding=True
            elif flag_for_adding is True:
                if element not in op_elem_account_list:op_elem_account_list.append(element)
                flag_for_adding=False
        
        if op_elem_account_list!=[]:return op_elem_account_list
        else:
            if op_elem=="OP_DEL_SC":return []
            else:return account_list

    def extract_account_list_from_unlocking_public_key_hash(self,utxo_account):
        #special process Smart Contract
        #when there is "SC" in unlocking_public_key_hash ex: "31f2ac8088005412c7b031a6e342b17a65a48d01 SC f998212b2adc762f114c9ec2b0b2d9bd6c811688
        new_utxo_account=utxo_account
        if utxo_account.find("SC ")!=-1:
            new_utxo_account=utxo_account[utxo_account.find("SC ")+3:len(utxo_account)]
        return new_utxo_account

