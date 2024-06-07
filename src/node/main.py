import logging
import os
import shutil
from operator import itemgetter
import requests
import time
import datetime as datetime_delta
from datetime import datetime
import math
import json
import copy

import threading
from multiprocessing.dummy import Pool as ThreadPool
from flask import Flask, request, jsonify,redirect, url_for

from common.io_blockchain import BlockchainMemory
from common.io_known_nodes import KnownNodesMemory
from common.master_state import MasterState
from common.network import Network
from common.node import Node
from node.new_block_validation.new_block_validation import NewBlock, NewBlockException
from node.transaction_validation.transaction_validation import Transaction, TransactionException
from common.transaction import Transaction as TransactionInBlock
from common.io_mem_pool import MemPool
from common.values import ROUND_VALUE_DIGIT
from common.utils import normal_round,clean_request,check_marketplace_step2
from common.io_leader_node_schedule import LeaderNodeScheduleMemory
from node.new_block_creation.new_block_creation import ProofOfWork, BlockException

from common.proof_of_history import ProofOfHistory
from common.smart_contract import SmartContract,check_smart_contract,load_smart_contract,load_smart_contract_from_master_state,load_smart_contract_from_master_state_leader_node,check_double_contract,create_smart_contract

from common.values import *


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
from common.master_state_readiness import master_state_readiness
from common.master_state_threading import master_state_threading
from common.maintenance import maintenance_mode



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
PoW_memory = ProofOfWork(MY_HOSTNAME)
PoH_memory=ProofOfHistory(PoW_memory=PoW_memory)





@app.before_request
def check_for_maintenance():
    '''Decorator for Maintenance'''
    if maintenance_mode.get_mode() is True and request.path != url_for('maintenance') and request.path != url_for('maintenance_on') and request.path != url_for('maintenance_off') and request.path != url_for('network_maintenance_on') and request.path != url_for('network_maintenance_off') and request.path != url_for('validate_block') and request.path != url_for('start') and request.path != url_for('block_saving_leader_node'):   
        return redirect(url_for('maintenance'))
       

@app.route("/start", methods=['GET'])
def start():
    '''Start the node'''
    logging.info("start request")
    network.join_network()
    PoW_memory.start()
    #PoH_memory.start()
    return "Restart success", 200

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
    block_pointer=content['block']['header']['previous_PoH_hash']
    blockchain_memory = BlockchainMemory()
    blockchain_base = blockchain_memory.get_blockchain_from_memory(block_pointer=block_pointer)
    try:
        while master_state_readiness.block() is False:
            #let's wait until MasterState is release by another thread
            pass
        
        block = NewBlock(blockchain_base, MY_HOSTNAME)
        block.receive(new_block=content["block"], sender=content["sender"])
        block.add_in_backlog(master_state_readiness)
        block.validate(master_state_readiness)

        if block.is_valid is False:
            #no need to wait for the BlockVote. A branch needs to be created in the consensus_blockchain
            block_to_reject_now_by_leader_node=block.new_block.block_header.current_PoH_hash
        else:block_to_reject_now_by_leader_node=None
        
        #refresh of the consensus blockchain
        from common.consensus_blockchain import consensus_blockchain
        consensus_blockchain.refresh(block_to_reject_now_by_leader_node=block_to_reject_now_by_leader_node)

        latest_received_block=block.new_block.block_header.current_PoH_hash
        if block.is_valid is True:
            #the Block is valid
            #leader_node_advance_purge_backlog()
            block.clear_block_transactions_from_mempool()
            received_block_2_slash=None

            #let's refresh the score of the contest if needed
            if 5==6:
                block.refresh_score_list
                for participant_public_key_hash in block.refresh_score_list:
                    if backlog_score_processing.check_request(participant_public_key_hash) is False:
                        participant_refresh_score_processing=ParticipantRefreshScoreProcessing()
                        participant_refresh_score_processing.launch(participant_public_key_hash)

        else:
            #the Block is not valid
            received_block_2_slash=block.new_block.block_header.current_PoH_hash
        block.check_vote_and_backlog(master_state_readiness,
                                     leader_node_flag=True,
                                     latest_received_block=latest_received_block,
                                     received_block_2_slash=received_block_2_slash,
                                     new_block_2_exclude=latest_received_block)
        
    #except (NewBlockException, TransactionException) as new_block_exception:
    #    return f'{new_block_exception}', 400

    except Exception as e:
        #issue with new block creation / Miner
        logging.info(f"###ERROR block_saving_leader_node issue: {e}")
        logging.exception(e)

    #let's release MasterState
    master_state_readiness.release()

    #let's release to allow the block receiving
    master_state_threading.receiving_reset()

    return "Transaction success", 200


@app.route("/transactions", methods=['POST'])
def validate_transaction():
    logging.info("New transaction validation request")
    content = request.json
    content=clean_request(content)
    blockchain_memory = BlockchainMemory()
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    try:
        transaction = Transaction(blockchain_base, MY_HOSTNAME)
        transaction.receive(transaction=content["transaction"])
        if transaction.validate_output_not_empty() == True:transaction.broadcast_to_leader_node()
        else:logging.info("###ERROR: transaction output is empty")
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
    transaction_multiprocessing.launch(content['transaction'],False)
    
    return "Transaction success", 200

def leader_node_advance_purge_backlog():
    logging.info(f"### leader_node_advance_purge_backlog")
    #this function aims to purge the potential backlog of transaction during leader note rotation
    backlog_list=[]
    import os
    if not os.path.exists(STORAGE_DIR+LEADER_NODE_TRANSACTIONS_ADVANCE):
        #the directory is not existing, let's create it
        os.makedirs(STORAGE_DIR+LEADER_NODE_TRANSACTIONS_ADVANCE)
    blockchain_memory = BlockchainMemory()
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    
    directory = os.fsencode(STORAGE_DIR+LEADER_NODE_TRANSACTIONS_ADVANCE)
    #files = filter(os.path.isfile, os.listdir(directory))
    #files = [os.path.join(directory, f) for f in files] # add path to each file
    #files.sort(key=lambda x: os.path.getmtime(x))
    #for file in files:
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
                backlog_list.append(transaction_data)
         else:
            logging.info(f"==> transaction in advance known: {filename}")
    
    #sorting of Backlog by timestamp
    backlog_list_sorted=sorted(backlog_list, key=itemgetter('timestamp'))
    for backlog_transaction in backlog_list_sorted:
        Process_transaction(purge_flag=True,transaction_data=backlog_transaction)
    
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
    transaction=content["transaction"]
    save_transactions_to_leader_node_advance(transaction)
    return "Transaction success", 200

