from Crypto.Hash import RIPEMD160, SHA256
import logging
from datetime import datetime
import random
from common.smart_contract_script import carriage_code_script



def calculate_hash(data, hash_function: str = "sha256") -> str:
    """
    Calculate the hash of a string
    """
    data = bytearray(data, "utf-8")
    if hash_function == "sha256":
        h = SHA256.new()
        h.update(data)
        return h.hexdigest()
    if hash_function == "ripemd160":
        h = RIPEMD160.new()
        h.update(data)
        return h.hexdigest()


def normal_round(num, ndigits=0):
    """
    Rounds a float to the specified number of decimal places.
    num: the value to round
    ndigits: the number of digits to round to
    """
    if ndigits == 0:
        return int(num + 0.5)
    else:
        digit_value = 10 ** ndigits
        return int(num * digit_value + 0.5) / digit_value


def convert_str_2_bool(string):
    """
    Convert the string value in boolean
    """
    if string=="True":bool=True
    elif string=="False":bool=False
    else:bool=None
    return bool

def clean_request(d: dict) -> dict:
    """
    Hack replacing the following value in Flask request:
    true => True, 
    false => False, 
    none => None, 
    """
    return dict_replace_value(d)

def dict_replace_value(d: dict) -> dict:
    """
    Function used by clean_request function
    """
    x = {}
    for k, v in d.items():
        if v=="true":v=True
        elif v=="false":v=False
        elif v=="none":v=None
        elif isinstance(v, dict):
            v = dict_replace_value(v)
        elif isinstance(v, list):
            v = list_replace_value(v)
        x[k] = v
    return x


def list_replace_value(l: list) -> list:
    """
    Function used by dict_replace_value function
    """
    x = []
    for e in l:
        if e=="true":v=True
        elif e=="false":v=False
        elif e=="none":v=None
        elif isinstance(e, list):
            e = list_replace_value(e)
        elif isinstance(e, dict):
            e = dict_replace_value(e)
        x.append(e)
    return x



def check_marketplace_raw(outputs,step, *args, **kwargs):
    """
    Flag used by check_smart_contract_consistency 
    to avoid checking one input for all MarketPlace 1 request
    """
    check_user_flag=kwargs.get('check_user_flag',True)
    
    marketplace_place_step_flag=False
    new_user_flag=None
    try:
        for i in range(0,len(outputs)):
            try:
                if outputs[i]['marketplace_transaction_flag'] is True:
                    smart_contract_memory=outputs[i]['smart_contract_memory']
                    #example of smart_contract_memory
                    #['MarketplaceRequest', 'mp_request_step2_done', 
                    #['account', 'step', 'timestamp', 'requested_amount', 'requested_currency', 'requested_deposit', 'buyer_public_key_hash', 'buyer_public_key_hex', 'requested_nig', 'timestamp_nig', 'seller_public_key_hex', 'seller_public_key_hash', 'encrypted_account', 'mp_request_signature', 'mp_request_id', 'previous_mp_request_name', 'mp_request_name', 'seller_safety_coef', 'smart_contract_ref'], 
                    #['531c2e528bd177866f7213b192833846018686e5', 1, 1694581434.188025, 1.0, 'EUR', None, '531c2e528bd177866f7213b192833846018686e5', 'xdfsdsd', 0.338, 1694581434.189025, None, None, None, None, 39464617, None, 'mp_request_step2_done', 2, 'a08fe9d2421e8b94ae8647cbabb81e5ad3018601']]
                    for j in range(0,len(smart_contract_memory[0][2])):
                        if smart_contract_memory[0][2][j]=='step':
                            if smart_contract_memory[0][3][j]==step:
                                marketplace_place_step_flag=True
                                #logging.info(f"======> MarketPlace {step}")
                        if smart_contract_memory[0][2][j]=='new_user_flag':
                            new_user_flag=smart_contract_memory[0][3][j]
                            #logging.info(f"======> new_user_flag {new_user_flag}")
            except:pass
    except:pass
    if step==1 and marketplace_place_step_flag is True and check_user_flag is True: 
        #specific check for Step1 with New User
        #because the Input transaction doesn't need to be checked in that case
        #but it needs ot be checked if this is not a new user
        if new_user_flag=="False" or new_user_flag is False or new_user_flag=="false":marketplace_place_step_flag=False

    return marketplace_place_step_flag

