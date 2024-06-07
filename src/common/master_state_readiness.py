#the purpose of this object is to ensure that there is only access to MasterState at the same time
# and so avoid contention especially for high frequency SmartContract like BlockVote
import time

class MasterStateReadiness:
    '''Object to ensure that MasterState is not udpate at the same time by 2 tasks
    '''
    def __init__(self,*args, **kwargs):
        self.readiness_flag=True
        self.start_time = None
        self.start_flag = False


    def block(self):
        '''to ensure that MasterState is not udpated at the same time by 2 tasks
        Return true if MasterState is free
        Otherwise False
        '''
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
        '''Reset to avoid blocking MasterState
        '''
        self.start_flag = False
        self.readiness_flag=True
        


master_state_readiness=MasterStateReadiness()