def save_transactions_to_leader_node_advance(transaction):
    try:
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

@app.route("/block", methods=['GET'])
def get_blocks():
    logging.info("Block request")
    blockchain_memory = BlockchainMemory()
    blockchain_base = blockchain_memory.get_all_blockchain_from_memory()
    return jsonify(blockchain_base.to_dict)

@app.route("/leader_node_schedule", methods=['GET'])
def get_leader_node_schedule():
    logging.info("Get Leader Node Schedule")
    leader_node_schedule=LeaderNodeScheduleMemory()
    return jsonify(leader_node_schedule.leader_node_schedule_json)

@app.route("/leader_node_schedule_next", methods=['GET'])
def get_leader_node_schedule_next():
    logging.info("Get Next Leader Node Schedule")
    #Launch Leader node Rotation
    PoW_memory.leader_node_schedule_memory.next_leader_node_schedule(PoW_memory.known_nodes_memory.known_nodes)
    PoW_memory.broadcast_leader_node_schedule()
    return "Next Leader Node Schedule", 200

@app.route("/maintenance")
def maintenance():
    response = app.response_class(
        response=json.dumps("Sorry, off for maintenance!"),
        status=503,
        mimetype='application/json'
    )
    return response

@app.route("/maintenance_on", methods=['GET'])
def maintenance_on():
    #active the maintenance of the Node only
    maintenance_mode.switch_on()
    response = app.response_class(
        response=json.dumps("Maintenance On"),
        status=200,
        mimetype='application/json'
    )
    return response

@app.route("/maintenance_off", methods=['GET'])
def maintenance_off():
    #deactive the maintenance of the Node only
    maintenance_mode.switch_off()
    response = app.response_class(
        response=json.dumps("Maintenance Off"),
        status=200,
        mimetype='application/json'
    )
    return response

@app.route("/network_maintenance_on", methods=['GET'])
def network_maintenance_on():
    #active the maintenance of all the network
    logging.info("===Network Maintenance On request")
    network_maintenance("on")
    response = app.response_class(
            response=json.dumps("Network Maintenance On success"),
            status=200,
            mimetype='application/json'
        )
    return response

@app.route("/network_maintenance_off", methods=['GET'])
def network_maintenance_off():
    #deactive the maintenance of all the network
    logging.info("===Network Maintenance Off request")
    network_maintenance("off")
    response = app.response_class(
            response=json.dumps("Network Maintenance Off success"),
            status=200,
            mimetype='application/json'
        )
    return response

def network_maintenance(mode):
    known_nodes_memory=KnownNodesMemory()
    known_nodes_memory.known_nodes
    node_list = known_nodes_memory.known_nodes
    new_node_list=[]
    for node in node_list:
        new_node_list.append(node)
    my_node = Node(MY_HOSTNAME)
    for node in new_node_list:
        if node!= my_node:
            try:
                if mode=="off":node.network_maintenance_off()
                if mode=="on":node.network_maintenance_on()
            except Exception as e:
                logging.info(f"**** ISSUE network_maintenance {mode}: {node.dict}")
                logging.exception(e)

    if mode=="off":maintenance_mode.switch_off()
    if mode=="on":maintenance_mode.switch_on()
    

@app.route("/utxo/<user>", methods=['GET'])
def get_user_utxos(user):
    logging.info(f"User utxo request {user}")
    blockchain_memory = BlockchainMemory()
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_user_utxos(user))

@app.route("/smart_contract_api/<account>/<smart_contract_transaction_hash>", methods=['GET'])
def get_smart_contract_api2(account,smart_contract_transaction_hash):
    logging.info(f"smart_contract_api account:{account} ")
    blockchain_memory = BlockchainMemory()
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_smart_contract_api(account,smart_contract_transaction_hash=smart_contract_transaction_hash))

@app.route("/smart_contract_api/<account>", methods=['GET'])
def get_smart_contract_api(account):
    logging.info(f"smart_contract_api account:{account} ")
    blockchain_memory = BlockchainMemory()
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
    blockchain_memory = BlockchainMemory()
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_user_utxos_balance(user))

@app.route("/all_utxo/<user>", methods=['GET'])
def get_user_all_utxos(user):
    logging.info(f"User all utxo request {user}")
    blockchain_memory = BlockchainMemory()
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_user_all_utxos(user))

@app.route("/utxo_raw/<user>", methods=['GET'])
def get_user_utxos_raw(user):
    logging.info(f"User utxo request {user}")
    blockchain_memory = BlockchainMemory()
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_user_utxos_raw(user))

@app.route("/utxo_account_temp/<user>", methods=['GET'])
def get_user_utxos_account_temp(user):
    logging.info(f"User utxo request for account temp {user}")
    blockchain_memory = BlockchainMemory()
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_user_utxos_account_temp(user))

@app.route("/utxo_account_temp/<user>/<payment_ref>", methods=['GET'])
def get_user_utxos_account_temp_payment_ref(user,payment_ref):
    logging.info(f"User utxo request for account temp {user}")
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    return jsonify(blockchain_base.get_user_utxos_account_temp(user,payment_ref=payment_ref))

@app.route("/user_creation", methods=['GET'])
def get_user_creation():
    logging.info(f"user creation request")
    user_dict={}
    owner = Owner()
    print(f"private key: {owner.private_key.export_key(format='DER')}")
    print(f"public key hash: {owner.public_key_hash}")
    print(f"public key hex: {owner.public_key_hex}")
    return "Transaction success", 200

@app.route("/transactions/<transaction_hash>", methods=['GET'])
def get_transaction(transaction_hash):
    logging.info(f"Transaction request {transaction_hash}")
    blockchain_memory = BlockchainMemory()
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
    #network = Network(my_node)
    mempool = MemPool()
    mempool.clear_transactions_from_memory()

    master_state_threading.receiving_reset()
    master_state_readiness.release()

    from common.consensus_blockchain import consensus_blockchain
    consensus_blockchain.refresh()
    
    
    #full reset of the network
    shutil.rmtree(STORAGE_DIR)
    os.makedirs(STORAGE_DIR)
    #ask all the node to rejoin the reseted network
    for node in new_node_list:
        logging.info(f"node: {node} my_node:{my_node}")
        if node!= my_node:
            node.restart_request()

    network.known_nodes_memory = KnownNodesMemory()
    network.join_network(reset_network=True)
    for node in new_node_list:
        logging.info(f"node: {node} my_node:{my_node}")
        if node!= my_node:
            node.restart_join()

    return "Network Restart success", 200