def extract_marketplace_account(outputs):
    """
    Retrieve the smart_contract_account out of marketplace request
    """
    marketplace_place_account=None
    try:
        for i in range(0,len(outputs)):
            try:
                marketplace_place_account=outputs[i]['smart_contract_account']
            except:pass
    except:pass
    return marketplace_place_account


def check_marketplace_step1_sell(outputs, *args, **kwargs):
    """
    Check if the output of a transaction is a MarketPlace sell request (step = -1)
    """
    return check_marketplace_raw(outputs,-1, *args, **kwargs)

def check_marketplace_step1_buy(outputs, *args, **kwargs):
    """
    Check if the output of a transaction is a MarketPlace buy request (step = 1)
    """
    return check_marketplace_raw(outputs,1, *args, **kwargs)


def check_marketplace_step(step,outputs):
    """
    Check if the output of a transaction is a MarketPlace in a specific number request
    """
    return check_marketplace_raw(outputs,step)

def check_marketplace_step15(outputs):
    """
    Check if the output of a transaction is a MarketPlace 15 request
    """
    return check_marketplace_raw(outputs,15)

def check_marketplace_step2(outputs):
    """
    Check if the output of a transaction is a MarketPlace 2 request
    """
    return check_marketplace_raw(outputs,2)

def check_carriage_request(outputs):
    """
    Check if the output of a transaction is a Carriage request for MarketPlace step 1 request
    """
    check1=check_marketplace_raw(outputs,10)
    check2=check_marketplace_raw(outputs,60)
    if check1 is True or check2 is True: return True
    else: return False


def check_smart_contract_consistency(transaction):
    """
    To ensure the consistency of the SmartContract:
    only 1 input, only 1 output except for marketplace_step 2 which can have several inputs
    ,transaction_hash of input of new transaxction = UTXO of SmartContrat
    """
    smart_contract_flag=False
    smart_contract_error_list=[]
    inputs=transaction['inputs']
    outputs=transaction['outputs']
    if "smart_contract_flag" in str(transaction):
        if 'BlockVote' in str(outputs) and inputs==[]:
            #specific process for initial BlockVote transaction at Block Creation
            #no need to check
            pass
        else:
            #check inputs
            if check_marketplace_step1_buy(outputs,check_user_flag=False) is False and check_marketplace_step1_sell(outputs,check_user_flag=False) is False and check_marketplace_step15(outputs) is False and check_marketplace_step2(outputs) is False:
                if len(inputs)>1:
                    smart_contract_flag="error"
                    smart_contract_error_list.append(["More than 1 input"])

            #check outputs
            smart_contract_counter=0
            for i in range(len(outputs)):
                try:
                    outputs[i]['smart_contract_flag']
                    smart_contract_counter+=1
                except:
                    pass
            if smart_contract_counter>1:
               smart_contract_flag="error"
               smart_contract_error_list.append(["More than 1 SmartContract in Output"])
                
    return smart_contract_flag,smart_contract_error_list




