import json
import random
import logging

from common.values import NETWORK_DEFAULT,DEFAULT_TRANSACTION_FEE_PERCENTAGE,INTERFACE_TRANSACTION_FEE_SHARE,NODE_TRANSACTION_FEE_SHARE,MINER_TRANSACTION_FEE_SHARE,ROUND_VALUE_DIGIT
from common.utils import calculate_hash,normal_round
from blockchain_users.node import public_key_hash as node_public_key_hash



class TransactionOutput:
    def __init__(self, list_public_key_hash: bytes, amount: float, *args, **kwargs):
        self.amount = normal_round(amount,ROUND_VALUE_DIGIT)
        from node.main import marketplace_owner
        account_temp=kwargs.get('account_temp',False)
        public_key_hash_str=list_public_key_hash[0]

        transfer_flag=kwargs.get('transfer_flag',False)
        marketplace_step=kwargs.get('marketplace_step',0)

        if account_temp is True or account_temp=="True" or account_temp=="true" or account_temp=="reputation_creation":
            #SmartContract transaction
            public_key_hash_str=''
            for public_key_hash in list_public_key_hash:
                public_key_hash_str+=" OP_SC "+public_key_hash
            self.locking_script = f"OP_DUP OP_HASH160 {marketplace_owner.public_key_hash} OP_EQUAL_VERIFY OP_CHECKSIG{public_key_hash_str}"
            if account_temp=="reputation_creation":self.locking_script+=" OP_RE"

            if marketplace_step==2:
                #in marketplace_step 2, the marketplace contract needs to be deassociated from the SmartContract
                self.locking_script+=" OP_DEL_SC "+marketplace_owner.public_key_hash

            if marketplace_step==99 or marketplace_step==98 or marketplace_step==66:
                #in marketplace_step 99, the marketplace request is cancelled so it needs to be archived
                #in marketplace_step 98, the marketplace request has expired so it needs to be archived
                #in marketplace_step 66, the marketplace request has a payment default so it needs to be archived
                self.locking_script+=" OP_DEL_SC "+marketplace_owner.public_key_hash
                for public_key_hash in list_public_key_hash:
                    self.locking_script+=" OP_DEL_SC "+public_key_hash
           
        else:
            self.locking_script = f"OP_DUP OP_HASH160 {public_key_hash_str} OP_EQUAL_VERIFY OP_CHECKSIG"
        self.account=kwargs.get('encrypted_account',None)
        

        #if marketplace_step == 0 or marketplace_step == 1:self.network="marketplace"
        #else:self.network=kwargs.get('network',NETWORK_DEFAULT)
        self.network=kwargs.get('network',NETWORK_DEFAULT)

        #transaction fee management
        if marketplace_step==4 or marketplace_step==45 or transfer_flag is True:
            self.transaction_fee_percentage=DEFAULT_TRANSACTION_FEE_PERCENTAGE
        else:
            self.transaction_fee_percentage=0
        self.interface_public_key_hash=kwargs.get('interface_public_key_hash',None)
        self.node_public_key_hash=node_public_key_hash
        coinbase_transaction=kwargs.get('coinbase_transaction',False)
        remaing_transaction=kwargs.get('remaing_transaction',False)
        self.marketplace_transaction_flag=kwargs.get('marketplace_transaction_flag',False)
        self.smart_contract_transaction_flag=kwargs.get('smart_contract_transaction_flag',False)
        

        #smart contract management
        self.smart_contract_flag=kwargs.get('smart_contract_flag',None)
        if self.smart_contract_flag is not None:
            self.smart_contract_sender=kwargs.get('smart_contract_sender',None)
            self.smart_contract_new=kwargs.get('smart_contract_new',False)
            self.smart_contract_account=kwargs.get('smart_contract_account',None)
            self.smart_contract_gas=kwargs.get('smart_contract_gas',None)
            self.smart_contract_memory=kwargs.get('smart_contract_memory',None)
            self.smart_contract_memory_size=kwargs.get('smart_contract_memory_size',None)
            self.smart_contract_type=kwargs.get('smart_contract_type',None)
            self.smart_contract_payload=kwargs.get('smart_contract_payload',None)
            self.smart_contract_result=kwargs.get('smart_contract_result',None)
            self.smart_contract_previous_transaction=kwargs.get('smart_contract_previous_transaction',None)

        if marketplace_step==4 or transfer_flag is True and coinbase_transaction is False and remaing_transaction is False:
            self.fee_node = normal_round(amount*(float(self.transaction_fee_percentage)/100)*float(NODE_TRANSACTION_FEE_SHARE)/100,ROUND_VALUE_DIGIT)
            self.fee_interface = normal_round(amount*(float(self.transaction_fee_percentage)/100)*float(INTERFACE_TRANSACTION_FEE_SHARE)/100,ROUND_VALUE_DIGIT)
            self.fee_miner = normal_round(amount*(float(self.transaction_fee_percentage)/100)*float(MINER_TRANSACTION_FEE_SHARE)/100,ROUND_VALUE_DIGIT)
            self.amount=normal_round(amount-self.fee_node-self.fee_interface-self.fee_miner,ROUND_VALUE_DIGIT)
        else:
            #only marketplace_step from 0 to 3 included are free
            self.fee_node = 0
            self.fee_interface = 0
            self.fee_miner = 0
            self.amount=normal_round(amount,ROUND_VALUE_DIGIT)

        
    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_dict(self) -> dict:
        if self.smart_contract_flag is not None:
            return {
                "amount": self.amount,
                "locking_script": self.locking_script,
                "network": self.network,
                "account": self.account,
                "interface_public_key_hash": self.interface_public_key_hash,
                "node_public_key_hash": self.node_public_key_hash,
                "fee_interface": self.fee_interface,
                "marketplace_transaction_flag":self.marketplace_transaction_flag,
                "smart_contract_transaction_flag":self.smart_contract_transaction_flag,
                "fee_node": self.fee_node,
                "fee_miner": self.fee_miner,
                "smart_contract_sender": self.smart_contract_sender,
                "smart_contract_new": self.smart_contract_new,
                "smart_contract_account": self.smart_contract_account,
                "smart_contract_flag": self.smart_contract_flag,
                "smart_contract_gas": self.smart_contract_gas,
                "smart_contract_memory": self.smart_contract_memory,
                "smart_contract_memory_size": self.smart_contract_memory_size,
                "smart_contract_type": self.smart_contract_type,
                "smart_contract_payload": self.smart_contract_payload,
                "smart_contract_result": self.smart_contract_result,
                "smart_contract_previous_transaction": self.smart_contract_previous_transaction}
        else:
            return {
                "amount": self.amount,
                "locking_script": self.locking_script,
                "network": self.network,
                "account": self.account,
                "interface_public_key_hash": self.interface_public_key_hash,
                "node_public_key_hash": self.node_public_key_hash,
                "fee_interface": self.fee_interface,
                "fee_node": self.fee_node,
                "fee_miner": self.fee_miner
            }

