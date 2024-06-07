import json
import logging
import os

from common.block import Block, BlockHeader
from common.master_state import MasterState
from common.io_storage_sharding import StorageSharding


class BlockchainMemory:

    def __init__(self):
        #self.file_name = os.environ["BLOCKCHAIN_DIR"]
        from node.main import BLOCKCHAIN_DIR,NEW_BLOCKCHAIN_DIR,NEW_BLOCKCHAIN_DEEPTH
        self.file_name = BLOCKCHAIN_DIR
        self.master_state=MasterState()
        self.storage_sharding=StorageSharding(NEW_BLOCKCHAIN_DIR,deepth=NEW_BLOCKCHAIN_DEEPTH)
        

    def get_blockchain_from_memory(self, *args, **kwargs):
        logging.info("Getting blockchain from memory")
        block_pointer=kwargs.get('block_pointer',None)
        if block_pointer is None:last_block_pointer=self.storage_sharding.read("last_block_pointer")
        else:last_block_pointer=self.storage_sharding.read(block_pointer)
        block_dict=self.storage_sharding.read(last_block_pointer)
        #logging.info(f"block_dict type: {type(block_dict)} block_dict: {block_dict}")
        block_header_str = block_dict.pop("header")
        block_header = BlockHeader(**block_header_str)
        block_object = Block(**block_dict, block_header=block_header,master_state=self.master_state)
        return block_object

    def get_all_blockchain_from_memory(self):
        logging.info("Getting all blockchain from memory")
        last_block_pointer=self.storage_sharding.read("last_block_pointer")
        block_key=last_block_pointer
        previous_block = None
        while True:
            block_dict=self.storage_sharding.read(block_key)
            #logging.info(f"block_dict type: {type(block_dict)} block_dict: {block_dict}")
            block_header_str = block_dict.pop("header")
            block_header = BlockHeader(**block_header_str)
            block_object = Block(**block_dict, block_header=block_header,master_state=self.master_state)
            block_key=block_object.block_header.previous_PoH_hash
            #if previous_block is not None:previous_block.previous_block = block_object
            #previous_block = block_object
            block_object.previous_block = previous_block
            previous_block = block_object
            if block_key=="111":break
        return block_object

    def store_block_in_blockchain_in_memory(self, new_block):
        #logging.info("Storing block in memory")
        new_block_key=new_block.data['header']['current_PoH_hash']
        new_block_data = new_block.data
        #logging.info(f"new_block_key: {new_block_key} new_block_data:{new_block_data} ")
        #storage of the block in the memory
        self.storage_sharding.store(new_block_key,new_block_data)
        #update of Master State
        for transaction in new_block.transactions:
            self.master_state.update_master_state(transaction)
            self.master_state.store_master_state_in_memory()

        #update of the block pointer to point to the latest block
        self.storage_sharding.store("last_block_pointer",new_block_key)


    def store_blockchain_dict_in_memory(self, blockchain_list: list):
        logging.info("Storing blockchain list in memory")
        previous_block = None
        #for block_dict in reversed(block_list):
        for block_dict in blockchain_list:
            block_header_str = block_dict.pop("header")
            block_header = BlockHeader(**block_header_str)
            block_object = Block(**block_dict, block_header=block_header)
            block_object.previous_block = previous_block
            self.store_block_in_blockchain_in_memory(block_object)
            previous_block = block_object





        text = json.dumps(blockchain_list).encode("utf-8")
        with open(self.file_name, "wb") as file_obj:
            file_obj.write(text)


