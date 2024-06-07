import logging
import os, shutil
import requests
import time
import datetime as datetime_delta
from datetime import datetime
import math
import json
import copy

import threading
from multiprocessing.dummy import Pool as ThreadPool

from flask import Flask, request, jsonify

from common.io_blockchain import BlockchainMemory
from common.io_known_nodes import KnownNodesMemory
from common.master_state import MasterState
from common.network import Network
from common.node import Node
from node.new_block_validation.new_block_validation import NewBlock, NewBlockException
from node.transaction_validation.transaction_validation import Transaction, TransactionException
from common.io_mem_pool import MemPool
from common.values import ROUND_VALUE_DIGIT
from common.utils import normal_round,clean_request
from common.io_leader_node_schedule import LeaderNodeScheduleMemory
from node.new_block_creation.new_block_creation import ProofOfWork, BlockException

from common.proof_of_history import ProofOfHistory
from common.smart_contract import SmartContract,check_smart_contract,load_smart_contract,load_smart_contract_from_master_state,load_smart_contract_from_master_state_leader_node,check_double_contract

logging.basicConfig(level=logging.DEBUG, format=f'%(asctime)s: %(message)s')

app = Flask(__name__)

from blockchain_users.albert import private_key as albert_private_key
from blockchain_users.albert import public_key_hash as albert_public_key_hash
from blockchain_users.bertrand import private_key as bertrand_private_key
from blockchain_users.bertrand import public_key_hash as bertrand_public_key_hash
from blockchain_users.camille import private_key as camille_private_key
from blockchain_users.camille import public_key_hash as camille_public_key_hash
from blockchain_users.marketplace import private_key as marketplace_private_key
from blockchain_users.marketplace import public_key_hash as marketplace_public_key_hash
from blockchain_users.daniel import private_key as daniel_private_key
from blockchain_users.daniel import public_key_hash as daniel_public_key_hash

from blockchain_users.albert import account_name as albert_account_name
from blockchain_users.albert import account_iban as albert_account_iban
from blockchain_users.albert import account_bic as albert_account_bic
from blockchain_users.albert import account_email as albert_account_email
from blockchain_users.albert import account_phone as albert_account_phone
from blockchain_users.albert import account_country as albert_account_country
from blockchain_users.albert import public_key_hex as albert_public_key_hex

from blockchain_users.bertrand import account_name as bertrand_account_name
from blockchain_users.bertrand import account_iban as bertrand_account_iban
from blockchain_users.bertrand import account_bic as bertrand_account_bic
from blockchain_users.bertrand import account_email as bertrand_account_email
from blockchain_users.bertrand import account_phone as bertrand_account_phone
from blockchain_users.bertrand import account_country as bertrand_account_country
from blockchain_users.bertrand import public_key_hex as bertrand_public_key_hex

from blockchain_users.camille import account_name as camille_account_name
from blockchain_users.camille import account_iban as camille_account_iban
from blockchain_users.camille import account_bic as camille_account_bic
from blockchain_users.camille import account_email as camille_account_email
from blockchain_users.camille import account_phone as camille_account_phone
from blockchain_users.camille import account_country as camille_account_country
from blockchain_users.camille import public_key_hex as camille_public_key_hex

from blockchain_users.daniel import account_name as daniel_account_name
from blockchain_users.daniel import account_iban as daniel_account_iban
from blockchain_users.daniel import account_bic as daniel_account_bic
from blockchain_users.daniel import account_email as daniel_account_email
from blockchain_users.daniel import account_phone as daniel_account_phone
from blockchain_users.daniel import account_country as daniel_account_country
from blockchain_users.daniel import public_key_hex as daniel_public_key_hex

from blockchain_users.interface import public_key_hash as interface_public_key_hash


albert_account_name,albert_account_iban,albert_account_bic,albert_account_email,albert_account_phone,albert_account_country

from wallet.wallet import Owner, Wallet
from common.transaction_account import TransactionAccount
    

#SERVER SETUP
#MY_HOSTNAME = 'vps90852.serveur-vps.net'
#TRANSACTION_HOSTNAME = 'vps90851.serveur-vps.net'
#NODE_FILES_ROOT = r'/home/pierre/nig_node'
#FIRST_KNOWN_NODE_HOSTNAME = 'vps90843.serveur-vps.net'
#NODE_TO_AVOID_HOSTNAME1 = {'hostname': 'vps90843.serveur-vps.net'}
#NODE_TO_AVOID_HOSTNAME3 = {'hostname': 'vps90852.serveur-vps.net'}
#MEMPOOL_DIR = NODE_FILES_ROOT+r'/files/MEMPOOL_DIR.txt'
#KNOWN_NODES_DIR = NODE_FILES_ROOT+r'/files/KNOWN_NODES_DIR.txt'
#LEADER_NODE_SCHEDULE_DIR = NODE_FILES_ROOT+r'/files/LEADER_NODE_SCHEDULE_DIR.txt'
#BLOCKCHAIN_DIR = NODE_FILES_ROOT+r'/files/BLOCKCHAIN_DIR.txt'
#STORAGE_DIR = NODE_FILES_ROOT+r'/STORAGE'
#MASTER_STATE_DIR = r'/master_state'
#MASTER_STATE_DIR_TEMP = r'/master_state_temp'
#LEADER_NODE_TRANSACTIONS_ADVANCE = r'/leader_node_advance'
#MASTER_STATE_DEEPTH=0
#NEW_BLOCKCHAIN_DIR = r'/blockchain'
#NEW_BLOCKCHAIN_DEEPTH=0
#PoH_DURATION_SEC=10


#LOCAL SETUP
MY_HOSTNAME = '127.0.0.3:5000'
TRANSACTION_HOSTNAME = '127.0.0.2:5000'
NODE_FILES_ROOT = r'C:\Users\davidlio\source\nig\node3'
FIRST_KNOWN_NODE_HOSTNAME = "127.0.0.1:5000"
NODE_TO_AVOID_HOSTNAME1 = {'hostname': '127.0.0.1:5000'}
NODE_TO_AVOID_HOSTNAME3 = {'hostname': '127.0.0.3:5000'}
MEMPOOL_DIR = NODE_FILES_ROOT+r'\files\MEMPOOL_DIR.txt'
KNOWN_NODES_DIR = NODE_FILES_ROOT+r'\files\KNOWN_NODES_DIR.txt'
LEADER_NODE_SCHEDULE_DIR = NODE_FILES_ROOT+r'\files\LEADER_NODE_SCHEDULE_DIR.txt'
BLOCKCHAIN_DIR = NODE_FILES_ROOT+r'\files\BLOCKCHAIN_DIR.txt'
STORAGE_DIR = NODE_FILES_ROOT+r'\STORAGE'
MASTER_STATE_DIR = r'\master_state'
MASTER_STATE_DIR_TEMP = r'\master_state_temp'
LEADER_NODE_TRANSACTIONS_ADVANCE = r'\leader_node_advance'
MASTER_STATE_DEEPTH=0
NEW_BLOCKCHAIN_DIR = r'\blockchain'
NEW_BLOCKCHAIN_DEEPTH=0
PoH_DURATION_SEC=10


