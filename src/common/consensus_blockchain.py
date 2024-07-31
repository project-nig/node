from operator import itemgetter
from common.block import Block, BlockHeader, BlockPoH
from common.io_storage_sharding import StorageSharding
import os
import logging

class ConcensusBlockChain:
    """
    Class to manage the vote and slash from the node of the blocks to identity
    the best blockchain.
    """
    def __init__(self):
        from common.values import NEW_BLOCKCHAIN_DIR_BACKLOG,STORAGE_DIR
        self.block_list=None
        self.final_block_list=[]
        self.final_chain_list=[]
        self.best_block=None
        self.backlog_storage_sharding=StorageSharding(NEW_BLOCKCHAIN_DIR_BACKLOG,deepth=0)
        self.backlog_chain_list={}
        self.backlog_chain_list_counter=1
        self.block_to_reject_now_by_leader_node=None
        self.__setup__()

    def __setup__(self):
        from common.values import NEW_BLOCKCHAIN_DIR_BACKLOG,STORAGE_DIR
        directory = os.fsencode(STORAGE_DIR+NEW_BLOCKCHAIN_DIR_BACKLOG)
        best_block_header_list=[]

        from common.smart_contract import SmartContract,load_smart_contract_from_master_state
        try:
            #step 1 extraction of all the block in backlog
            for file in os.listdir(directory):
                best_block_header_dic={}
                block_PoH_Hash = os.fsdecode(file)
                if block_PoH_Hash!="last_block_pointer" and block_PoH_Hash!="vote_book" and block_PoH_Hash!=self.block_to_reject_now_by_leader_node:
                    #the filename is the block PoH hash / block_pointer
                    #extration of the slot
                    best_block_header_dic=self.backlog_storage_sharding.read(block_PoH_Hash)['header']
                    best_block_header_dic['PoH']=self.backlog_storage_sharding.read(block_PoH_Hash)['PoH']
                    #extration of the vote ratio
                    try:
                        payload=f'''memory_obj_2_load=['block_vote']
block_vote.vote_ratio()
'''
                        smart_contract_previous_transaction,smart_contract_transaction_hash,smart_contract_transaction_output_index=load_smart_contract_from_master_state(block_PoH_Hash)
                        smart_contract=SmartContract(block_PoH_Hash,
                                                        smart_contract_sender="sender_public_key_hash4",
                                                        smart_contract_type="api",
                                                        payload=payload,
                                                        smart_contract_previous_transaction=smart_contract_transaction_hash,
                                                        smart_contract_transaction_hash=smart_contract_transaction_hash)
                        smart_contract.process()
                        if smart_contract.error_flag is False:
                            block_vote_ratio=smart_contract.result
                            best_block_header_dic['vote_ratio']=block_vote_ratio
                            best_block_header_list.append(best_block_header_dic)
                        else:
                            import logging
                            logging.info(f"**** ISSUE consensus blockchain: {block_PoH_Hash}")
                            logging.info(f"**** ISSUE: {smart_contract.error_code}")
                        
                    except:
                        #block without vote are unknown
                        best_block_header_dic['vote_ratio']=0
                        best_block_header_list.append(best_block_header_dic)
            self.block_list=best_block_header_list

            #Step 1 - sorting of the block list by slot number
            if self.block_list!=[]:
                block_list_sorted = sorted(self.block_list, key=itemgetter('slot'))
                import logging
            
                #Step 2 - creation of ConcensusBlock object per block
                new_block_list=[]
                for i in range(0,len(block_list_sorted)):
                    new_block_list.append(ConcensusBlock(block_list_sorted[i]))
            
                #Step 4 - chaining between the different blocs
                for i in range(0,len(new_block_list)):
                    for j in range(0,len(new_block_list)):
                        if i!=j:
                            if new_block_list[i].current_concensus_block['current_PoH_hash']==new_block_list[j].current_concensus_block['previous_PoH_hash']:
                                new_block_list[j].previous_concensus_block=new_block_list[i]
                                new_block_list[i].next_concensus_block=new_block_list[j]


                #Step 5 - sorting of block by slot order
                slot_counter_min=block_list_sorted[0]['slot']
                slot_counter_cursor=slot_counter_min
                block_list_temp=[]
                for i in range(0,len(new_block_list)):
                    if slot_counter_cursor==new_block_list[i].current_concensus_block['slot']:
                        block_list_temp.append(new_block_list[i])
                    else:
                        slot_counter_cursor=new_block_list[i].current_concensus_block['slot']
                        self.final_block_list.append(block_list_temp)
                        block_list_temp=[new_block_list[i]]
                if block_list_temp!=[]:self.final_block_list.append(block_list_temp)

                #Step 6 - sorting of the different available chain
                backlog_chain_list=[]
                for i in range(len(new_block_list)-1,-1,-1):
                    if new_block_list[i].next_concensus_block is None:
                        #this is a chain, let's add it.
                        final_chain_dic={}
                        final_chain_dic['block_header_data']=new_block_list[i].current_concensus_block
                        final_chain_dic['chain_vote']=self.calculate_chain_vote(new_block_list[i])
                        self.final_chain_list.append(final_chain_dic)
                    
                        #Step 3 - creation of ConcensusBlock object per block
                        #ex: {1: {'list': ['block4', '99e6dc11edeef7f6dcda2b7afe2459f5202dfc8bd43ba923d3e69a34fcabfd4c', 
                        ##'f0a1ad49dad8cacda894eed8cb55274c54faa64511384dfd469c4560b71897b5', '6cf20b7ba07c3884fb0abfa2d0f061673efb226a10191009c39193c54a790e1b'], 
                        ##'last': '6cf20b7ba07c3884fb0abfa2d0f061673efb226a10191009c39193c54a790e1b'}}
                        self.backlog_chain_list[self.backlog_chain_list_counter]={}
                        backlog_chain_list_temp=self.retrieve_blockchain_PoH(new_block_list[i])
                        self.backlog_chain_list[self.backlog_chain_list_counter]['list']=backlog_chain_list_temp
                        self.backlog_chain_list[self.backlog_chain_list_counter]['last']=backlog_chain_list_temp[-1]
                        self.backlog_chain_list_counter+=1
                
                #Step 7 - identification of best block by sorting by 'chain_vote'
                final_chain_list_sorted = sorted(self.final_chain_list, key=itemgetter('chain_vote'), reverse=True)
                self.final_chain_list=final_chain_list_sorted
                import logging
                #logging.info(f"==>final_chain_list_sorted:{final_chain_list_sorted}")
                block_header_data=final_chain_list_sorted[0]['block_header_data']
                best_block_header = BlockHeader(previous_block_hash=block_header_data['previous_block_hash'],
                                                   current_PoH_hash=block_header_data['current_PoH_hash'],
                                                   current_PoH_timestamp=block_header_data['current_PoH_timestamp'],
                                                   previous_PoH_hash=block_header_data['previous_PoH_hash'],
                                                   merkle_root=block_header_data['merkle_root'],
                                                   timestamp=block_header_data['timestamp'],
                                                   noonce=block_header_data['noonce'],
                                                   slot=block_header_data['slot'],
                                                   leader_node_public_key_hash=block_header_data['leader_node_public_key_hash'])
                best_block_block_PoH=BlockPoH(PoH_registry_input_data=block_header_data['PoH']['PoH_registry_input_data'],
                                              PoH_registry_intermediary=block_header_data['PoH']['PoH_registry_intermediary'])
                best_block = Block(
                    block_header=best_block_header,
                    block_PoH=best_block_block_PoH,
                    transactions="not loaded",
                    )
            
                self.best_block=best_block

        except Exception as e:
            logging.info(f"ERROR with ConcensusBlockChain setup")
            logging.exception(e)
        
        

    def calculate_chain_vote(slef,consensus_block):
        #this function is going back the chain to calculate the vote
        vote_count=0
        while True:
            vote_count+=consensus_block.current_concensus_block['vote_ratio']
            previous_concensus_block=consensus_block.previous_concensus_block
            consensus_block=previous_concensus_block
            if consensus_block is None:break
        return vote_count

    def retrieve_blockchain_PoH(slef,consensus_block):
        #this function is going back the chain to retrieve all the blockchain_PoH
        backlog_chain_list_temp=[]
        while True:
            backlog_chain_list_temp.append(consensus_block.current_concensus_block['current_PoH_hash'])
            previous_PoH_hash=consensus_block.current_concensus_block['previous_PoH_hash']
            previous_concensus_block=consensus_block.previous_concensus_block
            consensus_block=previous_concensus_block
            if consensus_block is None:break
        backlog_chain_list_temp.append(previous_PoH_hash)
        backlog_chain_list_temp.reverse()
        return backlog_chain_list_temp

    def refresh(self,*args, **kwargs):
        self.block_to_reject_now_by_leader_node = kwargs.get('block_to_reject_now_by_leader_node',False)
        #this function is refreshing the ConsensusBlockchain after block creation or block beceiving
        self.final_block_list=[]
        self.final_chain_list=[]
        self.best_block=None
        self.backlog_chain_list={}
        self.backlog_chain_list_counter=1
        self.__setup__()
    
class ConcensusBlock:
    """
    Class to encapsulate the real Block object into the ConcensusBlockChain object. 
    """
    def __init__(self,block):
        self.previous_concensus_block=None
        self.current_concensus_block=block
        self.next_concensus_block=None
        


consensus_blockchain=ConcensusBlockChain()