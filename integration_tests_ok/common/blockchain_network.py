import os

from common.node import Node

NODE00_HOSTNAME = "127.0.0.1:5000"
NODE01_HOSTNAME = "127.0.0.2:5000"
NODE02_HOSTNAME = "127.0.0.3:5000"


class DefaultBlockchainNetwork:
    def __init__(self):
        self.node_list = [Node(NODE00_HOSTNAME), Node(NODE01_HOSTNAME), Node(NODE02_HOSTNAME)]

    def restart(self):
        self.node_list[0].restart()