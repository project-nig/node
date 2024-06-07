
from common.values import *



marketplace_request_code_raw="""
###VERSION:1
###END
class MarketplaceRequest:
    def __init__(self):
        self.account=None
        self.step=0
        self.new_user_flag=False
        self.timestamp=datetime.timestamp(datetime.utcnow())
        self.timestamp_step1=None
        self.timestamp_step2=None
        self.timestamp_step3=None
        self.timestamp_step4=None
        self.requested_amount=0
        self.requested_currency='EUR'
        self.requested_deposit=0
        self.requested_nig=0
        self.requested_nig_step2=None
        self.requested_nig_step2_flag=False
        self.timestamp_nig=None
        self.buyer_public_key_hex=None
        self.buyer_public_key_hash=None
        self.buyer_public_key_hash=None
        self.buyer_reput_trans=0
        self.buyer_reput_reliability=0
        self.seller_public_key_hex=""
        self.seller_public_key_hash=""
        self.encrypted_account=""
        self.mp_request_signature=None
        self.mp_request_id=random.randint(10000000, 99999999)
        self.previous_mp_request_name=None
        self.mp_request_name=None
        self.seller_safety_coef=GET_SELLER_SAFETY_COEF()
        self.smart_contract_ref=None
        self.reputation_buyer=0
        self.reputation_seller=0

    def get_mp_details(self,step):
        mp_details = [self.timestamp,self.buyer_public_key_hash,self.buyer_public_key_hex,self.requested_amount,self.mp_request_id]
        if self.requested_nig_step2_flag is True:requested_nig=self.requested_nig_step2
        else:requested_nig=self.requested_nig
        if self.step>=1:
            self.seller_safety_coef=GET_SELLER_SAFETY_COEF()
            mp_details.extend([requested_nig,self.seller_safety_coef])
        if self.step>=2:mp_details.extend([self.seller_public_key_hex,self.seller_public_key_hash,self.requested_deposit])
        if self.step==99:mp_details.append("cancellation")
        if self.step==66:mp_details.append("payment default")
        return mp_details

    def get_requested_deposit(self):
        return self.requested_deposit

    def get_new_user_flag(self):
        return self.new_user_flag

    def get_reputation(self):
        if self.reputation_buyer!=0 or self.reputation_seller!=0:return {self.buyer_public_key_hash:self.reputation_buyer,self.seller_public_key_hash:self.reputation_seller}
        else:return None

    def get_mp_info(self,step,user_public_key_hash):
        try:step=int(step)
        except:step=99
        mp_details=None
        flag=False
        readonly_flag=False
        if self.step!=4 and self.step!=45 and self.step!=66 and self.step!=98 and self.step!=99:
            if step==1:
                flag=True
                if self.buyer_public_key_hash==user_public_key_hash:readonly_flag=True
            if step==2:
                if self.buyer_public_key_hash==user_public_key_hash:flag=True
                if self.step==1:readonly_flag=True
                if self.step==3:readonly_flag=True
            if step==3:
                if self.seller_public_key_hash==user_public_key_hash:flag=True
                if self.step==2:readonly_flag=True
            if flag is True:
                mp_details = {"timestamp_nig": self.timestamp,"requester_public_key_hash": self.buyer_public_key_hash,"requester_public_key_hex": self.buyer_public_key_hex,"seller_public_key_hash": self.seller_public_key_hash,"requested_amount": self.requested_amount,"requested_currency":self.requested_currency,"requested_nig": self.requested_nig,"payment_ref": self.mp_request_name}
                mp_details['seller_public_key_hex']=self.seller_public_key_hex
                mp_details['encrypted_account']=self.encrypted_account
                mp_details['smart_contract_ref']=self.smart_contract_ref
                mp_details['readonly_flag']=readonly_flag
                mp_details['buyer_reput_trans']=self.buyer_reput_trans
                mp_details['buyer_reput_reliability']=self.buyer_reput_reliability
                mp_details['step']=self.step
        return mp_details

    def get_mp_info_archive(self,step):
        mp_details=None
        if step==self.step:
            mp_details = {"timestamp_nig": self.timestamp_step4, "readonly_flag":False}
        return mp_details

    def step1(self,mp_request_name,buyer_public_key_hash,buyer_public_key_hex,requested_amount,smart_contract_ref,new_user_flag,buyer_reput_trans,buyer_reput_reliability):
        if buyer_public_key_hash is not None and 'None' not in buyer_public_key_hash:
            if self.step==0:
                self.mp_request_name=mp_request_name
                self.buyer_public_key_hash=buyer_public_key_hash
                self.buyer_public_key_hex=buyer_public_key_hex
                self.requested_amount=requested_amount
                self.timestamp_nig=datetime.timestamp(datetime.utcnow())
                self.requested_nig=CONVERT_2_NIG(requested_amount,self.timestamp_nig,self.requested_currency)
                self.step=1
                self.smart_contract_ref=smart_contract_ref
                self.timestamp_step1=datetime.timestamp(datetime.utcnow())
                if new_user_flag=="true" or new_user_flag=="True":new_user_flag=True
                if new_user_flag=="false" or new_user_flag=="False":
                    new_user_flag=False
                    self.requested_deposit=CONVERT_2_NIG(requested_amount,self.timestamp_nig,self.requested_currency)*GET_BUYER_SAFETY_COEF()
                self.new_user_flag=new_user_flag
                self.buyer_reput_trans=buyer_reput_trans
                self.buyer_reput_reliability=buyer_reput_reliability
            else:raise ValueError('request cannot be confirmed in step 1')
        else:raise ValueError('Please select a buyer')

    def step2(self,seller_public_key_hash,seller_public_key_hex,encrypted_account,mp_request_signature):
        if seller_public_key_hash is not None and 'None' not in seller_public_key_hash:
            if self.step==1:
                self.seller_public_key_hash=seller_public_key_hash
                self.seller_public_key_hex=seller_public_key_hex
                self.timestamp_nig=datetime.timestamp(datetime.utcnow())
                self.requested_nig_step2=copy.deepcopy(self.requested_nig)
                self.requested_nig_step2_flag=True
                self.requested_nig=CONVERT_2_NIG(self.requested_amount,self.timestamp_nig,self.requested_currency)
                self.encrypted_account=encrypted_account
                self.mp_request_signature=mp_request_signature
                self.step=2
                self.timestamp_step2=datetime.timestamp(datetime.utcnow())
            else:raise ValueError('request cannot be confirmed in step 2')
        else:raise ValueError('Please select a seller')
            

    def step3(self,mp_request_signature):
        if self.step==2:
            self.mp_request_signature=mp_request_signature
            self.step=3
            self.timestamp_step3=datetime.timestamp(datetime.utcnow())
        else:raise ValueError('request cannot be confirmed in step 3')

    def step4(self,mp_request_signature):
        if self.step==3:
            self.mp_request_signature=mp_request_signature
            self.step=4
            self.timestamp_step4=datetime.timestamp(datetime.utcnow())
            self.reputation_buyer=1
            self.reputation_seller=1
        else:raise ValueError('request cannot be confirmed in step 4')

    def step45(self,mp_request_signature):
        if self.step==3:
            self.mp_request_signature=mp_request_signature
            self.step=45
            self.timestamp_step4=datetime.timestamp(datetime.utcnow())
            self.reputation_buyer=-1
            self.reputation_seller=1
        else:raise ValueError('request cannot be confirmed in step 45')

    def check_cancellation(self,mp_request_signature):
        if self.step<3:
          self.mp_request_signature=mp_request_signature
          self.step=99
          self.timestamp_step4=datetime.timestamp(datetime.utcnow())
        else:raise ValueError('request cannot be confirmed in cancellation')

    def check_payment_default(self,mp_request_signature):
        if self.step==3:
          self.mp_request_signature=mp_request_signature
          self.step=66
          self.timestamp_step4=datetime.timestamp(datetime.utcnow())
          self.reputation_buyer=-1
          self.reputation_seller=1
        else:raise ValueError('request cannot be confirmed in payment default')

    def validate_step(self):
        signature_decoded = binascii.unhexlify(self.mp_request_signature.encode("utf-8"))
        if self.step==2 or self.step==4 or self.step==45 or self.step==66:
            public_key_bytes = self.seller_public_key_hex.encode("utf-8")
        elif self.step==3 or self.step==99:
            public_key_bytes = self.buyer_public_key_hex.encode("utf-8")
        else:
            raise ValueError(f'request not in predefined step:{self.step}')
      
        public_key_object = RSA.import_key(binascii.unhexlify(public_key_bytes))
        transaction_bytes = json.dumps(self.get_mp_details(self.step), indent=2).encode('utf-8')
        transaction_hash = SHA256.new(transaction_bytes)
        pkcs1_15.new(public_key_object).verify(transaction_hash, signature_decoded)

    def check_expiration(self,MARKETPLACE_STEP1_EXPIRATION,MARKETPLACE_STEP2_EXPIRATION,MARKETPLACE_STEP3_EXPIRATION):
        return self.check_expiration_raw(MARKETPLACE_STEP1_EXPIRATION,MARKETPLACE_STEP2_EXPIRATION,MARKETPLACE_STEP3_EXPIRATION,False)

    def validate_expiration(self,MARKETPLACE_STEP1_EXPIRATION,MARKETPLACE_STEP2_EXPIRATION,MARKETPLACE_STEP3_EXPIRATION):
        return self.check_expiration_raw(MARKETPLACE_STEP1_EXPIRATION,MARKETPLACE_STEP2_EXPIRATION,MARKETPLACE_STEP3_EXPIRATION,True)

    def check_expiration_raw(self,MARKETPLACE_STEP1_EXPIRATION,MARKETPLACE_STEP2_EXPIRATION,MARKETPLACE_STEP3_EXPIRATION,error_flag):
        expiration_flag=False
        check_now=datetime.timestamp(datetime.utcnow())
        if self.step==1 and check_now-self.timestamp_step1>MARKETPLACE_STEP1_EXPIRATION:expiration_flag=True
        if self.step==2 and check_now-self.timestamp_step2>MARKETPLACE_STEP2_EXPIRATION:
            self.reputation_buyer=-1
            expiration_flag=True
        if self.step==3 and check_now-self.timestamp_step3>MARKETPLACE_STEP3_EXPIRATION:
            self.reputation_seller=-1
            expiration_flag=True
        if expiration_flag is True:
            self.step=98
            self.timestamp_step4=datetime.timestamp(datetime.utcnow())
        else:
            if error_flag is True:ValueError('smart_contract is not expired')
        return expiration_flag
		
    def get_mp_info_and_expiration(self,step,user_public_key_hash,MARKETPLACE_STEP1_EXPIRATION,MARKETPLACE_STEP2_EXPIRATION,MARKETPLACE_STEP3_EXPIRATION):
        mp_info=self.get_mp_info(step,user_public_key_hash)
        expiration=self.check_expiration(MARKETPLACE_STEP1_EXPIRATION,MARKETPLACE_STEP2_EXPIRATION,MARKETPLACE_STEP3_EXPIRATION)
        return mp_info,expiration,self.requested_amount,self.step

    def cancel(self,user_public_key_hash,mp_request_signature):
        if self.step<3 and self.buyer_public_key_hash==user_public_key_hash:
            CANCEL_SC(self.smart_contract_ref,self.step,mp_request_signature)
        else:
            raise ValueError(f'Cancellation not possible in step:{self.step} for user:{user_public_key_hash}')

    def payment_default(self,user_public_key_hash,mp_request_signature):
        if self.step==3 and self.seller_public_key_hash==user_public_key_hash:
            PAYMENT_DEFAULT_SC(self.smart_contract_ref,self.step,mp_request_signature)
        else:
            raise ValueError(f'payment default not possible in step:{self.step} for user:{user_public_key_hash}')

"""


