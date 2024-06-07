from Crypto.Hash import RIPEMD160, SHA256
import logging


def calculate_hash(data, hash_function: str = "sha256") -> str:
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
    #convert the string value in boolean
    if string=="True":bool=True
    elif string=="False":bool=False
    else:bool=None
    return bool

def clean_request(d: dict) -> dict:
    #this function is replacing the following value in Flask request
    # true => True
    # false => False
    # none => None
    return dict_replace_value(d)

def dict_replace_value(d: dict) -> dict:
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



def check_marketplace_raw(outputs,step):
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
                                logging.info(f"======> MarketPlace {step}")
                        if smart_contract_memory[0][2][j]=='new_user_flag':
                            new_user_flag=smart_contract_memory[0][3][j]
                            logging.info(f"======> new_user_flag {new_user_flag}")
            except:pass
    except:pass
    if step==1 and marketplace_place_step_flag is True: 
        #specific check for Step1 with New User
        #because the Input transaction doesn't need to be checked in that case
        #but it needs ot be checked if this is not a new user
        if new_user_flag=="False" or new_user_flag is False or new_user_flag=="false":marketplace_place_step_flag=False

    return marketplace_place_step_flag

def extract_marketplace_account(outputs):
    marketplace_place_account=None
    try:
        for i in range(0,len(outputs)):
            try:
                marketplace_place_account=outputs[i]['smart_contract_account']
            except:pass
    except:pass
    return marketplace_place_account


def check_marketplace_step1(outputs):
    return check_marketplace_raw(outputs,1)

def check_marketplace_step2(outputs):
    return check_marketplace_raw(outputs,2)

def check_smart_contract_consistency(transaction):
    #this function ensure the consistency of the SmartContract:
    #only 1 input, only 1 output 
    #transaction_hash of input of new transaxction = UTXO of SmartContrat
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
            if 5==6:
                if check_marketplace_step1(outputs) is False and check_marketplace_step2(outputs) is False:
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


def check_transfer(outputs):
    marketplace_place_step_flag=False
    try:
        for i in range(0,len(outputs)):
            try:
                if outputs[i]['marketplace_transaction_flag'] is True:
                    smart_contract_memory=outputs[i]['smart_contract_memory']
                    #example of smart_contract_memory
                    #['MarketplaceRequest', 'mp_request_step2_done', 
                    #['account', 'step', 'timestamp', 'requested_amount', 'requested_currency', 'next_account', 'buyer_public_key_hash', 'buyer_public_key_hex', 'requested_nig', 'timestamp_nig', 'seller_public_key_hex', 'seller_public_key_hash', 'encrypted_account', 'mp_request_signature', 'mp_request_id', 'previous_mp_request_name', 'mp_request_name', 'seller_safety_coef', 'smart_contract_ref'], 
                    #['531c2e528bd177866f7213b192833846018686e5', 1, 1694581434.188025, 1.0, 'EUR', None, '531c2e528bd177866f7213b192833846018686e5', 'xdfsdsd', 0.338, 1694581434.189025, None, None, None, None, 39464617, None, 'mp_request_step2_done', 2, 'a08fe9d2421e8b94ae8647cbabb81e5ad3018601']]
                    for j in range(0,len(smart_contract_memory[0][2])):
                        if smart_contract_memory[0][2][j]=='step':
                            if smart_contract_memory[0][3][j]==step:
                                marketplace_place_step_flag=True
                                logging.info(f"======> MarketPlace {step}")
            except:pass
    except:pass
    return marketplace_place_step_flag


def retrieve_buyer_seller(outputs):
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
    #this function is checking if the transaction
    #needs to trigger a refresh of the score
    #it return the list of account to refresh
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
    

if 5==6:
    
    logging.info(f"===>PoH_registry_intermediary BEGIN:{PoH_registry_intermediary}")
    test=PoH_registry_intermediary[0][1]
    logging.info(f"===>test:{test}")

    position = 6
    new_character = 'e'
    temp = list(test)
    temp[position] = new_character
    test = "".join(temp)

    PoH_registry_intermediary[0][1]=test
    logging.info(f"===>PoH_registry_intermediary END:{PoH_registry_intermediary}")


