import json, logging, copy
from operator import itemgetter
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
import binascii
from datetime import datetime

from common.utils import calculate_hash,normal_round,convert_str_2_bool
from common.values import ROUND_VALUE_DIGIT,MARKETPLACE_STEP1_EXPIRATION,MARKETPLACE_STEP2_EXPIRATION,MARKETPLACE_STEP3_EXPIRATION,THRESHOLD0_TO_SALE_2_NEWUSER,THRESHOLD1_TO_SALE_2_NEWUSER,CHECK_SELLER_REPUTATION_FLAG_FOR_NEW_BUYER

from common.smart_contract_script import *

from common.master_state import MasterState


class BlockHeader:
    def __init__(self, previous_block_hash: str, current_PoH_hash: str, current_PoH_timestamp:str, previous_PoH_hash: str,timestamp: float, noonce: int, merkle_root: str, slot: int, leader_node_public_key_hash:str):
        self.previous_block_hash = previous_block_hash
        self.current_PoH_hash = current_PoH_hash
        self.current_PoH_timestamp = current_PoH_timestamp
        self.previous_PoH_hash = previous_PoH_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.noonce = noonce
        self.slot=slot
        self.leader_node_public_key_hash=leader_node_public_key_hash
        self.hash = self.get_hash()

    def __eq__(self, other):
        try:
            assert self.previous_block_hash == other.previous_block_hash
            assert self.current_PoH_hash == other.current_PoH_hash
            assert self.current_PoH_timestamp == other.current_PoH_timestamp
            assert self.previous_PoH_hash == other.previous_PoH_hash
            assert self.merkle_root == other.merkle_root
            assert self.timestamp == other.timestamp
            assert self.noonce == other.noonce
            assert self.slot == other.slot
            assert self.leader_node_public_key_hash == other.leader_node_public_key_hash
            assert self.hash == other.hash
            return True
        except AssertionError:
            return False

    def get_hash(self) -> str:
        header_data = {"previous_block_hash": self.previous_block_hash,
                       "current_PoH_hash": self.current_PoH_hash,
                       "current_PoH_timestamp": self.current_PoH_timestamp,
                       "previous_PoH_hash": self.previous_PoH_hash,
                       "merkle_root": self.merkle_root,
                       "timestamp": self.timestamp,
                       "noonce": self.noonce,
                       "slot": self.slot,
                       "leader_node_public_key_hash": self.leader_node_public_key_hash}
        return calculate_hash(json.dumps(header_data))

    @property
    def to_dict(self) -> dict:
        return {
            "previous_block_hash": self.previous_block_hash,
            "current_PoH_hash": self.current_PoH_hash,
            "current_PoH_timestamp": self.current_PoH_timestamp,
            "previous_PoH_hash": self.previous_PoH_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "noonce": self.noonce,
            "slot": self.slot,
            "leader_node_public_key_hash": self.leader_node_public_key_hash,
        }

    def __str__(self):
        return json.dumps(self.to_dict)

    @property
    def to_json(self) -> str:
        return json.dumps(self.to_dict)

class BlockPoH:
    def __init__(self, PoH_registry_input_data:str, PoH_registry_intermediary:str):
        self.PoH_registry_input_data=PoH_registry_input_data
        self.PoH_registry_intermediary=PoH_registry_intermediary

    def __eq__(self, other):
        try:
            assert self.PoH_registry_input_data == other.PoH_registry_input_data
            assert self.PoH_registry_intermediary == other.PoH_registry_intermediary
            return True
        except AssertionError:
            return False

    @property
    def to_dict(self) -> dict:
        return {
            "PoH_registry_input_data": self.PoH_registry_input_data,
            "PoH_registry_intermediary":self.PoH_registry_intermediary,
        }

    def __str__(self):
        return json.dumps(self.to_dict)