albert_owner=Owner(private_key=albert_private_key)
bertrand_owner=Owner(private_key=bertrand_private_key)
camille_owner=Owner(private_key=camille_private_key)
marketplace_owner=Owner(private_key=marketplace_private_key)
daniel_owner=Owner(private_key=daniel_private_key)
    
albert_wallet = Wallet(albert_owner,Node(MY_HOSTNAME),account=TransactionAccount(albert_account_name,albert_account_iban,albert_account_bic,albert_account_email,albert_account_phone,albert_account_country,albert_public_key_hash))
bertrand_wallet = Wallet(bertrand_owner,Node(MY_HOSTNAME),account=TransactionAccount(bertrand_account_name,bertrand_account_iban,bertrand_account_bic,bertrand_account_email,bertrand_account_phone,bertrand_account_country,bertrand_public_key_hash))
camille_wallet = Wallet(camille_owner,Node(MY_HOSTNAME),account=TransactionAccount(camille_account_name,camille_account_iban,camille_account_bic,camille_account_email,camille_account_phone,camille_account_country,camille_public_key_hash))
marketplace_wallet = Wallet(marketplace_owner,Node(MY_HOSTNAME))
daniel_wallet = Wallet(daniel_owner,Node(MY_HOSTNAME),account=TransactionAccount(daniel_account_name,daniel_account_iban,daniel_account_bic,daniel_account_email,daniel_account_phone,daniel_account_country,daniel_public_key_hash))

mempool = MemPool()
blockchain_memory = BlockchainMemory()
my_node = Node(MY_HOSTNAME)
network = Network(my_node)
network.join_network()

PoW_memory = ProofOfWork(MY_HOSTNAME)
PoH_memory=ProofOfHistory(PoW_memory=PoW_memory)
#PoH_memory.launch_PoH()

master_state=MasterState()

@app.route("/", methods=['GET'])
def main_request():
    logging.info("main page request")
    return "Restart success", 200


@app.route("/block", methods=['POST'])
def validate_block():
    content = request.json
    #fix for boolean
    content=clean_request(content)
    block_multiprocessing=BlockMultiProcessing()
    block_multiprocessing.launch(content)
    return "Transaction success", 200

@app.route("/block_saving_leader_node", methods=['POST'])
def block_saving_leader_node():
    content = request.json
    #fix for boolean
    content=clean_request(content)
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    try:
        block = NewBlock(blockchain_base, MY_HOSTNAME)
        block.receive(new_block=content["block"], sender=content["sender"])
        #no need to validate as it was already done for LeaderNode
        #block.validate()
        block.add()
        block.clear_block_transactions_from_mempool()
        try:
            shutil.rmtree(STORAGE_DIR+MASTER_STATE_DIR_TEMP)
            pass
        except:
            pass
        #block.broadcast()
    except (NewBlockException, TransactionException) as new_block_exception:
        return f'{new_block_exception}', 400
    return "Transaction success", 200

@app.route("/block_PoH_registry_input_data", methods=['POST'])
def validate_block_PoH_registry_input_data():
    PoH_registry_input_data = request.json
    start = time.time()
    PoH_validation=ProofOfHistory()
    #logging.info(f"registry_input_data {PoH_validation.registry_input_data}")
    PoH_validation.validate_PoH_registry(PoH_registry_input_data)
    check=PoH_validation.get_validation_status()
    if check==False:logging.info(f"Validation block_PoH_registry_input_data without success !!")
    else:logging.info(f"Validation block_PoH_registry_input_data with success")
    #logging.info(f"registry_intermediary {PoH_validation.registry_intermediary}")
    #PoH_validation.stop()
    end = time.time()
    logging.info(f"Validation block_PoH_registry_input_data operation:{end-start} sec")
    return "Transaction success", 200

@app.route("/block_PoH_registry_intermediary", methods=['POST'])
def validate_block_PoH_registry_intermediary():
    PoH_registry_intermediary = request.json
    start = time.time()
    PoH_validation=ProofOfHistory()
    #logging.info(f"registry_input_data {PoH_validation.registry_input_data}")
    PoH_validation.validate_PoH_registry_intermediary(PoH_registry_intermediary)
    check=PoH_validation.get_validation_status()
    if check==False:logging.info(f"Validation block_PoH_registry_intermediary without success !!")
    else:logging.info(f"Validation block_PoH_registry_intermediary with success")
    #logging.info(f"registry_intermediary {PoH_validation.registry_intermediary}")
    #PoH_validation.stop()
    end = time.time()
    logging.info(f"Validation block_PoH_registry_intermediary operation:{end-start} sec")
    return "Transaction success", 200





@app.route("/transactions", methods=['POST'])
def validate_transaction():
    logging.info("New transaction validation request")
    content = request.json
    #fix for boolean
    content=clean_request(content)
    #logging.info(f"content: {content}")
    logging.info(f"====>content: {content}")
    logging.info(f"Transaction: {content['transaction']}")
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    try:
        transaction = Transaction(blockchain_base, MY_HOSTNAME)
        transaction.receive(transaction=content["transaction"])
        if transaction.is_new:
            logging.info("Transaction is new")
            transaction.validate()
            transaction.validate_funds()
            #no more need to store 
            #transaction.store()
            smart_contract_flag,smart_contract_index_list=check_smart_contract(transaction)
            if smart_contract_flag:
                #there are smart contract in the transaction, let's validate them
                #transaction.validate_smart_contract(smart_contract_index_list)
                pass
            logging.info(f"Transaction api_readonly_flag: {transaction.api_readonly_flag}")
            if check_double_contract(transaction) is True: return "ERROR: multiple output transactions for same smart contract account", 400
            if transaction.api_readonly_flag is False:transaction.broadcast_to_leader_node()
    except TransactionException as transaction_exception:
        return f'{transaction_exception}', 400
    return "Transaction success", 200


@app.route("/transactions_to_leader_node", methods=['POST'])
def transactions_to_leader_node():
    logging.info("New transaction to leader node request")
    content = request.json
    #logging.info(f"content: {content}")
    logging.info(f"Transaction: {content['transaction']}")
    #Launch of Multiprocessing to handle the volume of transaction
    transaction_multiprocessing=TransactionMultiProcessing()
    transaction_multiprocessing.launch(content['transaction'])
    
    return "Transaction success", 200

