
from importlib import machinery
from platform import machine
from re import M
import time
import copy
import pytest
import json

from blockchain_users.camille import private_key as camille_private_key
from blockchain_users.bertrand import private_key as bertrand_private_key
from blockchain_users.daniel import private_key as daniel_private_key
from blockchain_users.marketplace import private_key as marketplace_private_key
from common.node import Node
from common.transaction_input import TransactionInput
from common.transaction_output import TransactionOutput
from node.new_block_creation.new_block_creation import ProofOfWork
from wallet.wallet import Owner, Wallet

from common.io_leader_node_schedule import LeaderNodeScheduleMemory
import requests
from common.values import MY_HOSTNAME
from blockchain_users.interface import public_key_hash as interface_public_key_hash
from common.io_blockchain import BlockchainMemory
from common.io_leader_node_schedule import LeaderNodeScheduleMemory
from common.smart_contract import SmartContract,check_smart_contract,load_smart_contract,load_smart_contract_from_master_state,load_smart_contract_from_master_state_leader_node,check_double_contract,create_smart_contract
from common.smart_contract_script import marketplace_script1
from common.values import MARKETPLACE_CODE_PUBLIC_KEY_HASH
from common.transaction_account import TransactionAccount

from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import binascii


@pytest.fixture(scope="module")
def transaction_amount_eur():
    return 10

@pytest.fixture(scope="module")
def transaction_amount_eur2():
    return 5

@pytest.fixture(scope="module")
def camille_owner():
    return Owner(private_key=camille_private_key)

@pytest.fixture(scope="module")
def daniel_owner():
    return Owner(private_key=daniel_private_key)

@pytest.fixture(scope="module")
def marketplace_owner():
    return Owner(private_key=marketplace_private_key)

@pytest.fixture(scope="module")
def smart_contract_owner():
    return Owner(private_key=marketplace_private_key)

@pytest.fixture(scope="module")
def my_node():
    return Node(MY_HOSTNAME)

@pytest.fixture(scope="module")
def camille_wallet(camille_owner):
    return Wallet(camille_owner,Node("127.0.0.1:5000"))
    #return Wallet(camille_owner,Node(MY_HOSTNAME))

@pytest.fixture(scope="module")
def daniel_wallet(daniel_owner):
    return Wallet(daniel_owner,Node("127.0.0.1:5000"))
    #return Wallet(camille_owner,Node(MY_HOSTNAME))

@pytest.fixture(scope="module")
def smart_contract_wallet(smart_contract_owner):
    return Wallet(smart_contract_owner,Node("127.0.0.1:5000"))
  


@pytest.fixture(scope="module")
def bertrand_owner():
    return Owner(private_key=bertrand_private_key)

@pytest.fixture(scope="module")
def blockchain_memory():
    return BlockchainMemory()

@pytest.fixture(scope="module")
def leader_node_schedule_memory():
    return LeaderNodeScheduleMemory()

def get_utxo(public_key_hash, *args, **kwargs):
    smart_contract_only=kwargs.get('smart_contract_only',True)
    utxo_url='http://'+MY_HOSTNAME+'/utxo/'+public_key_hash
    resp = requests.get(utxo_url)
    utxo_dict_init = resp.json()
    utxo_list=copy.deepcopy(utxo_dict_init['utxos'])
    for utxo in utxo_list:
        try:
            utxo['smart_contract_flag']
            if smart_contract_only is False:
                #we remove all the smart_contract, let's remove this value
                #this is used to transfer the nig out of the smart_contract
                utxo_dict_init['utxos'].remove(utxo)
        except:
            if smart_contract_only is True:
                #we keep only the smart_contract, let's remove this value
                utxo_dict_init['utxos'].remove(utxo)
    return utxo_dict_init

