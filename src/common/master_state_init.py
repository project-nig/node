import json
import logging
import os
import copy
from common.utils import normal_round,check_marketplace_step1
from common.values import ROUND_VALUE_DIGIT
from common.io_storage_sharding import StorageSharding


class MasterState:
    def __init__(self,*args, **kwargs):
        from node.main import MASTER_STATE_DIR,MASTER_STATE_DEEPTH,MASTER_STATE_DIR_TEMP
        self.current_master_state={}
        self.temporary_save_flag=kwargs.get('temporary_save_flag',False)
        self.advance_save_flag=kwargs.get('advance_save_flag',False)
        self.storage_sharding=StorageSharding(MASTER_STATE_DIR,deepth=MASTER_STATE_DEEPTH)
        self.temporary_storage_sharding=StorageSharding(MASTER_STATE_DIR_TEMP,deepth=0)

    def get_master_state_from_memory_from_transaction(self,transactions) -> list:
        #logging.info("Getting master state from memory for a transaction")
        account_list=[]
        try:
            #account_list.append(transactions['inputs'][0]['transaction_hash']+'_'+str(transactions['inputs'][0]['output_index']))
            for utxo in transactions['outputs']:
                account_list.extend(self.extract_account_list_from_locking_script("OP_SC",utxo))
                account_list.extend(self.extract_account_list_from_locking_script("OP_DEL_SC",utxo))
            for inputs in transactions['inputs']:
                new_account=self.extract_account_list_from_unlocking_public_key_hash(inputs['unlocking_public_key_hash'])
                if new_account not in account_list:account_list.append(new_account)
        except Exception as e:
            logging.info(f"**** Transaction2: {e}")
            logging.exception(e)
        self.get_master_state_from_memory_from_account_list(account_list)

    def get_master_state_from_memory_from_user(self,user) -> list:
        self.get_master_state_from_memory_from_account_list([user])
        
    def get_master_state_from_memory_from_account_list(self,account_list) -> list:
        for account in account_list:
            #read the file
            file_master_state=self.storage_sharding.read(account)
            if file_master_state is not None:
                self.current_master_state[account]={}
                self.current_master_state[account].update(file_master_state)
                #logging.info(f"########### current_master_state: {account} {self.current_master_state[account]}")
            
            #read the temporary file for LeaderNode
            temporary_file_master_state=self.temporary_storage_sharding.read(account)
            if temporary_file_master_state is not None:
                try:
                    self.current_master_state[account].update(temporary_file_master_state)
                    #logging.info(f"########### current_master_state_temp1: {account} {temporary_file_master_state}")
                    #logging.info(f"########### current_master_state_temp2: {account} {self.current_master_state[account]}")
                except:
                    self.current_master_state[account]={}
                    self.current_master_state[account].update(temporary_file_master_state)

        
    def update_master_state(self, transaction: list):
        #logging.info("Update master state with transaction")
        
        #Step 1 uploading of previous master state for that transaction
        self.get_master_state_from_memory_from_transaction(transaction)
        
        #Step 2 deletion of older UTXO
        deleted_utxo=None
        old_utxo_key=None
        old_utxo_account=None

        if check_marketplace_step1(transaction['outputs']) is False:
            try:
                for i in range(0, len(transaction['inputs'])):
                    old_utxo_key=transaction['inputs'][i]['transaction_hash']+'_'+str(transaction['inputs'][i]['output_index'])
                    #special process Smart Contract
                    #when there is "SC" in unlocking_public_key_hash ex: "31f2ac8088005412c7b031a6e342b17a65a48d01 SC f998212b2adc762f114c9ec2b0b2d9bd6c811688
                    old_utxo_account=self.extract_account_list_from_unlocking_public_key_hash(transaction['inputs'][i]['unlocking_public_key_hash'])

                    #extract of the data
                    if old_utxo_account!='':
                        #logging.info(f"###### current_master_state:{self.current_master_state}")
                        account_dic=self.current_master_state[old_utxo_account]
                        if account_dic!={}:
                            deleted_utxo=copy.deepcopy(account_dic['utxos_data'][old_utxo_key])
                            account_dic['total']-=normal_round(deleted_utxo['output']['amount'],ROUND_VALUE_DIGIT)
                            account_dic['utxos']=list(filter(lambda a: a != old_utxo_key, account_dic['utxos']))
                            account_dic['utxos_data'].pop(old_utxo_key)
                            self.current_master_state[old_utxo_account]=account_dic

                            for account in deleted_utxo['output']['account_list']:
                                if account!=old_utxo_account:
                                    account_dic=self.current_master_state[account]
                                    account_dic['total']-=normal_round(deleted_utxo['amount'],ROUND_VALUE_DIGIT)
                                    account_dic['utxos']=list(filter(lambda a: a != old_utxo_key, account_dic['utxos']))
                                    account_dic['utxos_data'].pop(old_utxo_key)
                                    self.current_master_state[account]=account_dic

            except Exception as e:
                logging.info(f"**** Transaction5: {e}")
                logging.exception(e)

        #Step 3 update of new UTXO
        try:
            output_index=0
            transaction_hash=transaction['transaction_hash']
            timestamp=transaction['timestamp']
            new_utxo_value_input={}
            account_credit_list=[]
            for utxo in transaction['inputs']:
                new_utxo_value_input['unlocking_public_key_hash']=utxo['unlocking_public_key_hash']
                #special process Smart Contract
                #when there is "SC" in unlocking_public_key_hash ex: "31f2ac8088005412c7b031a6e342b17a65a48d01 SC f998212b2adc762f114c9ec2b0b2d9bd6c811688
                account_credit_list.append(self.extract_account_list_from_unlocking_public_key_hash(utxo['unlocking_public_key_hash']))
                new_utxo_value_input['network']=utxo['network']
                new_utxo_value_input['transaction_hash']=utxo['transaction_hash']
                new_utxo_value_input['output_index']=utxo['output_index']


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
                new_utxo_value_output['account_list']=account_list
                try:
                    new_utxo_value_output['smart_contract_sender']=utxo['smart_contract_sender']
                    new_utxo_value_output['smart_contract_new']=utxo['smart_contract_new']
                    new_utxo_value_output['smart_contract_account']=utxo['smart_contract_account']
                    new_utxo_value_output['smart_contract_flag']=utxo['smart_contract_flag']
                    new_utxo_value_output['smart_contract_gas']=utxo['smart_contract_gas']
                    new_utxo_value_output['smart_contract_memory']=utxo['smart_contract_memory']
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


                for account in account_list:
                    try:
                        #there are values for this account, let's update them
                        account_dic=self.current_master_state[account]
                        if account_dic=={}:
                            account_dic['total']=0
                            account_dic['utxos']=[]
                            account_dic['utxos_data']={}
                            account_dic['marketplace']=[]
                            account_dic['smart_contract']=[]
                            account_dic['balance']={}
                            account_dic['balance']['credit']={}
                            account_dic['balance']['debit']={}

                    except:
                        #there is no value for this account, let's create them
                        self.current_master_state[account]={}
                        account_dic={}
                        account_dic['total']=0
                        account_dic['utxos']=[]
                        account_dic['utxos_data']={}
                        account_dic['marketplace']=[]
                        account_dic['smart_contract']=[]
                        account_dic['balance']={}
                        account_dic['balance']['credit']={}
                        account_dic['balance']['debit']={}
                    
                    if marketplace_transaction_flag is False and smart_contract_transaction_flag is False or account==account_list[0]:
                        #account==account_list[0] means that it's the datas of the SmartContract so we need to update the date of the Smart Contract
                        if account_dic!={}:
                            if new_utxo_key not in account_dic['utxos']:
                                account_dic['total']+=normal_round(new_utxo_value_output['amount'],ROUND_VALUE_DIGIT)
                                account_dic['utxos'].append(new_utxo_key)
                                account_dic['utxos_data'][new_utxo_key]={}
                                account_dic['utxos_data'][new_utxo_key]['output']=new_utxo_value_output
                                account_dic['utxos_data'][new_utxo_key]['input']=new_utxo_value_input
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
                                except:
                                    if old_utxo_account!=account:account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                        
                                if old_utxo_account!=account:self.update_old_utxo_key(old_utxo_account,old_utxo_key,new_utxo_key,new_utxo_value_output)
                            
                                account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                                self.current_master_state[account]=account_dic
                        else:
                            account_dic['total']+=normal_round(new_utxo_value_output['amount'],ROUND_VALUE_DIGIT)
                            account_dic['utxos'].append(new_utxo_key)
                            account_dic['utxos_data'][new_utxo_key]={}
                            account_dic['utxos_data'][new_utxo_key]['output']=new_utxo_value_output
                            account_dic['utxos_data'][new_utxo_key]['input']=new_utxo_value_input
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
                            except:
                                if old_utxo_account!=account:account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                        
                            if old_utxo_account!=account:self.update_old_utxo_key(old_utxo_account,old_utxo_key,new_utxo_key,new_utxo_value_output)
                            account_dic['balance']['credit'][new_utxo_key]=new_utxo_value_output
                            self.current_master_state[account]=account_dic
                    else:
                        #account_list[0] is the Smart Contract account
                        #account_list[1 and + ] are the other account associated to that Smart Contrat
                        if marketplace_transaction_flag is True:
                            #this is a marketplace transaction
                            if account_list[0] not in account_dic['marketplace']:account_dic['marketplace'].append(account_list[0])
                        elif smart_contract_transaction_flag is True:
                            #this is a smart contract transaction
                            if account_list[0] not in account_dic['smart_contract']:account_dic['smart_contract'].append(account_list[0])
                        self.current_master_state[account]=account_dic

                #Removal of association between some account and this SmartContract
                account_list=self.extract_account_list_from_locking_script("OP_DEL_SC",utxo)
                for account in account_list:
                    smart_contract_account=utxo["smart_contract_account"]
                    account_2_remove_dic=self.current_master_state[account]
                    if smart_contract_account in account_2_remove_dic['marketplace']:
                        account_2_remove_dic['marketplace'].remove(smart_contract_account)
                        self.current_master_state[account]=account_2_remove_dic
                    
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
                logging.info(f"**** Transaction7: {e}")
                logging.exception(e)

    

    def store_master_state_in_memory(self):
        try:
            for account in self.current_master_state.keys():
                new_master_state={}
                current_master_state = {}
                new_master_state[account]=self.current_master_state[account]
                #saving the file
                if self.temporary_save_flag is True:
                    #on a temporary file for LeaderNode
                    self.temporary_storage_sharding.store(account,new_master_state[account])
                else:
                    self.storage_sharding.store(account,new_master_state[account])
        except Exception as e:
            logging.info(f"**** Transaction7: {e}")

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
                account_list.append(element)
            #Step 2 list for specific OP like OP_SC, OP_DEL_SC
            if element.startswith(op_elem):flag_for_adding=True
            elif flag_for_adding is True:
                op_elem_account_list.append(element)
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

