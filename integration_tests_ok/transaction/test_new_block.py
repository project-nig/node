from re import A
import time

import pytest

from blockchain_users.camille import private_key as camille_private_key
from common.block import BlockHeader
from common.io_mem_pool import MemPool
from common.node import Node
from common.transaction_input import TransactionInput
from common.transaction_output import TransactionOutput
from integration_tests.common.blockchain_network import DefaultBlockchainNetwork, NODE00_HOSTNAME, \
    NODE01_HOSTNAME, NODE02_HOSTNAME
from node.new_block_creation.new_block_creation import ProofOfWork
from wallet.wallet import Owner, Wallet, Transaction

from common.io_leader_node_schedule import LeaderNodeScheduleMemory
from common.proof_of_history import ProofOfHistory



@pytest.fixture(scope="module")
def camille():
    return Owner(private_key=camille_private_key)

#@pytest.fixture(scope="module")
#def leader_node_schedule_memory():
#    return LeaderNodeScheduleMemory()


@pytest.fixture(scope="module")
def node00():
    return Node(NODE00_HOSTNAME)


@pytest.fixture(scope="module")
def node01():
    return Node(NODE01_HOSTNAME)


@pytest.fixture(scope="module")
def node02():
    return Node(NODE02_HOSTNAME)


@pytest.fixture(scope="module")
def blockchain_network():
    return DefaultBlockchainNetwork()


@pytest.fixture(scope="module")
def camille_wallet(camille, default_node):
    return Wallet(camille, default_node)


@pytest.fixture(scope="module")
def mempool():
    return MemPool()


@pytest.fixture(scope="module")
def pow():
    pow=ProofOfWork("127.0.0.3:5000")
    PoH_memory=ProofOfHistory(PoW_memory=pow)
    pow.start()
    return pow
    #return ProofOfWork("1.1.1.1:1234")


@pytest.fixture(scope="module")
def create_good_transactions(camille, mempool,blockchain_network):
    blockchain_network.restart()
    utxo_0 = TransactionInput(transaction_hash="e10154f49ae1119777b93e5bcd1a1506b6a89c1f82cc85f63c6cbe83a39df5dc",
                              output_index=0)
    output_0 = TransactionOutput(list_public_key_hash=[b"a037a093f0304f159fe1e49cfcfff769eaac7cda"], amount=5)
    transaction_1 = Transaction(inputs=[utxo_0], outputs=[output_0])
    transaction_1.sign(camille)
    transactions = [transaction_1]
    transactions_str = [transaction.transaction_data for transaction in transactions]
    #mempool.store_transactions_in_memory(transactions_str)
    from node.main import save_transactions_to_leader_node_advance
    save_transactions_to_leader_node_advance(transaction_1.transaction_data)


@pytest.fixture(scope="module")
def create_bad_transactions(camille, mempool,blockchain_network):
    blockchain_network.restart()
    utxo_0 = TransactionInput(transaction_hash="56697971b76850a4d725c75fbbc20ea97bd1382e2cfae43c41e121ca399b660",
                              output_index=0)
    output_0 = TransactionOutput(list_public_key_hash=[b"a037a093f0304f159fe1e49cfcfff769eaac7cda"], amount=25)
    transaction_1 = Transaction(inputs=[utxo_0], outputs=[output_0])
    transaction_1.sign(camille)
    transactions = [transaction_1]
    transactions_str = [transaction.transaction_data for transaction in transactions]
    mempool.store_transactions_in_memory(transactions_str)