def get_smart_contract_detail(marketplace_step,smart_contract_account,payload,marketplace_owner,daniel_owner,daniel_wallet,camille_owner,camille_wallet,smart_contract_wallet,*args, **kwargs):
    transaction_amount_eur = kwargs.get('transaction_amount_eur',None)
    requested_nig = kwargs.get('requested_nig',None)
    seller_transaction_amount = kwargs.get('seller_transaction_amount',None)
    seller_public_key_hash = kwargs.get('seller_public_key_hash',None)
    buyer_requested_deposit = kwargs.get('buyer_requested_deposit',0)
    
    
    
    
    smart_contract_amount=None
    try:
        smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(smart_contract_account)
        print(f"#### smart_contract_transaction_hash:{smart_contract_transaction_hash}")
    except:
        pass

    ####STEP 0
    if int(marketplace_step)==0:
        sender_public_key_hash=daniel_owner.public_key_hash
        utxo_dict=get_utxo(marketplace_owner.public_key_hash)
        print(f"###utxo_dict:{utxo_dict}")
        unlocking_public_key_hash=daniel_owner.public_key_hash
        transaction_wallet=daniel_wallet
        smart_contract_new=True
        list_public_key_hash=[smart_contract_account,sender_public_key_hash,marketplace_owner.public_key_hash]
        smart_contract_transaction_hash=None
        account_temp=True

    ####STEP 1
    if int(marketplace_step)==1:
        sender_public_key_hash=daniel_owner.public_key_hash
        utxo_dict=get_utxo(marketplace_owner.public_key_hash)
        buyer_utxo_dict=get_utxo(daniel_owner.public_key_hash,smart_contract_only=False)
        #print(f"###buyer_utxo_dict:{buyer_utxo_dict}")
        unlocking_public_key_hash=daniel_owner.public_key_hash
        transaction_wallet=daniel_wallet
        smart_contract_new=True
        list_public_key_hash=[smart_contract_account,sender_public_key_hash,marketplace_owner.public_key_hash]
        smart_contract_transaction_hash=None
        account_temp=True
        
    ####STEP 2
    if int(marketplace_step)==2:
        sender_public_key_hash=camille_owner.public_key_hash
        utxo_dict=get_utxo(smart_contract_account)
        #print(f"###utxo_dict:{utxo_dict}")
        seller_utxo_dict=get_utxo(camille_owner.public_key_hash,smart_contract_only=False)
        print(f"###seller_utxo_dict:{seller_utxo_dict}")
        unlocking_public_key_hash=marketplace_owner.public_key_hash+" SC "+smart_contract_account
        seller_unlocking_public_key_hash=camille_owner.public_key_hash
        transaction_wallet=camille_wallet
        smart_contract_new=False
        print(f"utxo_dict:{utxo_dict}")
        list_public_key_hash=[smart_contract_account,sender_public_key_hash,daniel_owner.public_key_hash]
        account_temp=True

    ####STEP 3
    if int(marketplace_step)==3:
        sender_public_key_hash=daniel_owner.public_key_hash
        utxo_dict=get_utxo(smart_contract_account)
        unlocking_public_key_hash=smart_contract_account
        transaction_wallet=smart_contract_wallet
        smart_contract_new=False
        print(f"utxo_dict:{utxo_dict}")
        list_public_key_hash=[smart_contract_account]
        account_temp=True

    ####STEP 4
    if int(marketplace_step)==4:
        sender_public_key_hash=camille_owner.public_key_hash
        utxo_dict=get_utxo(smart_contract_account)
        unlocking_public_key_hash=marketplace_owner.public_key_hash+" SC "+smart_contract_account
        transaction_wallet=smart_contract_wallet
        smart_contract_new=False
        print(f"utxo_dict:{utxo_dict}")
        list_public_key_hash=[smart_contract_account]
        account_temp=False
        

    input_list=[]
    output_list=[]
    for utxo in utxo_dict['utxos']:
        if int(marketplace_step)==1:amount=buyer_requested_deposit
        elif int(marketplace_step)==2:amount=requested_nig+buyer_requested_deposit
        #elif int(marketplace_step)==3 and requested_nig is not None:amount=requested_nig+buyer_requested_deposit
        elif int(marketplace_step)==4:amount=0
        else:amount=utxo['amount']

        #if smart_contract_amount is None:smart_contract_amount=utxo['amount']
        smart_contract=SmartContract(smart_contract_account,
                                        smart_contract_sender=sender_public_key_hash,
                                        smart_contract_type="source",
                                        payload=payload,
                                        smart_contract_new=smart_contract_new,
                                        smart_contract_previous_transaction=smart_contract_transaction_hash)

        smart_contract.process()
        
        if int(marketplace_step)==1:input_list.append(TransactionInput(transaction_hash=buyer_utxo_dict['utxos'][0]['transaction_hash'], output_index=buyer_utxo_dict['utxos'][0]['output_index'],unlocking_public_key_hash=unlocking_public_key_hash))
        elif int(marketplace_step)==2:
            input_list.append(TransactionInput(transaction_hash=seller_utxo_dict['utxos'][0]['transaction_hash'], output_index=seller_utxo_dict['utxos'][0]['output_index'],unlocking_public_key_hash=seller_unlocking_public_key_hash))
            input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash=unlocking_public_key_hash))
        else:input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash=unlocking_public_key_hash))

        print(f"####amount:{amount} buyer_requested_deposit:{buyer_requested_deposit}")
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
        print(f"####amount1:{output_list[0].amount}")
        if int(marketplace_step)==1:
            output_list.append(TransactionOutput(list_public_key_hash=[daniel_owner.public_key_hash], 
                                                amount=buyer_utxo_dict['utxos'][0]['amount']-buyer_requested_deposit,
                                                marketplace_step=marketplace_step,
                                                interface_public_key_hash=interface_public_key_hash))
            print(f"####amount2:{output_list[1].amount}")
        elif int(marketplace_step)==2:
            output_list.append(TransactionOutput(list_public_key_hash=[camille_owner.public_key_hash], 
                                                amount=seller_utxo_dict['utxos'][0]['amount']-amount+buyer_requested_deposit,
                                                interface_public_key_hash=interface_public_key_hash))

        elif int(marketplace_step)==4:
            #Transaction to the buyer with the potential requested_deposit
            output_list.append(TransactionOutput(list_public_key_hash=[daniel_owner.public_key_hash], 
                                                amount=requested_nig+buyer_requested_deposit,
                                                marketplace_step=4,
                                                interface_public_key_hash=interface_public_key_hash))
            #Transaction to the seller including the seller safety coef
            output_list.append(TransactionOutput(list_public_key_hash=[seller_public_key_hash], 
                                                amount=seller_transaction_amount,
                                                marketplace_step=0,
                                                interface_public_key_hash=interface_public_key_hash))
        #print("####Check Signature")
        transaction_wallet.process_transaction(inputs=input_list, outputs=output_list)
        break

