import json

from common.values import NETWORK_DEFAULT


class TransactionInput:
    """
    Class to display the input content of a transaction managed by Transaction class.
    """
    def __init__(self, transaction_hash: str, output_index: int, unlocking_script: str = "", unlocking_public_key_hash: str = "", *args, **kwargs):
        self.transaction_hash = transaction_hash
        self.output_index = output_index
        self.unlocking_script = unlocking_script
        self.unlocking_public_key_hash = unlocking_public_key_hash
        self.network=kwargs.get('network',NETWORK_DEFAULT)
        self.marketplace_flag=kwargs.get('marketplace_flag',False)

    def to_json(self, with_unlocking_script: bool = True) -> str:
        return json.dumps(self.to_dict(with_unlocking_script))

    def to_dict(self, with_unlocking_script: bool = True):
        if with_unlocking_script:
            return {
                "transaction_hash": self.transaction_hash,
                "output_index": self.output_index,
                "unlocking_script": self.unlocking_script,
                "unlocking_public_key_hash": self.unlocking_public_key_hash,
                "network": self.network
            }
        else:
            return {
                "transaction_hash": self.transaction_hash,
                "output_index": self.output_index,
                "unlocking_public_key_hash": self.unlocking_public_key_hash,
                "network": self.network
            }
