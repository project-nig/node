from datetime import datetime

from blockchain_users.albert import private_key as albert_private_key
from blockchain_users.bertrand import private_key as bertrand_private_key
from blockchain_users.camille import private_key as camille_private_key
from blockchain_users.marketplace import private_key as marketplace_private_key
from common.block import Block, BlockHeader
from common.io_blockchain import BlockchainMemory
from common.merkle_tree import get_merkle_root
from common.transaction import Transaction
from common.transaction_input import TransactionInput
from common.transaction_output import TransactionOutput
from wallet.wallet import Owner

albert_wallet = Owner(private_key=albert_private_key)
bertrand_wallet = Owner(private_key=bertrand_private_key)
camille_wallet = Owner(private_key=camille_private_key)
marketplace_wallet = Owner(private_key=marketplace_private_key)


def initialize_default_blockchain(blockchain_memory: BlockchainMemory):
    print("Initializing default blockchain")
    timestamp_0 = datetime.timestamp(datetime.fromisoformat('2011-11-04 00:05:23.111'))
    input_0 = TransactionInput(transaction_hash="abcd1234",
                               output_index=0,unlocking_public_key_hash="abcd1234_0")
    output_0 = TransactionOutput(public_key_hash=albert_wallet.public_key_hash,
                                 amount=40)
    transaction_0 = Transaction([input_0], [output_0])
    block_header_0 = BlockHeader(previous_block_hash="1111",
                                 current_PoH_hash="block0",
                                 current_PoH_timestamp=1669210525.019439,
                                 previous_PoH_hash="111",
                                 timestamp=timestamp_0,
                                 noonce=2,
                                 merkle_root=get_merkle_root([transaction_0.transaction_data]))
    block_0 = Block(
        transactions=[transaction_0.transaction_data],
        block_header=block_header_0
    )
    blockchain_memory.store_block_in_blockchain_in_memory(block_0)

    timestamp_1 = datetime.timestamp(datetime.fromisoformat('2011-11-04 00:05:23.111'))
    input_0 = TransactionInput(transaction_hash=block_0.transactions[0]["transaction_hash"], output_index=0,unlocking_public_key_hash=albert_wallet.public_key_hash)
    output_0 = TransactionOutput(public_key_hash=bertrand_wallet.public_key_hash, amount=30)
    output_1 = TransactionOutput(public_key_hash=albert_wallet.public_key_hash, amount=10)
    transaction_1 = Transaction([input_0], [output_0, output_1])
    transaction_1.sign(albert_wallet)
    block_header_1 = BlockHeader(
        previous_block_hash=block_0.block_header.hash,
        current_PoH_hash="block1",
        current_PoH_timestamp=1669210528.019439,
        previous_PoH_hash=block_0.block_header.current_PoH_hash,
        timestamp=timestamp_1,
        noonce=3,
        merkle_root=get_merkle_root([transaction_1.transaction_data])
    )
    block_1 = Block(
        transactions=[transaction_1.transaction_data],
        block_header=block_header_1,
        previous_block=block_0,
    )
    blockchain_memory.store_block_in_blockchain_in_memory(block_1)

    timestamp_2 = datetime.timestamp(datetime.fromisoformat('2011-11-07 00:05:13.222'))
    input_0 = TransactionInput(transaction_hash=block_1.transactions[0]["transaction_hash"], output_index=1,unlocking_public_key_hash=bertrand_wallet.public_key_hash)
    output_0 = TransactionOutput(public_key_hash=camille_wallet.public_key_hash, amount=10)
    transaction_2 = Transaction([input_0], [output_0])
    transaction_2.sign(bertrand_wallet)
    block_header_2 = BlockHeader(
        previous_block_hash=block_1.block_header.hash,
        current_PoH_hash="block2",
        current_PoH_timestamp=1669210531.019439,
        previous_PoH_hash=block_1.block_header.current_PoH_hash,
        timestamp=timestamp_2,
        noonce=4,
        merkle_root=get_merkle_root([transaction_2.transaction_data])
    )
    block_2 = Block(
        transactions=[transaction_2.transaction_data],
        block_header=block_header_2,
        previous_block=block_1,
    )
    blockchain_memory.store_block_in_blockchain_in_memory(block_2)

    timestamp_3 = datetime.timestamp(datetime.fromisoformat('2011-11-09 00:11:13.333'))
    input_0 = TransactionInput(transaction_hash=block_1.transactions[0]["transaction_hash"], output_index=0,unlocking_public_key_hash=bertrand_wallet.public_key_hash)
    output_0 = TransactionOutput(public_key_hash=camille_wallet.public_key_hash, amount=5)
    output_1 = TransactionOutput(public_key_hash=bertrand_wallet.public_key_hash, amount=25)
    transaction_3 = Transaction([input_0], [output_0, output_1])
    transaction_3.sign(bertrand_wallet)
    block_header_3 = BlockHeader(
        previous_block_hash=block_2.block_header.hash,
        current_PoH_hash="block3",
        current_PoH_timestamp=1669210534.019439,
        previous_PoH_hash=block_2.block_header.current_PoH_hash,
        timestamp=timestamp_3,
        noonce=5,
        merkle_root=get_merkle_root([transaction_3.transaction_data])
    )
    block_3 = Block(
        transactions=[transaction_3.transaction_data],
        block_header=block_header_3,
        previous_block=block_2,
    )
    blockchain_memory.store_block_in_blockchain_in_memory(block_3)

    from common.smart_contract_script import marketplace_script
    from common.smart_contract import SmartContract,check_smart_contract
    smart_contract=SmartContract(marketplace_wallet.public_key_hash,
                                 smart_contract_sender=marketplace_wallet.public_key_hash,
                                 smart_contract_new=True,
                                 smart_contract_gas=1000000,
                                 type="source",
                                 payload=marketplace_script)
    smart_contract.process()

    timestamp_4 = datetime.timestamp(datetime.fromisoformat('2011-11-11 00:11:13.333'))
    input_0 = TransactionInput(transaction_hash=block_1.transactions[0]["transaction_hash"], output_index=0)
    output_0 = TransactionOutput(public_key_hash=marketplace_wallet.public_key_hash, amount=0,
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
    transaction_4 = Transaction([input_0], [output_0])
    transaction_4.sign(marketplace_wallet)
    block_header_4 = BlockHeader(
        previous_block_hash=block_3.block_header.hash,
        current_PoH_hash="block4",
        current_PoH_timestamp=1669210537.019439,
        previous_PoH_hash=block_3.block_header.current_PoH_hash,
        timestamp=timestamp_4,
        noonce=6,
        merkle_root=get_merkle_root([transaction_4.transaction_data])
    )
    block_4 = Block(
        transactions=[transaction_4.transaction_data],
        block_header=block_header_4,
        previous_block=block_3,
    )
    blockchain_memory.store_block_in_blockchain_in_memory(block_4)