def test_marketplace0(marketplace_owner,daniel_owner,daniel_wallet,smart_contract_wallet,my_node,camille_owner,camille_wallet,transaction_amount_eur):
    #step1 : reset the blockchain
    utxo_url="http://127.0.0.1:5000/restart"
    resp = requests.get(utxo_url)
    time.sleep(10)
    
    #step2 : creation of the smart_contact account number
    utxo_url='http://'+MY_HOSTNAME+'/create_smart_contract_account'
    resp = requests.get(utxo_url)
    smart_contract_account=marketplace_resp = resp.json()
    #check that smart_contract_account is binary and its length is 40
    assert 40==len(smart_contract_account)
    int(smart_contract_account, 16)
    
    #step3 : check that there is no purchase request in marketplace 1
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/1/'+marketplace_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 0==len(marketplace_resp["results"])

    #step4 : Extract  marketplace_request_code_raw
    payload="""
memory_obj_2_load=['marketplace_request_code']
return marketplace_request_code.code
"""
    smart_contract_data = {
        'smart_contract_type': 'api',
        'smart_contract_public_key_hash': MARKETPLACE_CODE_PUBLIC_KEY_HASH,
        'sender_public_key_hash': 'sender_public_key_hash',
        'payload':payload,
      };
    smart_contract_value=my_node.smart_contract(smart_contract_data).json()
    marketplace_request_code_raw=smart_contract_value['smart_contract_result']
    
    payload1=f'''requester_public_key_hash="{daniel_owner.public_key_hash}"
requester_public_key_hex="{daniel_owner.public_key_hex}"
requested_amount={transaction_amount_eur}
smart_contract_ref="{smart_contract_account}"
new_user_flag=True
reputation_0=0
reputation_1=1
'''+marketplace_script1
    payload=marketplace_request_code_raw+payload1
    
    #step5 : launch the creation of a purchase request
    get_smart_contract_detail(0,smart_contract_account,payload,marketplace_owner,daniel_owner,daniel_wallet,camille_owner,camille_wallet,smart_contract_wallet,transaction_amount_eur=transaction_amount_eur)
    time.sleep(20)
    
    #step6 : check that there is one purchase request in marketplace 1 and its content
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/1/'+marketplace_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 1==len(marketplace_resp["results"])
    assert marketplace_resp["results"][0]['requested_amount']==10
    assert marketplace_resp["results"][0]['requester_public_key_hash']==daniel_owner.public_key_hash
    assert marketplace_resp["results"][0]['requester_public_key_hex']==daniel_owner.public_key_hex
    assert marketplace_resp["results"][0]['smart_contract_ref']==smart_contract_account


