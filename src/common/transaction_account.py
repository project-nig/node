import binascii, json, random
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
import logging


class TransactionAccount:
    def __init__(self, name: str, iban: str, bic: str, email: str, phone: str, country: str, public_key_hash: str, *args, **kwargs):
        self.name = name
        self.iban = iban
        self.bic = bic
        self.email = email
        self.phone = phone
        self.country = country
        self.public_key_hash = public_key_hash
        self.pin=kwargs.get('pin',random.randint(1000, 9999))

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    def to_json_part1(self) -> str:
        return json.dumps(self.to_dict_part1())
    def to_json_part2(self) -> str:
        return json.dumps(self.to_dict_part2())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "iban": self.iban,
            "bic": self.bic,
            "email": self.email,
            "phone": self.phone,
            "country": self.country,
            "public_key_hash": self.public_key_hash,
            "pin": self.pin
        }

    def to_dict_part1(self) -> dict:
        return {
            "iban": self.iban,
            "bic": self.bic,
            "email": self.email,
            "public_key_hash": self.public_key_hash,
        }
    def to_dict_part2(self) -> dict:
        return {
            "name": self.name,
            "phone": self.phone,
            "country": self.country,
            "pin": self.pin
        }

    def encrypt(self,requester_public_key_hex,sender_private_key):
        #Step 1 encryption of account with requester_public_key_hex
        key1 = RSA.importKey(binascii.unhexlify(requester_public_key_hex))
        cipher1 = Cipher_PKCS1_v1_5.new(key1)
        account_data_part1 = self.to_json_part1()
        account_data_part2 = self.to_json_part2()
        #Step 2 encryption of pin with sender_public_key_hex
        #key2 = RSA.importKey(binascii.unhexlify(sender_private_key))
        key2 = sender_private_key
        pin_data = self.pin
        cipher2 = Cipher_PKCS1_v1_5.new(key2)
        logging.info(f"============ PIN CODE: {self.pin}")
        return cipher1.encrypt(account_data_part1.encode()).hex()+" "+cipher1.encrypt(account_data_part2.encode()).hex()+" "+cipher2.encrypt(str(pin_data).encode()).hex()



def decrypt_account(account_encrypted_part1,account_encrypted_part2,private_key):
    #key = RSA.importKey(private_key)
    key = private_key
    decipher = Cipher_PKCS1_v1_5.new(key)
    account_decrypted_part1=decipher.decrypt(bytes.fromhex(account_encrypted_part1), None).decode()
    account_decrypted_data_part1 = json.loads(account_decrypted_part1.strip())
    account_decrypted_part2=decipher.decrypt(bytes.fromhex(account_encrypted_part2), None).decode()
    account_decrypted_data_part2 = json.loads(account_decrypted_part2.strip())
    return TransactionAccount(account_decrypted_data_part2['name'],
                              account_decrypted_data_part1['iban'],
                              account_decrypted_data_part1['bic'],
                              account_decrypted_data_part1['email'],
                              account_decrypted_data_part2['phone'],
                              account_decrypted_data_part2['country'],
                              account_decrypted_data_part1['public_key_hash'],
                              pin=account_decrypted_data_part2['pin'])

def decrypt_pin(pin_encrypted,private_key):
    key = RSA.importKey(private_key)
    decipher = Cipher_PKCS1_v1_5.new(key)
    pin_decrypted=decipher.decrypt(bytes.fromhex(pin_encrypted), None).decode()
    return pin_decrypted

if 5==6:
    def encrypt_request_proof(self,requester_public_key_hex,request_proof_to_encrypt):
        #Step 1 encryption of request_proof_to_encrypt with requester_public_key_hex
        key1 = RSA.importKey(binascii.unhexlify(requester_public_key_hex))
        cipher1 = Cipher_PKCS1_v1_5.new(key1)
        return cipher1.encrypt(request_proof_to_encrypt).hex()
    
        #signature
        transaction_dict = {"timestamp": self.timestamp,
                                "inputs": [tx_input.to_dict(with_unlocking_script=False) for tx_input in self.inputs],
                                "outputs": [tx_output.to_dict() for tx_output in self.outputs]}
        transaction_bytes = json.dumps(transaction_dict, indent=2).encode('utf-8')
        hash_object = SHA256.new(transaction_bytes)
        #signature = pkcs1_15.new(owner.private_key).sign(hash_object)
        signature = pkcs1_15.new(RSA.importKey(private_key)).sign(hash_object)
        return binascii.hexlify(signature).decode("utf-8")

        #validation of signature
        #signature_decoded = binascii.unhexlify(signature.encode("utf-8"))
        signature_decoded = binascii.unhexlify(test.encode("utf-8"))
        public_key_bytes = public_key.encode("utf-8")
        #public_key_object = RSA.import_key(binascii.unhexlify(public_key_bytes))
        public_key_object = RSA.import_key(binascii.unhexlify(public_key_hex))
        transaction_bytes = json.dumps(self.transaction_data, indent=2).encode('utf-8')
        import logging
        #logging.info(f"======check signature: self.transaction_data {self.transaction_data}")
        transaction_hash = SHA256.new(transaction_bytes)
        pkcs1_15.new(public_key_object).verify(transaction_hash, signature_decoded)

