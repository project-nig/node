
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
from common.values import NETWORK_DEFAULT,DEFAULT_TRANSACTION_FEE_PERCENTAGE,INTERFACE_TRANSACTION_FEE_SHARE,NODE_TRANSACTION_FEE_SHARE,MINER_TRANSACTION_FEE_SHARE,ROUND_VALUE_DIGIT
from common.transaction_account import TransactionAccount

from common.utils import normal_round


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



def test_simple_transaction(marketplace_owner,daniel_owner,daniel_wallet,smart_contract_wallet,my_node,camille_owner,camille_wallet,transaction_amount_eur):
    #step1 : reset the blockchain
    utxo_url="http://127.0.0.1:5000/restart"
    resp = requests.get(utxo_url)
    time.sleep(10)


    #step2 : retrieve initial value
    transaction_amount=10
    seller_utxo_dict=get_utxo(camille_owner.public_key_hash,smart_contract_only=False)
    buyer_utxo_dict=get_utxo(daniel_owner.public_key_hash,smart_contract_only=False)
    seller_total=seller_utxo_dict["total"]
    buyer_total=buyer_utxo_dict["total"]

    blockchain_memory = BlockchainMemory()
    first_block=blockchain_memory.get_blockchain_from_memory()
    first_block_header=first_block.block_header
    
    #step 3 : sale of NIG
    unlocking_public_key_hash=camille_owner.public_key_hash
    input_list=[]
    output_list=[]
    print(f"#### input_list:{input_list}")
    for utxo in seller_utxo_dict['utxos']:
        input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash=unlocking_public_key_hash))
        output_list.append(TransactionOutput(list_public_key_hash=[daniel_owner.public_key_hash], 
                                                amount=transaction_amount,
                                                transfer_flag=True,
                                                interface_public_key_hash=interface_public_key_hash))
        output_list.append(TransactionOutput(list_public_key_hash=[camille_owner.public_key_hash], 
                                                amount=utxo['amount']-transaction_amount,
                                                interface_public_key_hash=interface_public_key_hash))
        break

    camille_wallet.process_transaction(inputs=input_list, outputs=output_list)
    time.sleep(20)
    
    #step4 : retrieve new value
    seller_utxo_dict=get_utxo(camille_owner.public_key_hash)
    buyer_utxo_dict=get_utxo(daniel_owner.public_key_hash)
    new_seller_total=seller_utxo_dict["total"]
    new_buyer_total=buyer_utxo_dict["total"]

    #step5 : calculate fee
    fee_node = normal_round(transaction_amount*(float(DEFAULT_TRANSACTION_FEE_PERCENTAGE)/100)*float(NODE_TRANSACTION_FEE_SHARE)/100,ROUND_VALUE_DIGIT)
    fee_interface = normal_round(transaction_amount*(float(DEFAULT_TRANSACTION_FEE_PERCENTAGE)/100)*float(INTERFACE_TRANSACTION_FEE_SHARE)/100,ROUND_VALUE_DIGIT)
    fee_miner = normal_round(transaction_amount*(float(DEFAULT_TRANSACTION_FEE_PERCENTAGE)/100)*float(MINER_TRANSACTION_FEE_SHARE)/100,ROUND_VALUE_DIGIT)
    real_transaction_amount=normal_round(transaction_amount-fee_node-fee_interface-fee_miner,ROUND_VALUE_DIGIT)
    
    
    #step6 : retrieve new information
    last_block=blockchain_memory.get_blockchain_from_memory()
    last_block_header=last_block.block_header
    last_transaction=last_block.transactions[0]

    daniel_transaction=None
    camille_transaction=None
    for utxo in last_transaction["outputs"]:
        if daniel_owner.public_key_hash in utxo["locking_script"]:daniel_transaction=copy.deepcopy(utxo)
        if camille_owner.public_key_hash in utxo["locking_script"]:camille_transaction=copy.deepcopy(utxo)


    #step7 : validation
    assert first_block_header.current_PoH_hash==last_block_header.previous_PoH_hash
    assert last_block_header.leader_node_public_key_hash==leader_node_public_key_hash
    assert last_block_header.slot==13
    
    assert new_seller_total+transaction_amount==seller_total
    assert new_buyer_total==real_transaction_amount

    assert len(last_transaction["outputs"])==2

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
    #bug fixing : compare the amount of the transaction and not the total amount of the camille
    #assert  camille_transaction["amount"]+transaction_amount==seller_total
    assert  camille_transaction["fee_interface"]==0
    assert  camille_transaction["fee_miner"]==0
    assert  camille_transaction["fee_node"]==0
    assert  camille_transaction["interface_public_key_hash"]==interface_public_key_hash
    assert  camille_transaction["locking_script"]=="OP_DUP OP_HASH160 "+ camille_owner.public_key_hash+" OP_EQUAL_VERIFY OP_CHECKSIG"
    assert  camille_transaction["network"]=="nig"
    assert  camille_transaction["node_public_key_hash"]==node_public_key_hash


