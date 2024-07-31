import json
import logging
import os
from operator import itemgetter

from common.block import Block, BlockHeader, BlockPoH
from common.master_state import MasterState
from common.io_storage_sharding import StorageSharding



class BlockchainMemory:
    """
    Class to manage the storage of the blockchain in the files of the Node via the class StorageSharding. 
    There are 3 storages: the blockchain which is validated by ConcensusBlockChain, the backlog of blocks waiting to be validated,
    the blocks which are slashed.
    """

    def __init__(self,*args, **kwargs):
        from common.values import BLOCKCHAIN_DIR,NEW_BLOCKCHAIN_DIR,NEW_BLOCKCHAIN_DEEPTH,NEW_BLOCKCHAIN_DIR_BACKLOG,STORAGE_DIR,NEW_BLOCKCHAIN_DIR_SLASHED,NEW_BLOCKCHAIN_SLASHED_DEEPTH
        self.file_name = BLOCKCHAIN_DIR
        self.master_state=MasterState()
        self.storage_sharding=StorageSharding(NEW_BLOCKCHAIN_DIR,deepth=NEW_BLOCKCHAIN_DEEPTH)
        self.backlog_storage_sharding=StorageSharding(NEW_BLOCKCHAIN_DIR_BACKLOG,deepth=0)
        self.slashed_storage_sharding=StorageSharding(NEW_BLOCKCHAIN_DIR_SLASHED,deepth=NEW_BLOCKCHAIN_SLASHED_DEEPTH)
        self.backlog_flag=kwargs.get('backlog_flag',False)
        self.STORAGE_DIR=STORAGE_DIR
        self.NEW_BLOCKCHAIN_DIR_BACKLOG=NEW_BLOCKCHAIN_DIR_BACKLOG
        
    def setup_backlog_directory(self):
        self.backlog_storage_sharding.setup_directory()

    def get_blockchain_from_memory(self, *args, **kwargs):
        #logging.info("Getting blockchain from memory")
        block_pointer=kwargs.get('block_pointer',None)
        if block_pointer is None:
            block_pointer_to_retrieve="last_block_pointer"
            last_block_pointer=self.backlog_storage_sharding.read(block_pointer_to_retrieve)
            if last_block_pointer is None:last_block_pointer=self.storage_sharding.read(block_pointer_to_retrieve)
        else:
            last_block_pointer=block_pointer
        
        if last_block_pointer is not None:
            block_dict=self.backlog_storage_sharding.read(last_block_pointer)
            if block_dict is None:block_dict=self.storage_sharding.read(last_block_pointer)
            #logging.info(f"block_dict type: {type(block_dict)} block_dict: {block_dict}")
            block_header_str = block_dict.pop("header")
            block_PoH_str = block_dict.pop("PoH")
            block_signature_str = block_dict.pop("signature")
            block_header = BlockHeader(**block_header_str)
            block_PoH = BlockPoH(**block_PoH_str)
            block_object = Block(**block_dict, block_header=block_header,block_PoH=block_PoH,block_signature=block_signature_str, master_state=self.master_state)
            return block_object

    def get_best_block_pointer_in_backlog(self):
        '''this function is identifying the best last block in the Backlog'''
        from common.consensus_blockchain import consensus_blockchain
        if consensus_blockchain.best_block is not None:return consensus_blockchain.best_block
        else:return None


    def get_all_blockchain_from_memory(self):
        logging.info("Getting all blockchain from memory")
        last_block_pointer=self.backlog_storage_sharding.read("last_block_pointer")
        #logging.info(f"##last_block_pointer1:{last_block_pointer}")
        if last_block_pointer is None:
            #During first loading of the Node
            last_block_pointer=self.storage_sharding.read("last_block_pointer")
        #logging.info(f"##last_block_pointer2:{last_block_pointer}")
        block_key=last_block_pointer
        previous_block = None
        block_dict=None
        counter=0
        while True:
            counter+=1
            #logging.info(f"##block_key:{block_key}")
            block_dict=self.storage_sharding.read(block_key)
            if block_dict is None:block_dict=self.backlog_storage_sharding.read(block_key)
            if block_dict is None:block_dict=self.slashed_storage_sharding.read(block_key)
            if block_dict is None:
                #retrieve the block from other node
                pass


            block_header_str = block_dict.pop("header")
            block_PoH_str = block_dict.pop("PoH")
            block_signature_str = block_dict.pop("signature")
            block_header = BlockHeader(**block_header_str)
            block_PoH = BlockPoH(**block_PoH_str)
            block_object = Block(**block_dict, block_header=block_header,block_PoH=block_PoH,block_signature=block_signature_str, master_state=self.master_state)
            block_key=block_object.block_header.previous_PoH_hash
            #if previous_block is not None:previous_block.previous_block = block_object
            #previous_block = block_object
            block_object.previous_block = previous_block
            previous_block = block_object
            if block_key=="111":break
            if counter>10:break
        return block_object
    
    def store_block_in_blockchain_in_backlog(self, new_block,master_state_readiness):
        '''store the block in a file in blockchain_backlog folder
        '''
        logging.info("Storing block in backlog")
        new_block_key=new_block.data['header']['current_PoH_hash']
        new_block_data = new_block.data
        #logging.info(f"new_block_key: {new_block_key} new_block_data:{new_block_data} ")
        #storage of the block in the backlog
        self.backlog_storage_sharding.store(new_block_key,new_block_data)
       
        #update of the block pointer to point to the latest block
        self.backlog_storage_sharding.store("last_block_pointer",new_block_key)

        #no need to update of Master State as it's done during block validation

        #update of Master State
        #master_state_temp=MasterState(temporary_save_flag=True)
        #for transaction in new_block.transactions:
            #master_state_temp.update_master_state(transaction,new_block_key)
            #master_state_temp.store_master_state_in_memory(new_block_key)

    def store_block_in_blockchain_in_slashed(self, new_block):
        logging.info("Storing block in slashed archive")
        new_block_key=new_block.data['header']['current_PoH_hash']
        new_block_data = new_block.data
        self.slashed_storage_sharding.store(new_block_key,new_block_data)

    def store_block_in_blockchain_in_memory(self, new_block,latest_received_block):
        logging.info("Storing block in memory")
        new_block_key=new_block.data['header']['current_PoH_hash']
        new_block_data = new_block.data
        #logging.info(f"new_block_key: {new_block_key} new_block_data:{new_block_data} ")
        #storage of the block in the memory
        self.storage_sharding.store(new_block_key,new_block_data)
        #update of the block pointer to point to the latest block
        self.storage_sharding.store("last_block_pointer",new_block_key)

        master_state=MasterState(store_block_in_blockchain_in_memory_flag=True)
        
        for transaction in new_block.transactions:
            master_state.update_master_state(transaction,latest_received_block)
            #master_state.update_master_state(transaction,"add_in_blockchain")
            master_state.store_master_state_in_memory(new_block_key)


    def store_blockchain_dict_in_memory(self, blockchain_list: list):
        logging.info("Storing blockchain list in memory")
        previous_block = None
        #for block_dict in reversed(block_list):
        for block_dict in blockchain_list:
            block_header_str = block_dict.pop("header")
            block_PoH_str = block_dict.pop("PoH")
            block_signature_str = block_dict.pop("signature")
            block_header = BlockHeader(**block_header_str)
            block_PoH = BlockPoH(**block_PoH_str)
            block_object = Block(**block_dict, block_header=block_header,block_PoH=block_PoH,block_signature=block_signature_str, master_state=self.master_state)
            block_object.previous_block = previous_block
            self.store_block_in_blockchain_in_memory(block_object,None)
            previous_block = block_object





        text = json.dumps(blockchain_list).encode("utf-8")
        with open(self.file_name, "wb") as file_obj:
            file_obj.write(text)