marketplace_request_code_script=f"""
###VERSION:1
###END
class MarketplaceRequestCode:
    def __init__(self):
        self.code='''{marketplace_request_code_raw}'''
marketplace_request_code=MarketplaceRequestCode()
memory_list.add([marketplace_request_code,'marketplace_request_code',['code']])
123456
"""

marketplace_script="""
###VERSION:1
###END
class Marketplace:
    def __init__(self):
        self.first_mp_request_name=None
        self.current_mp_request_name=None
        self.current_mp_request_count=1

    def get_mp_request_name(self):
        return "mp_request_"+str(self.current_mp_request_count)

    def add_mp_request_name(self,mp_request_name):
        if self.first_mp_request_name is None or self.first_mp_request_name=="null" or self.first_mp_request_name=="None":self.first_mp_request_name=mp_request_name
        self.current_mp_request_name=mp_request_name
        self.current_mp_request_count+=1

    def get_current_mp_request_name(self):
        return self.current_mp_request_name

    def get_marketplace_step_list(self,step,user_public_key_hash):
        marketplace_step_list=[]
        cursor=self.current_mp_request_name
        while cursor is not None and 'null' not in cursor:
            cursor_obj=get_obj_by_name(cursor)
            if step==1 and cursor_obj.step==step and cursor_obj.buyer_public_key_hash!=user_public_key_hash:marketplace_step_list.append(cursor_obj.get_mp_info(1,user_public_key_hash))
            elif step==2 and cursor_obj.step==step and cursor_obj.buyer_public_key_hash==user_public_key_hash:marketplace_step_list.append(cursor_obj.get_mp_info(2,user_public_key_hash))
            elif step==3 and cursor_obj.step==step and cursor_obj.seller_public_key_hash==user_public_key_hash:marketplace_step_list.append(cursor_obj.get_mp_info(3,user_public_key_hash))
            cursor=cursor_obj.previous_mp_request_name
        return marketplace_step_list

marketplace=Marketplace()
memory_list.add([marketplace,'marketplace',['first_mp_request_name','current_mp_request_name','current_mp_request_count']])
123456
"""


