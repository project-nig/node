import ast
import logging
from datetime import datetime
from sys import getsizeof
from common.io_blockchain import BlockchainMemory
import json
import sys
import copy


import binascii
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
import random

import requests

from common.values import MARKETPLACE_SELLER_SAFETY_COEF

from common.master_state import MasterState
from common.smart_contract_function import *


smart_contract_memory_full={}

def check_smart_contract(transaction):
    #this function is checking if there are smart Contract in transaction
    smart_contract_flag=False
    smart_contract_index_list=[]
    index=0
    for output in transaction.outputs:
        try:
            output['smart_contract_flag']
            smart_contract_flag=True
            smart_contract_index_list.append(index)
        except:
            pass
        index+=1
    return smart_contract_flag,smart_contract_index_list

def check_double_contract(transaction):
    #this function is checking if there are not double smart Contract 
    ##for the same account in the transaction ouput
    check_double_contract_flag=False
    smart_contract_account_list=[]
    index=0
    for output in transaction.outputs:
        try:
            smart_contract_account=output['smart_contract_account']
            if smart_contract_account not in smart_contract_account_list:smart_contract_account_list.append(smart_contract_account)
            else:
                #There is an issue as it's not allowed to have 2 output transactions for the same smart_contract_account
                check_double_contract_flag=True
                logging.info(f"### ERROR: multiple output transactions for smart_contract_account:{smart_contract_account} ")
        except:
            pass
    return check_double_contract_flag