@app.route("/restart_request", methods=['POST'])
def restart_request():
    logging.info("Node restart request")
    my_node = Node(MY_HOSTNAME)
    #network = Network(my_node)
    mempool = MemPool()
    mempool.clear_transactions_from_memory()
    master_state_threading.receiving_reset()
    master_state_readiness.release()
    node_list = network.return_known_nodes()

    from common.consensus_blockchain import consensus_blockchain
    consensus_blockchain.refresh()
    #full reset of the netowrk
    shutil.rmtree(STORAGE_DIR)
    os.makedirs(STORAGE_DIR)
    return "Node Restart success", 200

@app.route("/PoH_reset", methods=['GET'])
def PoH_reset():
    logging.info("PoH_reset")
    PoH_memory.PoH_start_flag=False
    return "PoH_reset success", 200


@app.route("/restart_join", methods=['POST'])
def restart_join():
    logging.info("Node restart join")
    network.known_nodes_memory = KnownNodesMemory()
    network.join_network()
    return "Node Restart success", 200

def main():
    #global network
    #my_node = Node(MY_HOSTNAME)
    #network = Network(my_node)
    #network.join_network()
    app.run()


@app.route("/sell_followup_step4_pin/<user>/<payment_ref>", methods=['GET'])
def sell_followup_step4_pin(user,payment_ref):
    logging.info(f"sell_followup_step4_pin user:{user} payment_ref:{payment_ref}")
    pin_encrypted=None
    blockchain_memory = BlockchainMemory()
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

@app.route("/marketplace_step/<marketplace_step>/<user_public_key_hash>",defaults={'amount': None}, methods=['GET'])
@app.route("/marketplace_step/<marketplace_step>/<user_public_key_hash>/<amount>", methods=['GET'])
def get_marketplace_step(marketplace_step,user_public_key_hash,amount):
    logging.info(f"User marketplace_step request {marketplace_step} {user_public_key_hash}")
    try:
        blockchain_memory = BlockchainMemory()
        blockchain_base = blockchain_memory.get_all_blockchain_from_memory()
        return jsonify(blockchain_base.get_marketplace_step(marketplace_step,user_public_key_hash,amount=amount))
    except Exception as e:
        logging.info(f"exception: {e}")
        return jsonify([])


@app.route("/check_notification/<user_public_key_hash>/<notification_timestamp_dict_raw>", methods=['GET'])
def get_check_notification(user_public_key_hash,notification_timestamp_dict_raw):
    notification_timestamp_dict=json.loads(notification_timestamp_dict_raw)
    notification_dict={}
    for marketplace_step in notification_timestamp_dict.keys():
        marketplace_step_counter=0
        logging.info(f"marketplace_step for user: {marketplace_step}")
        archive_flag=False
        archive_timestamp=False
        if int(marketplace_step)>=4:
            archive_flag=True
            archive_timestamp=float(notification_timestamp_dict[marketplace_step])
        try:
            blockchain_memory = BlockchainMemory()
            blockchain_base = blockchain_memory.get_all_blockchain_from_memory()
            marketplace_step_raw=blockchain_base.get_marketplace_step(marketplace_step,user_public_key_hash,archive_flag=archive_flag,archive_timestamp=archive_timestamp)['results']
            for elem in marketplace_step_raw:
                if int(elem["timestamp_nig"])>int(float(notification_timestamp_dict[marketplace_step])) and elem["readonly_flag"] is False :marketplace_step_counter+=1
            notification_dict[marketplace_step]=marketplace_step_counter
        except Exception as e:
            logging.info(f"exception: {e}")
            notification_dict[marketplace_step]=0
    logging.info(f"==>notification_dict:{notification_dict}")
    logging.info(f"check_notification for user: {user_public_key_hash} notification_timestamp:{notification_timestamp_dict}")
    return jsonify(notification_dict)

    

@app.route("/marketplace_genesis", methods=['GET'])
def get_marketplace_genesis():
    logging.info(f"get_marketplace_genesis")
    blockchain_memory = BlockchainMemory()
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
        #delta=t2-t1
        delta=t2-datetime.fromtimestamp(float(EUR_NIG_VALUE_START_TIMESTAMP))
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
    #logging.info(f"nig_rate: {nig_rate}")
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

@app.route("/create_smart_contract_account", methods=['GET'])
def get_create_smart_contract_account():
    from common.owner import Owner
    owner = Owner()
    return jsonify(owner.public_key_hash)

@app.route("/smart_contract_creation", methods=['POST'])
def get_smart_contract_creation():
    content = request.json
    #fix for boolean
    content=clean_request(content)
    smart_contract_public_key_hash=content['smart_contract_public_key_hash']
    sender_public_key_hash=content['sender_public_key_hash']
    payload=content['payload']
    #logging.info(f"====smart_contract_public_key_hash:{smart_contract_public_key_hash}")
    smart_contract_dict=create_smart_contract(smart_contract_public_key_hash,sender_public_key_hash,payload)
    #logging.info(f"####smart_contract_dict:{smart_contract_dict}")
    return jsonify(smart_contract_dict)