marketplace_script1="""
memory_obj_2_load=['marketplace']
try:
  locals().pop('mp_request_step1')
except:
  pass
mp_request_step1_name=marketplace.get_mp_request_name()
mp_request_step1_name_init=str(mp_request_step1_name)
mp_request_step1=MarketplaceRequest()
mp_request_step1.previous_mp_request_name=marketplace.get_current_mp_request_name()
locals()[mp_request_step1_name]=mp_request_step1
marketplace.add_mp_request_name(mp_request_step1_name_init)
mp_request_step1.step1(buyer_public_key_hash,buyer_public_key_hex,requested_amount)
mp_request_step1.account=sender
mp_request_step1.mp_request_name=mp_request_step1_name
memory_list.add([mp_request_step1,mp_request_step1_name_init,['account','step','timestamp','requested_amount',
                                                      'requested_currency','requested_deposit','buyer_public_key_hash',
                                                      'buyer_public_key_hex','requested_nig','timestamp_nig','seller_public_key_hex','seller_public_key_hash','encrypted_account',
                                                      'mp_request_signature','mp_request_id','previous_mp_request_name','mp_request_name','seller_safety_coef']])

123456

"""

marketplace_script_step="""
marketplace.get_marketplace_step_list(marketplace_step,user_public_key_hash)
"""