def retrieve_buyer_seller(outputs):
    """
    Retrieve the buyer_public_key_hash and seller_public_key_hash of the output of a transaction
    """
    buyer=None
    seller=None
    try:
        for i in range(0,len(outputs)):
            try:
                if outputs[i]['marketplace_transaction_flag'] is True:
                    smart_contract_memory=outputs[i]['smart_contract_memory']
                    #example of smart_contract_memory
                    #['MarketplaceRequest', 'mp_request_step2_done', 
                    #['account', 'step', 'timestamp', 'requested_amount', 'requested_currency', 'requested_deposit', 'buyer_public_key_hash', 'buyer_public_key_hex', 'requested_nig', 'timestamp_nig', 'seller_public_key_hex', 'seller_public_key_hash', 'encrypted_account', 'mp_request_signature', 'mp_request_id', 'previous_mp_request_name', 'mp_request_name', 'seller_safety_coef', 'smart_contract_ref'], 
                    #['531c2e528bd177866f7213b192833846018686e5', 1, 1694581434.188025, 1.0, 'EUR', None, '531c2e528bd177866f7213b192833846018686e5', 'xdfsdsd', 0.338, 1694581434.189025, None, None, None, None, 39464617, None, 'mp_request_step2_done', 2, 'a08fe9d2421e8b94ae8647cbabb81e5ad3018601']]
                    for j in range(0,len(smart_contract_memory[0][2])):
                        if smart_contract_memory[0][2][j]=='buyer_public_key_hash':buyer=smart_contract_memory[0][3][j]
                        if smart_contract_memory[0][2][j]=='seller_public_key_hash':seller=smart_contract_memory[0][3][j]
            except:pass
    except:pass
    return buyer,seller


def check_contest_refresh_score(transaction):
    """to check if the transaction needs to trigger a refresh of the score.
    return the list of account to refresh.
    """
    logging.info(f"###INFO check_contest_refresh_score")
    refresh_score_list=[]
    #CHECK 1 Marketplace Step 4
    outputs=transaction['outputs']
    inputs=transaction['inputs']
    if check_marketplace_raw(outputs,4) is True:
        buyer,seller=retrieve_buyer_seller(outputs)
        if buyer is not None and buyer not in refresh_score_list:refresh_score_list.append(buyer)
        if seller is not None and seller not in refresh_score_list:refresh_score_list.append(seller)
        logging.info(f"###INFO check_contest_refresh_score Marketplace Step 4 buyer:{buyer} seller:{seller} ")

    #CHECK 2 Transfer
    from common.master_state import MasterState
    master_state=MasterState()
    check_input_flag=False
    for i in range(0,len(outputs)):
        try:
            outputs[i]['marketplace_transaction_flag']
            outputs[i]['smart_contract_transaction_flag']
            #this is either a marketplace transaction or a smartcontract which is out of scope
        except Exception as e:
            logging.info(f"###INFO check_contest_refresh_score Transfer")
            logging.exception(e)
            try:
                if outputs[i]['amount']>0:
                    #this is a transfert transaction
                    account_list=master_state.extract_account_list_from_locking_script("OP_HASH160",outputs[i])
                    check_input_flag=True
                    for buyer in account_list:
                        if buyer not in refresh_score_list:refresh_score_list.append(buyer)
                        logging.info(f"###INFO check_contest_refresh_score Transfer buyer:{buyer} ")
            except:
                pass
    if check_input_flag is True:
        for i in range(0,len(inputs)):
            seller=inputs[i]['unlocking_public_key_hash']
            if  seller not in refresh_score_list:
                refresh_score_list.append(seller)
                logging.info(f"###INFO check_contest_refresh_score Transfer seller:{seller} ")

    return refresh_score_list
    