def leader_node_advance_purge_backlog():
    logging.info(f"### leader_node_advance_purge_backlog")
    #this function aims to purge the potential backlog of transaction during leader note rotation
    import os
    if not os.path.exists(STORAGE_DIR+LEADER_NODE_TRANSACTIONS_ADVANCE):
        #the directory is not existing, let's create it
        os.makedirs(STORAGE_DIR+LEADER_NODE_TRANSACTIONS_ADVANCE)
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    directory = os.fsencode(STORAGE_DIR+LEADER_NODE_TRANSACTIONS_ADVANCE)
    for file in os.listdir(directory):
         filename = os.fsdecode(file)
         #the filename is the transaction hash
         if blockchain_base.get_transaction(filename)=={}:
             logging.info(f"==> transaction in advance UNKNOWN !!!!! :{filename}")
             #The transaction is unkown in the blockchain, weed to add it
             transaction_filename=STORAGE_DIR+LEADER_NODE_TRANSACTIONS_ADVANCE+f"/{filename.lower()}".replace("'","")
             with open(transaction_filename, "rb") as file_obj:
                transaction_str = file_obj.read()
                transaction_data = json.loads(transaction_str)
                #my_node.send_transaction_to_leader_node({"transaction": transaction_data,"purge_flag": False})
                Process_transaction(purge_flag=False,transaction_data=transaction_data)
         else:
            logging.info(f"==> transaction in advance known: {filename}")
    
    #let's clean all the file of the folder
    import os, glob
 
    dir = STORAGE_DIR+LEADER_NODE_TRANSACTIONS_ADVANCE
    filelist = glob.glob(os.path.join(dir, "*"))
    for f in filelist:
        os.remove(f)

             

@app.route("/transactions_to_leader_node_advance", methods=['POST'])
def transactions_to_leader_node_advance():
    logging.info("New transaction to leader node request in advance")
    content = request.json
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    try:
        transaction=content["transaction"]
        transaction_hash=transaction['transaction_hash']
        if not os.path.exists(STORAGE_DIR+LEADER_NODE_TRANSACTIONS_ADVANCE):
            #the directory is not existing, let's create it
            os.makedirs(STORAGE_DIR+LEADER_NODE_TRANSACTIONS_ADVANCE)
            
        transaction_filename=STORAGE_DIR+LEADER_NODE_TRANSACTIONS_ADVANCE+f"/{transaction_hash.lower()}".replace("'","")
        transaction_data = json.dumps(transaction).encode("utf-8")
        with open(transaction_filename, "wb") as file_obj:
            file_obj.write(transaction_data)
        
    except TransactionException as transaction_exception:
        return f'{transaction_exception}', 400
    return "Transaction success", 200


@app.route("/block", methods=['GET'])
def get_blocks():
    logging.info("Block request")
    #blockchain_base = blockchain_memory.get_blockchain_from_memory()
    blockchain_base = blockchain_memory.get_all_blockchain_from_memory()
    return jsonify(blockchain_base.to_dict)

@app.route("/leader_node_schedule", methods=['GET'])
def get_leader_node_schedule():
    logging.info("Get Leader Node Schedule")
    leader_node_schedule=LeaderNodeScheduleMemory()
    return jsonify(leader_node_schedule.leader_node_schedule_json)

@app.route("/current_leader_node", methods=['GET'])
def get_current_leader_node():
    return jsonify(get_current_leader_node_url())

def get_current_leader_node_url():
    leader_node_url=None
    logging.info("provide current Leader Node")
    leader_node_schedule=LeaderNodeScheduleMemory()
    leader_node_schedule_list=leader_node_schedule.leader_node_schedule_json
    for epoch in leader_node_schedule_list:
        for leader_node in epoch["LeaderNodeList"]:
            if leader_node["already_processed"]==False:
                #this is the active LeaderNode
                leader_node_url=leader_node["node"]["hostname"]
                break
        if leader_node_url is not None:break
    return leader_node_url

@app.route("/utxo/<user>", methods=['GET'])
def get_user_utxos(user):
    logging.info(f"User utxo request {user}")
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_user_utxos(user))

@app.route("/smart_contract_api/<account>/<smart_contract_transaction_hash>", methods=['GET'])
def get_smart_contract_api2(account,smart_contract_transaction_hash):
    logging.info(f"smart_contract_api account:{account} ")
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_smart_contract_api(account,smart_contract_transaction_hash=smart_contract_transaction_hash))

@app.route("/smart_contract_api/<account>", methods=['GET'])
def get_smart_contract_api(account):
    logging.info(f"smart_contract_api account:{account} ")
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_smart_contract_api(account))

@app.route("/smart_contract_api_leader_node/<account>/<smart_contract_transaction_hash>", methods=['GET'])
def get_smart_contract_api_leader_node(account,smart_contract_transaction_hash):
    logging.info(f"smart_contract_api_leader_node account:{account} ")
    return jsonify(load_smart_contract_from_master_state_leader_node(account,smart_contract_transaction_hash=smart_contract_transaction_hash))

@app.route("/leader_node_smart_contract_api/<account>", methods=['GET'])
def get_leader_node_smart_contract_api(account):
    logging.info(f"leader_node_smart_contract_api account:{account} ")
    smart_contract_previous_transaction,smart_contract_transaction_hash,smart_contract_transaction_output_index=load_smart_contract_from_master_state(account)
    return jsonify({'smart_contract_transaction_hash':smart_contract_transaction_hash})   

@app.route("/utxo_balance/<user>", methods=['GET'])
def get_user_utxo_balance(user):
    logging.info(f"User utxo spent request {user}")
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_user_utxos_balance(user))

@app.route("/all_utxo/<user>", methods=['GET'])
def get_user_all_utxos(user):
    logging.info(f"User all utxo request {user}")
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_user_all_utxos(user))

@app.route("/utxo_raw/<user>", methods=['GET'])
def get_user_utxos_raw(user):
    logging.info(f"User utxo request {user}")
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_user_utxos_raw(user))

@app.route("/utxo_account_temp/<user>", methods=['GET'])
def get_user_utxos_account_temp(user):
    logging.info(f"User utxo request for account temp {user}")
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_user_utxos_account_temp(user))

@app.route("/utxo_account_temp/<user>/<payment_ref>", methods=['GET'])
def get_user_utxos_account_temp_payment_ref(user,payment_ref):
    logging.info(f"User utxo request for account temp {user}")
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_user_utxos_account_temp(user,payment_ref=payment_ref))


@app.route("/transactions/<transaction_hash>", methods=['GET'])
def get_transaction(transaction_hash):
    logging.info(f"Transaction request {transaction_hash}")
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_transaction(transaction_hash))


@app.route("/new_node_advertisement", methods=['POST'])
def new_node_advertisement():
    logging.info("New node advertisement request")
    content = request.json
    hostname = content["hostname"]
    known_nodes_memory = KnownNodesMemory()
    try:
        new_node = Node(hostname)
        known_nodes_memory.store_new_node(new_node)
    except TransactionException as transaction_exception:
        return f'{transaction_exception}', 400
    return "New node advertisement success", 200

@app.route("/new_leader_node_schedule_advertisement", methods=['POST'])
def new_leader_node_schedule_advertisement():
    logging.info("New leader node schedule advertisement request")
    content = request.json
    leader_node_schedule_raw = content["leader_node_schedule"]
    leader_node_schedule_memory = LeaderNodeScheduleMemory()
    try:
        logging.info(f"leader_node_schedule_raw {leader_node_schedule_raw}")
        leader_node_schedule_json = json.loads(leader_node_schedule_raw)
        leader_node_schedule_memory.store_new_leader_node_schedule_json(leader_node_schedule_json)
    except TransactionException as transaction_exception:
        return f'{transaction_exception}', 400
    return "New node advertisement success", 200