marketplace_script2_1="""
mp_request_step1.get_mp_details(2)
"""

marketplace_script2_2="""
mp_request_step1.step2(seller_public_key_hash,seller_public_key_hex,requested_nig,encrypted_account,mp_request_signature)
mp_request_step1.validate_step()
123456
"""

marketplace_script3_1="""
mp_request_step1.encrypted_account
"""

marketplace_script3_2="""
mp_request_step1.get_mp_details(3)
"""

marketplace_script3_3="""
mp_request_step1.step3(mp_request_signature)
mp_request_step1.validate_step()
123456
"""

marketplace_script4_1="""
mp_request_step1.get_mp_details(4)
"""

marketplace_script4_2="""
mp_request_step1.step4(mp_request_signature)
mp_request_step1.validate_step()
123456
"""

marketplace_script_test="""
memory_obj_2_load=['marketplace','mp_request_2']
mp_request_step1=mp_request_2
mp_details=mp_request_step1.get_mp_details(2)
"""

block_script="""
###VERSION:1
###END
class BlockVote:
    def __init__(self,block_PoH):
        self.block_PoH=block_PoH
        self.vote_list=[]
        self.slash_list=[]
        self.validated=None

    def check_vote(self,node):
        if node in self.vote_list or node in self.slash_list or self.validated is True or self.validated is False:return False
        else:return True

    def vote(self,node):
        if node not in self.vote_list:self.vote_list.append(node)
        if node in self.slash_list:self.slash_list.remove(node)

    def slash(self,node):
        if node not in self.slash_list:self.slash_list.append(node)
        if node in self.vote_list:self.vote_list.remove(node)

    def vote_ratio(self):
        total=len(self.vote_list)+len(self.slash_list)
        self.ratio=0
        if total>0:
            ratio_vote=float(len(self.vote_list)/total)
            ratio_slash=float(len(self.slash_list)/total)
            if ratio_vote>ratio_slash:self.ratio=ratio_vote
            if ratio_vote<ratio_slash:self.ratio=-ratio_slash
        return self.ratio
        
    def validate(self,node):
        self.vote_ratio()
        total_vote=len(self.vote_list)+len(self.slash_list)
        if self.ratio>=0.66 and total_vote>=2:self.validated=True
        if self.ratio<=0.66 and total_vote>=2:self.validated=False
        return self.validated

    def is_validated(self,node):
        return self.validated

block_vote=BlockVote(block_PoH)
memory_list.add([block_vote,'block_vote',['block_PoH','vote_list','slash_list','validated']])
123456
"""

