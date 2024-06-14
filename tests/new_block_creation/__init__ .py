import json, logging, copy
from operator import itemgetter

from common.utils import calculate_hash,normal_round,convert_str_2_bool
from common.values import ROUND_VALUE_DIGIT

from common.smart_contract_script import *

class BlockHeader:
    def __init__(self, previous_block_hash: str, current_PoH_hash: str, current_PoH_timestamp:str, previous_PoH_hash: str,timestamp: float, noonce: int, merkle_root: str):
        self.previous_block_hash = previous_block_hash
        self.current_PoH_hash = current_PoH_hash
        self.current_PoH_timestamp = current_PoH_timestamp
        self.previous_PoH_hash = previous_PoH_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.noonce = noonce
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
                       "noonce": self.noonce}
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
        }

    def __str__(self):
        return json.dumps(self.to_dict)

    @property
    def to_json(self) -> str:
        return json.dumps(self.to_dict)


class Block:
    def __init__(
            self,
            transactions: [dict],
            block_header: BlockHeader,
            previous_block=None,
            *args, **kwargs,
    ):
        self.block_header = block_header
        self.transactions = transactions
        self.previous_block = previous_block
        self.master_state = kwargs.get('master_state',None)

    def __eq__(self, other):
        try:
            assert self.block_header == other.block_header
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
            "transactions": self.transactions
        }
        return block_data

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
                                logging.info(return_dict["utxos"])
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
        except Exception as e:
            return_dict['total']=float(0)
            return_dict['total_euro']=float(0)
            return_dict['utxos']=[]
            return_dict['user']=user
            logging.info(f"ERROR get_user_utxos Exception: {e}")
            logging.exception(e)
        return return_dict

    def get_smart_contract_api(self, account: str, *args, **kwargs) -> dict:
        smart_contract_transaction_hash=kwargs.get('smart_contract_transaction_hash',None)
        self.master_state.get_master_state_from_memory_from_user(account)
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
                            return_dict['smart_contract_transaction_hash']=return_dict['balance']['credit'][transaction]['transaction_hash']
                            #this is the last transaction with source code
                            check_contrac_flag=True
                    else:
                        return_dict['smart_contract_previous_transaction']=return_dict['balance']['credit'][transaction]['smart_contract_previous_transaction']
                        return_dict['smart_contract_transaction_hash']=return_dict['balance']['credit'][transaction]['transaction_hash']
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
        #logging.info(f"self.current_master_state[user]:{self.master_state.current_master_state[user]}")
        return_dict=copy.deepcopy(self.master_state.current_master_state[user])
        return_dict_balance = {
            "user": user,
            "total_credit": 0,
            "total_debit": 0,
            "utxos": []
        }
        for utxo in return_dict['balance']['credit'].keys():
            return_dict['balance']['credit'][utxo]['balance']='credit'
            return_dict['balance']['credit'][utxo]['user']=return_dict['balance']['credit'][utxo]['account_credit_list'][0]
            return_dict_balance['total_credit']+=return_dict['balance']['credit'][utxo]['amount']
            return_dict_balance['utxos'].append(return_dict['balance']['credit'][utxo])

        for utxo in return_dict['balance']['debit'].keys():
            return_dict['balance']['debit'][utxo]['balance']='debit'
            return_dict['balance']['debit'][utxo]['user']=return_dict['balance']['debit'][utxo]['account_credit_list'][0]
            return_dict_balance['total_debit']+=return_dict['balance']['debit'][utxo]['amount']
            return_dict_balance['utxos'].append(return_dict['balance']['debit'][utxo])

        return_dict_balance_utxos_sorted = sorted(return_dict_balance['utxos'], key=itemgetter('timestamp'), reverse=True)
        return_dict_balance['utxos']=return_dict_balance_utxos_sorted
        return return_dict_balance


    def get_user_utxos_account_temp(self, user: str, *args, **kwargs) -> dict:
        payment_ref=kwargs.get('payment_ref',None)
        return_dict=self.get_user_utxos_raw(user,payment_ref=payment_ref)
        return_dict["total"]=0
        utxos_elem_2_del=[]
        for utxos_elem in return_dict["utxos"]:
            logging.info(f" utxos_elem: {utxos_elem}")
            if utxos_elem['account_temp'] is False:
                print('false')
                utxos_elem_2_del.append(utxos_elem)
            else:
                print('true')
                return_dict["total"] = return_dict["total"] + utxos_elem["amount"]
        for utxos_elem in utxos_elem_2_del:return_dict["utxos"].remove(utxos_elem)
        return_dict["total"]=normal_round(return_dict["total"],ROUND_VALUE_DIGIT)
        return return_dict


    def get_transaction_from_utxo(self,utxo_unlocking_public_key_hash:str, utxo_hash: str) -> dict:
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

       

    def get_locking_script_from_utxo(self,utxo_unlocking_public_key_hash:str, utxo_hash: str, utxo_index: int):
        utxo_key=str(utxo_hash)+'_'+str(utxo_index)
        self.master_state.get_master_state_from_memory_from_user(utxo_unlocking_public_key_hash)
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

    def get_marketplace_step(self,marketplace_step,user_public_key_hash):
        return_list=self.get_marketplace_step_raw(marketplace_step,user_public_key_hash)
        return {"results":return_list}


    def get_marketplace_step_raw(self,marketplace_step,user_public_key_hash, *args, **kwargs):
        ####SMART CONTRACT
        from node.main import MY_HOSTNAME
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
        #if marketplace_step=="1":user_utxos=blockchain_base.get_user_utxos("marketplace_step1")
        if marketplace_step=="1":user_utxos=blockchain_base.get_user_utxos(marketplace_public_key)
        else:user_utxos=blockchain_base.get_user_utxos(user_public_key_hash)
        for marketplace_account in user_utxos["marketplace"]:
            logging.info(f"### marketplace_account:{marketplace_account}")
            payload=f'''
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.get_mp_info({marketplace_step},"{user_public_key_hash}")
'''
            logging.info(f"### get_marketplace_step_raw payload:{payload}")
            smart_contract=SmartContract(marketplace_account,
                                            smart_contract_sender='sender_public_key_hash',
                                            type="api",
                                            payload=payload)
            smart_contract.process()
            logging.info(f"### smart_contract result:{smart_contract.result}")
            locals()['smart_contract']
            if smart_contract.result is not None :return_list.append(smart_contract.result)
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