@app.route("/known_node_request", methods=['GET'])
def known_node_request():
    logging.info("Known node request")
    return jsonify(network.return_known_nodes())


@app.route("/restart", methods=['GET'])
def restart():
    logging.info("===Network restart request")
    known_nodes_memory=KnownNodesMemory()
    known_nodes_memory.known_nodes
    node_list = known_nodes_memory.known_nodes
    new_node_list=[]
    for node in node_list:
        new_node_list.append(node)

    logging.info(f"===new_node_list:{new_node_list}")
    my_node = Node(MY_HOSTNAME)
    network = Network(my_node)
    mempool = MemPool()
    mempool.clear_transactions_from_memory()
    
    
    #full reset of the netowrk
    shutil.rmtree(STORAGE_DIR)
    os.makedirs(STORAGE_DIR)
    network.known_nodes_memory = KnownNodesMemory()
    network.join_network()
    #ask all the node to rejoin the reseted networkd
    for node in new_node_list:
        logging.info(f"node: {node} my_node:{my_node}")
        if node!= my_node:
            node.restart_request()
    return "Network Restart success", 200

@app.route("/restart_request", methods=['POST'])
def restart_request():
    logging.info("Node restart request")
    my_node = Node(MY_HOSTNAME)
    network = Network(my_node)
    mempool = MemPool()
    mempool.clear_transactions_from_memory()
    node_list = network.return_known_nodes()
    #full reset of the netowrk
    shutil. rmtree(STORAGE_DIR)
    os.makedirs(STORAGE_DIR)
    network.known_nodes_memory = KnownNodesMemory()
    network.join_network()
    return "Node Restart success", 200


def main():
    global network
    my_node = Node(MY_HOSTNAME)
    network = Network(my_node)
    network.join_network()
    app.run()


@app.route("/sell_followup_step4_pin/<user>/<payment_ref>", methods=['GET'])
def sell_followup_step4_pin(user,payment_ref):
    logging.info(f"sell_followup_step4_pin user:{user} payment_ref:{payment_ref}")
    pin_encrypted=None
    try:
        blockchain_base = blockchain_memory.get_blockchain_from_memory()
    except Exception as e:
        logging.info(f"exception: {e}")
    
    pin_encrypted=blockchain_base.get_followup_step4_pin(user,payment_ref)


    if pin_encrypted is not None:
        response={'pin_encrypted':pin_encrypted}
        return jsonify(response)
    else:
        logging.info(f"not pin found for payment_ref: {payment_ref}")
        response={'pin_encrypted':'not found'}
        return jsonify(response)
    return "Restart success", 200

@app.route("/encryption_test", methods=['GET'])
def encryption_test():
    logging.info("encryption_test")
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
    import binascii, json
    transaction_data = {
            "name": "Banque Postale Lionel DAVID",
            "iban":"FR03 2004 1010 1709 5633 8F02 896",
            "bic": "PSSTFRPPGRE",
            "email": "lion.david@gmail.com",
            "phone": "0686872549",
            "country" : "France" ,
        }
    data = json.dumps(transaction_data, indent=2)
    
    #logging.info(f"data: {data}")
    #step 1 encryption
    key = RSA.importKey(binascii.unhexlify(camille_public_key_hex))
    cipher = Cipher_PKCS1_v1_5.new(key)
    data_encrypted=cipher.encrypt(data.encode())
    logging.info(f"data_encrypted: {data_encrypted}")

    #data2 = json.dumps(data_encrypted.decode("utf8"))
    data2 = json.dumps(data_encrypted.hex())
    logging.info(f"data2: {data2}")
    

    data3=bytes.fromhex(json.loads(data2))
    logging.info(f"data3: {data3}")

    

    #step 2 decryption
    key = RSA.importKey(camille_private_key)
    decipher = Cipher_PKCS1_v1_5.new(key)
    #data_decrypted=decipher.decrypt(str.encode(str(data_encrypted,'utf-8', 'ignore')), None).decode()
    data_decrypted=decipher.decrypt(bytes.fromhex(json.loads(data2)), None).decode()
    #logging.info(f"data_decrypted: {data_decrypted}")

    transaction_data_decrypted = json.loads(data_decrypted)
    test=transaction_data_decrypted['iban']
    logging.info(f"transaction_data_decrypted: {test}")

    
    return "Restart success", 200
    
@app.route("/new_owner", methods=['GET'])
def new_owner():
    logging.info("generate new Owner")
    test_owner=Owner()
    logging.info(f"private_key: {test_owner.private_key.exportKey(format='DER')}")
    logging.info(f"public_key_hex: {test_owner.public_key_hex}")
    logging.info(f"public_key_hash: {test_owner.public_key_hash}")
    return "Restart success", 200

def make_transaction(sender_wallet,input_list,output_list):
    from common.transaction import Transaction
    transaction = Transaction(input_list, output_list)
    signature=transaction.sign(sender_wallet)
    transaction_dict={}
    transaction_dict['transaction']=transaction.transaction_data
    req_return = requests.post('http://'+TRANSACTION_HOSTNAME+"/transactions", json=transaction_dict)


@app.route("/marketplace_step/<marketplace_step>/<user_public_key_hash>", methods=['GET'])
def get_marketplace_step(marketplace_step,user_public_key_hash):
    logging.info(f"User marketplace_step request {marketplace_step} {user_public_key_hash}")
    try:
        blockchain_base = blockchain_memory.get_all_blockchain_from_memory()
    except Exception as e:
        logging.info(f"exception: {e}")
    return jsonify(blockchain_base.get_marketplace_step(marketplace_step,user_public_key_hash))

@app.route("/marketplace_genesis", methods=['GET'])
def get_marketplace_genesis():
    logging.info(f"get_marketplace_genesis")
    try:
        #blockchain_base = blockchain_memory.get_blockchain_from_memory(block_pointer="marketplace_genesis")
        blockchain_base = blockchain_memory.get_blockchain_from_memory()
    except Exception as e:
        logging.info(f"exception: {e}")
    return jsonify(blockchain_base.get_marketplace_genesis())

@app.route("/nig_value_projection/<nig_amount>", methods=['GET'])
def get_nig_value_projection(nig_amount):
    range_list1=[190,365,730,1095,1825]
    range_list2=["6 mois","1 an  ","2 ans ","3 ans ","5 ans "]
    return get_nig_value_projection_raw(nig_amount,range_list1,range_list2)


@app.route("/nig_value_projection_year/<nig_amount>", methods=['GET'])
def get_nig_value_projection_year(nig_amount):
    range_list1=[30,60,90,180,270,365]
    range_list2=["1 mois","2 mois","3 mois","6 mois","9 mois","1 an"]
    return get_nig_value_projection_raw(nig_amount,range_list1,range_list2)