class SmartContract:
    """
    A class used to manage the SmartContract execution

    ...

    Attributes
    ----------
    smart_contract_account : str

        * the hash string of the smart_contract to manage
    
    smart_contract_type : str

        * api : for read only

        * source : for writing the smart_contrat on the blockchain

    Methods
    -------
    process() :

        * launch the execution of the smart_contrat based on smart_contract_type
    
    """
    def __init__(self,smart_contract_account,*args, **kwargs):
        self.smart_contract_sender=kwargs.get('smart_contract_sender',0)
        self.gas=kwargs.get('smart_contract_gas',0)
        self.smart_contract_type=kwargs.get('smart_contract_type',None)
        self.payload=kwargs.get('payload',"")
        self.smart_contract_account=smart_contract_account
        self.smart_contract_new=kwargs.get('smart_contract_new',False)
        #if self.smart_contract_account is None:self.gas=1000000
        self.gas=1000000
        self.result = None
        self.smart_contract_memory_size=kwargs.get('smart_contract_memory_size',0)
        self.smart_contract_memory=kwargs.get('smart_contract_memory',[])
        self.smart_contract_memory_init=[]
        self.memory_obj_2_load="memory_obj_2_load=[]"
        self.cpu=0
        self.sizeof=0
        self.code_source=None
        
        self.gas_price_cpu_per_sec=100
        self.gas_price_memory=1
        self.gas_ok_flag=True

        self.error_flag=False
        self.error_code=None
        
        self.smart_contract_previous_transaction=kwargs.get('smart_contract_previous_transaction',None)
        self.smart_contract_transaction_hash=kwargs.get('smart_contract_transaction_hash',None)
        #if self.smart_contract_new is False or self.smart_contract_new=='false':

        self.leader_node_flag=kwargs.get('leader_node_flag',False)
        self.block_PoH=kwargs.get('block_PoH',None)
        self.NIGthreading_flag=kwargs.get('NIGthreading_flag',False)

        #cleaning of local variables
        try:del globals()['local_var']
        except:pass
        try:del globals()['get_obj_by_name']
        except:pass
        try:del globals()['check_obj_dic'] 
        except:pass
        self.clean_memory()
        
        #preloaded code with some functions
        self.preloaded_code=f'''
globals()['local_var']=locals()
memory_list=MemoryList("common.smart_contract")
sender="{self.smart_contract_sender}"
'''

        if self.smart_contract_new is False:
            logging.info(f"loading of code source")
            #there is no parameters like Code Version in the Payload
            self.cleaned_payload=self.payload

            #let's load the memory_obj_2_load
            self.load_memory_obj_2_load()
            #let's load the code source and gas
            self.load_code_source()
            if self.error_flag is False:self.load_gas()

        else:
            logging.info(f"no loading of code source as it's a new Smart Contract")
            #code source is preloaded with MemoryList to allow the storing of object in memory
            self.code_source=self.preloaded_code
            #parameters like Code Version are extracted from Payload
            self.cleaned_payload=self.check_1st_payload_parameters(self.payload)
            
        #flag to check if an API call needs to be stored on the blockchain
        self.api_readonly_flag=False

    def check_1st_payload_parameters(self,payload):
        #This function is checking the paramaters at the beginning of the payload for a new contract
        payload_parameter=payload.split('\n')
        parameter_list=[]
        parameter_list_flag=False
        cleaned_payload=payload
        for line in payload_parameter:
            if line.startswith("###VERSION"):parameter_list_flag=True
            if parameter_list_flag is True:parameter_list.append(line)
            if line.startswith("###END"):
                parameter_list.append(line)
                #end of the parameters in the payload
                for elem in parameter_list:
                    cleaned_payload=cleaned_payload.replace(elem,"",1)
                break
        return cleaned_payload

            
    def load_memory_obj_2_load(self):
        memory_obj_2_load=self.payload.split('\n')
        for i in range(0,5):
            try:
                if "memory_obj_2_load" in memory_obj_2_load[i]:
                    #logging.info(f"memory_obj_2_load:{memory_obj_2_load[i]}")
                    self.memory_obj_2_load=memory_obj_2_load[i]
                    break
            except:
                pass

    def load_code_source(self):
        '''Load the code source of the SmartContract in the self.code_source
        '''
        blockchain_memory = BlockchainMemory()
        blockchain_base = blockchain_memory.get_blockchain_from_memory()
        #logging.info(f"#CHECK smart_contract_account:{self.smart_contract_account} smart_contract_transaction_hash {self.smart_contract_transaction_hash}")
        smart_contract_transaction_hash=self.smart_contract_transaction_hash
        #while True:
        code_source_list=[]
        smart_contract_memory_check_dic={}
        for i in range(100):
            try:
                value=load_smart_contract_from_master_state_leader_node(self.smart_contract_account,
                                                                        smart_contract_transaction_hash=smart_contract_transaction_hash,
                                                                        leader_node_flag=self.leader_node_flag,
                                                                        block_PoH=self.block_PoH,
                                                                        NIGthreading_flag=self.NIGthreading_flag)
                #logging.info(f"#CHECK smart_contract_account:{self.smart_contract_account} smart_contract_transaction_hash:{smart_contract_transaction_hash} leader_node_flag:{self.leader_node_flag} value:{value} ")
                smart_contract_new=value['smart_contract_new']
                if value['smart_contract_type']=="source":
                    self.smart_contract_memory=value['smart_contract_memory']
                    #self.smart_contract_memory.extend(value['smart_contract_memory'])
                    #logging.info(f"######CHECK value['smart_contract_memory']:{value['smart_contract_memory']}")
                    #logging.info(f"######CHECK self.smart_contract_memory:{self.smart_contract_memory}")
                    for smart_contract_memory_obj in value['smart_contract_memory']:
                        memory_obj_2_load_check=eval(self.memory_obj_2_load[18:len(self.memory_obj_2_load)])
                        #logging.info(f"######CHECK memory_obj_2_load_check:{memory_obj_2_load_check}")
                        #Step 1 loading of smart_contract_memory_init used to load the object in the source code of the Smart Contract
                        if any(smart_contract_memory_obj[1] in s for s in memory_obj_2_load_check):
                            try:
                                smart_contract_memory_check_dic[smart_contract_memory_obj[1]]
                            except:
                                self.smart_contract_memory_init.append(smart_contract_memory_obj)
                                smart_contract_memory_full[smart_contract_memory_obj[1]]=smart_contract_memory_obj
                                smart_contract_memory_check_dic[smart_contract_memory_obj[1]]=True

                        #Step 2 loading of smart_contract_memory_full used to load all the object in case it needs to be reloaded in the source code of the Smart Contract
                        try:
                            smart_contract_memory_check_dic[smart_contract_memory_obj[1]]
                        except:
                            smart_contract_memory_full[smart_contract_memory_obj[1]]=smart_contract_memory_obj
                            smart_contract_memory_check_dic[smart_contract_memory_obj[1]]=True
                
                smart_contract_transaction_hash=value['smart_contract_previous_transaction']
                #logging.info(f"#CHECK smart_contract_transaction_hash:{smart_contract_transaction_hash} value: {value}")
                #logging.info(f"#CHECK smart_contract_new:{smart_contract_new} {smart_contract_new is True}")
                if smart_contract_new is True:
                    code_source_list.append("""
"""
f"memory_obj_list={self.smart_contract_memory_init}")
                    code_source_list.append("""
for obj_list in memory_obj_list:
    obj_name=str(obj_list[1])
    try:
        check_obj_dic[obj_name]
    except Exception as e:
        try:
            obj_list[1]=locals()[obj_name]
        except Exception as e:
            obj_list[1]=locals()[obj_list[0]]()
        check_obj_dic[obj_name]=True
            
        for i in range(len(obj_list[2])):
            setattr(obj_list[1],obj_list[2][i],obj_list[3][i])
        globals()[obj_name]=obj_list[1]
    """)                
                    check_obj_dic="""
check_obj_dic={}
def get_obj_by_name(obj_name):
    result=None
    try:
        result=globals()['local_var'][obj_name]
    except:
        obj_list=LOAD_OBJ(obj_name)
        try:
            obj_list[1]=globals()['local_var'][obj_list[0]]()
        except Exception as e:
            print(f"@@@@@@ ERROR 2: {obj_list[0]} {e}")
        for i in range(len(obj_list[2])):
            setattr(obj_list[1],obj_list[2][i],obj_list[3][i])
        globals()[obj_name]=obj_list[1]
        result=obj_list[1]
    return result
globals()['get_obj_by_name']=locals()['get_obj_by_name']
"""
                    code_source_list.insert(0, check_obj_dic)
                    code_source_list.insert(0, self.check_1st_payload_parameters(value['smart_contract_payload']))
                    #code_source_list.insert(0, value['smart_contract_payload'])
                    break
            except Exception as e:
                #issue with the loading of source of  of the SmartContract
                logging.info(f"**** ISSUE loading source of SmartContract: {self.smart_contract_account}")
                logging.exception(e)
                self.error_flag=True
                self.error_code=e

        #code source is preloaded with MemoryList to allow the storing of object in memory
        self.code_source=self.preloaded_code
        #code_source_list.reverse()
        #logging.info(f"#CHECK code_source_list:{code_source_list}")
        for code_source in code_source_list:
            self.code_source+=code_source

        #we take a snapchot of the memory before processing the smartcontract
        #to make a delta after the processing and so store only the delta in the blockchain
        #logging.info(f"#CHECK smart_contract_memory_init:{self.smart_contract_memory_init}")


    def load_gas(self):
        blockchain_memory = BlockchainMemory()
        blockchain_base = blockchain_memory.get_blockchain_from_memory()
        #logging.info(f"#CHECK gas smart_contract_account:{self.smart_contract_account} smart_contract_transaction_hash {self.smart_contract_transaction_hash}")
        value=blockchain_base.get_smart_contract_api(self.smart_contract_account,
                                                     smart_contract_transaction_hash=self.smart_contract_transaction_hash,
                                                     block_PoH=self.block_PoH)
        self.gas=value['smart_contract_gas']
        
    def run_source(self,new_source,*args, **kwargs):
        reset_source = kwargs.get('reset_source',False)
        code_source=self.code_source
        if code_source is None or reset_source is True:code_source=new_source
        else:code_source+=new_source
        self.run_smart_contract(code_source)
        self.gas_ok_flag=True
        if self.gas_ok_flag is True:
            #there is enough gas
            #the code source is updated
            self.code_source=code_source
            #logging.info(f"##############CHECK code_source:{code_source}")
        else:
            #there is not enough gas
            #the code source is not updated
            self.raise_not_enough_gas(new_source)

        #cleaning of the memory in globals()
        self.clean_memory()


    def run_api(self,function):
        check_memory_start=str(self.smart_contract_memory)
        #print(f"START {check_memory_start} self.smart_contract_memory:{self.smart_contract_memory}")
        
        self.run_smart_contract(self.code_source+function)
        if self.gas_ok_flag is True:
            #there is enough gas
            #logging.info(f"##############CHECK code_source:{self.code_source+function}")
            #if self.result is not None:print(self.result)
            pass
        else:
            self.raise_not_enough_gas(function)
        
        check_memory_end=str(self.smart_contract_memory)
        #print(f"END {check_memory_end} self.smart_contract_memory:{self.smart_contract_memory}")
        #logging.info(f"===API CALL check memory. check:{check_memory_start==check_memory_end} check_memory_start:{check_memory_start} check_memory_end:{check_memory_end}")
        if check_memory_start==check_memory_end:
            #this API call is not changing the memory state
            #no need to store it on the blockain
            self.api_readonly_flag=True

        #cleaning of the memory in globals()
        self.clean_memory()
            
        
    def raise_not_enough_gas(self,expr):
        logging.info(f"#ERROR not enough GAS for Smart Contract for {expr}")
        print(f"#ERROR not enough GAS for Smart Contract for {expr}")

    def process(self):
        #logging.info(f"=====self.payload:{self.payload}")
        #a procedure is added as last line to read the object to be stored
        #process_memory="""memory_list.get_memory_obj_list()"""
        process_memory=f"""memory_list.get_memory_obj_list({self.smart_contract_memory_init})"""
        if self.smart_contract_type == "source":self.run_source(self.cleaned_payload+process_memory)
        if self.smart_contract_type == "api":self.run_api(self.payload+process_memory)
        smart_contract_memory_full={}
        


    def run_smart_contract(self,expr):
        self.result=None
        if self.gas_ok_flag is True:
            try:
                #launch of the Smart Contract
                start = datetime.now()
                #print(f"===== expr:{expr}")
                tree = ast.parse(expr)
                eval_expr = ast.Expression(tree.body[-2].value)
                eval_expr_memory = ast.Expression(tree.body[-1].value)
                exec_expr = ast.Module(tree.body[:-2],type_ignores=[])
                exec(compile(exec_expr, 'file', 'exec'))
                self.result=eval(compile(eval_expr, 'file', 'eval'))
                self.smart_contract_memory=eval(compile(eval_expr_memory, 'file', 'eval'))
                end = datetime.now()
                self.smart_contract_memory_size=getsizeof(tree)
                self.smart_contract_memory_size+=getsizeof(self.code_source)
                self.cpu=(end-start).total_seconds()
                self.burn_gas()
                logging.info(f"operation in {self.cpu} sec / memory {self.smart_contract_memory_size} / gas {int(self.gas)}")
            except Exception as e:
                #issue with the processing of the SmartContract
                logging.info(f"**** ISSUE run_smart_contract: {self.smart_contract_account}")
                logging.exception(e)
                self.error_flag=True
                self.error_code=e

    def clean_memory(self):
        #clean the variable in globals()
        process_memory_list=[self.smart_contract_memory,self.smart_contract_memory_init]
        for process_memory in process_memory_list:
            try:
                for obj_list in process_memory:
                    try:
                        obj_name=str(obj_list[1])
                        del globals()[obj_name]
                    except:pass
            except:pass
           

    def burn_gas(self):
        self.gas-=self.gas_price_cpu_per_sec*self.cpu
        self.gas-=self.gas_price_memory*self.smart_contract_memory_size
        if self.gas<0:self.gas_ok_flag=False




