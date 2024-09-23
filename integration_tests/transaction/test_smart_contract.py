
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
from blockchain_users.node import public_key_hash as node_public_key_hash
from blockchain_users.node3_local import public_key_hash as leader_node_public_key_hash
from blockchain_users.node2_local import public_key_hash as leader_node_public_key_hash2
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
from common.values import MARKETPLACE_CODE_PUBLIC_KEY_HASH,ROUND_VALUE_DIGIT
from common.values import NETWORK_DEFAULT,DEFAULT_TRANSACTION_FEE_PERCENTAGE,INTERFACE_TRANSACTION_FEE_SHARE,NODE_TRANSACTION_FEE_SHARE,MINER_TRANSACTION_FEE_SHARE,ROUND_VALUE_DIGIT
from common.transaction_account import TransactionAccount

from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import binascii
from node.main import calculate_nig_rate
from common.utils import normal_round,extract_marketplace_request


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
                                                amount=requested_nig,
                                                marketplace_step=4,
                                                interface_public_key_hash=interface_public_key_hash))
            if buyer_requested_deposit>0:
                output_list.append(TransactionOutput(list_public_key_hash=[daniel_owner.public_key_hash], 
                                                    amount=buyer_requested_deposit,
                                                    marketplace_step=0,
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

    #step2 : retrieve initial value
    seller_utxo_dict=get_utxo(camille_owner.public_key_hash,smart_contract_only=False)
    buyer_utxo_dict=get_utxo(daniel_owner.public_key_hash,smart_contract_only=False)
    seller_total=seller_utxo_dict["total"]
    buyer_total=buyer_utxo_dict["total"]
    blockchain_memory = BlockchainMemory()
    first_block=blockchain_memory.get_blockchain_from_memory()
    first_block_header=first_block.block_header
    
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
    
    requested_gap=0

    payload1=f'''requester_public_key_hash="{daniel_owner.public_key_hash}"
requester_public_key_hex="{daniel_owner.public_key_hex}"
requested_amount={transaction_amount_eur}
requested_gap={requested_gap}
smart_contract_ref="{smart_contract_account}"
new_user_flag=True
reputation_0=0
reputation_1=1
'''+marketplace_script1
    payload=marketplace_request_code_raw+payload1
    
    #step5 : launch the creation of a purchase request
    get_smart_contract_detail(0,smart_contract_account,payload,marketplace_owner,daniel_owner,daniel_wallet,camille_owner,camille_wallet,smart_contract_wallet,transaction_amount_eur=transaction_amount_eur)
    time.sleep(30)
    
    #step6 : check that there is one purchase request in marketplace 1 and its content
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/1/'+marketplace_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 1==len(marketplace_resp["results"])
    assert marketplace_resp["results"][0]['requested_amount']==10
    assert marketplace_resp["results"][0]['requester_public_key_hash']==daniel_owner.public_key_hash
    assert marketplace_resp["results"][0]['requester_public_key_hex']==daniel_owner.public_key_hex
    assert marketplace_resp["results"][0]['smart_contract_ref']==smart_contract_account

    #step7 : retrieve new information
    last_block=blockchain_memory.get_blockchain_from_memory()
    last_block_header=last_block.block_header
    last_transaction=extract_marketplace_request(last_block)

    daniel_transaction=None
    camille_transaction=None
    smart_contract_transaction=None
    for utxo in last_transaction["outputs"]:
        if daniel_owner.public_key_hash in utxo["locking_script"]:daniel_transaction=copy.deepcopy(utxo)
        if camille_owner.public_key_hash in utxo["locking_script"]:camille_transaction=copy.deepcopy(utxo)
        if smart_contract_account in utxo["locking_script"]:smart_contract_transaction=copy.deepcopy(utxo)


    #step8 : validation
    assert first_block_header.current_PoH_hash==last_block_header.previous_PoH_hash
    assert last_block_header.leader_node_public_key_hash==leader_node_public_key_hash
    assert last_block_header.slot==13
    
    assert len(last_transaction["outputs"])==1

    assert smart_contract_transaction["account"]==None
    assert smart_contract_transaction["amount"]==0
    assert smart_contract_transaction["fee_interface"]==0
    assert smart_contract_transaction["fee_miner"]==0
    assert smart_contract_transaction["fee_node"]==0
    assert smart_contract_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert smart_contract_transaction["locking_script"]=="OP_DUP OP_HASH160 "+marketplace_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG OP_SC "+smart_contract_account+" OP_SC "+daniel_owner.public_key_hash+" OP_SC "+marketplace_owner.public_key_hash
    assert smart_contract_transaction["network"]=="nig"
    assert smart_contract_transaction["node_public_key_hash"]==node_public_key_hash

    


def test_marketplace2(marketplace_owner,daniel_owner,camille_owner,smart_contract_wallet,my_node,daniel_wallet,camille_wallet,transaction_amount_eur):
    #step 1: extract the smart contract account
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/1/'+marketplace_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    smart_contract_ref=marketplace_resp["results"][0]["smart_contract_ref"]
    requested_nig=marketplace_resp["results"][0]["requested_nig"]

    #step2 : retrieve initial value
    seller_utxo_dict=get_utxo(camille_owner.public_key_hash,smart_contract_only=False)
    buyer_utxo_dict=get_utxo(daniel_owner.public_key_hash,smart_contract_only=False)
    seller_total=seller_utxo_dict["total"]
    buyer_total=buyer_utxo_dict["total"]
    blockchain_memory = BlockchainMemory()
    first_block=blockchain_memory.get_blockchain_from_memory()
    first_block_header=first_block.block_header

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
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap',
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability',
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
    
    time.sleep(30)
    
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


    #step7 : retrieve new information
    last_block=blockchain_memory.get_blockchain_from_memory()
    last_block_header=last_block.block_header
    last_transaction=extract_marketplace_request(last_block)

    daniel_transaction=None
    camille_transaction=None
    smart_contract_transaction=None
    for utxo in last_transaction["outputs"]:
        if daniel_owner.public_key_hash in utxo["locking_script"]:daniel_transaction=copy.deepcopy(utxo)
        if camille_owner.public_key_hash in utxo["locking_script"]:camille_transaction=copy.deepcopy(utxo)
        if smart_contract_ref in utxo["locking_script"]:smart_contract_transaction=copy.deepcopy(utxo)


    #step8 : validation
    nig_rate=calculate_nig_rate(currency='eur')
    assert first_block_header.current_PoH_hash==last_block_header.previous_PoH_hash
    assert last_block_header.leader_node_public_key_hash==leader_node_public_key_hash2
    assert last_block_header.slot==first_block_header.slot+1
    
    assert len(last_transaction["outputs"])==2
    
    assert smart_contract_transaction["account"]==None
    assert smart_contract_transaction["amount"]==requested_nig
    assert smart_contract_transaction["fee_interface"]==0
    assert smart_contract_transaction["fee_miner"]==0
    assert smart_contract_transaction["fee_node"]==0
    assert smart_contract_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert smart_contract_transaction["locking_script"]=="OP_DUP OP_HASH160 "+marketplace_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG OP_SC "+smart_contract_ref+" OP_SC "+camille_owner.public_key_hash+" OP_SC "+daniel_owner.public_key_hash+" OP_DEL_SC "+marketplace_owner.public_key_hash
    assert smart_contract_transaction["network"]=="nig"
    assert smart_contract_transaction["node_public_key_hash"]==node_public_key_hash

    assert  camille_transaction["account"]==None
    #bug fixing : compare the amount of the transaction and not the total amount of the camille
    #assert  camille_transaction["amount"]+transaction_amount==seller_total
    assert  camille_transaction["fee_interface"]==0
    assert  camille_transaction["fee_miner"]==0
    assert  camille_transaction["fee_node"]==0
    assert  camille_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert  camille_transaction["locking_script"]=="OP_DUP OP_HASH160 "+ camille_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG"
    assert  camille_transaction["network"]=="nig"
    assert  camille_transaction["node_public_key_hash"]==node_public_key_hash


def test_marketplace3(marketplace_owner,daniel_owner,camille_owner,smart_contract_wallet,my_node,daniel_wallet,camille_wallet,transaction_amount_eur):
    #step 1: extract the smart contract account
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/2/'+daniel_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    smart_contract_ref=marketplace_resp["results"][0]["smart_contract_ref"]
    requested_nig=marketplace_resp["results"][0]["requested_nig"]


    #step2 : retrieve initial value
    seller_utxo_dict=get_utxo(camille_owner.public_key_hash,smart_contract_only=False)
    buyer_utxo_dict=get_utxo(daniel_owner.public_key_hash,smart_contract_only=False)
    seller_total=seller_utxo_dict["total"]
    buyer_total=buyer_utxo_dict["total"]
    blockchain_memory = BlockchainMemory()
    first_block=blockchain_memory.get_blockchain_from_memory()
    first_block_header=first_block.block_header

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
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap',
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability',
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
    
    time.sleep(30)
    
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

    #step7 : retrieve new information
    last_block=blockchain_memory.get_blockchain_from_memory()
    last_block_header=last_block.block_header
    last_transaction=extract_marketplace_request(last_block)

    daniel_transaction=None
    camille_transaction=None
    smart_contract_transaction=None
    for utxo in last_transaction["outputs"]:
        if daniel_owner.public_key_hash in utxo["locking_script"]:daniel_transaction=copy.deepcopy(utxo)
        if camille_owner.public_key_hash in utxo["locking_script"]:camille_transaction=copy.deepcopy(utxo)
        if smart_contract_ref in utxo["locking_script"]:smart_contract_transaction=copy.deepcopy(utxo)


    #step8 : validation
    assert first_block_header.current_PoH_hash==last_block_header.previous_PoH_hash
    assert last_block_header.leader_node_public_key_hash==leader_node_public_key_hash
    assert last_block_header.slot==first_block_header.slot+1
    
    assert len(last_transaction["outputs"])==1
    
    assert smart_contract_transaction["account"]==None
    assert smart_contract_transaction["amount"]==normal_round(requested_nig*2,ROUND_VALUE_DIGIT)
    assert smart_contract_transaction["fee_interface"]==0
    assert smart_contract_transaction["fee_miner"]==0
    assert smart_contract_transaction["fee_node"]==0
    assert smart_contract_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert smart_contract_transaction["locking_script"]=="OP_DUP OP_HASH160 "+marketplace_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG OP_SC "+smart_contract_ref
    assert smart_contract_transaction["network"]=="nig"
    assert smart_contract_transaction["node_public_key_hash"]==node_public_key_hash


def test_marketplace4(marketplace_owner,daniel_owner,camille_owner,smart_contract_wallet,my_node,daniel_wallet,camille_wallet):
    #step 1: extract the smart contract account
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/3/'+camille_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    smart_contract_ref=marketplace_resp["results"][0]["smart_contract_ref"]
    requested_nig=marketplace_resp["results"][0]["requested_nig"]


    #step2 : retrieve initial value
    seller_utxo_dict=get_utxo(camille_owner.public_key_hash,smart_contract_only=False)
    buyer_utxo_dict=get_utxo(daniel_owner.public_key_hash,smart_contract_only=False)
    seller_total=seller_utxo_dict["total"]
    buyer_total=buyer_utxo_dict["total"]
    blockchain_memory = BlockchainMemory()
    first_block=blockchain_memory.get_blockchain_from_memory()
    first_block_header=first_block.block_header

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
    seller_deposit=mp_details[5]*mp_details[6]-mp_details[5]
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
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap',
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability',
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
    
    time.sleep(30)
    
    #step6 : check that there is one purchase request in marketplace 1 and its content
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/3/'+camille_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 0==len(marketplace_resp["results"])

     #step7 : retrieve new information
    last_block=blockchain_memory.get_blockchain_from_memory()
    last_block_header=last_block.block_header
    last_transaction=extract_marketplace_request(last_block)
    transaction_amount=mp_details[5]

    daniel_transaction=None
    camille_transaction=None
    smart_contract_transaction=None
    for utxo in last_transaction["outputs"]:
        if daniel_owner.public_key_hash in utxo["locking_script"]:daniel_transaction=copy.deepcopy(utxo)
        if camille_owner.public_key_hash in utxo["locking_script"]:camille_transaction=copy.deepcopy(utxo)
        if smart_contract_ref in utxo["locking_script"]:smart_contract_transaction=copy.deepcopy(utxo)


    #step5 : calculate fee
    fee_node = normal_round(transaction_amount*(float(DEFAULT_TRANSACTION_FEE_PERCENTAGE)/100)*float(NODE_TRANSACTION_FEE_SHARE)/100,ROUND_VALUE_DIGIT)
    fee_interface = normal_round(transaction_amount*(float(DEFAULT_TRANSACTION_FEE_PERCENTAGE)/100)*float(INTERFACE_TRANSACTION_FEE_SHARE)/100,ROUND_VALUE_DIGIT)
    fee_miner = normal_round(transaction_amount*(float(DEFAULT_TRANSACTION_FEE_PERCENTAGE)/100)*float(MINER_TRANSACTION_FEE_SHARE)/100,ROUND_VALUE_DIGIT)
    real_transaction_amount=normal_round(transaction_amount-fee_node-fee_interface-fee_miner,ROUND_VALUE_DIGIT)
    

    #step8 : validation
    assert first_block_header.current_PoH_hash==last_block_header.previous_PoH_hash
    assert last_block_header.leader_node_public_key_hash==leader_node_public_key_hash2
    assert last_block_header.slot==first_block_header.slot+1
    
    assert len(last_transaction["outputs"])==3
    
    assert smart_contract_transaction["account"]==None
    assert smart_contract_transaction["amount"]==0
    assert smart_contract_transaction["fee_interface"]==0
    assert smart_contract_transaction["fee_miner"]==0
    assert smart_contract_transaction["fee_node"]==0
    assert smart_contract_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert smart_contract_transaction["locking_script"]=="OP_DUP OP_HASH160 "+smart_contract_ref+" OP_EQUAL_VERIFY OP_CHECKSIG"
    assert smart_contract_transaction["network"]=="nig"
    assert smart_contract_transaction["node_public_key_hash"]==node_public_key_hash

    assert daniel_transaction["account"]==None
    assert daniel_transaction["amount"]==real_transaction_amount
    assert daniel_transaction["fee_interface"]==fee_interface
    assert daniel_transaction["fee_miner"]==fee_miner
    assert daniel_transaction["fee_node"]==fee_node
    assert daniel_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert daniel_transaction["locking_script"]=="OP_DUP OP_HASH160 "+daniel_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG"
    assert daniel_transaction["network"]=="nig"
    assert daniel_transaction["node_public_key_hash"]==node_public_key_hash

    assert  camille_transaction["account"]==None
    assert  camille_transaction["amount"]==seller_deposit
    assert  camille_transaction["fee_interface"]==0
    assert  camille_transaction["fee_miner"]==0
    assert  camille_transaction["fee_node"]==0
    assert  camille_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert  camille_transaction["locking_script"]=="OP_DUP OP_HASH160 "+ camille_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG"
    assert  camille_transaction["network"]=="nig"
    assert  camille_transaction["node_public_key_hash"]==node_public_key_hash


def test_marketplace1(marketplace_owner,daniel_owner,daniel_wallet,smart_contract_wallet,my_node,camille_owner,camille_wallet,transaction_amount_eur2):
    #step1 : creation of the smart_contact account number
    utxo_url='http://'+MY_HOSTNAME+'/create_smart_contract_account'
    resp = requests.get(utxo_url)
    smart_contract_account=marketplace_resp = resp.json()
    assert 40==len(smart_contract_account)
    int(smart_contract_account, 16)
    

    #step2 : retrieve initial value
    seller_utxo_dict=get_utxo(camille_owner.public_key_hash,smart_contract_only=False)
    buyer_utxo_dict=get_utxo(daniel_owner.public_key_hash,smart_contract_only=False)
    seller_total=seller_utxo_dict["total"]
    buyer_total=buyer_utxo_dict["total"]
    blockchain_memory = BlockchainMemory()
    first_block=blockchain_memory.get_blockchain_from_memory()
    first_block_header=first_block.block_header

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
mp_request_step2_done.step1("mp_request_step2_done","{daniel_owner.public_key_hash}","{daniel_owner.public_key_hex}",{transaction_amount_eur2},{requested_gap},"{smart_contract_account}","False",1,1)
mp_request_step2_done.account=sender
memory_list.add([mp_request_step2_done,mp_request_step2_done.mp_request_name,['account','step','timestamp','requested_amount',
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap',
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability',
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
    time.sleep(30)
    
    #step6 : check that there is one purchase request in marketplace 1 and its content
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/1/'+marketplace_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 1==len(marketplace_resp["results"])
    assert marketplace_resp["results"][0]['requested_amount']==5
    assert marketplace_resp["results"][0]['requester_public_key_hash']==daniel_owner.public_key_hash
    assert marketplace_resp["results"][0]['requester_public_key_hex']==daniel_owner.public_key_hex
    assert marketplace_resp["results"][0]['smart_contract_ref']==smart_contract_account

     #step7 : retrieve new information
    last_block=blockchain_memory.get_blockchain_from_memory()
    last_block_header=last_block.block_header
    last_transaction=extract_marketplace_request(last_block)

    daniel_transaction=None
    camille_transaction=None
    smart_contract_transaction=None
    for utxo in last_transaction["outputs"]:
        if daniel_owner.public_key_hash in utxo["locking_script"]:daniel_transaction=copy.deepcopy(utxo)
        if camille_owner.public_key_hash in utxo["locking_script"]:camille_transaction=copy.deepcopy(utxo)
        if smart_contract_account in utxo["locking_script"]:smart_contract_transaction=copy.deepcopy(utxo)


    #step8 : validation
    assert first_block_header.current_PoH_hash==last_block_header.previous_PoH_hash
    assert last_block_header.leader_node_public_key_hash==leader_node_public_key_hash
    assert last_block_header.slot==first_block_header.slot+1
    
    assert len(last_transaction["outputs"])==2

    assert smart_contract_transaction["account"]==None
    assert smart_contract_transaction["amount"]==buyer_requested_deposit
    assert smart_contract_transaction["fee_interface"]==0
    assert smart_contract_transaction["fee_miner"]==0
    assert smart_contract_transaction["fee_node"]==0
    assert smart_contract_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert smart_contract_transaction["locking_script"]=="OP_DUP OP_HASH160 "+marketplace_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG OP_SC "+smart_contract_account+" OP_SC "+daniel_owner.public_key_hash+" OP_SC "+marketplace_owner.public_key_hash
    assert smart_contract_transaction["network"]=="nig"
    assert smart_contract_transaction["node_public_key_hash"]==node_public_key_hash

    assert daniel_transaction["account"]==None
    #bug fixing : compare the amount of the transaction and not the total amount of the daniel
    #assert daniel_transaction["amount"]==real_transaction_amount
    assert daniel_transaction["fee_interface"]==0
    assert daniel_transaction["fee_miner"]==0
    assert daniel_transaction["fee_node"]==0
    assert daniel_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert daniel_transaction["locking_script"]=="OP_DUP OP_HASH160 "+daniel_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG"
    assert daniel_transaction["network"]=="nig"
    assert daniel_transaction["node_public_key_hash"]==node_public_key_hash


def test_marketplace21(marketplace_owner,daniel_owner,camille_owner,smart_contract_wallet,my_node,daniel_wallet,camille_wallet,transaction_amount_eur2):
    #step 1: extract the smart contract account
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/1/'+marketplace_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    smart_contract_ref=marketplace_resp["results"][0]["smart_contract_ref"]
    requested_nig=marketplace_resp["results"][0]["requested_nig"]

     #step2 : retrieve initial value
    seller_utxo_dict=get_utxo(camille_owner.public_key_hash,smart_contract_only=False)
    buyer_utxo_dict=get_utxo(daniel_owner.public_key_hash,smart_contract_only=False)
    seller_total=seller_utxo_dict["total"]
    buyer_total=buyer_utxo_dict["total"]
    blockchain_memory = BlockchainMemory()
    first_block=blockchain_memory.get_blockchain_from_memory()
    first_block_header=first_block.block_header

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
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap',
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability',
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
    
    time.sleep(30)
    
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


    #step7 : retrieve new information
    last_block=blockchain_memory.get_blockchain_from_memory()
    last_block_header=last_block.block_header
    last_transaction=extract_marketplace_request(last_block)

    daniel_transaction=None
    camille_transaction=None
    smart_contract_transaction=None
    for utxo in last_transaction["outputs"]:
        if daniel_owner.public_key_hash in utxo["locking_script"]:daniel_transaction=copy.deepcopy(utxo)
        if camille_owner.public_key_hash in utxo["locking_script"]:camille_transaction=copy.deepcopy(utxo)
        if smart_contract_ref in utxo["locking_script"]:smart_contract_transaction=copy.deepcopy(utxo)


    #step8 : validation
    nig_rate=calculate_nig_rate(currency='eur')
    assert first_block_header.current_PoH_hash==last_block_header.previous_PoH_hash
    assert last_block_header.leader_node_public_key_hash==leader_node_public_key_hash2
    assert last_block_header.slot==first_block_header.slot+1
    
    assert len(last_transaction["outputs"])==2
    
    assert smart_contract_transaction["account"]==None
    assert smart_contract_transaction["amount"]==normal_round(mp_details[5]*2+buyer_requested_deposit,ROUND_VALUE_DIGIT)
    assert smart_contract_transaction["fee_interface"]==0
    assert smart_contract_transaction["fee_miner"]==0
    assert smart_contract_transaction["fee_node"]==0
    assert smart_contract_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert smart_contract_transaction["locking_script"]=="OP_DUP OP_HASH160 "+marketplace_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG OP_SC "+smart_contract_ref+" OP_SC "+camille_owner.public_key_hash+" OP_SC "+daniel_owner.public_key_hash+" OP_DEL_SC "+marketplace_owner.public_key_hash
    assert smart_contract_transaction["network"]=="nig"
    assert smart_contract_transaction["node_public_key_hash"]==node_public_key_hash

    assert  camille_transaction["account"]==None
    #bug fixing : compare the amount of the transaction and not the total amount of the camille
    #assert  camille_transaction["amount"]+transaction_amount==seller_total
    assert  camille_transaction["fee_interface"]==0
    assert  camille_transaction["fee_miner"]==0
    assert  camille_transaction["fee_node"]==0
    assert  camille_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert  camille_transaction["locking_script"]=="OP_DUP OP_HASH160 "+ camille_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG"
    assert  camille_transaction["network"]=="nig"
    assert  camille_transaction["node_public_key_hash"]==node_public_key_hash


 
def test_marketplace31(marketplace_owner,daniel_owner,camille_owner,smart_contract_wallet,my_node,daniel_wallet,camille_wallet,transaction_amount_eur2):
    #step 1: extract the smart contract account
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/2/'+daniel_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    smart_contract_ref=marketplace_resp["results"][0]["smart_contract_ref"]
    requested_nig=marketplace_resp["results"][0]["requested_nig"]

    #step2 : retrieve initial value
    seller_utxo_dict=get_utxo(camille_owner.public_key_hash,smart_contract_only=False)
    buyer_utxo_dict=get_utxo(daniel_owner.public_key_hash,smart_contract_only=False)
    seller_total=seller_utxo_dict["total"]
    buyer_total=buyer_utxo_dict["total"]
    blockchain_memory = BlockchainMemory()
    first_block=blockchain_memory.get_blockchain_from_memory()
    first_block_header=first_block.block_header

    #step2 : retrieve initial value
    seller_utxo_dict=get_utxo(camille_owner.public_key_hash,smart_contract_only=False)
    buyer_utxo_dict=get_utxo(daniel_owner.public_key_hash,smart_contract_only=False)
    seller_total=seller_utxo_dict["total"]
    buyer_total=buyer_utxo_dict["total"]
    blockchain_memory = BlockchainMemory()
    first_block=blockchain_memory.get_blockchain_from_memory()
    first_block_header=first_block.block_header

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
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap',
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability',
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
    
    time.sleep(30)
    
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

    #step7 : retrieve new information
    last_block=blockchain_memory.get_blockchain_from_memory()
    last_block_header=last_block.block_header
    last_transaction=extract_marketplace_request(last_block)

    daniel_transaction=None
    camille_transaction=None
    smart_contract_transaction=None
    for utxo in last_transaction["outputs"]:
        if daniel_owner.public_key_hash in utxo["locking_script"]:daniel_transaction=copy.deepcopy(utxo)
        if camille_owner.public_key_hash in utxo["locking_script"]:camille_transaction=copy.deepcopy(utxo)
        if smart_contract_ref in utxo["locking_script"]:smart_contract_transaction=copy.deepcopy(utxo)


    #step8 : validation
    assert first_block_header.current_PoH_hash==last_block_header.previous_PoH_hash
    assert last_block_header.leader_node_public_key_hash==leader_node_public_key_hash
    assert last_block_header.slot==first_block_header.slot+1
    
    assert len(last_transaction["outputs"])==1
    
    assert smart_contract_transaction["account"]==None
    assert smart_contract_transaction["amount"]==normal_round(requested_nig*2+mp_details[9],ROUND_VALUE_DIGIT)
    assert smart_contract_transaction["fee_interface"]==0
    assert smart_contract_transaction["fee_miner"]==0
    assert smart_contract_transaction["fee_node"]==0
    assert smart_contract_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert smart_contract_transaction["locking_script"]=="OP_DUP OP_HASH160 "+marketplace_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG OP_SC "+smart_contract_ref
    assert smart_contract_transaction["network"]=="nig"
    assert smart_contract_transaction["node_public_key_hash"]==node_public_key_hash



def test_marketplace41(marketplace_owner,daniel_owner,camille_owner,smart_contract_wallet,my_node,daniel_wallet,camille_wallet):
    #step 1: extract the smart contract account
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/3/'+camille_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    smart_contract_ref=marketplace_resp["results"][0]["smart_contract_ref"]
    requested_nig=marketplace_resp["results"][0]["requested_nig"]

    #step2 : retrieve initial value
    seller_utxo_dict=get_utxo(camille_owner.public_key_hash,smart_contract_only=False)
    buyer_utxo_dict=get_utxo(daniel_owner.public_key_hash,smart_contract_only=False)
    seller_total=seller_utxo_dict["total"]
    buyer_total=buyer_utxo_dict["total"]
    blockchain_memory = BlockchainMemory()
    first_block=blockchain_memory.get_blockchain_from_memory()
    first_block_header=first_block.block_header

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
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1','timestamp_step2','timestamp_step3','timestamp_step4','requested_gap',
  'buyer_public_key_hex','requested_nig','timestamp_nig','recurrency_flag','recurrency_duration','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability',
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
    
    time.sleep(30)
    
    #step6 : check that there is one purchase request in marketplace 1 and its content
    utxo_url='http://'+MY_HOSTNAME+'/marketplace_step/3/'+camille_owner.public_key_hash
    resp = requests.get(utxo_url)
    marketplace_resp = resp.json()
    assert 0==len(marketplace_resp["results"])


     #step7 : retrieve new information
    last_block=blockchain_memory.get_blockchain_from_memory()
    last_block_header=last_block.block_header
    last_transaction=extract_marketplace_request(last_block)
    transaction_amount=mp_details[5]
    seller_deposit=mp_details[5]*mp_details[6]-mp_details[5]
    buyer_requested_deposit=mp_details[9]

    daniel_transaction1=None
    daniel_transaction2=None
    camille_transaction=None
    smart_contract_transaction=None
    for utxo in last_transaction["outputs"]:
        if daniel_owner.public_key_hash in utxo["locking_script"]:
            if daniel_transaction1 is None:daniel_transaction1=copy.deepcopy(utxo)
            else:daniel_transaction2=copy.deepcopy(utxo)
        if camille_owner.public_key_hash in utxo["locking_script"]:camille_transaction=copy.deepcopy(utxo)
        if smart_contract_ref in utxo["locking_script"]:smart_contract_transaction=copy.deepcopy(utxo)


    #step5 : calculate fee
    fee_node = normal_round(transaction_amount*(float(DEFAULT_TRANSACTION_FEE_PERCENTAGE)/100)*float(NODE_TRANSACTION_FEE_SHARE)/100,ROUND_VALUE_DIGIT)
    fee_interface = normal_round(transaction_amount*(float(DEFAULT_TRANSACTION_FEE_PERCENTAGE)/100)*float(INTERFACE_TRANSACTION_FEE_SHARE)/100,ROUND_VALUE_DIGIT)
    fee_miner = normal_round(transaction_amount*(float(DEFAULT_TRANSACTION_FEE_PERCENTAGE)/100)*float(MINER_TRANSACTION_FEE_SHARE)/100,ROUND_VALUE_DIGIT)
    real_transaction_amount=normal_round(transaction_amount-fee_node-fee_interface-fee_miner,ROUND_VALUE_DIGIT)
    

    #step8 : validation
    assert first_block_header.current_PoH_hash==last_block_header.previous_PoH_hash
    assert last_block_header.leader_node_public_key_hash==leader_node_public_key_hash2
    assert last_block_header.slot==first_block_header.slot+1
    
    assert len(last_transaction["outputs"])==4
    
    assert smart_contract_transaction["account"]==None
    assert smart_contract_transaction["amount"]==0
    assert smart_contract_transaction["fee_interface"]==0
    assert smart_contract_transaction["fee_miner"]==0
    assert smart_contract_transaction["fee_node"]==0
    assert smart_contract_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert smart_contract_transaction["locking_script"]=="OP_DUP OP_HASH160 "+smart_contract_ref+" OP_EQUAL_VERIFY OP_CHECKSIG"
    assert smart_contract_transaction["network"]=="nig"
    assert smart_contract_transaction["node_public_key_hash"]==node_public_key_hash

    assert daniel_transaction1["account"]==None
    assert daniel_transaction1["amount"]==real_transaction_amount
    assert daniel_transaction1["fee_interface"]==fee_interface
    assert daniel_transaction1["fee_miner"]==fee_miner
    assert daniel_transaction1["fee_node"]==fee_node
    assert daniel_transaction1["interface_public_key_hash"]==interface_public_key_hash
    assert daniel_transaction1["locking_script"]=="OP_DUP OP_HASH160 "+daniel_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG"
    assert daniel_transaction1["network"]=="nig"
    assert daniel_transaction1["node_public_key_hash"]==node_public_key_hash

    assert daniel_transaction2["account"]==None
    assert daniel_transaction2["amount"]==buyer_requested_deposit
    assert daniel_transaction2["fee_interface"]==0
    assert daniel_transaction2["fee_miner"]==0
    assert daniel_transaction2["fee_node"]==0
    assert daniel_transaction2["interface_public_key_hash"]==interface_public_key_hash
    assert daniel_transaction2["locking_script"]=="OP_DUP OP_HASH160 "+daniel_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG"
    assert daniel_transaction2["network"]=="nig"
    assert daniel_transaction2["node_public_key_hash"]==node_public_key_hash

    assert  camille_transaction["account"]==None
    assert  camille_transaction["amount"]==seller_deposit
    assert  camille_transaction["account"]==None
    assert  camille_transaction["fee_interface"]==0
    assert  camille_transaction["fee_miner"]==0
    assert  camille_transaction["fee_node"]==0
    assert  camille_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert  camille_transaction["locking_script"]=="OP_DUP OP_HASH160 "+ camille_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG"
    assert  camille_transaction["network"]=="nig"
    assert  camille_transaction["node_public_key_hash"]==node_public_key_hash