@app.route("/nig_value_projection_future/<nig_amount>", methods=['GET'])
def get_nig_value_projection_future(nig_amount):
    range_list1=[365,730,1095,1825,2555,3650]
    range_list2=["1 an  ","2 ans ","3 ans ","5 ans ","7 ans ","10 ans "]
    return get_nig_value_projection_raw(nig_amount,range_list1,range_list2)

def get_nig_value_projection_raw(nig_amount,range_list1,range_list2):
    logging.info(f"get_nig_value")
    from common.values import EUR_NIG_VALUE_START_TIMESTAMP,EUR_NIG_VALUE_START_CONVERSION_RATE,EUR_NIG_VALUE_START_INCREASE_DAILY_PERCENTAGE,EUR_NIG_VALUE_START_INCREASE_HALVING_DAYS
    current_timestamp=datetime.timestamp(datetime.utcnow())
    t1=datetime.utcnow()
    
    result=[]
    for i in range(len(range_list1)):
        t2=t1+datetime_delta.timedelta(days=range_list1[i])
        delta=t2-t1
        delta_days=delta.days
        flag=True
        nig_value=float(EUR_NIG_VALUE_START_CONVERSION_RATE)
        nig_increase=1
        INCREASE_DAILY_PERCENTAGE=float(EUR_NIG_VALUE_START_INCREASE_DAILY_PERCENTAGE)
        HALVING_DAYS=float(EUR_NIG_VALUE_START_INCREASE_HALVING_DAYS)
        while flag is True:
            if delta_days<HALVING_DAYS:
                nig_increase=nig_increase*math.pow((float(INCREASE_DAILY_PERCENTAGE)/100)+1,delta_days)
                nig_rate=nig_value*nig_increase
                nig_value=float(nig_amount)*nig_rate
            
                nig_increase_percentage=(nig_increase-1)*100
                nig_increase_percentage_string="{:.2f}".format(nig_increase_percentage)
                nig_value_string="{:.2f}".format(nig_value)
                nig_rate_string="{:.2f}".format(nig_rate)
                flag=False
            else:
                nig_increase=nig_increase*math.pow((float(INCREASE_DAILY_PERCENTAGE)/100)+1,HALVING_DAYS)
                delta_days-=HALVING_DAYS
                INCREASE_DAILY_PERCENTAGE=INCREASE_DAILY_PERCENTAGE/2

        result.append(str(int(nig_value)))

        logging.info(f" {range_list2[i]} => nig_value: {nig_value_string}€ increase: {nig_increase_percentage_string}% nig_rate : {nig_rate_string} NIG last increase: {INCREASE_DAILY_PERCENTAGE}")
    
    return jsonify(result)

@app.route("/nig_rate_eur", methods=['GET'])
def get_nig_rate():
    nig_rate=calculate_nig_rate(currency='eur')
    nig_rate_string="{:.2f}".format(nig_rate)
    logging.info(f" nig_rate : {nig_rate_string} € for 1 NIG")
    return jsonify(nig_rate)

def calculate_nig_rate(*args, **kwargs):
    #logging.info(f"get_nig_rate_eur")
    timestamp=kwargs.get('timestamp',None)
    currency=kwargs.get('currency','eur').upper()
    variable_module = __import__("common")
    NIG_VALUE_START_TIMESTAMP=variable_module.values.__getattribute__(currency+"_NIG_VALUE_START_TIMESTAMP")
    NIG_VALUE_START_CONVERSION_RATE=variable_module.values.__getattribute__(currency+"_NIG_VALUE_START_CONVERSION_RATE")
    NIG_VALUE_START_INCREASE_DAILY_PERCENTAGE=variable_module.values.__getattribute__(currency+"_NIG_VALUE_START_INCREASE_DAILY_PERCENTAGE")
    NIG_VALUE_START_INCREASE_HALVING_DAYS=variable_module.values.__getattribute__(currency+"_NIG_VALUE_START_INCREASE_HALVING_DAYS")
    if timestamp is not None:date_now=datetime.fromtimestamp(timestamp)
    else:date_now=datetime.utcnow()

    delta=date_now-datetime.fromtimestamp(float(NIG_VALUE_START_TIMESTAMP))
    #delta=date_now-(datetime.utcnow()-datetime_delta.timedelta(189))
    delta_days=delta.days
    #logging.info(f" delta_days: {delta_days}")
    flag=True
    nig_rate_initial=float(NIG_VALUE_START_CONVERSION_RATE)
    nig_increase=1
    INCREASE_DAILY_PERCENTAGE=float(NIG_VALUE_START_INCREASE_DAILY_PERCENTAGE)
    HALVING_DAYS=float(NIG_VALUE_START_INCREASE_HALVING_DAYS)
    while flag is True:
        if delta_days<HALVING_DAYS:
            nig_increase=nig_increase*math.pow((float(INCREASE_DAILY_PERCENTAGE)/100)+1,delta_days)
            nig_rate=nig_rate_initial*nig_increase
            flag=False
        else:
            nig_increase=nig_increase*math.pow((float(INCREASE_DAILY_PERCENTAGE)/100)+1,HALVING_DAYS)
            delta_days-=HALVING_DAYS
            INCREASE_DAILY_PERCENTAGE=INCREASE_DAILY_PERCENTAGE/2    
    logging.info(f"nig_rate: {nig_rate}")
    return nig_rate