def test_marketplace2(marketplace_owner,daniel_owner,camille_owner,smart_contract_wallet,my_node,daniel_wallet,camille_wallet,transaction_amount_eur):
    #step 1: extract the smart contract account
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/1/'+marketplace_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    smart_contract_ref=marketplace_resp["results"][0]["smart_contract_ref"]
    requested_nig=marketplace_resp["results"][0]["requested_nig"]

    #step 2: extract the smart contract account details
    marketplace_api_utxo_json=my_node.get_smart_contract_api(smart_contract_ref)
    smart_contract_previous_transaction=marketplace_api_utxo_json['smart_contract_previous_transaction']
    smart_contract_transaction_hash=marketplace_api_utxo_json['smart_contract_transaction_hash']
    smart_contract_total=marketplace_api_utxo_json['total']


    #step 3: encryption of account
    marketplace_script2_1="""
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.get_mp_details(2)
"""
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': 'sender_public_key_hash',
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':marketplace_script2_1,
    }
    smart_contract_value=my_node.smart_contract(smart_contract_data).json()
    mp_details=smart_contract_value['smart_contract_result']

    #seller_safety_coef management
    requested_nig=requested_nig*mp_details[6]
    #step2_transaction_amount=transaction_amount

    sender_public_key_hash=camille_owner.public_key_hash
    buyer_public_key_hex=daniel_owner.public_key_hex
    transaction_account=TransactionAccount("Banque Postale camille","FR03 7456 2398 1536 3487 9H45 361","PDTTZFPHTRE","james.bond@gmail.com","0123456789","France",camille_owner.public_key_hash)
    encrypted_account = transaction_account.encrypt(buyer_public_key_hex,camille_owner.private_key)

    #step 4: encryption of account
    mp_details.append(camille_owner.public_key_hex)
    mp_details.append(camille_owner.public_key_hash)
    step2_requested_deposit=0
    mp_details.append(step2_requested_deposit)
    print(f"@@@@@@step2 mp_details:{mp_details}")
    transaction_bytes = json.dumps(mp_details, indent=2).encode('utf-8')
    hash_object = SHA256.new(transaction_bytes)
    #signature = pkcs1_15.new(RSA.importKey(seller_owner.private_key)).sign(hash_object)
    signature = pkcs1_15.new(camille_owner.private_key).sign(hash_object)
    mp_request_signature=binascii.hexlify(signature).decode("utf-8")

    #step 5: Validate on the blockchain
    marketplace_script2_3=f'''
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.step2("{camille_owner.public_key_hash}","{camille_owner.public_key_hex}","{encrypted_account}","{mp_request_signature}")
mp_request_step2_done.validate_step()
memory_list.add([mp_request_step2_done,mp_request_step2_done.mp_request_name,['account','step','timestamp','requested_amount',
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1_sell','timestamp_step1_buy','timestamp_step15','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap'
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability','seller_reput_trans','seller_reput_reliability',
  'mp_request_signature','mp_request_id','previous_mp_request_name','mp_request_name','seller_safety_coef','smart_contract_ref','new_user_flag','reputation_buyer','reputation_seller']])
123456
'''
    payload=marketplace_script2_3
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': "requester_public_key_hash",
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':payload,
    }
    smart_contract_value=my_node.smart_contract(smart_contract_data).json()
    #print(f"###smart_contract_value:{smart_contract_value}")
    marketplace_request_code_raw=smart_contract_value['smart_contract_result']


    #step5 : launch the creation of a purchase request
    get_smart_contract_detail(2,smart_contract_ref,payload,marketplace_owner,daniel_owner,daniel_wallet,camille_owner,camille_wallet,smart_contract_wallet,requested_nig=requested_nig)
    
    time.sleep(20)
    
    #step6 : check that there is one purchase request in marketplace 1 and its content
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/2/'+daniel_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 1==len(marketplace_resp["results"])
    assert marketplace_resp["results"][0]['requested_amount']==transaction_amount_eur
    assert marketplace_resp["results"][0]['requested_nig']*mp_details[6]==requested_nig
    assert marketplace_resp["results"][0]['requester_public_key_hash']==daniel_owner.public_key_hash
    assert marketplace_resp["results"][0]['requester_public_key_hex']==daniel_owner.public_key_hex
    assert marketplace_resp["results"][0]['smart_contract_ref']==smart_contract_ref



 
def test_marketplace3(marketplace_owner,daniel_owner,camille_owner,smart_contract_wallet,my_node,daniel_wallet,camille_wallet,transaction_amount_eur):
    #step 1: extract the smart contract account
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/2/'+daniel_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    smart_contract_ref=marketplace_resp["results"][0]["smart_contract_ref"]
    requested_nig=marketplace_resp["results"][0]["requested_nig"]

    #step 2: extract the smart contract account details
    marketplace_api_utxo_json=my_node.get_smart_contract_api(smart_contract_ref)
    smart_contract_previous_transaction=marketplace_api_utxo_json['smart_contract_previous_transaction']
    smart_contract_transaction_hash=marketplace_api_utxo_json['smart_contract_transaction_hash']
    smart_contract_total=marketplace_api_utxo_json['total']


    #step 3: encryption of account
    marketplace_script2_1="""
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.get_mp_details(3)
"""
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': 'sender_public_key_hash',
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':marketplace_script2_1,
    }
    smart_contract_value=my_node.smart_contract(smart_contract_data).json()
    mp_details=smart_contract_value['smart_contract_result']

    
    
    #step 4: signature generation
    print(f"@@@@@@step2 mp_details:{mp_details}")
    transaction_bytes = json.dumps(mp_details, indent=2).encode('utf-8')
    hash_object = SHA256.new(transaction_bytes)
    #signature = pkcs1_15.new(RSA.importKey(seller_owner.private_key)).sign(hash_object)
    signature = pkcs1_15.new(daniel_owner.private_key).sign(hash_object)
    mp_request_signature=binascii.hexlify(signature).decode("utf-8")

    #step 5: Validate on the blockchain
    marketplace_script3_2=f'''
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.step3("{mp_request_signature}")
mp_request_step2_done.validate_step()
memory_list.add([mp_request_step2_done,mp_request_step2_done.mp_request_name,['account','step','timestamp','requested_amount',
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1_sell','timestamp_step1_buy','timestamp_step15','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap'
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability','seller_reput_trans','seller_reput_reliability',
  'mp_request_signature','mp_request_id','previous_mp_request_name','mp_request_name','seller_safety_coef','smart_contract_ref','new_user_flag','reputation_buyer','reputation_seller']])
123456
'''

    payload=marketplace_script3_2
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': "requester_public_key_hash",
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':payload,
    }

    #step5 : launch the creation of a purchase request
    get_smart_contract_detail(3,smart_contract_ref,payload,marketplace_owner,daniel_owner,daniel_wallet,camille_owner,camille_wallet,smart_contract_wallet)
    
    time.sleep(20)
    
    #step6 : check that there is one purchase request in marketplace 1 and its content
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/3/'+camille_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 1==len(marketplace_resp["results"])
    assert marketplace_resp["results"][0]['requested_amount']==transaction_amount_eur
    assert marketplace_resp["results"][0]['requested_nig']==requested_nig
    assert marketplace_resp["results"][0]['requester_public_key_hash']==daniel_owner.public_key_hash
    assert marketplace_resp["results"][0]['requester_public_key_hex']==daniel_owner.public_key_hex
    assert marketplace_resp["results"][0]['smart_contract_ref']==smart_contract_ref



