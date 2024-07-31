import logging

import requests

from common.initialize_default_blockchain import initialize_default_blockchain
from common.io_blockchain import BlockchainMemory
from common.io_known_nodes import KnownNodesMemory
from common.node import Node
from common.io_leader_node_schedule import LeaderNodeScheduleMemory
from wallet.wallet import Owner



class Network:
    """
    Class to connect the node to the NIG network when starting the node
    """
    
    def __init__(self, node: Node, init_known_nodes_file: bool = True):
        from common.values import FIRST_KNOWN_NODE_HOSTNAME_LIST
        self.FIRST_KNOWN_NODE_HOSTNAME_LIST=FIRST_KNOWN_NODE_HOSTNAME_LIST
        self.node = node
        self.blockchain_memory = BlockchainMemory()
        self.known_nodes_memory = KnownNodesMemory()
        self.leader_node_schedule_memory = LeaderNodeScheduleMemory()
        from blockchain_users.node_network import private_key as node_network_private_key
        self.node_network_account=Owner(node_network_private_key)
        self.init_known_nodes_file_flag=False
        if init_known_nodes_file and self.init_known_nodes_file_flag is False:
            self.initialize_known_nodes_file()

    def initialize_known_nodes_file(self):
        self.init_known_nodes_file_flag =True
        logging.info("Initializing known nodes file")
        initial_known_nodes_list=self.known_nodes_memory.return_known_nodes()
        for FIRST_KNOWN_NODE_HOSTNAME in self.FIRST_KNOWN_NODE_HOSTNAME_LIST:
            initial_known_node = Node(hostname=FIRST_KNOWN_NODE_HOSTNAME)
            if self.node.dict != initial_known_node.dict and initial_known_node.dict not in initial_known_nodes_list:
                initial_known_nodes_list.append(initial_known_node.dict)
        self.known_nodes_memory.store_known_nodes(initial_known_nodes_list)

    def advertise_to_all_known_nodes(self):
        logging.info("Advertising to all known nodes")
        for node in self.known_nodes_memory.known_nodes:
            if node.hostname != self.node.hostname:
                try:
                    node.advertise(self.node.hostname)
                except requests.exceptions.ConnectionError:
                    logging.info(f"Node not answering: {node.hostname}")
                except Exception as e:
                    logging.info(f"**** ISSUE Node not answering: {node.hostname}")
                    logging.exception(e)

    def advertise_leader_node_schedule_to_all_known_nodes(self):
        logging.info("Advertising to leader node schedule all known nodes")
        for node in self.known_nodes_memory.known_nodes:
            if node.hostname != self.node.hostname:
                try:
                    node.advertise_leader_node_schedule(self.leader_node_schedule_memory.leader_node_schedule)
                except requests.exceptions.ConnectionError:
                    logging.info(f"Node not answering: {node.hostname}")
                except Exception as e:
                    logging.info(f"**** ISSUE Node not answering: {node.hostname}")
                    logging.exception(e)

    def advertise_to_default_node(self) -> bool:
        for KNOWN_NODE_HOSTNAME in self.FIRST_KNOWN_NODE_HOSTNAME_LIST:
            default_node = Node(hostname=KNOWN_NODE_HOSTNAME)
            if default_node!= self.node:
                logging.info(f"Advertising to default node: {KNOWN_NODE_HOSTNAME}")
                try:
                    default_node.advertise(self.node.hostname)
                    logging.info(f"Default node {KNOWN_NODE_HOSTNAME} answered to advertising!")
                    return True
                except requests.exceptions.ConnectionError:
                    logging.info(f"Default node {KNOWN_NODE_HOSTNAME} not answering")
                except Exception as e:
                    logging.info(f"**** ISSUE Default Node not answering: {KNOWN_NODE_HOSTNAME}")
                    #logging.exception(e)
        return False

    def ask_known_nodes_for_their_known_nodes(self) -> list:
        logging.info("Asking known nodes for their own known nodes")
        known_nodes_of_known_nodes = []
        for currently_known_node in self.known_nodes_memory.known_nodes:
            if currently_known_node.hostname != self.node.hostname:
                try:
                    known_nodes_of_known_node = currently_known_node.known_node_request()
                    for node in known_nodes_of_known_node:
                        if Node(node["hostname"]) not in known_nodes_of_known_nodes:
                            known_nodes_of_known_nodes.append(Node(node["hostname"]))
                except requests.exceptions.ConnectionError:
                    logging.info(f"Node not answering: {currently_known_node.hostname}")
                except Exception as e:
                    logging.info(f"**** ISSUE Node not answering: {currently_known_node.hostname}")
                    logging.exception(e)
        return known_nodes_of_known_nodes

    def initialize_blockchain(self):
        blockchain_backlog_memory = BlockchainMemory(backlog_flag=True)
        blockchain_backlog_memory.setup_backlog_directory()
        longest_blockchain = self.get_longest_blockchain()
        self.blockchain_memory.store_blockchain_dict_in_memory(longest_blockchain)

    def get_longest_blockchain(self):
        logging.info("Retrieving the longest blockchain")
        longest_blockchain_size = 0
        longest_blockchain = None
        for node in self.known_nodes_memory.known_nodes:
            if node.hostname != self.node.hostname:
                try:
                    blockchain = node.get_blockchain()[::-1]
                    blockchain_length = len(blockchain)
                    if blockchain_length > longest_blockchain_size:
                        longest_blockchain_size = blockchain_length
                        longest_blockchain = blockchain
                except requests.exceptions.ConnectionError:
                    logging.info(f"Node not answering: {node.hostname}")
                except Exception as e:
                    logging.info(f"**** ISSUE Node not answering: {node.hostname}")
                    logging.exception(e)
        logging.info(f"Longest blockchain has a size of {longest_blockchain_size} blocks")
        return longest_blockchain

    def join_network(self,*args, **kwargs):
        logging.info("Joining network")
        reset_network = kwargs.get('reset_network',False)
        default_node_answered = self.advertise_to_default_node()
        if reset_network is False:
            if default_node_answered:
                self.initialize_blockchain()
                known_nodes_of_known_node = self.ask_known_nodes_for_their_known_nodes()
                self.known_nodes_memory.store_nodes(known_nodes_of_known_node)
                self.advertise_to_all_known_nodes()
                self.leader_node_schedule_memory.create_leader_node_schedule(known_nodes_of_known_node)
                self.advertise_leader_node_schedule_to_all_known_nodes()
            
            else:
                logging.info("Default node didn't answer. This could be caused by a network issue.")
                initialize_default_blockchain(self.blockchain_memory)

        else:initialize_default_blockchain(self.blockchain_memory)

    def return_known_nodes(self) -> []:
        return self.known_nodes_memory.return_known_nodes()