@app.route("/smart_contract", methods=['POST'])
def get_smart_contract():
    content = request.json
    #fix for boolean
    content=clean_request(content)
    smart_contract_type=content['smart_contract_type']
    smart_contract_public_key_hash=content['smart_contract_public_key_hash']
    sender_public_key_hash=content['sender_public_key_hash']
    try:smart_contract_transaction_hash=content['smart_contract_transaction_hash']
    except:smart_contract_transaction_hash=None
    try:smart_contract_previous_transaction=content['smart_contract_previous_transaction']
    except:smart_contract_previous_transaction=None
    try:smart_contract_new=content['smart_contract_new']
    except:smart_contract_new=False
    payload=content['payload']
    
    smart_contract_dict={}
    if smart_contract_public_key_hash=="marketplace":
        smart_contract_public_key_hash=smart_contract_owner.public_key_hash
    smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(smart_contract_public_key_hash)
    if smart_contract_transaction_hash is None:
        smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(smart_contract_public_key_hash)
    logging.info(f"########### CHECK smart_contract_transaction_hash: {smart_contract_transaction_hash}")
    smart_contract=SmartContract(smart_contract_public_key_hash,
                                 smart_contract_sender=sender_public_key_hash,
                                 smart_contract_type=smart_contract_type,
                                 payload=payload,
                                 smart_contract_previous_transaction=smart_contract_transaction_hash,
                                 smart_contract_transaction_hash=smart_contract_transaction_hash,
                                 smart_contract_new=smart_contract_new)

    smart_contract.process()
    if smart_contract.error_flag is False:
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
    smart_contract_dict['smart_contract_error_flag']=smart_contract.error_flag
    smart_contract_dict['smart_contract_error_code']=str(smart_contract.error_code)
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
                                        smart_contract_type="api",
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
                                        smart_contract_type="api",
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
                                        smart_contract_type="api",
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
                                        smart_contract_type="api",
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
                                        smart_contract_type="source",
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


class TransactionMultiProcessing:
    def __init__(self,*args, **kwargs):
        self.e = threading.Event()

    def launch(self,transaction_data,new_transaction_flag):
        self.PoH_threading = threading.Thread(target=self.start, args=(self.e,transaction_data,new_transaction_flag))
        self.PoH_threading.start()
        #self.PoH_threading.join()

    def start(self,e,transaction_data,new_transaction_flag):
        while e.is_set() is False:
            Process_transaction(transaction_data=transaction_data,new_transaction_flag=new_transaction_flag)
            logging.info('===> TransactionMultiProcessing termination')
            self.stop()
            break

    def stop(self):
        self.e.set()



def Process_transaction(*args, **kwargs):
    purge_flag = kwargs.get('purge_flag',False)
    transaction_data = kwargs.get('transaction_data',True)
    new_transaction_flag = kwargs.get('new_transaction_flag',False)
    #logging.info(f"### purge_flag:{purge_flag}")
    
    #STEP2 Processing of transaction
    blockchain_base = blockchain_memory.get_blockchain_from_memory()
    previous_PoH_hash=blockchain_base.block_header.current_PoH_hash
    previous_PoH_timestamp=blockchain_base.block_header.current_PoH_timestamp
    #check if it's the first new transaction
    #logging.info(f"{previous_PoH_hash!=PoH_memory.previous_PoH_hash} previous_PoH_hash: {previous_PoH_hash} PoH_memory.previous_PoH_hash:{PoH_memory.previous_PoH_hash}")
    leader_node_schedule=LeaderNodeScheduleMemory()
    #logging.info(f"### current_leader_node_url:{leader_node_schedule.current_leader_node_url} MY_HOSTNAME:{MY_HOSTNAME} PoH_memory.PoH_start_flag:{PoH_memory.PoH_start_flag==False}")
    #check_test="BlockVote" not in str(transaction_data)
    #logging.info(f"### PoH_memory.PoH_start_flag:{PoH_memory.PoH_start_flag}")
    #logging.info(f"### check_test:{check_test}")
    #logging.info(f"### transaction_data:{transaction_data}")
    if leader_node_schedule.current_leader_node_url==MY_HOSTNAME:leader_node_flag=True
    else:leader_node_flag=False
    #logging.info(f"### purge_flag:{purge_flag}")
    logging.info(f"### leader_node_flag:{leader_node_flag}")
    


    if leader_node_flag is True:
        #if PoH_memory.PoH_start_flag==False:
       
        if PoH_memory.PoH_start_flag==False and "NIGthreading" not in str(transaction_data):
        #if leader_node_schedule.current_leader_node_url==MY_HOSTNAME and PoH_memory.PoH_start_flag==False:
            #this is the first transaction of the SLOT, 
            #or there is the new LeaderNode following a block assertion error
            # and this is not only a BlockVote to avoid infinite loop for creating Block
            #let's start PoH
            #PoH_memory.reset(previous_PoH_hash,previous_PoH_timestamp)
            previous_previous_PoH_hash=PoH_memory.previous_PoH_hash
            PoH_memory.reset(previous_previous_PoH_hash,previous_PoH_hash,datetime.timestamp(datetime.utcnow()))
            PoH_memory.launch_PoH()
            logging.info(f"Launch of PoH: {previous_PoH_hash}")

        #check if the PoH is terminated to avoid being blocked
        if PoH_memory.PoH_start_flag==True and purge_flag is False:
            #logging.info(f"==>PoH_memory.previous_PoH_timestamp: {PoH_memory.previous_PoH_timestamp}")
            PoH_memory.check_termination()

        if purge_flag is False and PoH_memory.wip_flag is False:
            logging.info("Saving of transaction in advance by leader node")
            save_transactions_to_leader_node_advance(transaction_data)
        else:
            try:
                transaction = Transaction(blockchain_base, MY_HOSTNAME)
                transaction.receive(transaction=transaction_data)
                if transaction.is_new:
                    logging.info("Transaction is new")

                    #let's block MasterState
                    while master_state_readiness.block() is False:
                        #let's wait until MasterState is release by another thread
                        pass
                    #logging.info(f"###Transaction is locked: {transaction.transaction_data}")
                    
                    smart_contract_flag,smart_contract_index_list=check_smart_contract(transaction)
            
                    if smart_contract_flag:
                        #there are smart contract in the transaction, let's validate them
                        #input UTXO can be change so transaction_validation.validate() can only happen after 
                        transaction.validate_smart_contract(smart_contract_index_list,leader_node_flag=leader_node_flag)

                    transaction.validate(NIGthreading_flag=True)
                    transaction.validate_funds(NIGthreading_flag=True)

                    #if transaction.is_valid is True and transaction.is_smart_contract_valid is True or leader_node_flag is False and "BlockVote" not in str(transaction_data):
                    if transaction.is_valid is True and transaction.is_smart_contract_valid is True:
                        #storing in a temporay master state
                        master_state_temp=MasterState(temporary_save_flag=True)
                        #logging.info(f"########### temporary_storage_sharding transaction: {transaction.transaction_data}")
                        #update of transaction_data as smart_contract_previous_transaction has changed
                        transaction.transaction_data["outputs"]=transaction.outputs
                        transaction.transaction_data["inputs"]=transaction.inputs
                        logging.info(f"==>block_PoH:TempBlockPoH")
                        #if "127.0.0.3:5000" not in str(transaction.transaction_data):
                        try:
                            master_state_temp.update_master_state(transaction.transaction_data,"TempBlockPoH",leader_node_flag=leader_node_flag,NIGthreading_flag=True)
                            master_state_temp.store_master_state_in_memory("TempBlockPoH")
                        except Exception as e:
                            #issue with the SmartContract
                            transaction.is_smart_contract_valid=False
                            logging.info(f"ERROR with update_master_state of SmartContract  Exception: {e}")
                            logging.exception(e)

                    if transaction.is_smart_contract_valid is True:
                        transaction.store()
                        transaction.add_to_PoH(PoH_memory)
            
                        logging.info(f"PoH_memory: {PoH_memory.registry_input_data}")

                    #let's release MasterState
                    master_state_readiness.release()
                    #logging.info(f"###Transaction is released: {transaction.transaction_data}")
      
            except TransactionException as transaction_exception:
                return f'{transaction_exception}', 400

       