def test_marketplace4(marketplace_owner,daniel_owner,camille_owner,smart_contract_wallet,my_node,daniel_wallet,camille_wallet):
    #step 1: extract the smart contract account
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/3/'+camille_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    smart_contract_ref=marketplace_resp["results"][0]["smart_contract_ref"]
    requested_nig=marketplace_resp["results"][0]["requested_nig"]

    #step 2: extract the smart contract account details
    marketplace_api_utxo_json=my_node.get_smart_contract_api(smart_contract_ref)
    smart_contract_previous_transaction=marketplace_api_utxo_json['smart_contract_previous_transaction']
    smart_contract_transaction_hash=marketplace_api_utxo_json['smart_contract_transaction_hash']
    smart_contract_total=marketplace_api_utxo_json['total']



    #step 3: encryption of account
    marketplace_script2_1="""
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.get_mp_details(4)
"""
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': 'sender_public_key_hash',
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':marketplace_script2_1,
    }
    smart_contract_value=my_node.smart_contract(smart_contract_data).json()
    mp_details=smart_contract_value['smart_contract_result']

    #seller_safety_coef management
    seller_transaction_amount=mp_details[5]*mp_details[6]-mp_details[5]
    seller_public_key_hash=mp_details[8]
    buyer_requested_deposit=mp_details[9]
    
    #step 4: signature generation
    print(f"@@@@@@step2 mp_details:{mp_details}")
    transaction_bytes = json.dumps(mp_details, indent=2).encode('utf-8')
    hash_object = SHA256.new(transaction_bytes)
    #signature = pkcs1_15.new(RSA.importKey(seller_owner.private_key)).sign(hash_object)
    signature = pkcs1_15.new(camille_owner.private_key).sign(hash_object)
    mp_request_signature=binascii.hexlify(signature).decode("utf-8")

    #step 5: Validate on the blockchain
    marketplace_script4_3=f'''
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.step4("{mp_request_signature}")
mp_request_step2_done.validate_step()
memory_list.add([mp_request_step2_done,mp_request_step2_done.mp_request_name,['account','step','timestamp','requested_amount',
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1_sell','timestamp_step1_buy','timestamp_step15','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap'
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability','seller_reput_trans','seller_reput_reliability',
  'mp_request_signature','mp_request_id','previous_mp_request_name','mp_request_name','seller_safety_coef','smart_contract_ref','new_user_flag','reputation_buyer','reputation_seller']])

123456
'''

    payload=marketplace_script4_3
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': "requester_public_key_hash",
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':payload,
    }

    #step5 : launch the creation of a purchase request
    get_smart_contract_detail(4,smart_contract_ref,payload,marketplace_owner,daniel_owner,daniel_wallet,camille_owner,camille_wallet,smart_contract_wallet,requested_nig=requested_nig,seller_transaction_amount=seller_transaction_amount,buyer_requested_deposit=buyer_requested_deposit,seller_public_key_hash=seller_public_key_hash)
    
    time.sleep(20)
    
    #step6 : check that there is one purchase request in marketplace 1 and its content
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/3/'+camille_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 0==len(marketplace_resp["results"])



