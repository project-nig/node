import logging

import requests

from common.block import Block, BlockHeader
from common.io_mem_pool import MemPool
from common.master_state import MasterState
from common.io_known_nodes import KnownNodesMemory
from common.io_blockchain import BlockchainMemory
from common.values import NUMBER_OF_LEADING_ZEROS, BLOCK_REWARD,ROUND_VALUE_DIGIT
from node.transaction_validation.transaction_validation import Transaction
from common.utils import normal_round
from common.io_leader_node_schedule import LeaderNodeScheduleMemory
from common.smart_contract import check_smart_contract


class NewBlockException(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class NewBlock:
    def __init__(self, blockchain: Block,  hostname: str):
        self.blockchain = blockchain
        self.new_block = None
        self.sender = ""
        self.mempool = MemPool()
        self.known_nodes_memory = KnownNodesMemory()
        self.blockchain_memory = BlockchainMemory()
        self.leader_node_schedule_memory=LeaderNodeScheduleMemory()
        self.master_state=MasterState()
        self.hostname = hostname

    def receive(self, new_block: dict, sender: str):
        block_header = BlockHeader(**new_block["header"])
        self.new_block = Block(transactions=new_block["transactions"], block_header=block_header)
        self.sender = sender
        try:
            assert self.blockchain.block_header.hash == self.new_block.block_header.previous_block_hash
            #the block is well inserted in the blockain, we switch to the next leader node
            #self.leader_node_schedule_memory.next_leader_node_schedule(self.known_nodes_memory.known_nodes)
        #except AssertionError:
        except Exception as e:
            logging.info(f"ERROR receive block: {e}")
            print("Previous block provided is not the most recent block")
            logging.info(f"====self.blockchain.block_header: {self.blockchain.block_header.hash} {self.blockchain.block_header}")
            logging.info(f"====self.new_block.block_header: {self.new_block.block_header.previous_block_hash} {self.new_block.block_header}")
            logging.info(f"====check: {self.blockchain.block_header.hash == self.new_block.block_header.previous_block_hash}")
            #new SETUP, leader node schedule is activated despite ERROR with Block
            #next leader node will fix the issue thanks to leader node in advance
            #self.leader_node_schedule_memory.next_leader_node_schedule(self.known_nodes_memory.known_nodes)
            raise NewBlockException("", "Previous block provided is not the most recent block")
        

    def validate(self):
        self._validate_hash()
        self._validate_transactions()

    def _validate_hash(self):
        new_block_hash = self.new_block.block_header.get_hash()
        number_of_zeros_string = "".join([str(0) for _ in range(NUMBER_OF_LEADING_ZEROS)])
        try:
            assert new_block_hash.startswith(number_of_zeros_string)
        except AssertionError:
            print('Proof of work validation failed')
            raise NewBlockException("", "Proof of work validation failed")

    def _validate_transactions(self):
        input_amount = 0
        output_amount = 0
        
        for transaction in self.new_block.transactions:
            transaction_validation = Transaction(self.blockchain, self.hostname)
            transaction_validation.receive(transaction=transaction)
            import logging
            logging.info(f"####transaction _validate_funds: {transaction}")
            transaction_validation.validate()
            smart_contract_flag,smart_contract_index_list=check_smart_contract(transaction_validation)
            if smart_contract_flag:
                #there are smart contract in the transaction, let's validate them
                transaction_validation.validate_smart_contract(smart_contract_index_list)
            
            input_amount = input_amount + transaction_validation.get_total_amount_in_inputs()
            output_amount = output_amount + transaction_validation.get_total_amount_in_outputs()
            output_amount = output_amount - transaction_validation.get_total_fee_in_outputs()
            import logging
            #logging.info(f"##### output_amount {output_amount} input:{transaction_validation.inputs} ouput:{transaction_validation.outputs} transaction_data:{transaction_validation.transaction_data} output:{transaction_validation.outputs}")
        self._validate_funds(input_amount, output_amount)


    @staticmethod
    def _validate_funds(input_amount: float, output_amount: float):
        import logging
        logging.info(f"input_amount: {input_amount} {type(input_amount)}+ BLOCK_REWARD:{BLOCK_REWARD} {type(BLOCK_REWARD)} == output_amount:{output_amount} {type(output_amount)}")
        #assert round(1.01000000,2) + round(1,2) == round(2,2)
        test1=normal_round(float(normal_round(float(input_amount),ROUND_VALUE_DIGIT) + normal_round(float(BLOCK_REWARD),ROUND_VALUE_DIGIT)),ROUND_VALUE_DIGIT)
        test2=normal_round(float(output_amount),ROUND_VALUE_DIGIT)
        test3=test1==test2
        logging.info(f"test1: {test1} test2: {test2} test3: {test3}")
        assert normal_round(float(normal_round(float(input_amount),ROUND_VALUE_DIGIT) + normal_round(float(BLOCK_REWARD),ROUND_VALUE_DIGIT)),ROUND_VALUE_DIGIT) == normal_round(float(output_amount),ROUND_VALUE_DIGIT)
        

    def add(self):
        self.new_block.previous_block = self.blockchain
        self.blockchain_memory.store_block_in_blockchain_in_memory(self.new_block)

    def clear_block_transactions_from_mempool(self):
        current_transactions = self.mempool.get_transactions_from_memory()
        transactions_cleared = [i for i in current_transactions if not (i in self.new_block.transactions)]
        self.mempool.store_transactions_in_memory(transactions_cleared)
        #let's purge the transactions Store in advance
        from node.main import leader_node_advance_purge_backlog
        leader_node_advance_purge_backlog()

    def broadcast(self):
        logging.info(f"Broadcasting validated block")
        node_list = self.known_nodes_memory.known_nodes
        for node in node_list:
            if node.hostname != self.hostname and node.hostname != self.sender:
                block_content = {
                    "block": {
                        "header": self.new_block.block_header.to_dict,
                        "transactions": self.new_block.transactions
                    },
                    "sender": self.hostname
                }
                try:
                    logging.info(f"Broadcasting to {node.hostname}")
                    node.send_new_block(block_content)
                except requests.exceptions.HTTPError as error:
                    logging.info(f"Failed to broadcast block to {node.hostname}: {error}")

 