@app.route("/transaction_creation", methods=['GET'])
def transaction_creation():
    #test for making a transaction via API
    #Camille => Bertand  

    from blockchain_users.albert import private_key as albert_private_key
    from blockchain_users.bertrand import private_key as bertrand_private_key
    from blockchain_users.camille import private_key as camille_private_key
    from blockchain_users.albert import public_key_hash as albert_public_key_hash
    from blockchain_users.bertrand import public_key_hash as bertrand_public_key_hash
    from blockchain_users.camille import public_key_hash as camille_public_key_hash
    from common.transaction import Transaction
    from common.transaction_input import TransactionInput
    from common.transaction_output import TransactionOutput
    from wallet.wallet import Owner, Wallet, Transaction
    import requests
    albert_owner=Owner(private_key=albert_private_key)
    bertrand_owner=Owner(private_key=bertrand_private_key)
    camille_owner=Owner(private_key=camille_private_key)
    albert_wallet = Wallet(albert_owner,Node(MY_HOSTNAME))
    bertrand_wallet = Wallet(bertrand_owner,Node(MY_HOSTNAME))
    camille_wallet = Wallet(camille_owner,Node(MY_HOSTNAME))

    #sender_wallet=bertrand_wallet
    #receiver_wallet=camille_wallet

    sender_owner=camille_owner
    receiver_owner=bertrand_owner
    sender_wallet=camille_wallet
    receiver_wallet=bertrand_wallet
    transaction_amount=2

    #let's retrieve the utxo
    utxo_url='http://'+MY_HOSTNAME+'/utxo/'+sender_owner.public_key_hash
    resp = requests.get(utxo_url)
    utxo_dict = resp.json()

    if transaction_amount>utxo_dict['total']:
        #transaction amount is exceeding wallet total
        logging.info(f"transaction amount {transaction_amount} is exceeding wallet total {utxo_dict['total']} for sender {sender_owner.public_key_hash} ")
    else:
        #wallet total is exceeding transaction amount
        remaing_transaction_amount=transaction_amount
        input_list=[]
        output_list=[]
        for utxo in utxo_dict['utxos']:
            if utxo['amount']>=remaing_transaction_amount:
                #only one utxo is sufficient
                input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash=sender_owner.public_key_hash))
                #input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash='sender_wallet.public_key_hash'))
                #check=TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash='sender_wallet.public_key_hash')
                #logging.info(f"====check check.to_json() {check.to_json()}")
                
                
                output_list.append(TransactionOutput(public_key_hash=receiver_owner.public_key_hash, amount=remaing_transaction_amount,interface_public_key_hash=interface_public_key_hash,))
                if utxo['amount']-remaing_transaction_amount>0:
                    output_list.append(TransactionOutput(public_key_hash=sender_owner.public_key_hash, amount=(utxo['amount']-remaing_transaction_amount),interface_public_key_hash=interface_public_key_hash,))
                #make_transaction(sender_wallet,input_list,output_list)
                sender_wallet.process_transaction(inputs=input_list, outputs=output_list)
                break
            else:
                #more than one utxo will be needed
                input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash=sender_owner.public_key_hash))
                #input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash='sender_wallet.public_key_hash'))
                #check=TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash='sender_wallet.public_key_hash')
                #logging.info(f"====check check.to_json() {check.to_json()}")

                output_list.append(TransactionOutput(public_key_hash=receiver_owner.public_key_hash, amount=utxo['amount'],interface_public_key_hash=interface_public_key_hash,))
                
                remaing_transaction_amount-=utxo['amount']
                #make_transaction(sender_wallet,input_list,output_list)
                sender_wallet.process_transaction(inputs=input_list, outputs=output_list)
                input_list=[]
                output_list=[]

    return "Restart success", 200

####SMART CONTRACT
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import binascii

from blockchain_users.marketplace import private_key as marketplace_private_key
smart_contract_owner=Owner(private_key=marketplace_private_key)
smart_contract_wallet = Wallet(smart_contract_owner,Node(MY_HOSTNAME))


#from common.transaction import Transaction
from common.transaction_input import TransactionInput
from common.transaction_output import TransactionOutput
#from wallet.wallet import Owner, Wallet, Transaction
from wallet.wallet import Owner, Wallet
from common.transaction_account import decrypt_account


from blockchain_users.bertrand import private_key as bertrand_private_key
bertrand_owner=Owner(private_key=bertrand_private_key)
bertrand_wallet = Wallet(bertrand_owner,Node(MY_HOSTNAME))

from blockchain_users.camille import private_key as camille_private_key
camille_owner=Owner(private_key=camille_private_key)
camille_wallet = Wallet(camille_owner,Node(MY_HOSTNAME))

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


from common.smart_contract_script import *

@app.route("/smart_contract_creation", methods=['POST'])
def get_smart_contract_creation():
    content = request.json
    #fix for boolean
    content=clean_request(content)
    smart_contract_public_key_hash=content['smart_contract_public_key_hash']
    sender_public_key_hash=content['sender_public_key_hash']
    payload=content['payload']
    smart_contract_dict={}
    smart_contract=SmartContract(smart_contract_public_key_hash,
                                 smart_contract_sender=sender_public_key_hash,
                                 type='source',
                                 payload=payload,
                                 smart_contract_new=True)

    smart_contract.process()

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
    logging.info(f"####smart_contract_dict:{smart_contract_dict}")
    return jsonify(smart_contract_dict)

@app.route("/smart_contract", methods=['POST'])
def get_smart_contract():
    content = request.json
    #fix for boolean
    content=clean_request(content)
    smart_contract_type=content['smart_contract_type']
    smart_contract_public_key_hash=content['smart_contract_public_key_hash']
    sender_public_key_hash=content['sender_public_key_hash']
    smart_contract_transaction_hash=content['smart_contract_transaction_hash']
    smart_contract_previous_transaction=content['smart_contract_previous_transaction']
    payload=content['payload']
    
    smart_contract_dict={}
    if smart_contract_public_key_hash=="marketplace":
        smart_contract_public_key_hash=smart_contract_owner.public_key_hash
    smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(smart_contract_public_key_hash)
    logging.info(f"########### CHECK smart_contract_transaction_hash: {smart_contract_transaction_hash}")
    smart_contract=SmartContract(smart_contract_public_key_hash,
                                 smart_contract_sender=sender_public_key_hash,
                                 type=smart_contract_type,
                                 payload=payload,
                                 smart_contract_previous_transaction=smart_contract_transaction_hash,
                                 smart_contract_transaction_hash=smart_contract_transaction_hash)

    smart_contract.process()

    smart_contract_dict['smart_contract_account']=smart_contract.smart_contract_account
    smart_contract_dict['smart_contract_sender']=smart_contract.smart_contract_sender
    smart_contract_dict['smart_contract_new']=smart_contract.smart_contract_new
    smart_contract_dict['smart_contract_flag']=True
    smart_contract_dict['smart_contract_gas']=smart_contract.gas
    smart_contract_dict['smart_contract_memory']=smart_contract.smart_contract_memory
    smart_contract_dict['smart_contract_memory_size']=smart_contract.smart_contract_memory_size
    smart_contract_dict['smart_contract_type']=smart_contract.smart_contract_type
    smart_contract_dict['smart_contract_payload']=smart_contract.payload
    smart_contract_dict['smart_contract_result']=smart_contract.result
    smart_contract_dict['smart_contract_previous_transaction']=smart_contract.smart_contract_previous_transaction
    smart_contract_dict['smart_contract_transaction_hash']=smart_contract.smart_contract_transaction_hash
    return jsonify(smart_contract_dict)