class Memory:
    def __init__(self,module_name):
        self.__module_name=module_name

    def set_memory_process(self,obj_list_init,smart_contract_memory_init):
        #obj_list=[obj_class,obj_name,[attribut1,attribut2,...],[attribut1_value,attribut2_value,...]]
        # ex: obj_list=[token,'token',['token_total','token_name','balanceOf']]
        value_list=[]
        obj_list = copy.deepcopy(obj_list_init)
        #print(f"CHECK obj_list:{obj_list}")
        for attribut in obj_list[2]:
            attribut_value=getattr(obj_list[0],attribut)
            attribut_value_init=self.get_smart_contract_memory_init_attribut_value(obj_list[1],attribut,smart_contract_memory_init)
            if attribut_value_init is None or attribut_value!=attribut_value_init:
                #there is at least a new value for this attribut, we need to add it on the memory
                for attribut2 in obj_list[2]:value_list.append(getattr(obj_list[0],attribut2))
                break
        if value_list!=[]:
            #there is value to be stored on the memory
            obj_list.append(value_list)
            obj_list.insert(1,obj_list[0].__class__.__name__)
            obj_list.pop(0)
            #print(f"CHECK obj_list NEW value")
            return obj_list
        else:
            #there is no new value to be stored on the memory
            #print(f"CHECK obj_list NO value")
            return None
        
    def get_smart_contract_memory_init_attribut_value(self,obj_name,attribut,smart_contract_memory_init):
        #obj_list=[obj_class,obj_name,[attribut1,attribut2,...],[attribut1_value,attribut2_value,...]]
        #smart_contract_memory_init=[obj_list1,obj_list2,..]
        obj_list_attribut_value=None
        for obj_list in smart_contract_memory_init:
            if obj_name==obj_list[1]:
                for i in range(0,len(obj_list[2])):
                    obj_list_attribut=obj_list[2][i]
                    obj_list_attribut_value=obj_list[3][i]
                    if attribut==obj_list_attribut:
                        return obj_list_attribut_value
                        break