class Block:
    def __init__(
            self,
            transactions: [dict],
            block_header: BlockHeader,
            block_PoH: BlockPoH,
            previous_block=None,
            block_signature=None,
            *args, **kwargs,
    ):
        self.block_header = block_header
        self.block_PoH = block_PoH
        self.block_signature = block_signature
        self.transactions = transactions
        self.previous_block = previous_block
        self.master_state=MasterState()

    def __eq__(self, other):
        try:
            assert self.block_header == other.block_header
            assert self.block_PoH == other.block_PoH
            assert self.block_signature == other.block_signature
            assert self.transactions == other.transactions
            return True
        except AssertionError:
            return False

    def __len__(self) -> int:
        i = 1
        current_block = self
        while current_block.previous_block:
            i = i + 1
            current_block = current_block.previous_block
        return i

    def __str__(self):
        return json.dumps({"timestamp": self.block_header.timestamp,
                           "hash": self.block_header.hash,
                           "transactions": self.transactions})

    @property
    def to_dict(self):
        block_list = []
        current_block = self
        while current_block:
            block_data = {
                "header": current_block.block_header.to_dict,
                "PoH": current_block.block_PoH.to_dict,
                "signature": current_block.block_signature,
                "transactions": current_block.transactions
            }
            block_list.append(block_data)
            current_block = current_block.previous_block
        return block_list[::-1]


    @property
    def to_json(self) -> str:
        return json.dumps(self.to_dict)

    @property
    def data(self):
        block_data = {
            "header": self.block_header.to_dict,
            "PoH": self.block_PoH.to_dict,
            "signature": self.block_signature,
            "transactions": self.transactions
        }
        return block_data

    def signature_data(self):
        block_data = {
            "header": self.block_header.to_dict,
            "PoH": self.block_PoH.to_dict,
            "transactions": self.transactions
        }
        #logging.info(f"===== signature block_data:{block_data}")
        return block_data

    def signature_hash(self):
        block_bytes = json.dumps(self.signature_data(), indent=2).encode('utf-8')
        hash_object = SHA256.new(block_bytes)
        logging.info(f"===== signature_hash:{hash_object.hexdigest()}")
        return hash_object

    def sign_block(self, owner):        
        signature = pkcs1_15.new(owner.private_key).sign(self.signature_hash())
        logging.info(f"===== signature:{binascii.hexlify(signature)}")
        self.block_signature=binascii.hexlify(signature).decode("utf-8")
        

    def get_transaction(self, transaction_hash: dict) -> dict:
        current_block = self
        while True:
            for transaction in current_block.transactions:
                try:
                    if transaction["transaction_hash"] == transaction_hash:
                        return transaction
                except Exception as e:
                    #issue with new block creation / Miner
                    logging.info(f"get_transaction Exception: {e}")
                    logging.exception(e)
                    break
            current_block = current_block.previous_block
            if current_block is None:break
        return {}

    def get_user_utxos_raw(self, user: str, *args, **kwargs) -> dict:
        payment_ref=kwargs.get('payment_ref',None)
        return_dict = {
            "user": user,
            "total": 0,
            "utxos": []
        }
        #1st loop to search for all UTXOS
        current_block = self
        while current_block.previous_block:
            for transaction in current_block.transactions:
                output_index=0
                for output in transaction["outputs"]:
                    locking_script = output["locking_script"]
                    for element in locking_script.split(" "):
                        if not element.startswith("OP") and element == user:
                            if 'OP_ACCOUNT_TEMP' in locking_script:
                                #transaction to the temporary account
                                account_temp=True
                            else:account_temp=False

                            #only if needed, included only the requested payment_ref
                            check_payment_flag=True
                            if payment_ref is not None:
                                check_payment_flag=False
                                for i in range (1,len(locking_script.split(" "))):
                                    if locking_script.split(" ")[i]=="MP_PAYREF":
                                        t=locking_script.split(" ")[i+1]
                                        check=locking_script.split(" ")[i+1]==payment_ref
                                        transaction_hash2=transaction["transaction_hash"]
                                        logging.info(f"payment_ref {payment_ref} value {t} check{check} transaction_hash: {transaction_hash2}")
                                        if locking_script.split(" ")[i+1]==payment_ref:
                                            #this is the requested payment_ref
                                            check_payment_flag=True
                                        break
                            if check_payment_flag is True:
                                return_dict["utxos"].append(
                                    {
                                        "amount": output["amount"],
                                        "transaction_hash": transaction["transaction_hash"],
                                        "output_index":output_index,
                                        "account_temp":account_temp,
                                        "interface_public_key_hash": output["interface_public_key_hash"],
                                        "node_public_key_hash": output["node_public_key_hash"],
                                        "fee_interface": output["fee_interface"],
                                        "fee_node": output["fee_node"],
                                        "fee_miner": output["fee_miner"],
                                    }
                                    )
                                #logging.info(return_dict["utxos"])
                        elif element.startswith("MP"):
                            #first operation of the Marketplace, no need to go further
                            break
                    output_index+=1
            current_block = current_block.previous_block

        #2nd loop to search for all unspent UTXOS
        current_block = self
        utxos_text=str(return_dict["utxos"])
        while current_block.previous_block:
            for transaction in current_block.transactions:
                #logging.info(f"transaction: {transaction}")
                try:
                    transaction_hash=transaction["inputs"][0]['transaction_hash']
                    output_index=transaction["inputs"][0]['output_index']
                    if transaction_hash in utxos_text:
                        #the utxos is already used
                        for utxos_elem in return_dict["utxos"]:
                            if transaction_hash==utxos_elem["transaction_hash"] and output_index==utxos_elem["output_index"]:
                                return_dict["utxos"].remove(utxos_elem)
                except:
                    #in case of BlockReward input=[]
                    pass
                    
            current_block = current_block.previous_block

        #3rd loop to calculate the total
        for utxos_elem in return_dict["utxos"]:
            return_dict["total"] = return_dict["total"] + utxos_elem["amount"]

        return_dict["total"]=normal_round(return_dict["total"],ROUND_VALUE_DIGIT)
        return return_dict

    def get_user_all_utxos(self, user: str) -> dict:
        return_dict = {
            "user": user,
            "total": 0,
            "utxos": []
        }
        current_block = self
        while current_block.previous_block:
            for transaction in current_block.transactions:
                output_index=0
                for output in transaction["outputs"]:
                    locking_script = output["locking_script"]
                    for element in locking_script.split(" "):
                        if not element.startswith("OP") and element == user:
                            if 'OP_ACCOUNT_TEMP' in locking_script:
                                #transaction to the temporary account
                                account_temp=True
                            else:account_temp=False
                            return_dict["total"] = return_dict["total"] + output["amount"]
                            return_dict["utxos"].append(
                                {
                                    "amount": normal_round(output["amount"],ROUND_VALUE_DIGIT),
                                    "transaction_hash": transaction["transaction_hash"],
                                    "output_index":output_index,
                                    "account_temp":str(account_temp),
                                    "interface_public_key_hash": output["interface_public_key_hash"],
                                    "node_public_key_hash": output["node_public_key_hash"],
                                    "fee_interface": output["fee_interface"],
                                    "fee_node": output["fee_node"],
                                    "fee_miner": output["fee_miner"],
                                }
                            )
                            logging.info(f"============ return_dict: {return_dict}")
                        elif element.startswith("MP"):
                            #first operation of the Marketplace, no need to go further
                            break
                    output_index+=1
            current_block = current_block.previous_block
        return return_dict

    def get_user_utxos(self, user: str) -> dict:
        self.master_state.get_master_state_from_memory_from_user(user)
        return_dict={}
        try:
            return_dict=copy.deepcopy(self.master_state.current_master_state[user])
            return_dict['user']=user
            return_dict.pop('balance')
            return_dict['total']=normal_round(return_dict['total'],ROUND_VALUE_DIGIT)
            from node.main import calculate_nig_rate
            return_dict['total_euro']=normal_round(return_dict['total']*calculate_nig_rate(),ROUND_VALUE_DIGIT)
            index=0
            logging.info(f"return_dict['utxos']:{return_dict['utxos']}")
            for utxo in return_dict['utxos']:
                return_dict['utxos'][index]=self.master_state.current_master_state[user]['utxos_data'][utxo]['output']
                return_dict['utxos'][index].pop('account_list')
                index+=1
            return_dict.pop('utxos_data')
            try:marketplace_total_debit_eur=return_dict['marketplace_profit_details']['EUR']['debit']
            except:marketplace_total_debit_eur=0
            try:marketplace_total_credit_eur=return_dict['marketplace_profit_details']['EUR']['credit']
            except:marketplace_total_credit_eur=0
            try:mp_total_debit=return_dict['marketplace_profit_details']['EUR']['debit_nig']
            except:mp_total_debit=0
            try:mp_total_credit=return_dict['marketplace_profit_details']['EUR']['credit_nig']
            except:mp_total_credit=0
            mp_total_debit_EUR=normal_round(mp_total_debit*calculate_nig_rate(),ROUND_VALUE_DIGIT)
            mp_total_credit_EUR=normal_round(mp_total_credit*calculate_nig_rate(),ROUND_VALUE_DIGIT)
            
            return_dict['marketplace_total_debit_eur']=float(marketplace_total_debit_eur)
            return_dict['marketplace_total_credit_eur']=float(marketplace_total_credit_eur)
            #return_dict['marketplace_profit']=normal_round(return_dict['total_euro']-(marketplace_total_credit_eur-marketplace_total_debit_eur),ROUND_VALUE_DIGIT)
            return_dict['marketplace_profit']=normal_round(mp_total_credit_EUR-(marketplace_total_credit_eur-marketplace_total_debit_eur),ROUND_VALUE_DIGIT)

        except Exception as e:
            return_dict['total']=float(0)
            return_dict['total_euro']=float(0)
            return_dict['utxos']=[]
            return_dict['user']=user
            return_dict['marketplace_profit']=float(0)
            return_dict['marketplace_total_debit_eur']=float(0)
            return_dict['marketplace_total_credit_eur']=float(0)
            return_dict['marketplace']=[]
            return_dict['marketplace_archive']=[]
            return_dict['reputation']=[]
            return_dict['smart_contract']=[]
            logging.info(f"ERROR get_user_utxos Exception: {e}")
            logging.exception(e)
        return return_dict

    def get_smart_contract_api(self, account: str, *args, **kwargs) -> dict:
        smart_contract_transaction_hash=kwargs.get('smart_contract_transaction_hash',None)
        block_PoH = kwargs.get('block_PoH',None)
        self.master_state.get_master_state_from_memory_from_user(account,block_PoH=block_PoH)
        return_dict={}
        #try:
        return_dict=copy.deepcopy(self.master_state.current_master_state[account])
        #logging.info(f" get_smart_contract_api return_dict['utxos']:{return_dict['utxos']}")
        check_contrac_flag=False       
       
        #step 1 check on credit of the balance
        for transaction in return_dict['balance']['credit']:
            key_list=return_dict['balance']['credit'][transaction].keys()
            for key in key_list:
                if key.startswith('smart_contract') is True:
                    return_dict[key]=return_dict['balance']['credit'][transaction][key]
                    if smart_contract_transaction_hash is not None:
                        if smart_contract_transaction_hash in transaction:
                            #transaction # has "_0" or "_1" in the end
                            return_dict['smart_contract_previous_transaction']=return_dict['balance']['credit'][transaction]['smart_contract_previous_transaction']
                            return_dict['smart_contract_transaction_hash']=return_dict['balance']['credit'][transaction]['transaction_hash']+'_'+str(return_dict['balance']['credit'][transaction]['output_index'])
                            #this is the last transaction with source code
                            check_contrac_flag=True
                    else:
                        return_dict['smart_contract_previous_transaction']=return_dict['balance']['credit'][transaction]['smart_contract_previous_transaction']
                        return_dict['smart_contract_transaction_hash']=return_dict['balance']['credit'][transaction]['transaction_hash']+'_'+str(return_dict['balance']['credit'][transaction]['output_index'])
                        #this is the last transaction with source code
               

            if check_contrac_flag is True:
                #only the first transaction is taken into account
                break

        return_dict.pop('balance')
        return_dict.pop('utxos')
        return_dict.pop('utxos_data')
        #return_dict.pop('total')
        #except Exception as e:
        #    return_dict['total']=float(0)
        #    return_dict['utxos']=[]
        #    return_dict['account']=account
        #    logging.info(f"ERROR get_smart_contract_api Exception: {e}")
        #    logging.exception(e)
        return return_dict

    def get_user_utxos_balance(self, user: str) -> dict:
        self.master_state.get_master_state_from_memory_from_user(user)
        from node.main import calculate_nig_rate
        #logging.info(f"self.current_master_state[user]:{self.master_state.current_master_state[user]}")
        return_dict_balance = {
                "user": user,
                "mp_total_credit": 0,
                "mp_total_debit": 0,
                "marketplace_total_credit_eur": 0,
                "marketplace_total_debit_eur": 0,        
                "mp_score":0,
                "marketplace_profit":0,
                "utxos": []
            }
        try:
            return_dict=copy.deepcopy(self.master_state.current_master_state[user])
            return_dict_balance['total_euro']=normal_round(return_dict['total']*calculate_nig_rate(),ROUND_VALUE_DIGIT)

            try:return_dict_balance['marketplace_total_debit_eur']=return_dict['marketplace_profit_details']['EUR']['debit']
            except:pass
            try:return_dict_balance['marketplace_total_credit_eur']=return_dict['marketplace_profit_details']['EUR']['credit']
            except:pass
            try:return_dict_balance['mp_total_debit']=return_dict['marketplace_profit_details']['EUR']['debit_nig']
            except:pass
            try:return_dict_balance['mp_total_credit']=return_dict['marketplace_profit_details']['EUR']['credit_nig']
            except:pass
            mp_total_debit_EUR=normal_round(return_dict_balance['mp_total_debit']*calculate_nig_rate(),ROUND_VALUE_DIGIT)
            #logging.info(f"====>mp_total_debit_EUR:{mp_total_debit_EUR}")
            mp_total_credit_EUR=normal_round(return_dict_balance['mp_total_credit']*calculate_nig_rate(),ROUND_VALUE_DIGIT)
            #logging.info(f"====>mp_total_credit_EUR:{mp_total_credit_EUR}")
            mp_total_total_EUR=mp_total_credit_EUR-mp_total_debit_EUR
            #logging.info(f"====>mp_total_total_EUR:{mp_total_total_EUR}")
            return_dict_balance['marketplace_profit']=normal_round(mp_total_total_EUR-(return_dict_balance['marketplace_total_credit_eur']-return_dict_balance['marketplace_total_debit_eur']),ROUND_VALUE_DIGIT)
            #return_dict_balance['marketplace_profit']=normal_round(return_dict_balance['total_euro']-(return_dict_balance['marketplace_total_credit_eur']-return_dict_balance['marketplace_total_debit_eur']),ROUND_VALUE_DIGIT)

            total_credit=0
            total_credit_eur=0
            total_debit=0
            total_debit_eur=0

            for utxo in return_dict['balance']['credit'].keys():
                return_dict['balance']['credit'][utxo]['balance']='credit'
                try:
                    #issue to manage with BlockVote
                    return_dict['balance']['credit'][utxo]['user']=return_dict['balance']['credit'][utxo]['account_credit_list'][0]
                except:pass
                total_credit+=return_dict['balance']['credit'][utxo]['amount']
                total_credit_eur+=return_dict['balance']['credit'][utxo]['amount']*calculate_nig_rate(timestamp=return_dict['balance']['credit'][utxo]['timestamp'])
                return_dict_balance['utxos'].append(return_dict['balance']['credit'][utxo])

            for utxo in return_dict['balance']['debit'].keys():
                logging.info(f"****INFO utxo user: {utxo}")
                return_dict['balance']['debit'][utxo]['balance']='debit'
                return_dict['balance']['debit'][utxo]['user']=return_dict['balance']['debit'][utxo]['account_credit_list'][0]
                total_debit+=return_dict['balance']['debit'][utxo]['amount']
                total_debit_eur+=return_dict['balance']['debit'][utxo]['amount']*calculate_nig_rate(timestamp=return_dict['balance']['debit'][utxo]['timestamp'])
                return_dict_balance['utxos'].append(return_dict['balance']['debit'][utxo])

            return_dict_balance_utxos_sorted = sorted(return_dict_balance['utxos'], key=itemgetter('timestamp'), reverse=True)
            return_dict_balance['utxos']=return_dict_balance_utxos_sorted

            score_profit=return_dict_balance['total_euro']+(total_credit_eur-total_debit_eur)
            return_dict_balance['mp_score']=int(round(score_profit*total_debit_eur, 0)/10000)
        except Exception as e:
            logging.info(f"****INFO user_utxos_balance user: {user}")
            logging.exception(e)
        return return_dict_balance


    def get_user_utxos_account_temp(self, user: str, *args, **kwargs) -> dict:
        payment_ref=kwargs.get('payment_ref',None)
        return_dict=self.get_user_utxos_raw(user,payment_ref=payment_ref)
        return_dict["total"]=0
        utxos_elem_2_del=[]
        for utxos_elem in return_dict["utxos"]:
            logging.info(f" utxos_elem: {utxos_elem}")
            if utxos_elem['account_temp'] is False:
                utxos_elem_2_del.append(utxos_elem)
            else:
                return_dict["total"] = return_dict["total"] + utxos_elem["amount"]
        for utxos_elem in utxos_elem_2_del:return_dict["utxos"].remove(utxos_elem)
        return_dict["total"]=normal_round(return_dict["total"],ROUND_VALUE_DIGIT)
        return return_dict


    def get_transaction_from_utxo(self,utxo_unlocking_public_key_hash:str, utxo_hash: str, output_index : str,*args, **kwargs):
        NIGthreading_flag=kwargs.get('NIGthreading_flag',False)
        if '_' in utxo_hash:utxo_key=str(utxo_hash)
        else:utxo_key=str(utxo_hash)+'_'+str(output_index)
        self.master_state.get_master_state_from_memory_from_user(utxo_unlocking_public_key_hash,NIGthreading_flag=NIGthreading_flag)
        try:
            return self.master_state.current_master_state[utxo_unlocking_public_key_hash]['utxos_data'][utxo_key]
        except:
            #there is no Transaction for this utxo_unlocking_public_key_hash
            logging.info(f"ERROR no Transaction for utxo_unlocking_public_key_hash: {utxo_unlocking_public_key_hash} utxo_key:{utxo_key} ")

    def get_transaction_from_utxo_old(self,utxo_unlocking_public_key_hash:str, utxo_hash: str, output_index : str) -> dict:
        utxo_key0=str(utxo_hash)+'_'+str(0)
        utxo_key1=str(utxo_hash)+'_'+str(1)
        utxo_key2=str(utxo_hash)+'_'+str(2)
        utxo_key3=str(utxo_hash)+'_'+str(3)
        logging.info(f"utxo_key0:{utxo_key0} utxo_key1:{utxo_key1} utxo_key2:{utxo_key2} utxo_key3:{utxo_key3}")
        self.master_state.get_master_state_from_memory_from_user(utxo_unlocking_public_key_hash)

        try:
            return self.master_state.current_master_state[utxo_unlocking_public_key_hash]['utxos_data'][utxo_key0]
        except:
            try:
                 return self.master_state.current_master_state[utxo_unlocking_public_key_hash]['utxos_data'][utxo_key1]
            except:
                try:
                    return self.master_state.current_master_state[utxo_unlocking_public_key_hash]['utxos_data'][utxo_key2]
                except:
                    try:
                         return self.master_state.current_master_state[utxo_unlocking_public_key_hash]['utxos_data'][utxo_key3]
                    except:
                        #there is no Transaction for this utxo_unlocking_public_key_hash
                        logging.info(f"ERROR no Transaction for utxo_unlocking_public_key_hash: {utxo_unlocking_public_key_hash} utxo_hash:{utxo_hash}")

       
       

    def get_locking_script_from_utxo_new(self,utxo_unlocking_public_key_hash:str, utxo_hash: str):
        #utxo_key=str(utxo_hash)+'_'+str(utxo_index)
        utxo_key=str(utxo_hash)
        self.master_state.get_master_state_from_memory_from_user(utxo_unlocking_public_key_hash,leader_node_flag=True)
        return self.master_state.current_master_state[utxo_unlocking_public_key_hash]['utxos_data'][utxo_key]['output']['locking_script']

    def get_locking_script_from_utxo(self,utxo_unlocking_public_key_hash:str, utxo_hash: str, utxo_index: int,*args, **kwargs):
        NIGthreading_flag=kwargs.get('NIGthreading_flag',False)
        if '_' in utxo_hash:utxo_key=str(utxo_hash)
        else:utxo_key=str(utxo_hash)+'_'+str(utxo_index)
        self.master_state.get_master_state_from_memory_from_user(utxo_unlocking_public_key_hash,leader_node_flag=True,NIGthreading_flag=NIGthreading_flag)
        return self.master_state.current_master_state[utxo_unlocking_public_key_hash]['utxos_data'][utxo_key]['output']['locking_script']




    def get_followup_step4_pin(self,user_public_key_hash,payment_ref):
        return_list=self.get_marketplace_step_raw(3,user_public_key_hash,followup_step4_pin_flag=True)
        pin_encrypted=None
        logging.info(f"return_list: {return_list}")
        for elem in return_list:
            if elem['payment_ref']==payment_ref:
                pin_encrypted=elem["encrypted_account"].split(" ")[2]
                break
        return pin_encrypted

    def get_marketplace_step(self,marketplace_step,user_public_key_hash, *args, **kwargs):
        return_list=self.get_marketplace_step_raw(marketplace_step,user_public_key_hash, *args, **kwargs)
        return {"results":return_list}


    def get_marketplace_step_raw(self,marketplace_step_raw,user_public_key_hash, *args, **kwargs):
        step2_amount=kwargs.get('amount',None)
        archive_flag=kwargs.get('archive_flag',False)
        archive_timestamp=kwargs.get('archive_timestamp',False)
        if step2_amount is not None:step2_amount=float(step2_amount)
        ####SMART CONTRACT
        try:marketplace_step=int(marketplace_step_raw)
        except:marketplace_step=0
        from common.values import MY_HOSTNAME
        from blockchain_users.marketplace import private_key as marketplace_private_key
        from blockchain_users.marketplace import public_key_hash as marketplace_public_key
        from common.node import Node
        from wallet.wallet import Owner, Wallet
        smart_contract_owner=Owner(private_key=marketplace_private_key)
        smart_contract_wallet = Wallet(smart_contract_owner,Node(MY_HOSTNAME))

        from common.smart_contract import SmartContract,check_smart_contract,load_smart_contract
        return_list=[]
       
        from common.io_blockchain import BlockchainMemory
        blockchain_memory = BlockchainMemory()
        blockchain_base = blockchain_memory.get_blockchain_from_memory()

        if CHECK_SELLER_REPUTATION_FLAG_FOR_NEW_BUYER is True:sell_to_new_user_flag=False
        else:sell_to_new_user_flag=True
        logging.info(f"### Check sell_to_new_user_flag:{sell_to_new_user_flag}")
        if marketplace_step==1:
            user_utxos=blockchain_base.get_user_utxos(marketplace_public_key)
            if CHECK_SELLER_REPUTATION_FLAG_FOR_NEW_BUYER is True:
                logging.info(f"### Check  seller reputation for marketplace_step 1")
                #let's check the reputation of this user to check if he can sell to new user or not
                check_user_utxos=blockchain_base.get_user_utxos(user_public_key_hash)
                try:
                    reputation_public_key_hash=check_user_utxos['reputation']
                    payload=f'''
memory_obj_2_load=['reputation']
reputation.get_reputation()
'''
                    smart_contract=SmartContract(reputation_public_key_hash,
                                                 smart_contract_sender='sender_public_key_hash',
                                                 smart_contract_type="api",
                                                 payload=payload)
                    smart_contract.process()
                    reputation=smart_contract.result
                    if reputation[0]>THRESHOLD0_TO_SALE_2_NEWUSER and reputation[1]>THRESHOLD1_TO_SALE_2_NEWUSER:
                        #This user is allowed to sell to new user
                        sell_to_new_user_flag=True
                except Exception as e:
                    logging.info(f"###ERROR checking reputation of user_public_key_hash:{user_public_key_hash} exception: {e}")

        else:user_utxos=blockchain_base.get_user_utxos(user_public_key_hash)
        logging.info(f"### user_utxos:{user_utxos}")
        #STEP 1 : check marketplace
        try:
            for marketplace_account in user_utxos["marketplace"]:
                payload=f'''
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.get_mp_info_and_expiration({marketplace_step},'{user_public_key_hash}',{MARKETPLACE_STEP1_EXPIRATION},{MARKETPLACE_STEP2_EXPIRATION},{MARKETPLACE_STEP3_EXPIRATION})
'''
                smart_contract=SmartContract(marketplace_account,
                                                smart_contract_sender='sender_public_key_hash',
                                                smart_contract_type="api",
                                                payload=payload)
                smart_contract.process()
                logging.info(f"### marketplace_account:{marketplace_account} marketplace_step:{marketplace_step} MARKETPLACE_STEP1_EXPIRATION:{MARKETPLACE_STEP1_EXPIRATION} MARKETPLACE_STEP2_EXPIRATION:{MARKETPLACE_STEP2_EXPIRATION} MARKETPLACE_STEP3_EXPIRATION:{MARKETPLACE_STEP3_EXPIRATION}")
                if smart_contract.error_flag is False:
                    locals()['smart_contract']
                    mp_info,expiration,requested_amount,step=smart_contract.result
                    #Step 1: Check if the request has expired
                    logging.info(f"### marketplace_account:{marketplace_account} expiration:{expiration}")
                    if expiration is True or expiration=="True":
                        #this request needs to be archived
                        logging.info(f"###INFO marketplace request: {marketplace_account} in step:{step} has expired")
                        from node.main import MarketplaceRequestArchivingProcessing
                        marketplace_request_archiving_processing=MarketplaceRequestArchivingProcessing()
                        marketplace_request_archiving_processing.launch(request_type="expiration",marketplace_account=marketplace_account,marketplace_step=step,mp_request_signature=None)
                    else:
                        #Step 2: Check if it's a new user only for marketplace_step 1
                        check_flag=True
                        if step==1:
                            try:
                                buyer_reput_trans=mp_info['buyer_reput_trans']
                                if buyer_reput_trans==0 and sell_to_new_user_flag is False:
                                    #this user is not allowed to sell to new user
                                    check_flag=False
                            except Exception as e:
                                check_flag=False
                                logging.info(f"**** INFO no buyer_reput_trans: {mp_info}")
                                logging.exception(e)
                        if check_flag is True:
                            #requested_nig needs to be updated with the last NIG rate
                            from node.main import calculate_nig_rate
                            try:mp_info['requested_nig']=normal_round(mp_info['requested_amount']/calculate_nig_rate(),ROUND_VALUE_DIGIT)
                            except:pass
                            if step2_amount is None:
                                if mp_info is not None:return_list.append(mp_info)
                            else:
                                if mp_info is not None and float(requested_amount)<=step2_amount:
                                    return_list.append(mp_info)
                                    step2_amount-=float(requested_amount)

                    
                else:
                    logging.info(f"**** ISSUE get_marketplace_step_raw marketplace_account1: {marketplace_account}")
                    logging.info(f"**** ISSUE: {smart_contract.error_code}")
        except Exception as e:
            logging.info(f"**** ISSUE get_marketplace_step_raw marketplace_account2")
            logging.exception(e)

        #STEP 2 : check marketplace_archive if needed
        if archive_flag is True:
            try:
                user_utxos["marketplace_archive"].reverse()
                for marketplace_account in user_utxos["marketplace_archive"]:
                    payload=f'''
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.get_mp_info_archive({marketplace_step})
'''
                    smart_contract=SmartContract(marketplace_account,
                                                    smart_contract_sender='sender_public_key_hash',
                                                    smart_contract_type="api",
                                                    payload=payload)
                    smart_contract.process()
                    logging.info(f"### marketplace_account:{marketplace_account} marketplace_step:{marketplace_step} MARKETPLACE_STEP1_EXPIRATION:{MARKETPLACE_STEP1_EXPIRATION} MARKETPLACE_STEP2_EXPIRATION:{MARKETPLACE_STEP2_EXPIRATION} MARKETPLACE_STEP3_EXPIRATION:{MARKETPLACE_STEP3_EXPIRATION}")
                    if smart_contract.error_flag is False:
                        if smart_contract.result is not None:
                            locals()['smart_contract']
                            mp_info=smart_contract.result
                            logging.info(f"### marketplace_account:{marketplace_account} mp_info:{mp_info} archive_timestamp:{archive_timestamp}")
                            logging.info(f"### marketplace_account:{marketplace_account} mp_info2:{type(mp_info)} archive_timestamp2:{type(archive_timestamp)}")
                            check_timestamp=mp_info["timestamp_nig"]>archive_timestamp
                            logging.info(f"### marketplace_account:{marketplace_account} mp_info:{mp_info} mp_info>archive_timestamp:{check_timestamp}")
                            if mp_info["timestamp_nig"]>archive_timestamp:return_list.append(mp_info)
                            else:
                                #no need to go futher to avoid analysing all the archive
                                break
                    else:
                        logging.info(f"**** ISSUE get_marketplace_step_raw archive marketplace_account1: {marketplace_account}")
                        logging.info(f"**** ISSUE: {smart_contract.error_code}")
            except Exception as e:
                logging.info(f"**** ISSUE get_marketplace_step_raw archive marketplace_account2")
                logging.exception(e)


        return return_list

    def get_marketplace_genesis(self) -> dict:
        return_dict = {
            "user": "marketplace_genesis",
            "total": 0,
            "utxos": []
        }
        current_block = self
        marketplace_genesis_flag=True
        while current_block.previous_block and marketplace_genesis_flag is True:
            for transaction in current_block.transactions:
                output_index=0
                for output in transaction["outputs"]:
                    locking_script = output["locking_script"]
                    if "MP_MARKETPLACE_GENESIS" in locking_script:
                        return_dict["utxos"].append(
                                {
                                    "transaction_hash": transaction["transaction_hash"],
                                    "output_index":output_index,
                                    "amount": 0,
                                })
                        marketplace_genesis_flag=False
                        break
                    output_index+=1
            current_block = current_block.previous_block
        return return_dict