@app.route("/smart_contract_detail/<value>", methods=['GET'])
def get_smart_contract_detail(value):
    logging.info(f"test smart_contract step:{value}")
    #smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(smart_contract_owner.public_key_hash)
    smart_contract_amount=None
    smart_contract_owner=marketplace_owner
    receiver_public_key_hash=smart_contract_owner.public_key_hash

    seller_owner=camille_owner
    seller_wallet=camille_wallet
    buyer_owner=daniel_owner
    buyer_public_key_hash=buyer_owner.public_key_hash
    unlocking_public_key_hash=smart_contract_owner.public_key_hash
    transaction_wallet=smart_contract_wallet

    ####STEP 1
    if int(value)==1:
        sender_public_key_hash=buyer_owner.public_key_hash
        
        smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(smart_contract_owner.public_key_hash)
        logging.info(f"marketplace_owner.public_key_hash:{marketplace_owner.public_key_hash}")
        utxo_dict=get_utxo(marketplace_owner.public_key_hash)
        logging.info(f"utxo_dict:{utxo_dict}")
        payload=f'''buyer_public_key_hash="{buyer_owner.public_key_hash}"
buyer_public_key_hex="{buyer_owner.public_key_hex}"
requested_amount=10
'''+marketplace_script1


     ####STEP 2
    if int(value)==2:
        #STEP 2-1 - retrieval of request information to make signature
        payload=marketplace_script2_1
        sender_public_key_hash=camille_owner.public_key_hash
        smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(smart_contract_owner.public_key_hash)
        smart_contract=SmartContract(smart_contract_owner.public_key_hash,
                                        smart_contract_sender=sender_public_key_hash,
                                        type="api",
                                        payload=payload,
                                        smart_contract_previous_transaction=smart_contract_transaction_hash,
                                        smart_contract_transaction_hash=smart_contract_transaction_hash)
        smart_contract.process()
        mp_details=smart_contract.result
        
        #STEP 2-2 - encryption of account
        
        smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(smart_contract_owner.public_key_hash)
        sender_public_key_hash=camille_owner.public_key_hash
        buyer_public_key_hex=buyer_owner.public_key_hex
        transaction_account=TransactionAccount("Banque Postale camille","FR03 2004 1010 1709 5633 8F02 896","PSSTFRPPGRE","lion.david@gmail.com","0686872549","France",seller_owner.public_key_hash)
        encrypted_account = transaction_account.encrypt(buyer_public_key_hex,seller_owner.private_key)

        #STEP 2-3 - signature generation
        mp_details.append(seller_owner.public_key_hex)
        logging.info(f"@@@@@@step2 mp_details:{mp_details}")
        transaction_bytes = json.dumps(mp_details, indent=2).encode('utf-8')
        hash_object = SHA256.new(transaction_bytes)
        #signature = pkcs1_15.new(RSA.importKey(seller_owner.private_key)).sign(hash_object)
        signature = pkcs1_15.new(seller_owner.private_key).sign(hash_object)
        mp_request_signature=binascii.hexlify(signature).decode("utf-8")

        smart_contract_amount=9.9
        utxo_dict=get_utxo(seller_owner.public_key_hash,smart_contract_only=False)
        transaction_wallet=seller_wallet
        unlocking_public_key_hash=seller_owner.public_key_hash
        payload=f'''seller_public_key_hash="{seller_owner.public_key_hash}"
seller_public_key_hex="{seller_owner.public_key_hex}"
requested_nig=10
encrypted_account="{encrypted_account}"
mp_request_signature="{mp_request_signature}"
'''+marketplace_script2_2

    ####STEP 3
    if int(value)==3:
        #STEP 3-1 - retrieval of bank account information
        payload=marketplace_script3_1
        sender_public_key_hash=buyer_owner.public_key_hash
        smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(smart_contract_owner.public_key_hash)
        smart_contract=SmartContract(smart_contract_owner.public_key_hash,
                                        smart_contract_sender=sender_public_key_hash,
                                        type="api",
                                        payload=payload,
                                        smart_contract_previous_transaction=smart_contract_transaction_hash,
                                        smart_contract_transaction_hash=smart_contract_transaction_hash)

        smart_contract.process()
        account=smart_contract.result
        account_encrypted_part1=str(account).split(" ")[0]
        account_encrypted_part2=str(account).split(" ")[1]
        decrypted_account=decrypt_account(account_encrypted_part1,account_encrypted_part2,buyer_owner.private_key)
        logging.info(f"@@@@@@ decrypted_account step:{decrypted_account.to_dict()}")

        #STEP 3-2 - retrieval of request information to make signature
        payload=marketplace_script3_2
        utxo_dict=get_utxo(marketplace_owner.public_key_hash)
        sender_public_key_hash=buyer_owner.public_key_hash
        smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(smart_contract_owner.public_key_hash)
        smart_contract=SmartContract(smart_contract_owner.public_key_hash,
                                        smart_contract_sender=sender_public_key_hash,
                                        type="api",
                                        payload=payload,
                                        smart_contract_previous_transaction=smart_contract_transaction_hash,
                                        smart_contract_transaction_hash=smart_contract_transaction_hash)
        smart_contract.process()
        mp_details=smart_contract.result

        #STEP 3-3 - signature generation
        logging.info(f"@@@@@@step3 mp_details:{mp_details}")
        transaction_bytes = json.dumps(mp_details, indent=2).encode('utf-8')
        hash_object = SHA256.new(transaction_bytes)
        #signature = pkcs1_15.new(RSA.importKey(buyer_owner.private_key)).sign(hash_object)
        signature = pkcs1_15.new(buyer_owner.private_key).sign(hash_object)
        mp_request_signature=binascii.hexlify(signature).decode("utf-8")

        payload=f'''mp_request_signature="{mp_request_signature}"
'''+marketplace_script3_3


    if int(value)==4:
        #STEP 4-0 - transfer of Nig to smart_contract_owner to freeze the request
        input_list=[]
        output_list=[]
        utxo_dict=get_utxo(marketplace_owner.public_key_hash,smart_contract_only=False)
        for utxo in utxo_dict['utxos']:
            input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash=smart_contract_owner.public_key_hash))
            output_list.append(TransactionOutput(public_key_hash=buyer_public_key_hash, 
                                                 amount=utxo['amount'],
                                                 interface_public_key_hash=interface_public_key_hash))
            smart_contract_wallet.process_transaction(inputs=input_list, outputs=output_list)
            break

    if int(value)==5:
        #STEP 4-1 - retrieval of request information to make signature
        payload=marketplace_script4_1
        sender_public_key_hash=camille_owner.public_key_hash
        smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(smart_contract_owner.public_key_hash)
        smart_contract=SmartContract(smart_contract_owner.public_key_hash,
                                        smart_contract_sender=sender_public_key_hash,
                                        type="api",
                                        payload=payload,
                                        smart_contract_previous_transaction=smart_contract_transaction_hash,
                                        smart_contract_transaction_hash=smart_contract_transaction_hash)
        smart_contract.process()
        mp_details=smart_contract.result
        
        #STEP 4-2 - signature generation
        utxo_dict=get_utxo(marketplace_owner.public_key_hash)
        transaction_bytes = json.dumps(mp_details, indent=2).encode('utf-8')
        hash_object = SHA256.new(transaction_bytes)
        #signature = pkcs1_15.new(RSA.importKey(seller_owner.private_key)).sign(hash_object)
        signature = pkcs1_15.new(seller_owner.private_key).sign(hash_object)
        mp_request_signature=binascii.hexlify(signature).decode("utf-8")

        receiver_public_key_hash=buyer_public_key_hash

        
        payload=f'''mp_request_signature="{mp_request_signature}"
'''+marketplace_script4_2
    
   
    input_list=[]
    output_list=[]
    for utxo in utxo_dict['utxos']:
        if smart_contract_amount is None:smart_contract_amount=utxo['amount']
        smart_contract=SmartContract(smart_contract_owner.public_key_hash,
                                        smart_contract_sender=sender_public_key_hash,
                                        type="source",
                                        payload=payload,
                                        smart_contract_previous_transaction=smart_contract_transaction_hash,
                                        smart_contract_transaction_hash=smart_contract_transaction_hash)

        smart_contract.process()
        input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash=unlocking_public_key_hash))
        output_list.append(TransactionOutput(public_key_hash=receiver_public_key_hash, 
                                                amount=utxo['amount'],
                                                interface_public_key_hash=interface_public_key_hash,
                                                smart_contract_account=smart_contract.smart_contract_account,
                                                smart_contract_sender=smart_contract.smart_contract_sender,
                                                smart_contract_new=smart_contract.smart_contract_new,
                                                smart_contract_flag=True,
                                                smart_contract_gas=smart_contract.gas,
                                                smart_contract_memory=smart_contract.smart_contract_memory,
                                                smart_contract_memory_size=smart_contract.smart_contract_memory_size,
                                                smart_contract_type=smart_contract.smart_contract_type,
                                                smart_contract_payload=smart_contract.payload,
                                                smart_contract_result=smart_contract.result,
                                                smart_contract_previous_transaction=smart_contract.smart_contract_previous_transaction,
                                                smart_contract_transaction_hash=smart_contract.smart_contract_transaction_hash))
        transaction_wallet.process_transaction(inputs=input_list, outputs=output_list)
        break
    
    return "Restart success", 200

