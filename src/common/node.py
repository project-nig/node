import requests
import json

class Node:
    def __init__(self, hostname: str):
        self.hostname = hostname
        self.base_url = f"http://{hostname}/"

    def __eq__(self, other):
        return self.hostname == other.hostname

    @property
    def dict(self):
        return {
            "hostname": self.hostname
        }

    def post(self, endpoint: str, data: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        if data:
            req_return = requests.post(url, json=data)
        else:
            req_return = requests.post(url)
        req_return.raise_for_status()
        return req_return

    def get(self, endpoint: str, data: dict = None) -> list:
        url = f"{self.base_url}{endpoint}"
        if data:
            req_return = requests.get(url, json=data)
        else:
            req_return = requests.get(url)
        req_return.raise_for_status()
        return req_return.json()

    def advertise(self, hostname: str):
        data = {"hostname": hostname}
        return self.post(endpoint="new_node_advertisement", data=data)
    
    def advertise_leader_node_schedule(self, leader_node_schedule: list):
        for epoch in leader_node_schedule:
            for node_dic in epoch['LeaderNodeList']:
                for value in node_dic.keys():
                    if value=="node":
                        node_hostname_dic=node_dic[value].dict
                        node_dic[value]=node_hostname_dic
        data = {"leader_node_schedule": json.dumps(leader_node_schedule)}
        return self.post(endpoint="new_leader_node_schedule_advertisement", data=data)

    def known_node_request(self):
        return self.get(endpoint="known_node_request")

    def send_new_block(self, block: dict) -> requests.Response:
        return self.post(endpoint="block", data=block)

    def saving_new_block_leader_node(self, block: dict) -> requests.Response:
        return self.post(endpoint="block_saving_leader_node", data=block)

    def send_transaction(self, transaction_data: dict) -> requests.Response:
        return self.post("transactions", transaction_data)

    def send_transaction_to_leader_node(self, transaction_data: dict) -> requests.Response:
        return self.post("transactions_to_leader_node", transaction_data)
    
    def send_transaction_to_leader_node_advance(self, transaction_data: dict) -> requests.Response:
        return self.post("transactions_to_leader_node_advance", transaction_data)

    def get_blockchain(self) -> list:
        return self.get(endpoint="block")

    def restart(self):
        return self.get(endpoint="restart")

    def restart_request(self):
        return self.post(endpoint="restart_request")

    def restart_join(self):
        return self.post(endpoint="restart_join")

    def network_maintenance_on(self):
        return self.get(endpoint="maintenance_on")

    def network_maintenance_off(self):
        return self.get(endpoint="maintenance_off")

    def get_smart_contract_api(self, account: str) -> requests.Response:
        return self.post(endpoint=f"smart_contract_api/{account}", data=block)

 