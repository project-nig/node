import requests
import time

from blockchain_users.daniel import private_key as daniel_private_key
from blockchain_users.marketplace import private_key as marketplace_private_key
from blockchain_users.interface import public_key_hash as interface_public_key_hash

from common.node import Node
from common.transaction_input import TransactionInput
from common.transaction_output import TransactionOutput
from common.smart_contract import SmartContract
from common.values import MARKETPLACE_CODE_PUBLIC_KEY_HASH,MY_HOSTNAME

from wallet.wallet import Owner, Wallet


def test_marketplace0():
    #step 1: initialize default objects
    my_node=Node(MY_HOSTNAME)
    marketplace_owner=Owner(private_key=marketplace_private_key)
    daniel_owner=Owner(private_key=daniel_private_key)
    daniel_wallet=Wallet(daniel_owner,Node("127.0.0.1:5000"))
    purchase_request_amount_eur=100
    smart_contract_account="hello_world"

    #step 2: Get the default payload for a marketplace request
    payload="""
memory_obj_2_load=['marketplace_request_code']
return marketplace_request_code.code
"""
    smart_contract_data = {
        'smart_contract_type': 'api',
        'smart_contract_public_key_hash': MARKETPLACE_CODE_PUBLIC_KEY_HASH,
        'sender_public_key_hash': 'sender_public_key_hash',
        'payload':payload,
      }
    smart_contract_value=my_node.smart_contract(smart_contract_data).json()
    marketplace_request_default_code=smart_contract_value['smart_contract_result']

    #step 3: Generate the payload for the purchase request
    marketplace_script="""
mp_request_step2_done=MarketplaceRequest()
mp_request_step2_done.step1("mp_request_step2_done",requester_public_key_hash,requester_public_key_hex,requested_amount,smart_contract_ref,new_user_flag,reputation_0,reputation_1)
mp_request_step2_done.account=sender
memory_list.add([mp_request_step2_done,mp_request_step2_done.mp_request_name,['account','step','timestamp','requested_amount',
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1','timestamp_step2','timestamp_step3','timestamp_step4',
  'buyer_public_key_hex','requested_nig','timestamp_nig','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability',
  'mp_request_signature','mp_request_id','previous_mp_request_name','mp_request_name','seller_safety_coef','smart_contract_ref','new_user_flag','reputation_buyer','reputation_seller']])
mp_request_step2_done.get_requested_deposit()

"""
    
    parameters=f'''requester_public_key_hash="{daniel_owner.public_key_hash}"
requester_public_key_hex="{daniel_owner.public_key_hex}"
requested_amount={purchase_request_amount_eur}
smart_contract_ref="{smart_contract_account}"
new_user_flag=True
reputation_0=0
reputation_1=1
'''+marketplace_script
    payload=marketplace_request_default_code+parameters
    
    #step 4: retrieve the utxo of the marketplace
    public_key_hash=marketplace_owner.public_key_hash
    utxo_url='http://'+MY_HOSTNAME+'/utxo/'+public_key_hash
    resp = requests.get(utxo_url)
    utxo_dict = resp.json()

    #step 5: launch the creation of a purchase request
    sender_public_key_hash=daniel_owner.public_key_hash
    unlocking_public_key_hash=daniel_owner.public_key_hash
    list_public_key_hash=[smart_contract_account,sender_public_key_hash,marketplace_owner.public_key_hash]
    account_temp=True
    marketplace_step=0

    input_list=[]
    output_list=[]
    for utxo in utxo_dict['utxos']:
        amount=utxo['amount']

        
        smart_contract=SmartContract(smart_contract_account,
                                        smart_contract_sender=sender_public_key_hash,
                                        smart_contract_type="source",
                                        payload=payload,
                                        smart_contract_new=True)

        smart_contract.process()
        
        input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash=unlocking_public_key_hash))

        output_list.append(TransactionOutput(list_public_key_hash=list_public_key_hash, 
                                                amount=amount,
                                                interface_public_key_hash=interface_public_key_hash,
                                                smart_contract_account=smart_contract.smart_contract_account,
                                                smart_contract_sender=smart_contract.smart_contract_sender,
                                                smart_contract_new=smart_contract.smart_contract_new,
                                                smart_contract_flag=True,
                                                account_temp=account_temp,
                                                marketplace_step=marketplace_step,
                                                marketplace_transaction_flag=True,
                                                smart_contract_gas=smart_contract.gas,
                                                smart_contract_memory=smart_contract.smart_contract_memory,
                                                smart_contract_memory_size=smart_contract.smart_contract_memory_size,
                                                smart_contract_type=smart_contract.smart_contract_type,
                                                smart_contract_payload=smart_contract.payload,
                                                smart_contract_result=smart_contract.result,
                                                smart_contract_previous_transaction=smart_contract.smart_contract_previous_transaction,
                                                smart_contract_transaction_hash=smart_contract.smart_contract_transaction_hash))
        
        daniel_wallet.process_transaction(inputs=input_list, outputs=output_list)
        break
    
    #step 6: check that there is one purchase request in marketplace 1 and its content
    # check that url => http://127.0.0.3:5000/marketplace_step/1/test
    # check that url => http://127.0.0.3:5000/block
    