def test_marketplace1(marketplace_owner,daniel_owner,daniel_wallet,smart_contract_wallet,my_node,camille_owner,camille_wallet,transaction_amount_eur2):
    #step1 : creation of the smart_contact account number
    utxo_url='http://'+MY_HOSTNAME+'/create_smart_contract_account'
    resp = requests.get(utxo_url)
    smart_contract_account=marketplace_resp = resp.json()
    assert 40==len(smart_contract_account)
    int(smart_contract_account, 16)
    
    #step2 : check that there is no purchase request in marketplace 1
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/1/'+marketplace_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    #assert 0==len(marketplace_resp["results"])

    #step3 : Extract marketplace_request_code_raw
    payload="""
memory_obj_2_load=['marketplace_request_code']
return marketplace_request_code.code
"""
    smart_contract_data = {
        'smart_contract_type': 'api',
        'smart_contract_public_key_hash': MARKETPLACE_CODE_PUBLIC_KEY_HASH,
        'sender_public_key_hash': 'sender_public_key_hash',
        'payload':payload,
      };
    smart_contract_value=my_node.smart_contract(smart_contract_data).json()
    marketplace_request_code_raw=smart_contract_value['smart_contract_result']

    #step4 : Extract the buyer requested deposit
    requested_gap=0
    payload1=f'''
mp_request_step2_done=MarketplaceRequest()
mp_request_step2_done.step1_buy("mp_request_step2_done","{daniel_owner.public_key_hash}","{daniel_owner.public_key_hex}",{transaction_amount_eur2},{requested_gap},"{smart_contract_account}","False",1,1)
mp_request_step2_done.account=sender
memory_list.add([mp_request_step2_done,mp_request_step2_done.mp_request_name,['account','step','timestamp','requested_amount',
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1_sell','timestamp_step1_buy','timestamp_step15','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap'
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability','seller_reput_trans','seller_reput_reliability',
  'mp_request_signature','mp_request_id','previous_mp_request_name','mp_request_name','seller_safety_coef','smart_contract_ref','new_user_flag','reputation_buyer','reputation_seller']])
mp_request_step2_done.get_requested_deposit()
'''
    payload=marketplace_request_code_raw+payload1

    smart_contract=SmartContract(smart_contract_account,
                                smart_contract_sender='sender_public_key_hash',
                                smart_contract_type='source',
                                payload=payload,
                                smart_contract_new=True)

    smart_contract.process()
    buyer_requested_deposit=smart_contract.result
    print(f"###buyer_requested_deposit:{buyer_requested_deposit}")

    #step5 : launch the creation of a purchase request
    get_smart_contract_detail(1,smart_contract_account,payload,marketplace_owner,daniel_owner,daniel_wallet,camille_owner,camille_wallet,smart_contract_wallet,buyer_requested_deposit=buyer_requested_deposit)
    time.sleep(20)
    
    #step6 : check that there is one purchase request in marketplace 1 and its content
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/1/'+marketplace_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 1==len(marketplace_resp["results"])
    assert marketplace_resp["results"][0]['requested_amount']==5
    assert marketplace_resp["results"][0]['requester_public_key_hash']==daniel_owner.public_key_hash
    assert marketplace_resp["results"][0]['requester_public_key_hex']==daniel_owner.public_key_hex
    assert marketplace_resp["results"][0]['smart_contract_ref']==smart_contract_account

