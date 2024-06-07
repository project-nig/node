
import threading
import logging
import time
import random

test={'a':0}

import time

class MasterStateReadiness:
    def __init__(self,*args, **kwargs):
        self.readiness_flag=True
        self.start_time = None
        self.start_flag = False


    def block(self):
        if self.start_flag is True:check_time=(time.time()-self.start_time)>5
        else:check_time=False
        if self.readiness_flag is True:
            #MasterState is ready, let's block MasterState
            self.readiness_flag=False
            self.start_flag = True
            self.start_time = time.time()
            return True
        elif check_time is True:
            #MasterState is blocked since more than 5 sec
            #let's release it as it's too long
            import logging
            logging.info("### release of MasterStateReadiness after 5 sec")
            self.release()
            return True
        else:
            #MasterState is not ready, let's wait for its readiness
            return False

    def release(self):
        self.start_flag = False
        self.readiness_flag=True

master_state_readiness=MasterStateReadiness()

class BlockMultiProcessing:
    def __init__(self,*args, **kwargs):
        self.e = threading.Event()

    def launch(self,data):
        print(f"data:{data}")
        self.PoH_threading = threading.Thread(target=self.start, args=(self.e,data))
        self.PoH_threading.start()
        self.PoH_threading.join()

    def start(self,e,data):
        while e.is_set() is False:
            Process_block(data)
            self.stop()
            break

    def stop(self):
        self.e.set()


def Process_block(*args, **kwargs):
     #let's block MasterState
    print(f"check:{test}")
    while master_state_readiness.block() is False:
        #let's wait until MasterState is release by another thread
        pass
    time.sleep(random.randrange(20)/100)
    #value=test['a']
    #value+=1
    #test['a']=value
    test['a']+=1
    #let's release MasterState
    master_state_readiness.release()


def main():
    
    for i in range(20):
        block_multiprocessing=BlockMultiProcessing()
        block_multiprocessing.launch(i)
        #print(f"test:{test}")
    print(f"test:{test}")

if __name__ == "__main__":
    main()