@app.route("/smart_contract_api_detail/<value>", methods=['GET'])
def get_smart_contract_api_detail(value):
    logging.info(f"smart_contract_api_detail:{value}")
    payload=marketplace_script_test
    sender_public_key_hash=camille_owner.public_key_hash
    smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(smart_contract_owner.public_key_hash)
    smart_contract=SmartContract(smart_contract_owner.public_key_hash,
                                    smart_contract_sender=sender_public_key_hash,
                                    type="api",
                                    payload=payload,
                                    smart_contract_previous_transaction=smart_contract_transaction_hash,
                                    smart_contract_transaction_hash=smart_contract_transaction_hash)
    smart_contract.process()
    mp_details=smart_contract.result
    logging.info(f"result:{mp_details}")
    logging.info(f"smart_contract_transaction_hash:{smart_contract_transaction_hash}")

    return "Restart success", 200



class TransactionMultiProcessing:
    def __init__(self,*args, **kwargs):
        self.e = threading.Event()

    def launch(self,transaction_data):
        self.PoH_threading = threading.Thread(target=self.start, args=(self.e,transaction_data))
        self.PoH_threading.start()

    def start(self,e,transaction_data):
        while e.is_set() is False:
            Process_transaction(transaction_data=transaction_data)
            logging.info('===> TransactionMultiProcessing termination')
            self.stop()
            break

    def stop(self):
        self.e.set()


def Process_transaction(*args, **kwargs):
    purge_flag = kwargs.get('purge_flag',False)
    transaction_data = kwargs.get('transaction_data',True)
    logging.info(f"### purge_flag:{purge_flag}")
    
    #STEP2 Processing of transaction
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    previous_PoH_hash=blockchain_base.block_header.current_PoH_hash
    previous_PoH_timestamp=blockchain_base.block_header.current_PoH_timestamp
    #check if it's the first new transaction
    logging.info(f"{previous_PoH_hash!=PoH_memory.previous_PoH_hash} previous_PoH_hash: {previous_PoH_hash} PoH_memory.previous_PoH_hash:{PoH_memory.previous_PoH_hash}")
    logging.info(f"### get_current_leader_node_url():{get_current_leader_node_url()} MY_HOSTNAME:{MY_HOSTNAME} PoH_memory.PoH_start_flag:{PoH_memory.PoH_start_flag==False}")
    if get_current_leader_node_url()==MY_HOSTNAME and PoH_memory.PoH_start_flag==False:
        #this is the first transaction of the SLOT, 
        #or there is the new LeaderNode following a block assertion error
        #let's start PoH
        #PoH_memory.reset(previous_PoH_hash,previous_PoH_timestamp)
        previous_previous_PoH_hash=PoH_memory.previous_PoH_hash
        PoH_memory.reset(previous_previous_PoH_hash,previous_PoH_hash,datetime.timestamp(datetime.utcnow()))
        PoH_memory.launch_PoH()
        logging.info(f"Launch of PoH: {previous_PoH_hash}")
    try:
        transaction = Transaction(blockchain_base, MY_HOSTNAME)
        transaction.receive(transaction=transaction_data)
        if transaction.is_new:
            logging.info("Transaction is new")
            transaction.validate()
            transaction.validate_funds()
            smart_contract_flag,smart_contract_index_list=check_smart_contract(transaction)
            
            if smart_contract_flag:
                #there are smart contract in the transaction, let's validate them
                transaction.validate_smart_contract(smart_contract_index_list,leader_node_flag=True)

            if transaction.is_valid is True and transaction.is_smart_contract_valid is True:
                #storing in a temporay master state
                master_state_temp=MasterState(temporary_save_flag=True)
                #logging.info(f"########### temporary_storage_sharding transaction: {transaction.transaction_data}")
                #update of transaction_data as smart_contract_previous_transaction has changed
                transaction.transaction_data["outputs"]=transaction.outputs
                transaction.transaction_data["inputs"]=transaction.inputs
                master_state_temp.update_master_state(transaction.transaction_data)
                master_state_temp.store_master_state_in_memory()
                #storing in the meempool and PoH
                #logging.info(f"########### transaction.transaction_data: {transaction.transaction_data}")
                transaction.store()
                transaction.add_to_PoH(PoH_memory)
            
                logging.info(f"PoH_memory: {PoH_memory.registry_input_data}")
    except TransactionException as transaction_exception:
        return f'{transaction_exception}', 400





class BlockMultiProcessing:
    def __init__(self,*args, **kwargs):
        self.e = threading.Event()

    def launch(self,block_data):
        self.PoH_threading = threading.Thread(target=self.start, args=(self.e,block_data))
        self.PoH_threading.start()

    def start(self,e,block_data):
        while e.is_set() is False:
            Process_block(block_data=block_data)
            logging.info('===> BlockMultiProcessing termination')
            self.stop()
            break

    def stop(self):
        self.e.set()


def Process_block(*args, **kwargs):
    block_data = kwargs.get('block_data',True)
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    try:
        block = NewBlock(blockchain_base, MY_HOSTNAME)
        block.receive(new_block=block_data["block"], sender=block_data["sender"])
        block.validate()
        block.add()
        block.clear_block_transactions_from_mempool()
        try:
            shutil.rmtree(STORAGE_DIR+MASTER_STATE_DIR_TEMP)
            pass
        except:
            pass
        #block.broadcast()
    except (NewBlockException, TransactionException) as new_block_exception:
        return f'{new_block_exception}', 400



if __name__ == "__main__":
    main()
