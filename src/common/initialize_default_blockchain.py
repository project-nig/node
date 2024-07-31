from datetime import datetime
import logging

from blockchain_users.albert import private_key as albert_private_key
from blockchain_users.bertrand import private_key as bertrand_private_key
from blockchain_users.camille import private_key as camille_private_key
from blockchain_users.marketplace import private_key as marketplace_private_key

from common.block import Block, BlockHeader, BlockPoH
from common.io_blockchain import BlockchainMemory
from common.merkle_tree import get_merkle_root
from common.transaction import Transaction
from common.transaction_input import TransactionInput
from common.transaction_output import TransactionOutput
from wallet.wallet import Owner

from common.smart_contract import SmartContract
from common.smart_contract_script import marketplace_script,node_network_script, node_script,contest_script,application_version_script,marketplace_request_code_script,reputation_code_script

from common.values import CONTEST_PUBLIC_KEY_HASH,APPLICATION_VERSION_PUBLIC_KEY_HASH,MARKETPLACE_CODE_PUBLIC_KEY_HASH,REPUTATION_CODE_PUBLIC_KEY_HASH



albert_wallet = Owner(private_key=albert_private_key)
bertrand_wallet = Owner(private_key=bertrand_private_key)
camille_wallet = Owner(private_key=camille_private_key)
marketplace_wallet = Owner(private_key=marketplace_private_key)


