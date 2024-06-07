import binascii
import json
from datetime import datetime

from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15

from common.transaction_input import TransactionInput
from common.transaction_output import TransactionOutput
from common.utils import calculate_hash

import logging


class Transaction:
    def __init__(self, inputs: [TransactionInput], outputs: [TransactionOutput],*args, **kwargs):
        smart_contract_timestamp = kwargs.get('smart_contract_timestamp',None)
        if smart_contract_timestamp is None:self.timestamp = datetime.timestamp(datetime.utcnow())
        else:self.timestamp = smart_contract_timestamp
        self.inputs = inputs
        self.outputs = outputs
        self.transaction_hash = self.get_transaction_hash()

    def get_transaction_hash(self) -> str:
        #logging.info(f"===== self.inputs:{self.inputs}")
        transaction_data = {
            "timestamp": self.timestamp,
            "inputs": [i.to_dict() for i in self.inputs],
            "outputs": [i.to_dict() for i in self.outputs]
        }
        
        #logging.info(f"===== transaction_data:{transaction_data}")
        transaction_bytes = json.dumps(transaction_data, indent=2)
        return calculate_hash(transaction_bytes)

    def sign_transaction_data(self, owner):
        transaction_dict = {"timestamp": self.timestamp,
                            "inputs": [tx_input.to_dict(with_unlocking_script=False) for tx_input in self.inputs],
                            "outputs": [tx_output.to_dict() for tx_output in self.outputs]}
        transaction_bytes = json.dumps(transaction_dict, indent=2).encode('utf-8')
        hash_object = SHA256.new(transaction_bytes)
        signature = pkcs1_15.new(owner.private_key).sign(hash_object)
        #logging.info(f"===== transaction_dict:{transaction_dict}")
        #logging.info(f"===== signature:{binascii.hexlify(signature)}")
        return signature

    def sign(self, owner):
        signature_hex = binascii.hexlify(self.sign_transaction_data(owner)).decode("utf-8")
        for transaction_input in self.inputs:
            transaction_input.unlocking_script = f"{signature_hex} {owner.public_key_hex}"

    @property
    def transaction_data(self) -> dict:
        transaction_data = {
            "timestamp": self.timestamp,
            "inputs": [i.to_dict() for i in self.inputs],
            "outputs": [i.to_dict() for i in self.outputs],
            "transaction_hash": self.transaction_hash
        }
        return transaction_data




#from Crypto.Hash import SHA256
#from Crypto.Signature import pkcs1_15
#import json
#import binascii
#import Crypto.PublicKey.RSA as RSA


#transaction_bytes = json.dumps(transaction_data, indent=2).encode('utf-8')
#transaction_hash = SHA256.new(transaction_bytes)
#signature_hex = binascii.hexlify(pkcs1_15.new(RSA.importKey(private_key)).sign(transaction_hash)).decode("utf-8")



#pkcs1_15.new(public_key_object).verify(transaction_hash, binascii.unhexlify(signature_hex.encode("utf-8")))



#public_key="30820122300d06092a864886f70d01010105000382010f003082010a0282010100a1024da701411ea065119f40079b8e18b3f3546a9aacb4a5fd79a190cb052c5df8f469d00d659c9817a59a243bc781da15df5ed5cde52804556e283fa6205d1c76c290b332ed415236446ad12f56a7f2b06e64fd552372bc775f7ac2d1367ca79816ce010980a33a14b39522516e023e8a44d90d5ba9cfd3231b0a69efe9e82d74893d0420fb8bb7961ba0e5d04d697d98b9669e5c0dbcd80b9942d6e776e089fbb5cde7c1768458fc778b7421fdc0ebeb6e01c4b25f74def4c49b7fa7eacec582fd03054170d5ed6c23bf9d39b8affa104e24a522c162a7e201834462b4e5bd5530327bb614907358e75bb5234a122b460550710e178d030558a0d8e2d552830203010001"
#public_key_bytes = public_key.encode("utf-8")
#public_key_object = RSA.import_key(binascii.unhexlify(public_key_bytes))

#private_key = b'0\x82\x04\...