def check_marketplace_reputation_refresh(outputs):
    """
    to check if the reputation of some accounts needs to be refreshed
    """
    reputation_refresh_flag=False
    buyer_public_key_hash=None
    seller_public_key_hash=None
    try:
        for i in range(0,len(outputs)):
            try:
                if outputs[i]['marketplace_transaction_flag'] is True:
                    smart_contract_memory=outputs[i]['smart_contract_memory']
                    #example of smart_contract_memory
                    #['MarketplaceRequest', 'mp_request_step2_done', 
                    #['account', 'step', 'timestamp', 'requested_amount', 'requested_currency', 'requested_deposit', 'buyer_public_key_hash', 'buyer_public_key_hex', 'requested_nig', 'timestamp_nig', 'seller_public_key_hex', 'seller_public_key_hash', 'encrypted_account', 'mp_request_signature', 'mp_request_id', 'previous_mp_request_name', 'mp_request_name', 'seller_safety_coef', 'smart_contract_ref'], 
                    #['531c2e528bd177866f7213b192833846018686e5', 1, 1694581434.188025, 1.0, 'EUR', None, '531c2e528bd177866f7213b192833846018686e5', 'xdfsdsd', 0.338, 1694581434.189025, None, None, None, None, 39464617, None, 'mp_request_step2_done', 2, 'a08fe9d2421e8b94ae8647cbabb81e5ad3018601']]
                    for j in range(0,len(smart_contract_memory[0][2])):
                        if smart_contract_memory[0][2][j]=='step':
                            if smart_contract_memory[0][3][j]==4 or smart_contract_memory[0][3][j]==45 or smart_contract_memory[0][3][j]==66 or smart_contract_memory[0][3][j]==98:
                                reputation_refresh_flag=True
                        if smart_contract_memory[0][2][j]=='buyer_public_key_hash':buyer_public_key_hash=smart_contract_memory[0][3][j]
                        if smart_contract_memory[0][2][j]=='seller_public_key_hash':seller_public_key_hash=smart_contract_memory[0][3][j]
            except:pass
    except:pass
    return reputation_refresh_flag,[buyer_public_key_hash,seller_public_key_hash]


def get_carriage_transaction(mp_account,requested_amount,requested_gap,sc,next_mp):
    '''SmartContract use to carriage a step 1 (buy request) or -1 (sell request) transaction in the Marketplace
    '''
    from common.smart_contract import SmartContract
    from common.transaction import Transaction
    from common.transaction_output import TransactionOutput
    from common.transaction_input import TransactionInput
    from node.main import marketplace_owner
    payload=f'''
requested_amount="{requested_amount}"
requested_gap="{requested_gap}"
sc="{sc}"
next_mp="{next_mp}"
'''+carriage_code_script
    smart_contract_block=SmartContract(mp_account,
                                smart_contract_sender=marketplace_owner.public_key_hash,
                                smart_contract_new=True,
                                smart_contract_gas=1000000,
                                smart_contract_type="source",
                                payload=payload)
    smart_contract_block.process()
    
    from common.io_blockchain import BlockchainMemory
    blockchain_memory = BlockchainMemory()
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    utxo_dict=blockchain_base.get_user_utxos(mp_account)

    
    unlocking_public_key_hash=marketplace_owner.public_key_hash+" SC "+mp_account

    #default input value in case of new carriage request
    transaction_hash="abcd1234"
    output_index=0
    for utxo in utxo_dict['utxos']:
        #input value in case of existing carriage request
        transaction_hash=utxo['transaction_hash']
        output_index=utxo['output_index']
        break
   
    input_1 = TransactionInput(transaction_hash=transaction_hash, output_index=output_index,unlocking_public_key_hash=unlocking_public_key_hash)
    output_1 = TransactionOutput(list_public_key_hash=[mp_account], 
                                            amount=0,
                                            account_temp=True,
                                            smart_contract_transaction_flag=False,
                                            marketplace_transaction_flag=True,
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
                                            smart_contract_previous_transaction=smart_contract_block.smart_contract_previous_transaction)
    transaction_1 = Transaction([input_1], [output_1])
    transaction_1.sign(marketplace_owner)
    return transaction_1