class BlockMultiProcessing:
    def __init__(self,*args, **kwargs):
        self.e = threading.Event()

    def launch(self,block_data):
        self.PoH_threading = threading.Thread(target=self.start, args=(self.e,block_data))
        self.PoH_threading.start()
        #self.PoH_threading.join()

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
    block_pointer=block_data['block']['header']['previous_PoH_hash']
    block_PoH=block_data['block']['header']['current_PoH_hash']
    logging.info(f"===> BlockReceiving PoH_hash:{block_PoH}")
    #logging.info(f"===> master_state_threading.receiving_readiness_flag:{master_state_threading.receiving_readiness_flag}")
    #logging.info(f"===> master_state_readiness.block():{master_state_readiness.block()}")

    leader_node_schedule=LeaderNodeScheduleMemory()
    if leader_node_schedule.current_leader_node_url==MY_HOSTNAME:leader_node_flag=True
    else:leader_node_flag=False
    
    
    #for leader node only
    #ensure that the block is allowed to be received (not purge nor block under creation)
    #while master_state_threading.receiving_readiness_flag is False:
    #    pass

    if leader_node_flag is True:
        #ensure that a block will be not created during the receiving of Block
        master_state_threading.receiving_block()
    blockchain_memory = BlockchainMemory()
    blockchain_base = blockchain_memory.get_blockchain_from_memory(block_pointer=block_pointer)

    try:
        while master_state_readiness.block() is False:
           #let's wait until MasterState is release by another thread
           pass

        block = NewBlock(blockchain_base, MY_HOSTNAME)
        block.receive(new_block=block_data["block"], sender=block_data["sender"])
        block.add_in_backlog(master_state_readiness)
        block.validate(master_state_readiness)
        
        if block.is_valid is False and leader_node_flag is True:
            #no need to wait for the BlockVote. A branch needs to be created in the consensus_blockchain
            block_to_reject_now_by_leader_node=block.new_block.block_header.current_PoH_hash
        else:block_to_reject_now_by_leader_node=None
        
        #refresh of the consensus blockchain
        from common.consensus_blockchain import consensus_blockchain
        consensus_blockchain.refresh(block_to_reject_now_by_leader_node=block_to_reject_now_by_leader_node)
        
        latest_received_block=block.new_block.block_header.current_PoH_hash
        if block.is_valid is True:
            #the Block is valid
            #leader_node_advance_purge_backlog()
            block.clear_block_transactions_from_mempool()
            received_block_2_slash=None
        else:
            #the Block is not valid 
            received_block_2_slash=block.new_block.block_header.current_PoH_hash

        block.check_vote_and_backlog(master_state_readiness,
                                     latest_received_block=latest_received_block,
                                     received_block_2_slash=received_block_2_slash)
        
        if leader_node_flag is True:
            #for leader node only
            #let's aknowledge the block receiving to allow the purge of the backlog and the block creation
            master_state_threading.receiving_akn()

        else:
            master_state_threading.receiving_reset()
       
    #except (NewBlockException, TransactionException) as new_block_exception:
    #    return f'{new_block_exception}', 400

    except Exception as e:
        #issue with new block creation / Miner
        master_state_threading.receiving_reset()
        logging.info(f"###ERROR block_saving issue: {e}")
        logging.exception(e)

    #let's release MasterState
    master_state_readiness.release()
    

@app.route("/blockchain_root", methods=['GET'])
def get_blockchain_root():
    logging.info("Get Root of BlockChain")
    #step 2 sorting of best block
    from common.consensus_blockchain import consensus_blockchain
    final_chain_list=copy.deepcopy(consensus_blockchain.final_chain_list)
    logging.info(f"final_chain_list:{final_chain_list}")
    
    consensus_blockchain.backlog_chain_list
    logging.info(f"consensus_blockchain.backlog_chain_list:{consensus_blockchain.backlog_chain_list}")
    logging.info(f"final_chain_list:{final_chain_list}")
    for i in range(len(final_chain_list)):
        del final_chain_list[i]['block_header_data']['current_PoH_timestamp']
        del final_chain_list[i]['block_header_data']['merkle_root']
        del final_chain_list[i]['block_header_data']['noonce']
        del final_chain_list[i]['block_header_data']['previous_block_hash']
    if final_chain_list!=[]:
        final_chain_list.insert(0, "=====Best Block=====")
        for backlog_chain_list_counter in consensus_blockchain.backlog_chain_list.keys():
            final_chain_list.insert(0,consensus_blockchain.backlog_chain_list[backlog_chain_list_counter]['list'])
            backlog_chain_text=f"=====BlockChain List {backlog_chain_list_counter} ====="
            final_chain_list.insert(0,backlog_chain_text)
    return jsonify(final_chain_list)


class BacklogScoreProcessing:
    #this object is ensuring that there is not too much request
    #to avoid overloading
    def __init__(self,*args, **kwargs):
        self.backlog=[]

    def __clean_request(self):
        backlog=copy.deepcopy(self.backlog)
        for item in backlog:
            if (time.time()-item[1])>60:
                #the request is older than 60 sec
                #we can remove it
                self.backlog.remove(item)
                
    def check_request(self,participant_public_key_hash):
        self.__clean_request()
        if participant_public_key_hash in [y[0] for y in self.backlog]:return True
        else:
            self.backlog.append([participant_public_key_hash,time.time()])
            return False
       