class MemoryList:
    def __init__(self,module_name):
        self.module_name=module_name
        self.obj_name_check=[]
        self.memory_obj_list=[]

    def get_memory_obj_list(self,smart_contract_memory_init):
        memory_obj_list_live=[]
        for obj_list in self.memory_obj_list:
            memory_obj=Memory(self.module_name)
            obj_list_checked=memory_obj.set_memory_process(obj_list,smart_contract_memory_init)
            if obj_list_checked is not None:memory_obj_list_live.append(obj_list_checked)
        return memory_obj_list_live

    def add(self,obj_list):
        #obj_list=[obj_class,obj_name,[attribut1,attribut2,...],[attribut1_value,attribut2_value,...]]
        # ex: obj_list=[token,'token',['token_total','token_name','balanceOf']]
        if obj_list[1] not in self.obj_name_check: 
            self.obj_name_check.append(obj_list[1])
            self.memory_obj_list.append(obj_list)


def GET_SELLER_SAFETY_COEF():
    #coef multiply to the amount to ensure that the seller will confirm step4
    return MARKETPLACE_SELLER_SAFETY_COEF

def CONVERT_2_NIG(requested_amount,timestamp_nig,currency):
    #function to convert the request amount into nig
    from node.main import calculate_nig_rate
    from common.values import ROUND_VALUE_DIGIT
    from common.utils import normal_round
    nig_rate=calculate_nig_rate(timestamp=timestamp_nig,currency=currency)
    requested_nig=normal_round(requested_amount/nig_rate,ROUND_VALUE_DIGIT)
    return requested_nig

        
