import json
import logging
import os
import random

from common.node import Node
from common.values import LEADER_NODE_SCHEDULE_NB_SLOT


class LeaderNodeScheduleMemory:
    def __init__(self):
        #self.known_nodes_file = os.environ["KNOWN_NODES_DIR"]
        from node.main import LEADER_NODE_SCHEDULE_DIR
        self.leader_node_schedule_file=LEADER_NODE_SCHEDULE_DIR

    @property
    def leader_node_schedule(self) -> [Node]:
        with open(self.leader_node_schedule_file) as f:
            leader_node_schedule = json.load(f)
        for epoch in leader_node_schedule:
            for node_dic in epoch['LeaderNodeList']:
                for value in node_dic.keys():
                    if value=="node":
                        node_hostname=node_dic[value]['hostname']
                        node_dic[value]=Node(hostname=node_hostname)
        return leader_node_schedule
    @property
    def leader_node_schedule_json(self) -> [Node]:
        with open(self.leader_node_schedule_file) as f:
            leader_node_schedule = json.load(f)
        return leader_node_schedule

    @property
    def leader_nodes(self) -> [Node]:
        leader_node_schedule=self.leader_node_schedule
        return leader_node_schedule[0]
    
    def store_new_leader_node_schedule(self, leader_node_schedule_raw):
        import copy
        leader_node_schedule = copy.deepcopy(leader_node_schedule_raw)
        logging.info(f"Storing new leader node schedule")
        for epoch in leader_node_schedule:
            for node_dic in epoch['LeaderNodeList']:
                for value in node_dic.keys():
                    if value=="node":
                        #conversion of the node object into string
                        node=node_dic[value]
                        node_dic[value]=node.dict
        if leader_node_schedule!=[]:
            #leader_node_schedule_json=leader_node_schedule
            self.store_new_leader_node_schedule_json(leader_node_schedule)

    def store_new_leader_node_schedule_json(self, leader_node_schedule_json):
        #logging.info(f"Storing new leader node schedule json: {leader_node_schedule_json}")
        with open(self.leader_node_schedule_file, "w") as f:
            f.write(json.dumps(leader_node_schedule_json))

    def create_leader_node_schedule(self,known_nodes_of_known_node):
        logging.info(f"===========Creating new leader node schedule ")
        leader_node_schedule=[]
        for i in range(0,2):
            epoc_dic={'Epoch':i+1,
                      'PreviousEpoch':i,
                      'NextEpoch':i+2,
                      'FirstSlot':i*LEADER_NODE_SCHEDULE_NB_SLOT,
                      'LastSlot':(i+1)*LEADER_NODE_SCHEDULE_NB_SLOT-1,
                      'LeaderNodeList':[]}
            epoc_dic=self.create_LeaderNodeList(epoc_dic,known_nodes_of_known_node,i)
            leader_node_schedule.append(epoc_dic)

        if leader_node_schedule!=[]:self.store_new_leader_node_schedule(leader_node_schedule)

    def create_LeaderNodeList(self,epoc_dic,known_nodes_of_known_node,epoch_number):
        from node.main import NODE_TO_AVOID_HOSTNAME1,NODE_TO_AVOID_HOSTNAME3
        #patch to ensure that NODE_TO_AVOID_HOSTNAME3 is always first
        for k in range(0,len(known_nodes_of_known_node)):
            if known_nodes_of_known_node[k].dict==NODE_TO_AVOID_HOSTNAME3:
                leader_node_dic={}
                leader_node_dic['node']=known_nodes_of_known_node[k]
                leader_node_dic['slot']=epoch_number*LEADER_NODE_SCHEDULE_NB_SLOT
                leader_node_dic['already_processed']=False
                epoc_dic['LeaderNodeList'].append(leader_node_dic)
                break

        #patch to ensure  that there is no NODE_TO_AVOID_HOSTNAME1 and always different leader node 
        #to test transition between leader node
        count=1
        previous_leader_none=None
        for j in range(0,100000):
            pos=random.randint(0,len(known_nodes_of_known_node)-1)
            if previous_leader_none is None and known_nodes_of_known_node[pos].dict==NODE_TO_AVOID_HOSTNAME3:
                continue
            if known_nodes_of_known_node[pos].dict!=NODE_TO_AVOID_HOSTNAME1 and known_nodes_of_known_node[pos].dict!=previous_leader_none:
                leader_node_dic={}
                leader_node_dic['node']=known_nodes_of_known_node[pos]
                leader_node_dic['slot']=epoch_number*LEADER_NODE_SCHEDULE_NB_SLOT+count
                leader_node_dic['already_processed']=False
                epoc_dic['LeaderNodeList'].append(leader_node_dic)
                count+=1
                previous_leader_none=known_nodes_of_known_node[pos].dict
            if len(epoc_dic['LeaderNodeList'])>=LEADER_NODE_SCHEDULE_NB_SLOT:break
        #patch to ensure  that there is no NODE_TO_AVOID_HOSTNAME1
        if 5==6:
            count=1
            for j in range(0,100000):
                pos=random.randint(0,len(known_nodes_of_known_node)-1)
                if known_nodes_of_known_node[pos].dict!=NODE_TO_AVOID_HOSTNAME1:
                    leader_node_dic={}
                    leader_node_dic['node']=known_nodes_of_known_node[pos]
                    leader_node_dic['slot']=epoch_number*LEADER_NODE_SCHEDULE_NB_SLOT+count
                    leader_node_dic['already_processed']=False
                    epoc_dic['LeaderNodeList'].append(leader_node_dic)
                    count+=1
                if len(epoc_dic['LeaderNodeList'])>=LEADER_NODE_SCHEDULE_NB_SLOT:break

        #original code to include
        if 5==6:
            for j in range(0,LEADER_NODE_SCHEDULE_NB_SLOT):
                pos=random.randint(0,len(known_nodes_of_known_node)-1)
                leader_node_dic={}
                leader_node_dic['node']=known_nodes_of_known_node[pos]
                leader_node_dic['slot']=epoch_number*LEADER_NODE_SCHEDULE_NB_SLOT+j
                leader_node_dic['already_processed']=False
                epoc_dic['LeaderNodeList'].append(leader_node_dic)
        
        return epoc_dic
        
            

    def next_leader_node_schedule(self,known_nodes_of_known_node):
        #logging.info(f"===========###################$$$$$$$$$$$$$$$$$$ next_leader_node_schedule")
        leader_node_schedule=self.leader_node_schedule
        epoch=leader_node_schedule[0]
        update_flag=False
        for epoch in leader_node_schedule:
            node_dic_count=0
            node_dic_total=len(epoch['LeaderNodeList'])
            for node_dic in epoch['LeaderNodeList']:
                node_dic_count+=1
                #logging.info(f"===========###################$$$$$$$$$$$$$$$$$$ node_dic_count: {node_dic_count} node_dic_total:{node_dic_total}")
                if node_dic["already_processed"]==False:
                    if node_dic_count>=node_dic_total:
                        #let's add a new leader_node_schedule
                        self.add_new_leader_node_schedule(leader_node_schedule,known_nodes_of_known_node)
                    else:
                        #this is the current node
                        #let's switch to the next one
                        node_dic["already_processed"]=True
                    update_flag=True
                    break
            if update_flag is True:break
        #logging.info(f"===========###################$$$$$$$$$$$$$$$$$$ NEXT leader_node_schedule: {leader_node_schedule}")
        self.store_new_leader_node_schedule(leader_node_schedule)

    def add_new_leader_node_schedule(self,leader_node_schedule,known_nodes_of_known_node):
        logging.info(f"===========Add new leader node schedule ")
        leader_node_schedule.pop(0)
        previous_epoch=leader_node_schedule[0]['Epoch']
        epoc_dic={'Epoch':previous_epoch+1,
                  'PreviousEpoch':previous_epoch,
                  'NextEpoch':previous_epoch+2,
                  'FirstSlot':previous_epoch*LEADER_NODE_SCHEDULE_NB_SLOT,
                  'LastSlot':(previous_epoch+1)*LEADER_NODE_SCHEDULE_NB_SLOT-1,
                  'LeaderNodeList':[]}
        epoc_dic=self.create_LeaderNodeList(epoc_dic,known_nodes_of_known_node,previous_epoch+1)
        leader_node_schedule.append(epoc_dic)
        if leader_node_schedule!=[]:self.store_new_leader_node_schedule(leader_node_schedule)
        logging.info(f"Storing new leader node schedule json: {leader_node_schedule}")