node_network_script="""
###VERSION:1
###END
class NodeNetwork:
    def __init__(self):
        self.node_dict={}

    def add_node(self,node_input_dict):
        node_dict_temp=self.node_dict.copy()
        node_public_key_hash=node_input_dict['node_public_key_hash']
        node_public_key_hex=node_input_dict['node_public_key_hex']
        node_url=node_input_dict['node_url']
        try:
            node_dict_temp[node_public_key_hash]
        except:
            new_node_dict={}
            new_node_dict['creation']=datetime.timestamp(datetime.utcnow())
            new_node_dict['public_key_hex']=node_public_key_hex
            new_node_dict['node_url']=node_url
            new_node_dict['active']=True
            node_dict_temp[node_public_key_hash]=new_node_dict
            self.node_dict=node_dict_temp

    def get_public_key_hash(self,node_url):
        public_key_hash=None
        for item in [i for i in self.node_dict.items() if i[1]['node_url']==node_url]:
            public_key_hash=item[0]
        return public_key_hash

    def get_public_key_hex(self,node_public_key_hash):
        public_key_hex=None
        try:
            public_key_hex=self.node_dict[node_public_key_hash]['public_key_hex']
        except:pass
        return public_key_hex

    def active_node(self,node_public_key_hash):
        try:
            self.node_dict[node_public_key_hash]['active']=True
        except:pass

    def deactive_node(self,node_public_key_hash):
        try:
            self.node_dict[node_public_key_hash]['active']=False
        except:pass

    def remove_node(self,node_public_key_hash):
        try:del self.node_dict[node_public_key_hash]
        except:pass
        
node_network=NodeNetwork()
memory_list.add([node_network,'node_network',['node_dict']])
123456
"""
node_script="""
node_input_dict={}
node_input_dict['node_public_key_hash']=node_public_key_hash
node_input_dict['node_public_key_hex']=node_public_key_hex
node_input_dict['node_url']=node_url
node_network.add_node(node_input_dict)
memory_list.add([node_network,'node_network',['node_dict']])
123456
"""

participant_get_score_script="""
memory_obj_2_load=['participant']
participant.get_score_data()
"""
ranking_dic={'ranking':[]}

contest_script=f"""
###VERSION:1
###END
class Contest:
    def __init__(self):
        self.participant_list=[]
        self.ranking={ranking_dic}

    def add_participant(self,public_key_hash,smart_contract_account):
        if self.check_participant(public_key_hash) is False:self.participant_list.append([public_key_hash,smart_contract_account])

    def check_participant(self,public_key_hash):
        if public_key_hash in [y[0] for y in self.participant_list]:return True
        else:return False

    def remove_participant(self,public_key_hash):
        for item in [y for y in self.participant_list if y[0]==public_key_hash]:
            self.participant_list.remove(smart_contract_account)

    def get_smart_contract(self,public_key_hash):
        result=None
        for item in self.participant_list:
            if public_key_hash==item[0]:
                result=item[1]
                break
        return result

    def get_ranking(self):
        raw_ranking=[]
        for item in self.participant_list:
            try:
                payload='''{participant_get_score_script}'''
                result=LOAD_SC(item[1],payload)
                if result is not None:raw_ranking.append(result)
            except:pass
        counter=1
        for item in sorted(raw_ranking, key=lambda d: d[1],reverse = True):
            item.insert(0,counter)
            self.ranking['ranking'].append(item)
            counter+=1
        return self.ranking
        
        
contest=Contest()
memory_list.add([contest,'contest',['participant_list','ranking']])
123456
"""

