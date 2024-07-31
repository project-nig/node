import binascii

from Crypto.PublicKey import RSA

from common.utils import calculate_hash


class Owner:
    """
    Class to generate all the needed keys (private and public including hash and hex) or 
    to generate the hash and hex of the public key based a provided private key
    """
    def __init__(self, private_key: str = "", *args, **kwargs):
        if private_key:
            self.private_key = RSA.importKey(private_key)
        else:
            self.private_key = RSA.generate(2048)
        public_key = self.private_key.publickey().export_key("DER")
        self.public_key_hex = binascii.hexlify(public_key).decode("utf-8")
        self.public_key_hash = calculate_hash(calculate_hash(self.public_key_hex, hash_function="sha256"),
                                              hash_function="ripemd160")

        self.smart_contract=kwargs.get('smart_contract',None)
        