def LOAD_OBJ(obj_name):
    #provide the smart_contract_memory_obj of obj_name
    #print(f"@@@@@@ smart_contract_memory_full: {smart_contract_memory_full}")
    #print(f"@@@@@@ obj_name: {obj_name}")
    try:
        result=smart_contract_memory_full[obj_name]
    except:
        result=None
    return result




def CHECK_UTXO_BALANCE(public_key_hash,public_key_hash_to_check):
    blockchain_memory = BlockchainMemory()
    #logging.info(f"### check_utxo_balance {public_key_hash}")
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    utxo_balance=blockchain_base.get_user_utxos_balance(public_key_hash)
    amount=0
    for utxo in utxo_balance['utxos']:
        if public_key_hash_to_check in utxo['account_credit_list']:
            amount+=utxo['amount']
    return amount


def load_smart_contract(public_key_hash):
    from common.values import MY_HOSTNAME
    logging.info(f"public_key_hash=>:{public_key_hash}")
    utxo_url='http://'+MY_HOSTNAME+'/smart_contract_api/'+public_key_hash
    resp = requests.get(utxo_url)
    smart_contract_dict = resp.json()
    #logging.info(f"### smart_contract_dict: {smart_contract_dict}")
    smart_contract_previous_transaction=smart_contract_dict['smart_contract_previous_transaction']
    smart_contract_transaction_hash=smart_contract_dict['smart_contract_transaction_hash']
    #logging.info(f"CHECK load_smart_contract / public_key_hash:{public_key_hash} smart_contract_previous_transaction:{smart_contract_previous_transaction} smart_contract_transaction_hash:{smart_contract_transaction_hash}")
    return smart_contract_previous_transaction,smart_contract_transaction_hash