participant_script1="""
###VERSION:1
###END
class Participant:
    def __init__(self,smart_contract_account,public_key_hash,name):
        if smart_contract_account is None or smart_contract_account=='None':raise ValueError('smart_contract_account is missing')
        else:self.smart_contract_account=smart_contract_account
        if public_key_hash is None or public_key_hash=='None':raise ValueError('public_key_hash is missing')
        else:self.public_key_hash=public_key_hash
        if name is None or name=='None':raise ValueError('name is missing')
        else:self.name=name
        self.score=0
        self.total_debit=0
        self.profit=0

    def get_score_data(self):
        self.score=int(round(self.profit*self.total_debit, 0)/10000)
        return [self.name,self.score]

    def refresh_score(self):
        try:
            utxo=GET_UTXO(self.public_key_hash)
            total_euro=normal_round(utxo['total']*NIG_RATE(),ROUND_VALUE_DIGIT)
            total_debit=0
            for key in utxo['balance']['debit'].keys():
                total_debit+=utxo['balance']['debit'][key]['amount']*NIG_RATE(timestamp=utxo['balance']['debit'][key]['timestamp'])
            self.total_debit=total_debit
            total_credit=0
            for key in utxo['balance']['credit'].keys():
                total_credit+=utxo['balance']['credit'][key]['amount']*NIG_RATE(timestamp=utxo['balance']['credit'][key]['timestamp'])
            self.profit=total_euro+(total_credit-total_debit)
            self.score=int(round(self.profit*self.total_debit, 0)/10000)
        except Exception as e:
            logging.info(f"###INFO refresh_score issue: {e}")
            logging.exception(e)
"""

participant_script2="""\r
participant=Participant('$smart_contract_ref','$requester_public_key_hash','$requested_name')
memory_list.add([participant,'participant',['public_key_hash','name','score','total_debit','profit']])
123456
"""

participant_retrieve_smart_contract="""
memory_obj_2_load=['contest']
contest.get_smart_contract(public_key_hash)
"""

participant_refresh_score_script="""
memory_obj_2_load=['participant']
participant.refresh_score()
memory_list.add([participant,'participant',['public_key_hash','name','score','total_debit','profit']])
123456
"""

contest_refresh_ranking_script="""
memory_obj_2_load=['contest']
contest.get_ranking()
"""

marketplace_archiving_script="""
memory_obj_2_load=['mp_request_step2_done']
return [mp_request_step2_done.buyer_public_key_hash,mp_request_step2_done.seller_public_key_hash]
"""


marketplace_expiration_script=f"""
memory_obj_2_load=['mp_request_step2_done']
mp_request_step2_done.validate_expiration({MARKETPLACE_STEP1_EXPIRATION},{MARKETPLACE_STEP2_EXPIRATION},{MARKETPLACE_STEP3_EXPIRATION})
memory_list.add([mp_request_step2_done,mp_request_step2_done.mp_request_name,['account','step','timestamp','requested_amount',
  'requested_currency','requested_deposit','buyer_public_key_hash','timestamp_step1','timestamp_step2','timestamp_step3','timestamp_step4',
  'buyer_public_key_hex','requested_nig','timestamp_nig','seller_public_key_hex','seller_public_key_hash','encrypted_account','buyer_reput_trans','buyer_reput_reliability',
  'mp_request_signature','mp_request_id','previous_mp_request_name','mp_request_name','seller_safety_coef','smart_contract_ref','new_user_flag','reputation_buyer','reputation_seller']])
mp_request_step2_done.get_requested_deposit()
"""



application_version_script="""
###VERSION:1
###END
class Application:
    def __init__(self):
        self.version="22"
        self.url="https://drive.google.com/file/d/14e-xmqB-B59XACSRFNMsJa4yyJdyUG62/view?usp=drive_link"

    def get_version_data(self):
        return {"version":self.version,"url":self.url}

        
application=Application()
memory_list.add([application,'application',['version','url']])
123456
"""

reputation_code_raw="""
###VERSION:1
###END
class Reputation:
    def __init__(self):
        self.nb_transaction=0
        self.nb_pos=0
        self.nb_neg=0

    def get_reputation(self):
        if self.nb_transaction==0:reliability=0
        else:reliability=max(0,round(((float(self.nb_pos)-float(self.nb_neg))/float(self.nb_transaction))*100,2))
        return [self.nb_transaction,reliability]
reputation=Reputation()
memory_list.add([reputation,'reputation',['nb_transaction','nb_pos','nb_neg']])
"""

reputation_code_script=f"""
###VERSION:1
###END
class ReputationCode:
    def __init__(self):
        self.code='''{reputation_code_raw}'''
reputation_code=ReputationCode()
memory_list.add([reputation_code,'reputation_code',['code']])
123456
"""


