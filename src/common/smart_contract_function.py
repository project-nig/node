
from common.values import ROUND_VALUE_DIGIT
from common.utils import normal_round
from common.values import MARKETPLACE_SELLER_SAFETY_COEF,MARKETPLACE_BUYER_SAFETY_COEF
from common.io_blockchain import BlockchainMemory
from common.master_state import MasterState



smart_contract_memory_full={}




def GET_SELLER_SAFETY_COEF():
    #coef multiply to the amount to ensure that the seller will confirm step4
    return MARKETPLACE_SELLER_SAFETY_COEF

def GET_BUYER_SAFETY_COEF():
    #coef multiply to the amount to ensure that the buyer will transfer the money
    return MARKETPLACE_BUYER_SAFETY_COEF

def CONVERT_2_NIG(requested_amount,timestamp_nig,currency):
    #function to convert the request amount into nig
    from node.main import calculate_nig_rate
    nig_rate=calculate_nig_rate(timestamp=timestamp_nig,currency=currency)
    requested_nig=normal_round(requested_amount/nig_rate,ROUND_VALUE_DIGIT)
    return normal_round(requested_nig,ROUND_VALUE_DIGIT)

        
def LOAD_OBJ(obj_name):
    #provide the smart_contract_memory_obj of obj_name
    #print(f"@@@@@@ smart_contract_memory_full: {smart_contract_memory_full}")
    #print(f"@@@@@@ obj_name: {obj_name}")
    try:
        result=smart_contract_memory_full[obj_name]
    except:
        result=None
    return result



def LOAD_SC_OLD(smart_contract_account,smart_contract_sender,payload):
    from common.smart_contract import SmartContract
    t="""
"""
    smart_contract=SmartContract(smart_contract_account,
                                 smart_contract_sender=smart_contract_sender,
                                 smart_contract_type="api",
                                 payload=payload+t)

    smart_contract.process()
    return smart_contract.result

def LOAD_SC(smart_contract_account,payload):
    from common.smart_contract import SmartContract
    t="""
"""
    smart_contract=SmartContract(smart_contract_account,
                                 smart_contract_type="api",
                                 payload=payload+t)
    smart_contract.process()
    if smart_contract.error_flag is False:
        return smart_contract.result
    else:return None
    

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

def GET_UTXO(public_key_hash):
    master_state=MasterState()
    master_state.get_master_state_from_memory_from_user(public_key_hash)
    return master_state.current_master_state[public_key_hash]

def NIG_RATE(*args, **kwargs):
    from node.main import calculate_nig_rate
    return calculate_nig_rate(*args, **kwargs)

def CANCEL_SC(marketplace_account,marketplace_step,mp_request_signature,user_type):
    from node.main import MarketplaceRequestArchivingProcessing
    marketplace_request_archiving_processing=MarketplaceRequestArchivingProcessing()
    if user_type=="buyer":request_type="cancellation_by_buyer"
    if user_type=="seller":request_type="cancellation_by_seller"
    marketplace_request_archiving_processing.launch(request_type=request_type,marketplace_account=marketplace_account,marketplace_step=marketplace_step,mp_request_signature=mp_request_signature)

def PAYMENT_DEFAULT_SC(marketplace_account,marketplace_step,mp_request_signature):
    from node.main import MarketplaceRequestArchivingProcessing
    marketplace_request_archiving_processing=MarketplaceRequestArchivingProcessing()
    marketplace_request_archiving_processing.launch(request_type="payment_default",marketplace_account=marketplace_account,marketplace_step=marketplace_step,mp_request_signature=mp_request_signature)




