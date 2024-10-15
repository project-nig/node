import binascii
import json

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

from common.utils import calculate_hash,normal_round
from common.values import ROUND_VALUE_DIGIT


class Stack:
    def __init__(self):
        self.elements = []

    def push(self, element):
        self.elements.append(element)

    def pop(self):
        return self.elements.pop()


class StackScript(Stack):
    def __init__(self, transaction_data: dict):
        super().__init__()
        for count, tx_input in enumerate(transaction_data["inputs"]):
            tx_input.pop("unlocking_script")
            transaction_data["inputs"][count] = tx_input
        self.transaction_data = transaction_data

    def op_dup(self):
        try:
            last_element = self.pop()
            self.push(last_element)
            self.push(last_element)
        except Exception as e:
            #self.is_valid = True
            import logging
            logging.info(f"op_dup issue: {e}")

    def op_hash160(self):
        try:
            last_element = self.pop()
            self.push(calculate_hash(calculate_hash(last_element, hash_function="sha256"), hash_function="ripemd160"))
        except Exception as e:
            #self.is_valid = True
            import logging
            logging.info(f"op_hash160 issue: {e}")

    def op_equal_verify(self):
        try:
            last_element_1 = self.pop()
            last_element_2 = self.pop()
            assert last_element_1 == last_element_2
        except Exception as e:
            #self.is_valid = True
            import logging
            logging.info(f"&&&&&&& last_element_1: {last_element_1} last_element_2: {last_element_2} check:{last_element_1 == last_element_2}")
            logging.info(f"op_equal_verify issue: {e}")

    def op_checksig(self):
        try:
            public_key = self.pop()
            signature = self.pop()
            signature_decoded = binascii.unhexlify(signature.encode("utf-8"))
            public_key_bytes = public_key.encode("utf-8")
            public_key_object = RSA.import_key(binascii.unhexlify(public_key_bytes))
            transaction_bytes = json.dumps(self.transaction_data, indent=2).encode('utf-8')
            import logging
            logging.info(f"======check signature: self.transaction_data {self.transaction_data}")
            logging.info(f"======check signature_decoded: self.transaction_data {signature}")
            transaction_hash = SHA256.new(transaction_bytes)
            pkcs1_15.new(public_key_object).verify(transaction_hash, signature_decoded)
        except Exception as e:
            #self.is_valid = True
            logging.info(f"op_checksig issue: {e}")

    def op_account_temp(self):
        #nothing to do
        pass

    def mp_amount(self):
        #removal of public_key_hash
        last_element = self.pop()

    def mp_payref(self):
        #validation that the conversion rate of NIG in MP_CUR is valid
        from node.main import calculate_nig_rate
        MP_NIG_TIME  = float(self.pop())
        MP_NIG  = float(self.pop())
        MP_CUR  = self.pop()
        MP_AMOUNT  = float(self.pop())
        nig_rate=calculate_nig_rate(timestamp=MP_NIG_TIME,currency=MP_CUR)
        requested_nig=normal_round(MP_AMOUNT/nig_rate,ROUND_VALUE_DIGIT)
        import logging
        logging.info(f"&&&&&&& nig_rate: {nig_rate} requested_nig: {requested_nig} check:{requested_nig == MP_NIG}")
        assert requested_nig == MP_NIG

    def mp_marketplace_genesis(self):
        #nothing to do
        pass
    def mp_marketplace_step0(self):
        #nothing to do
        pass
    def mp_marketplace_step1(self):
        #nothing to do
        pass
    def mp_marketplace_step2(self):
        #nothing to do
        pass
    def mp_marketplace_step3(self):
        #nothing to do
        pass
    def mp_marketplace_step4(self):
        #nothing to do
        pass
    def mp_cur(self):
        #nothing to do
        pass
    def mp_nig(self):
        #nothing to do
        pass
    def mp_nig_time(self):
        #nothing to do
        pass
    def mp_public_key(self):
        #nothing to do
        pass

    def op_sc(self):
        #nothing to do
        pass

    def op_del_sc(self):
        #nothing to do
        pass

    def op_re(self):
        #nothing to do
        pass