def test_marketplace21(marketplace_owner,daniel_owner,camille_owner,smart_contract_wallet,my_node,daniel_wallet,camille_wallet,transaction_amount_eur2):
    #step 1: extract the smart contract account
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/1/'+marketplace_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    smart_contract_ref=marketplace_resp["results"][0]["smart_contract_ref"]
    requested_nig=marketplace_resp["results"][0]["requested_nig"]

    #step 2: extract the smart contract account details
    marketplace_api_utxo_json=my_node.get_smart_contract_api(smart_contract_ref)
    smart_contract_previous_transaction=marketplace_api_utxo_json['smart_contract_previous_transaction']
    smart_contract_transaction_hash=marketplace_api_utxo_json['smart_contract_transaction_hash']
    smart_contract_total=marketplace_api_utxo_json['total']


    #step 3: retrieve buyer requested_deposit
    marketplace_script2_1="""
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.get_requested_deposit()
"""
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': 'sender_public_key_hash',
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':marketplace_script2_1,
    }
    smart_contract_value=my_node.smart_contract(smart_contract_data).json()
    buyer_requested_deposit=smart_contract_value['smart_contract_result']

    #step 4: encryption of account
    marketplace_script2_2="""
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.get_mp_details(2)
"""
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': 'sender_public_key_hash',
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':marketplace_script2_2,
    }
    smart_contract_value=my_node.smart_contract(smart_contract_data).json()
    mp_details=smart_contract_value['smart_contract_result']

    #seller_safety_coef management
    requested_nig=requested_nig*mp_details[6]
    #step2_transaction_amount=transaction_amount

    sender_public_key_hash=camille_owner.public_key_hash
    buyer_public_key_hex=daniel_owner.public_key_hex
    transaction_account=TransactionAccount("Banque Postale camille","FR03 7456 2398 1536 3487 9H45 361","PDTTZFPHTRE","james.bond@gmail.com","0123456789","France",camille_owner.public_key_hash)
    encrypted_account = transaction_account.encrypt(buyer_public_key_hex,camille_owner.private_key)

    #step 5: encryption of account
    mp_details.append(camille_owner.public_key_hex)
    mp_details.append(camille_owner.public_key_hash)
    mp_details.append(buyer_requested_deposit)
    print(f"@@@@@@step2 mp_details:{mp_details}")
    transaction_bytes = json.dumps(mp_details, indent=2).encode('utf-8')
    hash_object = SHA256.new(transaction_bytes)
    #signature = pkcs1_15.new(RSA.importKey(seller_owner.private_key)).sign(hash_object)
    signature = pkcs1_15.new(camille_owner.private_key).sign(hash_object)
    mp_request_signature=binascii.hexlify(signature).decode("utf-8")

    #step 6: Validate on the blockchain
    marketplace_script2_3=f'''
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.step2("{camille_owner.public_key_hash}","{camille_owner.public_key_hex}","{encrypted_account}","{mp_request_signature}")
mp_request_step2_done.validate_step()
memory_list.add([mp_request_step2_done,mp_request_step2_done.mp_request_name,['account','step','timestamp','requested_amount',
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1_sell','timestamp_step1_buy','timestamp_step15','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap'
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability','seller_reput_trans','seller_reput_reliability',
  'mp_request_signature','mp_request_id','previous_mp_request_name','mp_request_name','seller_safety_coef','smart_contract_ref','new_user_flag','reputation_buyer','reputation_seller']])
123456
'''
    payload=marketplace_script2_3
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': "requester_public_key_hash",
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':payload,
    }
    smart_contract_value=my_node.smart_contract(smart_contract_data).json()

    #step7 : launch the creation of a purchase request
    get_smart_contract_detail(2,smart_contract_ref,payload,marketplace_owner,daniel_owner,daniel_wallet,camille_owner,camille_wallet,smart_contract_wallet,requested_nig=requested_nig,buyer_requested_deposit=buyer_requested_deposit)
    
    time.sleep(20)
    
    #step8 : check that there is one purchase request in marketplace 1 and its content
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/2/'+daniel_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 1==len(marketplace_resp["results"])
    assert marketplace_resp["results"][0]['requested_amount']==transaction_amount_eur2
    assert marketplace_resp["results"][0]['requested_nig']*mp_details[6]==requested_nig
    assert marketplace_resp["results"][0]['requester_public_key_hash']==daniel_owner.public_key_hash
    assert marketplace_resp["results"][0]['requester_public_key_hex']==daniel_owner.public_key_hex
    assert marketplace_resp["results"][0]['smart_contract_ref']==smart_contract_ref




 
def test_marketplace31(marketplace_owner,daniel_owner,camille_owner,smart_contract_wallet,my_node,daniel_wallet,camille_wallet,transaction_amount_eur2):
    #step 1: extract the smart contract account
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/2/'+daniel_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    smart_contract_ref=marketplace_resp["results"][0]["smart_contract_ref"]
    requested_nig=marketplace_resp["results"][0]["requested_nig"]

    #step 2: extract the smart contract account details
    marketplace_api_utxo_json=my_node.get_smart_contract_api(smart_contract_ref)
    smart_contract_previous_transaction=marketplace_api_utxo_json['smart_contract_previous_transaction']
    smart_contract_transaction_hash=marketplace_api_utxo_json['smart_contract_transaction_hash']
    smart_contract_total=marketplace_api_utxo_json['total']


    #step 3: encryption of account
    marketplace_script2_1="""
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.get_mp_details(3)
"""
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': 'sender_public_key_hash',
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':marketplace_script2_1,
    }
    smart_contract_value=my_node.smart_contract(smart_contract_data).json()
    mp_details=smart_contract_value['smart_contract_result']

    
    
    #step 4: signature generation
    print(f"@@@@@@step2 mp_details:{mp_details}")
    transaction_bytes = json.dumps(mp_details, indent=2).encode('utf-8')
    hash_object = SHA256.new(transaction_bytes)
    #signature = pkcs1_15.new(RSA.importKey(seller_owner.private_key)).sign(hash_object)
    signature = pkcs1_15.new(daniel_owner.private_key).sign(hash_object)
    mp_request_signature=binascii.hexlify(signature).decode("utf-8")

    #step 5: Validate on the blockchain
    marketplace_script3_2=f'''
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.step3("{mp_request_signature}")
mp_request_step2_done.validate_step()
memory_list.add([mp_request_step2_done,mp_request_step2_done.mp_request_name,['account','step','timestamp','requested_amount',
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1_sell','timestamp_step1_buy','timestamp_step15','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap'
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability','seller_reput_trans','seller_reput_reliability',
  'mp_request_signature','mp_request_id','previous_mp_request_name','mp_request_name','seller_safety_coef','smart_contract_ref','new_user_flag','reputation_buyer','reputation_seller']])
123456
'''

    payload=marketplace_script3_2
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': "requester_public_key_hash",
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':payload,
    }

    #step5 : launch the creation of a purchase request
    get_smart_contract_detail(3,smart_contract_ref,payload,marketplace_owner,daniel_owner,daniel_wallet,camille_owner,camille_wallet,smart_contract_wallet)
    
    time.sleep(20)
    
    #step6 : check that there is one purchase request in marketplace 1 and its content
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/3/'+camille_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 1==len(marketplace_resp["results"])
    assert marketplace_resp["results"][0]['requested_amount']==transaction_amount_eur2
    assert marketplace_resp["results"][0]['requested_nig']==requested_nig
    assert marketplace_resp["results"][0]['requester_public_key_hash']==daniel_owner.public_key_hash
    assert marketplace_resp["results"][0]['requester_public_key_hex']==daniel_owner.public_key_hex
    assert marketplace_resp["results"][0]['smart_contract_ref']==smart_contract_ref



