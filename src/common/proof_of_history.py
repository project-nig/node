import json, logging
import threading
import time
from datetime import datetime
from hashlib import sha256
from multiprocessing.dummy import Pool as ThreadPool
from common.io_blockchain import BlockchainMemory




class ProofOfHistory:
    """
    Class to manage the Proof O fHistory (PoH) of the blockchain to ensure a consistency in terms of
    timing and content between the different blocks.
    """
    def __init__(self,*args, **kwargs):
        from common.values import PoH_DURATION_SEC
        self.PoW_memory = kwargs.get('PoW_memory',None)
        if self.PoW_memory is not None:self.PoW_memory.PoH_memory = self
        self.reset("None","None",datetime.timestamp(datetime.utcnow()))
        self.PoH_DURATION_SEC=PoH_DURATION_SEC
        self.PoH_start_flag=False
        self.wip_flag=False
        self.wip_flag_processing=False

    def reset(self,previous_previous_PoH_hash:str,previous_PoH_hash:str,previous_PoH_timestamp:str):
        self.previous_previous_PoH_hash=previous_previous_PoH_hash
        self.previous_PoH_hash = previous_PoH_hash
        self.previous_PoH_timestamp = float(previous_PoH_timestamp)
        self.input_hash=previous_PoH_hash
        self.input_data_list=[]
        self.input_data_counter=0
        self.counter=1
        text_to_hash=str(self.previous_PoH_timestamp)+self.input_hash+str(self.counter)+str(None)
        self.output_hash=sha256(text_to_hash.encode('utf-8')).hexdigest()
        self.registry=[]
        self.registry_input_data=[]
        #example of registry or registry_input_data
        #[input_hash,counter,input_data,output_hash,input_data_counter]
        #counter => counter of the PoH function
        #input_data_counter=> counter only for the input_data
        #[["f95189a85a76f0115da4c38c3e6a2d3c1ee5be45a3498d3de3e6088225387a49", 1834, "step 0", "57c0c762de2ac72c0fdf3ff7c72bd684b3365b38b4b3ad4206a6eb389f6e91f2", 1], ["d24937d7b5d12ffcc2768c6c1f5c48d9510eb59f5bc9f13302c6e87353968c92", 1836, "step 1",

        self.registry_intermediary=[]
        #example of registry_intermediary
        #this list is used to ensure that the PoH loop is consistent between the input_data
        #[counter of 1st input_data, output_hash of the 1st input_data, counter of 2nd input_data,input_hash of the of 2nd input_data
        #[[1, "37ef796ef812992837f0ff1882d866aa92c38630b3eb36dbb97aa553d2112e02", 1834, "f95189a85a76f0115da4c38c3e6a2d3c1ee5be45a3498d3de3e6088225387a49", 1], [1834, "57c0c762de2ac72c0fdf3ff7c72bd
        self.e = threading.Event()
        self.log_in_registry(None,None)

        self.check1_flag=True
        self.check2_flag=True
        self.check3_flag=True

        self.end_loop_flag=False

        self.next_PoH_hash=None
        self.next_PoH_timestamp=None

        self.wip_flag=False
        self.wip_flag_processing=False


        #improvement to be made
        #make self.registry_intermediary from self.registry_input_data
        
    def launch_PoH(self):
        self.PoH_start_flag=True
        self.PoH_threading = threading.Thread(target=self.PoHloop, args=(self.e,))
        self.PoH_threading.start()
        #self.PoH_threading.join()
     
    def log_in_registry(self,input_data,input_data_counter):
        #this list is kept only on the memory
        self.registry.append([self.input_hash,self.counter,input_data,self.output_hash,input_data_counter])

    def log_in_registry_input_data(self,input_data,input_data_counter):
        #this list will be saved
        self.registry_input_data.append([self.input_hash,self.counter,input_data,self.output_hash,input_data_counter])

    def PoHloop(self,e):
        input_data=None
        input_data_counter=self.input_data_counter
        while e.is_set() is False:
            self.increment_PoH(input_data)
            self.log_in_registry(input_data,input_data_counter)
            if input_data is not None:
                self.log_in_registry_input_data(input_data,input_data_counter)
                #logging.info(f"counter: {self.counter} input_data:{input_data} input_hash: {self.input_hash} output_hash: {self.output_hash}")
                input_data=None
            else:
                if self.input_data_list!=[]:
                    input_raw_data=self.input_data_list.pop(0)
                    input_data=input_raw_data[0]
                    input_data_counter=input_raw_data[1]
                else:
                    input_data=None
                    input_data_counter=None
            #if self.counter>200000:
            #logging.info(f"##########===> PoHloop termination check1 {check_now} {type(check_now)} {self.previous_PoH_timestamp} {type(self.previous_PoH_timestamp)}")
            if self.wip_flag is False:
                self.wip()
            if self.check_termination() is True: 
                break

    def wip(self):
        '''this function is purging the backlog once a new block is received or 3 sec before termination'''
        from common.master_state_threading import master_state_threading
        check_now=datetime.timestamp(datetime.utcnow())
        check_before_end_PoH=check_now-self.previous_PoH_timestamp>self.PoH_DURATION_SEC-3
        check_block_receiving=master_state_threading.get_receiving_status()
        if check_before_end_PoH or check_block_receiving:
            #the transaction needs to be processed now live and not "in advance"
            self.wip_flag=True

            if check_before_end_PoH and master_state_threading.receiving_readiness_flag is False:
                #ensure that a block under receiving is fully received
                while master_state_threading.get_receiving_status is False:
                    pass
            else:
                #block the receiving of new block until reset after block creating and saving by leader node
                master_state_threading.receiving_readiness_flag=False

            
            #Purge Backlog
            from node.main import leader_node_advance_purge_backlog
            leader_node_advance_purge_backlog()

            #validate that the purge has been done to launch the processing of transaction 
            #and so block creation at the end of PoH
            self.wip_flag_processing=True
                

    def check_termination(self):
        '''this function is checking if the PoH is ended'''
        check_now=datetime.timestamp(datetime.utcnow())
        check=check_now-self.previous_PoH_timestamp>self.PoH_DURATION_SEC
        #logging.info(f"##########===> PoHloop termination check2 {check} check_now:{check_now} previous_PoH_timestamp:{self.previous_PoH_timestamp} check_now:{check_now-self.previous_PoH_timestamp}")
        if check and self.end_loop_flag is False:
            self.end_loop_flag=True

            #wait for the end of WIP
            while self.wip_flag_processing is False:
                pass

            logging.info('===> PoHloop termination')
            self.stop()
            #launch of the block creation
            self.PoW_memory.reload_blockchain()
            check_new_block_creation=self.PoW_memory.launch_new_block_creation()
            if check_new_block_creation is False:
                #the PoH needs to be stop and reset waiting for a new transaction
                self.end_loop_flag=False
                previous_previous_PoH_hash=self.previous_previous_PoH_hash
                self.reset("None",previous_previous_PoH_hash,datetime.timestamp(datetime.utcnow()))
                self.PoH_start_flag=False
        return check

    def increment_PoH(self,input_data):
        self.counter+=1
        self.input_hash=self.output_hash
        text_to_hash=self.input_hash+str(self.counter)+str(input_data)
        self.output_hash=sha256(text_to_hash.encode('utf-8')).hexdigest()

    def input(self,input_data):
        self.input_data_counter+=1
        self.input_data_list.append([input_data,self.input_data_counter])
        logging.info(f'input_data:{input_data} self.input_data_list:{self.input_data_list} ')
    
    def create_PoH_registry_last(self):
        #creation of the last transaction of the registry
        #to ensure that the last input_date is taken into account
        #this input date will be taken into account
        # as it will be the last "last part1" of create_PoH_registry_intermediary)
        self.input_data_counter+=1
        input_data="last"
        self.increment_PoH(input_data)
        self.log_in_registry(input_data,self.input_data_counter)

    def create_PoH_registry_intermediary(self):
        #creation of the last transaction of the registry
        self.create_PoH_registry_last()
        PoH_registry=self.registry
        PoH_registry_intermediary=[]
        part1=[PoH_registry[0][1],PoH_registry[0][3]]
        counter=0
        for i in range(1,len(PoH_registry)):
            counter+=1
            if PoH_registry[i][2]!=None or PoH_registry[i][1]!=part1[0]+counter and PoH_registry[i][1]!=part1[0]:
                part2=[PoH_registry[i][1],PoH_registry[i][0],PoH_registry[i][4]]
                part1.extend(part2)
                PoH_registry_intermediary.append(part1)
                part1=[PoH_registry[i][1],PoH_registry[i][3]]
                counter=0

        #logging.info(f" PoH_registry_intermediary: {self.registry_intermediary} {PoH_registry_intermediary}")
        self.registry_intermediary=PoH_registry_intermediary

        self.next_PoH_hash=self.registry_intermediary[-1][3]
        self.next_PoH_timestamp=datetime.timestamp(datetime.utcnow())
        

    def stop(self):
        self.e.set()
        self.create_PoH_registry_intermediary()


    def validate(self,PoH_registry,PoH_registry_intermediary):
        self.validate_PoH_registry(PoH_registry)
        self.validate_PoH_registry_intermediary(PoH_registry_intermediary)
        return self.get_validation_status()

    def get_validation_status(self):
        if self.check1_flag==False or self.check2_flag==False or self.check3_flag==False:return False
        else: return True

    def validate_PoH_registry(self,PoH_registry):
        start = time.time()
        pool = ThreadPool(4)

        #Check 1
        #Check of all the entries transaction in the PoH
        if 5==5:
            #check with multiprocessing
            results = pool.map(self.validate_PoH_registry_entry, PoH_registry)
            pool.close()
            pool.join()
        if 5==6:
            #check without multiprocessing
            for entry in PoH_registry:
                self.validate_PoH_registry_entry(entry)

        end = time.time()
        logging.info(f"CHECK 1 validate_PoH_registry_entry:{end-start} sec")

        #Check 2
        #Check of the input_data_counter of each entry to ensure that there is no missing entry
        start = time.time()
        check3_flag=self.validate_PoH_input_data_counter(PoH_registry)
        end = time.time()
        logging.info(f"CHECK 2 validate_PoH_input_data_counter:{end-start} sec")


    def validate_PoH_registry_intermediary(self,PoH_registry_intermediary):
        #Check 3
        #Check of all transaction between the entries in the PoH
        start = time.time()
        self.validate_PoH_registry_intermediary(PoH_registry_intermediary)
        end = time.time()
        logging.info(f"CHECK 3 validate_PoH_registry_intermediary:{end-start} sec")


    def validate_PoH_registry_entry(self,PoH_registry_entry):
        #logging.info(f"==PoH_registry_entry:{PoH_registry_entry} ")
        try:
            text_to_hash=PoH_registry_entry[0]+str(PoH_registry_entry[1])+str(PoH_registry_entry[2])
            test1=sha256(text_to_hash.encode('utf-8')).hexdigest()
            test2=PoH_registry_entry[3]
            assert test1== test2
        except AssertionError:
            logging.info(f" ERROR  PoH_registry_entry: {PoH_registry_entry}")
            logging.info(f" test1:{test1} test2:{test2} check: {test1== test2}")
            self.check1_flag=False

    def validate_PoH_registry_intermediary(self,PoH_registry_intermediary):
        if 5==5:
            #check with multiprocessing
            pool = ThreadPool(4)
            results = pool.map(self.validate_PoH_registry_intermediary_entry, PoH_registry_intermediary)
            pool.close()
            pool.join()
        if 5==6:
            #check without multiprocessing
            for entry in PoH_registry_intermediary:
                self.validate_PoH_registry_intermediary_entry(entry)



    def validate_PoH_registry_intermediary_entry(self,PoH_registry_intermediary_entry):
        input_hash=PoH_registry_intermediary_entry[1]
        input_data=None
        output_hash=PoH_registry_intermediary_entry[3]
        #logging.info(f"PoH_registry_intermediary_entry:{PoH_registry_intermediary_entry}")
        for i in range(PoH_registry_intermediary_entry[0]+1,PoH_registry_intermediary_entry[2]):
            text_to_hash=input_hash+str(i)+str(input_data)
            output_hash=sha256(text_to_hash.encode('utf-8')).hexdigest()
            input_hash=output_hash
        try:
            test1=PoH_registry_intermediary_entry[3]
            test2=output_hash
            assert test1== test2
        except AssertionError:
            logging.info(f" #####ERROR  PoH_registry_intermediary_entry: {PoH_registry_intermediary_entry}")
            logging.info(f" test1:{test1} test2:{test2} check: {test1== test2}")
            self.check2_flag=False


    def validate_PoH_input_data_counter(self,PoH_registry):
        #logging.info(f"==PoH_registry_entry:{PoH_registry} ")
        for i in range(0,len(PoH_registry)-1):
            try:
                assert PoH_registry[i][4]+1 == PoH_registry[i+1][4]
            except AssertionError:
                logging.info(f" $$$$$ ERROR  PoH_input_data_counter between: {PoH_registry[i][4]} and {PoH_registry[i+1][4]}")
                self.check3_flag=False