def initialize_default_blockchain(blockchain_memory: BlockchainMemory):
    """
    A function to initialize the default blockchain when launching the blockchain from the 1st Node
    """
    print("Initializing default blockchain")
    from node.main import MY_NODE
    if MY_NODE.startswith('local'):
        from blockchain_users.node2_local import public_key_hex as node2_public_key_hex
        from blockchain_users.node2_local import public_key_hash as node2_public_key_hash
        from blockchain_users.node2_local import url as node2_url
        from blockchain_users.node3_local import public_key_hex as node3_public_key_hex
        from blockchain_users.node3_local import public_key_hash as node3_public_key_hash
        from blockchain_users.node3_local import url as node3_url
    if MY_NODE.startswith('server'):
        from blockchain_users.node2_server import public_key_hex as node2_public_key_hex
        from blockchain_users.node2_server import public_key_hash as node2_public_key_hash
        from blockchain_users.node2_server import url as node2_url
        from blockchain_users.node3_server import public_key_hex as node3_public_key_hex
        from blockchain_users.node3_server import public_key_hash as node3_public_key_hash
        from blockchain_users.node3_server import url as node3_url
    
    from node.main import network
    node_network_account=network.node_network_account

    slot_count=0

    ###################BLOCK 0
    timestamp_0 = datetime.timestamp(datetime.fromisoformat('2011-11-04 00:05:23.111'))
    input_0 = TransactionInput(transaction_hash="abcd1234",
                               output_index=0,unlocking_public_key_hash="abcd1234_0")
    output_0 = TransactionOutput(list_public_key_hash=[albert_wallet.public_key_hash],
                                 amount=1000000)
    transaction_0 = Transaction([input_0], [output_0])




    
    node_public_key_hash=node_network_account.public_key_hash
    smart_contract=SmartContract(node_public_key_hash,
                                 smart_contract_sender=marketplace_wallet.public_key_hash,
                                 smart_contract_new=True,
                                 smart_contract_gas=1000000,
                                 smart_contract_type="source",
                                 payload=node_network_script)
    smart_contract.process()


    input_1 = TransactionInput(transaction_hash="abcd1234",
                               output_index=0,unlocking_public_key_hash="abcd1234_0")
    output_1 = TransactionOutput(list_public_key_hash=[node_public_key_hash], amount=0, account_temp=True,
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
                                             smart_contract_previous_transaction=smart_contract.smart_contract_previous_transaction)
    transaction_1 = Transaction([input_1], [output_1])
    transaction_1.sign(marketplace_wallet)


    block_header_0 = BlockHeader(previous_block_hash="1111",
                                 current_PoH_hash="block0",
                                 current_PoH_timestamp=1669210525.019439,
                                 previous_PoH_hash="111",
                                 timestamp=timestamp_0,
                                 noonce=2,
                                 slot=slot_count,
                                 leader_node_public_key_hash=None,
                                 merkle_root=get_merkle_root([transaction_0.transaction_data,transaction_1.transaction_data]))
    block_PoH_0=BlockPoH(PoH_registry_input_data=None,PoH_registry_intermediary=None)
    block_0 = Block(
        transactions=[transaction_0.transaction_data,transaction_1.transaction_data],
        block_header=block_header_0,
        block_PoH=block_PoH_0,
        block_signature=None
    )
    blockchain_backlog_memory = BlockchainMemory(backlog_flag=True)
    blockchain_backlog_memory.setup_backlog_directory()
    blockchain_memory.store_block_in_blockchain_in_memory(block_0,None)



    

    
    ###################BLOCK 1
    slot_count+=1
    timestamp_1 = datetime.timestamp(datetime.fromisoformat('2011-11-04 00:05:23.111'))
    input_0 = TransactionInput(transaction_hash=block_0.transactions[0]["transaction_hash"], output_index=0,unlocking_public_key_hash=albert_wallet.public_key_hash)
    output_0 = TransactionOutput(list_public_key_hash=[bertrand_wallet.public_key_hash], amount=500000)
    output_1 = TransactionOutput(list_public_key_hash=[albert_wallet.public_key_hash], amount=500000)
    transaction_2 = Transaction([input_0], [output_0, output_1])
    transaction_2.sign(albert_wallet)


    node_script_payload=f'''
memory_obj_2_load=['node_network']
node_public_key_hash="{node2_public_key_hash}"
node_public_key_hex="{node2_public_key_hex}"
node_url="{node2_url}"
'''+node_script

    node_public_key_hash=node_network_account.public_key_hash
    smart_contract_previous_transaction=block_0.transactions[1]["transaction_hash"]+"_0"
    smart_contract=SmartContract(node_public_key_hash,
                                 smart_contract_sender=marketplace_wallet.public_key_hash,
                                 smart_contract_new=False,
                                 smart_contract_previous_transaction=smart_contract_previous_transaction,
                                 smart_contract_type="source",
                                 payload=node_script_payload)
    smart_contract.process()

    input_0 = TransactionInput(transaction_hash=block_0.transactions[1]["transaction_hash"], output_index=0,unlocking_public_key_hash=marketplace_wallet.public_key_hash+" SC "+node_public_key_hash)
    output_0 = TransactionOutput(list_public_key_hash=[node_public_key_hash], amount=0, account_temp=True,
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
                                             smart_contract_previous_transaction=smart_contract.smart_contract_previous_transaction)
    transaction_3 = Transaction([input_0], [output_0])
    transaction_3.sign(marketplace_wallet)




    block_header_1 = BlockHeader(
        previous_block_hash=block_0.block_header.hash,
        current_PoH_hash="block1",
        current_PoH_timestamp=1669210528.019439,
        previous_PoH_hash=block_0.block_header.current_PoH_hash,
        timestamp=timestamp_1,
        noonce=3,
        slot=slot_count,
        leader_node_public_key_hash=None,
        merkle_root=get_merkle_root([transaction_2.transaction_data,transaction_3.transaction_data])
    )
    block_PoH_1=BlockPoH(PoH_registry_input_data=None,PoH_registry_intermediary=None)
    block_1 = Block(
        transactions=[transaction_2.transaction_data,transaction_3.transaction_data],
        block_header=block_header_1,
        block_PoH=block_PoH_1,
        block_signature=None,
        previous_block=block_0,
    )
    blockchain_memory.store_block_in_blockchain_in_memory(block_1,None)


    ###################BLOCK 2
    slot_count+=1
    timestamp_2 = datetime.timestamp(datetime.fromisoformat('2011-11-07 00:05:13.222'))
    input_0 = TransactionInput(transaction_hash=block_1.transactions[0]["transaction_hash"], output_index=1,unlocking_public_key_hash=bertrand_wallet.public_key_hash)
    output_0 = TransactionOutput(list_public_key_hash=[camille_wallet.public_key_hash], amount=100000)
    transaction_4 = Transaction([input_0], [output_0])
    transaction_4.sign(bertrand_wallet)


    node_script_payload=f'''
memory_obj_2_load=['node_network']
node_public_key_hash="{node3_public_key_hash}"
node_public_key_hex="{node3_public_key_hex}"
node_url="{node3_url}"
'''+node_script

    node_public_key_hash=node_network_account.public_key_hash
    smart_contract_previous_transaction=block_1.transactions[1]["transaction_hash"]+"_0"
    smart_contract=SmartContract(node_public_key_hash,
                                 smart_contract_sender=marketplace_wallet.public_key_hash,
                                 smart_contract_new=False,
                                 smart_contract_previous_transaction=smart_contract_previous_transaction,
                                 smart_contract_type="source",
                                 payload=node_script_payload)
    smart_contract.process()

    input_0 = TransactionInput(transaction_hash=block_1.transactions[1]["transaction_hash"], output_index=0,unlocking_public_key_hash=marketplace_wallet.public_key_hash+" SC "+node_public_key_hash)
    output_0 = TransactionOutput(list_public_key_hash=[node_public_key_hash], amount=0, account_temp=True,
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
                                             smart_contract_previous_transaction=smart_contract.smart_contract_previous_transaction)
    transaction_5 = Transaction([input_0], [output_0])
    transaction_5.sign(marketplace_wallet)

    block_header_2 = BlockHeader(
        previous_block_hash=block_1.block_header.hash,
        current_PoH_hash="block2",
        current_PoH_timestamp=1669210531.019439,
        previous_PoH_hash=block_1.block_header.current_PoH_hash,
        timestamp=timestamp_2,
        noonce=4,
        slot=slot_count,
        leader_node_public_key_hash=None,
        merkle_root=get_merkle_root([transaction_4.transaction_data,transaction_5.transaction_data])
    )
    block_PoH_2=BlockPoH(PoH_registry_input_data=None,PoH_registry_intermediary=None)
    block_2 = Block(
        transactions=[transaction_4.transaction_data,transaction_5.transaction_data],
        block_header=block_header_2,
        block_PoH=block_PoH_2,
        block_signature=None,
        previous_block=block_1,
    )
    blockchain_memory.store_block_in_blockchain_in_memory(block_2,None)


    ###################BLOCK 3
    slot_count+=1
    timestamp_3 = datetime.timestamp(datetime.fromisoformat('2011-11-09 00:11:13.333'))
    input_0 = TransactionInput(transaction_hash=block_1.transactions[0]["transaction_hash"], output_index=0,unlocking_public_key_hash=bertrand_wallet.public_key_hash)
    output_0 = TransactionOutput(list_public_key_hash=[camille_wallet.public_key_hash], amount=50000)
    output_1 = TransactionOutput(list_public_key_hash=[bertrand_wallet.public_key_hash], amount=450000)

    


    transaction_6 = Transaction([input_0], [output_0, output_1])
    transaction_6.sign(bertrand_wallet)
    block_header_3 = BlockHeader(
        previous_block_hash=block_2.block_header.hash,
        current_PoH_hash="block3",
        current_PoH_timestamp=1669210534.019439,
        previous_PoH_hash=block_2.block_header.current_PoH_hash,
        timestamp=timestamp_3,
        noonce=5,
        slot=slot_count,
        leader_node_public_key_hash=None,
        merkle_root=get_merkle_root([transaction_6.transaction_data])
    )
    block_PoH_3=BlockPoH(PoH_registry_input_data=None,PoH_registry_intermediary=None)
    block_3 = Block(
        transactions=[transaction_6.transaction_data],
        block_header=block_header_3,
        block_PoH=block_PoH_3,
        block_signature=None,
        previous_block=block_2,
    )
    
    blockchain_memory.store_block_in_blockchain_in_memory(block_3,None)
    

    ###################BLOCK 4
    smart_contract=SmartContract(marketplace_wallet.public_key_hash,
                                 smart_contract_sender=marketplace_wallet.public_key_hash,
                                 smart_contract_new=True,
                                 smart_contract_gas=1000000,
                                 smart_contract_type="source",
                                 payload=marketplace_script)
    smart_contract.process()

    slot_count+=1
    timestamp_4 = datetime.timestamp(datetime.fromisoformat('2011-11-11 00:11:13.333'))
    input_0 = TransactionInput(transaction_hash=block_1.transactions[0]["transaction_hash"], output_index=0)
    output_0 = TransactionOutput(list_public_key_hash=[marketplace_wallet.public_key_hash], amount=0,
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
                                             smart_contract_previous_transaction=smart_contract.smart_contract_previous_transaction)
    transaction_7 = Transaction([input_0], [output_0])
    transaction_7.sign(marketplace_wallet)

   

    block_header_4 = BlockHeader(
        previous_block_hash=block_3.block_header.hash,
        current_PoH_hash="block4",
        current_PoH_timestamp=1669210537.019439,
        previous_PoH_hash=block_3.block_header.current_PoH_hash,
        timestamp=timestamp_4,
        noonce=6,
        slot=slot_count,
        leader_node_public_key_hash=None,
        merkle_root=get_merkle_root([transaction_7.transaction_data])
    )
    block_PoH_4=BlockPoH(PoH_registry_input_data=None,PoH_registry_intermediary=None)
    block_4 = Block(
        transactions=[transaction_7.transaction_data],
        block_header=block_header_4,
        block_PoH=block_PoH_4,
        block_signature=None,
        previous_block=block_3,
    )
   
    blockchain_memory.store_block_in_blockchain_in_memory(block_4,None)

    ###################BLOCK 5

    smart_contract=SmartContract(APPLICATION_VERSION_PUBLIC_KEY_HASH,
                                 smart_contract_sender=marketplace_wallet.public_key_hash,
                                 smart_contract_new=True,
                                 smart_contract_gas=1000000,
                                 smart_contract_type="source",
                                 payload=application_version_script)
    smart_contract.process()

    slot_count+=1
    timestamp_5 = datetime.timestamp(datetime.fromisoformat('2011-11-11 00:11:13.333'))
    input_0 = TransactionInput(transaction_hash="abcd1234",
                               output_index=0,unlocking_public_key_hash="abcd1234_0")
    output_0 = TransactionOutput(list_public_key_hash=[APPLICATION_VERSION_PUBLIC_KEY_HASH], 
                                 amount=0,
                                 account_temp=True,
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
                                smart_contract_previous_transaction=smart_contract.smart_contract_previous_transaction)



    transaction_7 = Transaction([input_0], [output_0])
    transaction_7.sign(marketplace_wallet)

   

    block_header_5 = BlockHeader(
        previous_block_hash=block_4.block_header.hash,
        current_PoH_hash="block5",
        current_PoH_timestamp=1669210537.019439,
        previous_PoH_hash=block_4.block_header.current_PoH_hash,
        timestamp=timestamp_4,
        noonce=6,
        slot=slot_count,
        leader_node_public_key_hash=None,
        merkle_root=get_merkle_root([transaction_7.transaction_data])
    )
    block_PoH_5=BlockPoH(PoH_registry_input_data=None,PoH_registry_intermediary=None)
    block_5 = Block(
        transactions=[transaction_7.transaction_data],
        block_header=block_header_5,
        block_PoH=block_PoH_5,
        block_signature=None,
        previous_block=block_4,
    )
   
    blockchain_memory.store_block_in_blockchain_in_memory(block_5,None)

    ###################BLOCK 6

    smart_contract=SmartContract(MARKETPLACE_CODE_PUBLIC_KEY_HASH,
                                 smart_contract_sender=marketplace_wallet.public_key_hash,
                                 smart_contract_new=True,
                                 smart_contract_gas=1000000,
                                 smart_contract_type="source",
                                 payload=marketplace_request_code_script)
    smart_contract.process()

    slot_count+=1
    timestamp_6 = datetime.timestamp(datetime.fromisoformat('2011-11-11 00:11:13.333'))
    input_0 = TransactionInput(transaction_hash="abcd1234",
                               output_index=0,unlocking_public_key_hash="abcd1234_0")
    output_0 = TransactionOutput(list_public_key_hash=[MARKETPLACE_CODE_PUBLIC_KEY_HASH], 
                                 amount=0,
                                 account_temp=True,
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
                                smart_contract_previous_transaction=smart_contract.smart_contract_previous_transaction)



    transaction_7 = Transaction([input_0], [output_0])
    transaction_7.sign(marketplace_wallet)

   

    block_header_6 = BlockHeader(
        previous_block_hash=block_5.block_header.hash,
        current_PoH_hash="block6",
        current_PoH_timestamp=1669210537.019439,
        previous_PoH_hash=block_5.block_header.current_PoH_hash,
        timestamp=timestamp_6,
        noonce=6,
        slot=slot_count,
        leader_node_public_key_hash=None,
        merkle_root=get_merkle_root([transaction_7.transaction_data])
    )
    block_PoH_6=BlockPoH(PoH_registry_input_data=None,PoH_registry_intermediary=None)
    block_6 = Block(
        transactions=[transaction_7.transaction_data],
        block_header=block_header_6,
        block_PoH=block_PoH_6,
        block_signature=None,
        previous_block=block_5,
    )
   
    blockchain_memory.store_block_in_blockchain_in_memory(block_6,None)
    

    ###################BLOCK 7
    slot_count+=1
    input_0 = TransactionInput(transaction_hash="abcd1234",
                               output_index=0,unlocking_public_key_hash="abcd1234_0")
    smart_contract=SmartContract(CONTEST_PUBLIC_KEY_HASH,
                                 smart_contract_sender=marketplace_wallet.public_key_hash,
                                 smart_contract_new=True,
                                 smart_contract_gas=1000000,
                                 smart_contract_type="source",
                                 payload=contest_script)
    smart_contract.process()
    output_0 = TransactionOutput(list_public_key_hash=[CONTEST_PUBLIC_KEY_HASH], 
                                 amount=0,
                                 account_temp=True,
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
                                    smart_contract_previous_transaction=smart_contract.smart_contract_previous_transaction)
    
    transaction_0 = Transaction([input_0], [output_0])
    transaction_0.sign(marketplace_wallet)


    block_header_7 = BlockHeader(previous_block_hash=block_6.block_header.hash,
                                   current_PoH_hash="block7",
                                   current_PoH_timestamp=1669210528.019439,
                                   previous_PoH_hash=block_6.block_header.current_PoH_hash,
                                 timestamp=timestamp_0,
                                 noonce=2,
                                 slot=slot_count,
                                 leader_node_public_key_hash=None,
                                 merkle_root=get_merkle_root([transaction_0.transaction_data]))
    block_PoH_7=BlockPoH(PoH_registry_input_data=None,PoH_registry_intermediary=None)
    block_7 = Block(
        transactions=[transaction_0.transaction_data],
        block_header=block_header_7,
        block_PoH=block_PoH_7,
        block_signature=None,
        previous_block=block_6,
    )
    blockchain_backlog_memory = BlockchainMemory(backlog_flag=True)
    blockchain_backlog_memory.setup_backlog_directory()
    blockchain_memory.store_block_in_blockchain_in_memory(block_7,None)

    ###################BLOCK 8
    slot_count+=1
    input_0 = TransactionInput(transaction_hash="abcd1234",
                               output_index=0,unlocking_public_key_hash="abcd1234_0")
    smart_contract=SmartContract(REPUTATION_CODE_PUBLIC_KEY_HASH,
                                 smart_contract_sender=marketplace_wallet.public_key_hash,
                                 smart_contract_new=True,
                                 smart_contract_gas=1000000,
                                 smart_contract_type="source",
                                 payload=reputation_code_script)
    smart_contract.process()
    output_0 = TransactionOutput(list_public_key_hash=[REPUTATION_CODE_PUBLIC_KEY_HASH], 
                                 amount=0,
                                 account_temp=True,
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
                                    smart_contract_previous_transaction=smart_contract.smart_contract_previous_transaction)
    
    transaction_0 = Transaction([input_0], [output_0])
    transaction_0.sign(marketplace_wallet)


    block_header_8 = BlockHeader(previous_block_hash=block_7.block_header.hash,
                                   current_PoH_hash="block8",
                                   current_PoH_timestamp=1669210528.019439,
                                   previous_PoH_hash=block_7.block_header.current_PoH_hash,
                                 timestamp=timestamp_0,
                                 noonce=2,
                                 slot=slot_count,
                                 leader_node_public_key_hash=None,
                                 merkle_root=get_merkle_root([transaction_0.transaction_data]))
    block_PoH_8=BlockPoH(PoH_registry_input_data=None,PoH_registry_intermediary=None)
    block_8 = Block(
        transactions=[transaction_0.transaction_data],
        block_header=block_header_8,
        block_PoH=block_PoH_8,
        block_signature=None,
        previous_block=block_7,
    )
    blockchain_backlog_memory = BlockchainMemory(backlog_flag=True)
    blockchain_backlog_memory.setup_backlog_directory()
    blockchain_memory.store_block_in_blockchain_in_memory(block_8,None)