def test_marketplace41(marketplace_owner,daniel_owner,camille_owner,smart_contract_wallet,my_node,daniel_wallet,camille_wallet):
    #step 1: extract the smart contract account
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/3/'+camille_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    smart_contract_ref=marketplace_resp["results"][0]["smart_contract_ref"]
    requested_nig=marketplace_resp["results"][0]["requested_nig"]

    #step 2: extract the smart contract account details
    marketplace_api_utxo_json=my_node.get_smart_contract_api(smart_contract_ref)
    smart_contract_previous_transaction=marketplace_api_utxo_json['smart_contract_previous_transaction']
    smart_contract_transaction_hash=marketplace_api_utxo_json['smart_contract_transaction_hash']
    smart_contract_total=marketplace_api_utxo_json['total']



    #step 3: encryption of account
    marketplace_script2_1="""
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.get_mp_details(4)
"""
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': 'sender_public_key_hash',
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':marketplace_script2_1,
    }
    smart_contract_value=my_node.smart_contract(smart_contract_data).json()
    mp_details=smart_contract_value['smart_contract_result']

    #seller_safety_coef management
    seller_transaction_amount=mp_details[5]*mp_details[6]-mp_details[5]
    seller_public_key_hash=mp_details[8]
    buyer_requested_deposit=mp_details[9]
    
    #step 4: signature generation
    print(f"@@@@@@step2 mp_details:{mp_details}")
    transaction_bytes = json.dumps(mp_details, indent=2).encode('utf-8')
    hash_object = SHA256.new(transaction_bytes)
    #signature = pkcs1_15.new(RSA.importKey(seller_owner.private_key)).sign(hash_object)
    signature = pkcs1_15.new(camille_owner.private_key).sign(hash_object)
    mp_request_signature=binascii.hexlify(signature).decode("utf-8")

    #step 5: Validate on the blockchain
    marketplace_script4_3=f'''
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.step4("{mp_request_signature}")
mp_request_step2_done.validate_step()
memory_list.add([mp_request_step2_done,mp_request_step2_done.mp_request_name,['account','step','timestamp','requested_amount',
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1_sell','timestamp_step1_buy','timestamp_step15','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap'
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability','seller_reput_trans','seller_reput_reliability',
  'mp_request_signature','mp_request_id','previous_mp_request_name','mp_request_name','seller_safety_coef','smart_contract_ref','new_user_flag','reputation_buyer','reputation_seller']])

123456
'''

    payload=marketplace_script4_3
    smart_contract_data = {
      'smart_contract_type': 'source',
      'smart_contract_public_key_hash': smart_contract_ref,
      'sender_public_key_hash': "requester_public_key_hash",
      'smart_contract_transaction_hash': smart_contract_transaction_hash,
      'smart_contract_previous_transaction': smart_contract_transaction_hash,
      'payload':payload,
    }

    #step5 : launch the creation of a purchase request
    get_smart_contract_detail(4,smart_contract_ref,payload,marketplace_owner,daniel_owner,daniel_wallet,camille_owner,camille_wallet,smart_contract_wallet,requested_nig=requested_nig,seller_transaction_amount=seller_transaction_amount,buyer_requested_deposit=buyer_requested_deposit,seller_public_key_hash=seller_public_key_hash)
    
    time.sleep(20)
    
    #step6 : check that there is one purchase request in marketplace 1 and its content
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/3/'+camille_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 0==len(marketplace_resp["results"])