backlog_score_processing=BacklogScoreProcessing()

@app.route("/participant_refresh_score/<participant_public_key_hash>", methods=['GET'])
def participant_refresh_score(participant_public_key_hash):
    #refresh of the participant score
    if backlog_score_processing.check_request(participant_public_key_hash) is False:
        participant_refresh_score_processing=ParticipantRefreshScoreProcessing()
        participant_refresh_score_processing.launch(participant_public_key_hash)
    return "Transaction success", 200


class ParticipantRefreshScoreProcessing:
    def __init__(self,*args, **kwargs):
        self.e = threading.Event()

    def launch(self,participant_public_key_hash):
        self.PoH_threading = threading.Thread(target=self.start, args=(self.e,participant_public_key_hash))
        self.PoH_threading.start()

    def start(self,e,participant_public_key_hash):
        while e.is_set() is False:
            participant_refresh_score(participant_public_key_hash=participant_public_key_hash)
            logging.info('===> participant_rating_refresh termination')
            self.stop()
            break

    def stop(self):
        self.e.set()



def participant_refresh_score(*args, **kwargs):
    #Step 0 during 4 PoH_DURATION_SEC to ensure that the preivous block is processed
    logging.info(f"###INFO participant_refresh_score init")
    participant_public_key_hash = kwargs.get('participant_public_key_hash',None)
    block_creation_flag = kwargs.get('block_creation_flag',False)
    if block_creation_flag is False:time.sleep(PoH_DURATION_SEC*3)
    
    logging.info(f"###INFO participant_refresh_score participant_public_key_hash:{participant_public_key_hash}")
    #Step 1 retrieve the smart_contract associated to the participant
    sender_public_key_hash=marketplace_owner.public_key_hash
    payload=f"""
public_key_hash="{participant_public_key_hash}"
"""+participant_retrieve_smart_contract
    smart_contract=SmartContract(CONTEST_PUBLIC_KEY_HASH,
                                smart_contract_sender=sender_public_key_hash,
                                smart_contract_type="api",
                                payload=payload)
    smart_contract.process()
    participant_smart_contract_public_key_hash=smart_contract.result
    if participant_smart_contract_public_key_hash is not None:
        #Step 2 refresh the score
        sender_public_key_hash=marketplace_owner.public_key_hash
        smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(participant_smart_contract_public_key_hash)
        utxo_dict=get_utxo(participant_smart_contract_public_key_hash)
        input_list=[]
        output_list=[]
        for utxo in utxo_dict['utxos']:
            smart_contract=SmartContract(participant_smart_contract_public_key_hash,
                                        smart_contract_sender=sender_public_key_hash,
                                        smart_contract_type="source",
                                        payload=participant_refresh_score_script,
                                        smart_contract_previous_transaction=smart_contract_transaction_hash,
                                        smart_contract_transaction_hash=smart_contract_transaction_hash)
            smart_contract.process()
            logging.info(f'####smart_contract.result:{smart_contract.result}')
            if smart_contract.error_flag is False and smart_contract.smart_contract_memory!=[]:
                unlocking_public_key_hash=marketplace_owner.public_key_hash+" SC "+participant_smart_contract_public_key_hash
                input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash=unlocking_public_key_hash))
                output_list.append(TransactionOutput(list_public_key_hash=[participant_smart_contract_public_key_hash], 
                                                     account_temp=True,
                                                    amount=0,
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
                                                    smart_contract_transaction_hash=smart_contract.smart_contract_transaction_hash,
                                                    marketplace_transaction_flag=False,
                                                    smart_contract_transaction_flag=True))

                if block_creation_flag is True:
                    transaction_refresh_score = TransactionInBlock(input_list, output_list)
                    transaction_refresh_score.sign(marketplace_owner)
                    return transaction_refresh_score
                    break
                else:
                    marketplace_wallet.process_transaction(inputs=input_list, outputs=output_list)
                break

    return None


@app.route("/contest_refresh_ranking", methods=['GET'])
def contest_refresh_ranking():
    #refresh of the contest ranking
    sender_public_key_hash=marketplace_owner.public_key_hash
    smart_contract=SmartContract(CONTEST_PUBLIC_KEY_HASH,
                                smart_contract_sender=sender_public_key_hash,
                                smart_contract_type="api",
                                payload=contest_refresh_ranking_script)
    smart_contract.process()
    return jsonify(smart_contract.result)



class MarketplaceRequestArchivingProcessing:
    def __init__(self,*args, **kwargs):
        self.e = threading.Event()

    def launch(self,request_type,marketplace_account,marketplace_step,mp_request_signature):
        self.PoH_threading = threading.Thread(target=self.start, args=(self.e,request_type,marketplace_account,marketplace_step,mp_request_signature))
        self.PoH_threading.start()

    def start(self,e,request_type,marketplace_account,marketplace_step,mp_request_signature):
        while e.is_set() is False:
            marketplace_request_archiving(request_type=request_type,marketplace_account=marketplace_account,marketplace_step=marketplace_step,mp_request_signature=mp_request_signature)
            logging.info('===> marketplace_request_archiving termination')
            self.stop()
            break

    def stop(self):
        self.e.set()