def get_carriage_transaction_to_delete(sc_to_delete):
    '''Delete the SmartContract use to carriage a step 1 transaction in the Marketplace
    '''
    try:
        locals()['smart_contract']
    except:
        pass
    logging.info(f"### INFO get_carriage_transaction_to_delete sc:{sc_to_delete}")
    from common.master_state import MasterState
    from common.smart_contract import SmartContract
    from common.transaction import Transaction
    from common.transaction_output import TransactionOutput
    from common.transaction_input import TransactionInput
    from node.main import marketplace_owner
    carriage_transaction_list=[]
    master_state=MasterState()
    action_list=["buy","sell"]
    for action in action_list:
        try:
            mp_2_delete_flag,mp_account_to_update,new_next_mp,nb_transactions,mp_account_to_update_data,mp_first_account_to_update_data_flag=master_state.get_delete_mp_account_from_memory(action,sc_to_delete)
            if mp_2_delete_flag is True:
                #a carriage request to be deleted has been found
                mp_account_to_update_flag=False
                try:
                    if mp_account_to_update_data['sc'] is not None and mp_account_to_update_data['sc']!='None':mp_account_to_update_flag=True
                except:
                    pass
            
                if mp_account_to_update_flag is True:

                    from common.smart_contract import load_smart_contract_from_master_state
                    smart_contract_previous_transaction,smart_contract_transaction_hash,smart_contract_transaction_output_index=load_smart_contract_from_master_state(mp_account_to_update)
                    if nb_transactions<=1:
                        payload=f'''
memory_obj_2_load=['carriage_request']
carriage_request.reset()
memory_list.add([carriage_request,'carriage_request',['step','requested_amount','requested_gap','requested_currency','sc','next_mp']])
'''
                    else:
                        if mp_first_account_to_update_data_flag is True:
                            requested_amount=mp_account_to_update_data["amount"]
                            requested_gap=mp_account_to_update_data["gap"]
                            sc=mp_account_to_update_data["sc"]
                            next_mp=mp_account_to_update_data["next_mp"]
                            payload=f'''
memory_obj_2_load=['carriage_request']
carriage_request.step=10
carriage_request.requested_amount="{requested_amount}"
carriage_request.requested_gap="{requested_gap}"
carriage_request.sc="{sc}"
carriage_request.next_mp="{next_mp}"
memory_list.add([carriage_request,'carriage_request',['step','requested_amount','requested_gap','requested_currency','sc','next_mp']])
'''
                        else:
                            payload=f'''
memory_obj_2_load=['carriage_request']
carriage_request.step=10
carriage_request.next_mp="{new_next_mp}"
memory_list.add([carriage_request,'carriage_request',['step','requested_amount','requested_gap','requested_currency','sc','next_mp']])
'''
                    smart_contract_block=SmartContract(mp_account_to_update,
                                                smart_contract_sender=marketplace_owner.public_key_hash,
                                                smart_contract_new=False,
                                                smart_contract_gas=1000000,
                                                smart_contract_type="source",
                                                payload=payload,
                                                smart_contract_previous_transaction=smart_contract_transaction_hash)
                    smart_contract_block.process()
                    from common.io_blockchain import BlockchainMemory
                    blockchain_memory = BlockchainMemory()
                    blockchain_base = blockchain_memory.get_blockchain_from_memory()
                    utxo_dict=blockchain_base.get_user_utxos(mp_account_to_update)
    
                    unlocking_public_key_hash=marketplace_owner.public_key_hash+" SC "+mp_account_to_update
            
                    transaction_1=None
                    for utxo in utxo_dict['utxos']:
                        #input value in case of existing carriage request
                        input_1 = TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash=unlocking_public_key_hash)
                        output_1 = TransactionOutput(list_public_key_hash=[mp_account_to_update], 
                                                                amount=0,
                                                                account_temp=True,
                                                                smart_contract_transaction_flag=False,
                                                                marketplace_transaction_flag=True,
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
                                                                smart_contract_previous_transaction=smart_contract_block.smart_contract_previous_transaction)
                        transaction_1 = Transaction([input_1], [output_1])
                        break
                    if transaction_1 is not None:
                        transaction_1.sign(marketplace_owner)
                        carriage_transaction_list.append(transaction_1)
        except Exception as e:
            logging.info(f"###ERROR get_carriage_transaction_to_delete  Exception: {e}")
    return carriage_transaction_list

       
def extract_marketplace_request(block):
    #this function is extract the marketplace request out of the list of transaction
    #it's used in integration test
    result=None
    for transaction in block.transactions:
        try:
            for outputs in transaction["outputs"]:
                try:
                    if outputs['marketplace_transaction_flag']=="true" or outputs['marketplace_transaction_flag']=="True" or outputs['marketplace_transaction_flag'] is True:
                        result=transaction
                        break
                except:
                    pass
        except:
            pass
    return result
