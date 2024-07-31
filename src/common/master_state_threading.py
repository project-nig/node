import time

class MasterStateThreading:
    """
    Class to ensure that Threading transaction are processed only 
    once a new block has been well received,
    to ensure that a block is not created while another block is received,
    and to ensure that a block is not received while another block is created.
    """
    def __init__(self,*args, **kwargs):
        self.receiving_readiness_flag=True
        self.receiving_status=False
        self.receiving_start_time = None

    def get_receiving_status(self):
        if self.receiving_start_time is not None:
            if (time.time()-self.receiving_start_time)>60:
                #let's reset after 60 sec
                self.receiving_status=True
                self.receiving_readiness_flag=False
        return self.receiving_status

    def receiving_block(self):
        '''ensure that a block will be not created 
        during the receiving of Block
        '''
        self.receiving_readiness_flag=False
        self.receiving_start_time = time.time()

    def receiving_akn(self):
        '''aaknowledge the block receiving 
        and to launch the purge of the backlog 
        and the block creation
        '''
        self.receiving_status=True

    def receiving_reset(self):
        '''avoid blocking MasterStateThreading
        '''
        self.receiving_readiness_flag=True
        self.receiving_status=False
        self.receiving_start_time = None


master_state_threading=MasterStateThreading()