def marketplace_request_archiving(*args, **kwargs):
    #Archiving of the expired marketplace request
    logging.info(f"###INFO marketplace_request_archiving init")
    marketplace_account = kwargs.get('marketplace_account',None)
    marketplace_step = kwargs.get('marketplace_step',0)
    request_type = kwargs.get('request_type',None)
    mp_request_signature = kwargs.get('mp_request_signature',None)
    
    
    
    if marketplace_account is not None:
        logging.info(f"###INFO marketplace_request_archiving check1")
        #STEP 1 retrieve the needed information
        sender_public_key_hash=marketplace_owner.public_key_hash
        payload=marketplace_archiving_script
        smart_contract=SmartContract(marketplace_account,
                                    smart_contract_sender=sender_public_key_hash,
                                    smart_contract_type="api",
                                    payload=payload)
        smart_contract.process()
        logging.info(f'###INFO marketplace_request_archiving check 1 result:{smart_contract.result}')
        if smart_contract.result is not None and smart_contract.error_flag is False:
            logging.info(f"###INFO marketplace_request_archiving check2")
            #STEP 2 process the Marketplace SmartContract
            account_list_2_remove=smart_contract.result
            #account_list_2_remove[0]=buyer_public_key_hash
            #account_list_2_remove[1]=seller_public_key_hash]
            #removal of '' for step 1 as there is no Seller
            try:account_list_2_remove.remove('')
            except:pass
            marketplace_cancellation_script=f"""
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.check_cancellation("{mp_request_signature}")
mp_request_step2_done.validate_step()
memory_list.add([mp_request_step2_done,mp_request_step2_done.mp_request_name,['account','step','timestamp','requested_amount',
  'requested_currency','requested_deposit','buyer_public_key_hash','reputation_buyer','reputation_seller',
  'buyer_public_key_hex','requested_nig','timestamp_nig','seller_public_key_hex','seller_public_key_hash','encrypted_account',
  'mp_request_signature','mp_request_id','previous_mp_request_name','mp_request_name','seller_safety_coef','smart_contract_ref']])
mp_request_step2_done.get_requested_deposit()
"""
            payment_default_script=f"""
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.check_payment_default("{mp_request_signature}")
mp_request_step2_done.validate_step()
memory_list.add([mp_request_step2_done,mp_request_step2_done.mp_request_name,['account','step','timestamp','requested_amount',
  'requested_currency','requested_deposit','buyer_public_key_hash','reputation_buyer','reputation_seller',
  'buyer_public_key_hex','requested_nig','timestamp_nig','seller_public_key_hex','seller_public_key_hash','encrypted_account',
  'mp_request_signature','mp_request_id','previous_mp_request_name','mp_request_name','seller_safety_coef','smart_contract_ref']])
mp_request_step2_done.get_requested_deposit()
"""


            from common.smart_contract_script import marketplace_expiration_script
            archiving_step=None
            if request_type=="expiration":
                payload=marketplace_expiration_script
                archiving_step=98
            if request_type=="cancellation":
                payload=marketplace_cancellation_script
                archiving_step=99
            if request_type=="payment_default":
                payload=payment_default_script
                archiving_step=66

            smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(marketplace_account)
            utxo_dict=get_utxo(marketplace_account)
            input_list=[]
            output_list=[]
            for utxo in utxo_dict['utxos']:
                #there is normally only one UTXO
                smart_contract_amount=0
                smart_contract=SmartContract(marketplace_account,
                                            smart_contract_sender=sender_public_key_hash,
                                            smart_contract_type="source",
                                            payload=payload,
                                            smart_contract_previous_transaction=smart_contract_transaction_hash,
                                            smart_contract_transaction_hash=smart_contract_transaction_hash)
                smart_contract.process()
                smart_contract.error_flag
                smart_contract.error_code
                logging.info(f"### smart_contract error_flag:{smart_contract.error_flag} smart_contract.error_code:{smart_contract.error_code}")
                logging.info(f"### smart_contract result:{smart_contract.result}")
                requested_deposit=smart_contract.result
                if requested_deposit is None:requested_deposit=0
                #STEP 2 : retrieve payment amount to buyer


                if request_type=="payment_default":
                    seller_safety_coef_script=f"""
memory_obj_2_load=['mp_request_step2_done']
return mp_request_step2_done.requested_nig
"""
                    smart_contract_requested_nig=SmartContract(marketplace_account,
                                            smart_contract_sender=sender_public_key_hash,
                                            smart_contract_type="source",
                                            payload=seller_safety_coef_script,
                                            smart_contract_previous_transaction=smart_contract_transaction_hash,
                                            smart_contract_transaction_hash=smart_contract_transaction_hash)
                    smart_contract_requested_nig.process()
                    payment_default_transaction_amount=smart_contract_requested_nig.result
                    logging.info(f"### payment_default_transaction_amount result:{payment_default_transaction_amount}")
                    #the transaction amount is recredited to the seller
                    #the seller is losing his deposit
                    #this amount is sent in the SmartContract and so lost
                    smart_contract_amount=(utxo['amount']-payment_default_transaction_amount)

                        
                unlocking_public_key_hash=marketplace_owner.public_key_hash+" SC "+marketplace_account
                #trigger for removing the SmartContract from the Marketplace of the account
                #list_public_key_hash=[marketplace_owner.public_key_hash,marketplace_account]
                list_public_key_hash=[marketplace_account]
                for account in account_list_2_remove:
                    if account is not None and account not in list_public_key_hash:list_public_key_hash.append(account)
                input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash=unlocking_public_key_hash))
                output_list.append(TransactionOutput(list_public_key_hash=list_public_key_hash, 
                                                        marketplace_step=archiving_step,
                                                        account_temp=True,
                                                        amount=smart_contract_amount,
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
                                                        smart_contract_transaction_hash=smart_contract.smart_contract_transaction_hash,
                                                        marketplace_transaction_flag=True,
                                                        smart_contract_transaction_flag=False))
                #The buyer needs to be recreditted
                if requested_deposit>0:
                    if archiving_step!=66:
                        #the buyer is not credited of the deposit when there is a payment default (66)
                        output_list.append(TransactionOutput(list_public_key_hash=[account_list_2_remove[0]], 
                                                                amount=(requested_deposit)))
                            
                try:
                    #account_list_2_remove[1]=seller_public_key_hash
                    #seller_public_key_hash can be None in step 2 
                    account_list_2_remove[1]
                    seller_public_key_hash_ok=True
                except:
                    seller_public_key_hash_ok=False
                        

                if marketplace_step==3 and request_type=="payment_default":
                    #The seller needs to be recreditted only in step 3 only in case of payment_default
                    #in marketplace_step 3, the seller needs to confirm the transaction so he cannot be recreditted
                    output_list.append(TransactionOutput(list_public_key_hash=[account_list_2_remove[1]], 
                                                        amount=payment_default_transaction_amount))

                else:
                    if marketplace_step!=3 and seller_public_key_hash_ok is True:
                        #The seller needs to be recreditted only in step 2
                        output_list.append(TransactionOutput(list_public_key_hash=[account_list_2_remove[1]], 
                                                            amount=(utxo['amount']-requested_deposit)))

                    
                        
                        
                marketplace_wallet.process_transaction(inputs=input_list, outputs=output_list)

                #Refresh of the reputation
                #refresh_reputation(account_list_2_remove[0])
                #refresh_reputation(account_list_2_remove[1])
        else:
            logging.info(f"**** ISSUE marketplace_request_archiving , marketplace_account: {marketplace_account} marketplace_step:{marketplace_step} request_type:{request_type}")
            logging.info(f"**** ISSUE: {smart_contract.error_code}")