def load_smart_contract_from_master_state(public_key_hash,*args, **kwargs):
    leader_node_flag=kwargs.get('leader_node_flag',False)
    block_PoH=kwargs.get('block_PoH',None)
    NIGthreading_flag=kwargs.get('NIGthreading_flag',False)
    smart_contract_previous_transaction=None
    smart_contract_transaction_hash=None
    smart_contract_transaction_output_index=None
    #this function is used to directly access masterState bypassing the blockchain
    #it's faster and mandatory for LeaderNode in order to process a huge nb of SmartContract per second
    smart_contract_content=load_smart_contract_from_master_state_leader_node(public_key_hash,
                                                                             leader_node_flag=leader_node_flag,
                                                                             block_PoH=block_PoH,
                                                                             NIGthreading_flag=NIGthreading_flag)
    if smart_contract_content!={}:
        #logging.info(f"### smart_contract_account:{public_key_hash} smart_contract_previous_transaction:{smart_contract_previous_transaction}")
        smart_contract_previous_transaction=smart_contract_content['smart_contract_previous_transaction']
        smart_contract_transaction_hash=smart_contract_content['smart_contract_transaction_hash']
        smart_contract_transaction_output_index=smart_contract_content['output_index']
        if smart_contract_previous_transaction is not None:smart_contract_previous_transaction=smart_contract_previous_transaction
        if smart_contract_transaction_hash is not None:smart_contract_transaction_hash=smart_contract_transaction_hash
    return smart_contract_previous_transaction,smart_contract_transaction_hash,smart_contract_transaction_output_index