@app.route("/refresh_reputation/<account_public_key_hash>", methods=['GET'])
def refresh_reputation(account_public_key_hash):
    #refresh of the reputation of an account
    #if backlog_score_processing.check_request(account_public_key_hash) is False:
    refresh_reputation_processing=RefreshReputationProcessing()
    refresh_reputation_processing.launch(account_public_key_hash)
    return "Transaction success", 200


class RefreshReputationProcessing:
    def __init__(self,*args, **kwargs):
        self.e = threading.Event()

    def launch(self,account_public_key_hash):
        self.PoH_threading = threading.Thread(target=self.start, args=(self.e,account_public_key_hash))
        self.PoH_threading.start()

    def start(self,e,account_public_key_hash):
        while e.is_set() is False:
            refresh_reputation(account_public_key_hash=account_public_key_hash)
            logging.info('===> refresh_reputation_processing termination')
            self.stop()
            break

    def stop(self):
        self.e.set()


def refresh_reputation(*args, **kwargs):
    #Step 0 during 4 PoH_DURATION_SEC to ensure that the preivous block is processed
    logging.info(f"###INFO refresh_reputation init")
    #time.sleep(PoH_DURATION_SEC*3)
    account_public_key_hash = kwargs.get('account_public_key_hash',None)
    #Flag use to create reputation transaction to be inserted directly in the block at creation
    block_creation_flag = kwargs.get('block_creation_flag',False)
    logging.info(f"###INFO refresh_reputation account_public_key_hash:{account_public_key_hash}")
    
    if account_public_key_hash is not None and account_public_key_hash!="":
        #Step 1 retrieve all the Marketplace Archive associated to the account
        blockchain_memory = BlockchainMemory()
        blockchain_base = blockchain_memory.get_blockchain_from_memory()
        account_public_key_hash_utxo=blockchain_base.get_smart_contract_api(account_public_key_hash)
        nb_transaction=0
        nb_pos=0
        nb_neg=0
        for marketplace_request_account in account_public_key_hash_utxo["marketplace_archive"]:
            payload=f"""
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.get_reputation()
"""
            smart_contract=SmartContract(marketplace_request_account,
                                        smart_contract_sender="sender_public_key_hash",
                                        smart_contract_type="api",
                                        payload=payload)
            smart_contract.process()

            reputation_dict=smart_contract.result
            logging.info(f"==>reputation_dict:{reputation_dict}")
            if reputation_dict is not None:
                #reputation_dict = None if step != 4  or step !=99 (expiration)
                for account in reputation_dict.keys():
                    if account==account_public_key_hash:
                        nb_transaction+=1
                        if reputation_dict[account]<0:nb_neg+=-reputation_dict[account]
                        if reputation_dict[account]>0:nb_pos+=reputation_dict[account]

        logging.info(f'==>nb_transaction:{nb_transaction}')
        logging.info(f'==>nb_neg:{nb_neg}')
        logging.info(f'==>nb_pos:{nb_pos}')
        #Step 2 refresh the reputation SmartContrat
        if nb_transaction>0:
            reputation_smart_contrat_public_key_hash=account_public_key_hash_utxo["reputation"]
            if reputation_smart_contrat_public_key_hash!="" and reputation_smart_contrat_public_key_hash!=[]:
                sender_public_key_hash=marketplace_owner.public_key_hash
                smart_contract_previous_transaction,smart_contract_transaction_hash=load_smart_contract(reputation_smart_contrat_public_key_hash)
                logging.info(f'==>smart_contract_previous_transaction:{smart_contract_previous_transaction}')
                logging.info(f'==>smart_contract_transaction_hash:{smart_contract_transaction_hash}')
                utxo_dict=get_utxo(reputation_smart_contrat_public_key_hash)
                logging.info(f'==>utxo_dict:{utxo_dict}')
                input_list=[]
                output_list=[]
                for utxo in utxo_dict['utxos']:
                    refresh_reputation_script=f"""
memory_obj_2_load=['reputation']
reputation.nb_transaction={nb_transaction}
reputation.nb_pos={nb_pos}
reputation.nb_neg={nb_neg}
memory_list.add([reputation,'reputation',['nb_transaction','nb_pos','nb_neg']])
123456
"""
                    smart_contract=SmartContract(reputation_smart_contrat_public_key_hash,
                                                smart_contract_sender=sender_public_key_hash,
                                                smart_contract_type="source",
                                                payload=refresh_reputation_script,
                                                smart_contract_previous_transaction=smart_contract_transaction_hash,
                                                smart_contract_transaction_hash=smart_contract_transaction_hash)
                    smart_contract.process()
                    logging.info(f'####smart_contract.result:{smart_contract.result}')
                    logging.info(f'####smart_contract.error_flag:{smart_contract.error_flag}')
                    logging.info(f'####smart_contract.error_code:{smart_contract.error_code}')
                    if smart_contract.error_flag is False and smart_contract.smart_contract_memory!=[]:
                        #smart_contract_memory can be equal to [] is the user is manually refreshing his reputation
                        unlocking_public_key_hash=marketplace_owner.public_key_hash+" SC "+reputation_smart_contrat_public_key_hash
                        input_list.append(TransactionInput(transaction_hash=utxo['transaction_hash'], output_index=utxo['output_index'],unlocking_public_key_hash=unlocking_public_key_hash))
                        output_list.append(TransactionOutput(list_public_key_hash=[reputation_smart_contrat_public_key_hash], 
                                                             account_temp=True,
                                                            amount=0,
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
                                                            smart_contract_transaction_hash=smart_contract.smart_contract_transaction_hash,
                                                            marketplace_transaction_flag=False,
                                                            smart_contract_transaction_flag=True))
                        if block_creation_flag is True:
                            transaction_reputation = TransactionInBlock(input_list, output_list)
                            transaction_reputation.sign(marketplace_owner)
                            return transaction_reputation
                            break
                        else:
                            marketplace_wallet.process_transaction(inputs=input_list, outputs=output_list)
                            #logging.info(f'==>input_list:{input_list}')
                            #logging.info(f'==>output_list:{output_list}')
                        break


if __name__ == "__main__":
    main()

if MY_NODE.startswith("local"):start()