def load_smart_contract_from_master_state_leader_node(public_key_hash,*args, **kwargs):
    smart_contract_transaction_hash=kwargs.get('smart_contract_transaction_hash',None)
    leader_node_flag=kwargs.get('leader_node_flag',False)
    NIGthreading_flag=kwargs.get('NIGthreading_flag',False)
    block_PoH=kwargs.get('block_PoH',None)
    #logging.info(f"CHECK smart_contract_transaction_hash: {smart_contract_transaction_hash}")
    #logging.info(f"CHECK smart_contract_data smart_contract_transaction_hash: {smart_contract_transaction_hash}")
    #this function is used to directly access masterState bypassing the blockchain
    #it's faster and mandatory for LeaderNode in order to process a huge nb of SmartContract per second
    smart_contract_content={}
    master_state=MasterState()
    #master_state.get_master_state_from_memory_from_user(public_key_hash,block_PoH="TempBlockPoH")
    master_state.get_master_state_from_memory_from_user(public_key_hash,
                                                        leader_node_flag=leader_node_flag,
                                                        block_PoH=block_PoH,
                                                        NIGthreading_flag=NIGthreading_flag)
    try:
        smart_contract_data=master_state.current_master_state[public_key_hash]
        #logging.info(f"CHECK smart_contract_content: {public_key_hash} {smart_contract_data}")
        if smart_contract_transaction_hash is None:
            smart_contract_utxo_key=smart_contract_data["utxos"][len(smart_contract_data["utxos"])-1]
            smart_contract_content=smart_contract_data["utxos_data"][smart_contract_utxo_key]['output']
        else:
            sc_list=smart_contract_data["balance"]["credit"].keys()
            #logging.info(f"CHECK smart_contract_data key: {sc_list}")
            for transaction_hash in smart_contract_data["balance"]["credit"].keys():
                if transaction_hash==smart_contract_transaction_hash:smart_contract_content=smart_contract_data["balance"]["credit"][transaction_hash]
    except Exception as e:
        logging.info(f"**** ISSUE load_smart_contract_from_master_state_leader_node: {public_key_hash}")
        logging.exception(e)
    new_smart_contract_content={}
    for key in smart_contract_content.keys():
        if key.startswith('smart_contract') is True:
            new_smart_contract_content[key]=smart_contract_content[key]
    #logging.info(f"CHECK smart_contract_content: {smart_contract_content}")
    try:
        new_smart_contract_content['output_index']=smart_contract_content['output_index']
    except:
        pass
    try:
        new_smart_contract_content['total']=smart_contract_content['amount']
    except:
        pass

    #logging.info(f"CHECK smart_contract_data: {public_key_hash} {smart_contract_content}")
    return new_smart_contract_content


def create_smart_contract(smart_contract_public_key_hash,sender_public_key_hash,payload):
    smart_contract_dict={}
    smart_contract=SmartContract(smart_contract_public_key_hash,
                                 smart_contract_sender=sender_public_key_hash,
                                 smart_contract_type='source',
                                 payload=payload,
                                 smart_contract_new=True)

    smart_contract.process()
    if smart_contract.error_flag is False:
        smart_contract_dict['smart_contract_account']=smart_contract.smart_contract_account
        smart_contract_dict['smart_contract_sender']=smart_contract.smart_contract_sender
        smart_contract_dict['smart_contract_new']=True
        smart_contract_dict['smart_contract_flag']=True
        smart_contract_dict['smart_contract_gas']=smart_contract.gas
        smart_contract_dict['smart_contract_memory']=smart_contract.smart_contract_memory
        smart_contract_dict['smart_contract_memory_size']=smart_contract.smart_contract_memory_size
        smart_contract_dict['smart_contract_type']=smart_contract.smart_contract_type
        smart_contract_dict['smart_contract_payload']=smart_contract.payload
        smart_contract_dict['smart_contract_result']=smart_contract.result
        smart_contract_dict['smart_contract_previous_transaction']=smart_contract.smart_contract_previous_transaction
        smart_contract_dict['smart_contract_transaction_hash']=smart_contract.smart_contract_transaction_hash
    smart_contract_dict['smart_contract_error_flag']=smart_contract.error_flag
    smart_contract_dict['smart_contract_error_code']=str(smart_contract.error_code)
    return smart_contract_dict