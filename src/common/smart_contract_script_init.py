
marketplace_script="""

class MarketplaceRequest:
    def __init__(self):
        self.account=None
        self.step=0
        self.timestamp=datetime.timestamp(datetime.utcnow())
        self.requested_amount=0
        self.requested_currency='EUR'
        self.next_account=None
        self.requested_nig=0
        self.timestamp_nig=None
        self.buyer_public_key_hex=None
        self.buyer_public_key_hash=None
        self.seller_public_key_hex=None
        self.seller_public_key_hash=None
        self.encrypted_account=None
        self.mp_request_signature=None
        self.mp_request_id=random.randint(10000000, 99999999)
        self.previous_mp_request_name=None
        self.mp_request_name=None
        self.seller_safety_coef=GET_SELLER_SAFETY_COEF()
        self.smart_contract_ref=None
    
    def setup(self,mp_request_name,account,step,mp_details):
      self.mp_request_name=mp_request_name
      self.account=account
      self.step=step
      self.timestamp=mp_details[0]
      self.buyer_public_key_hash=mp_details[1]
      self.buyer_public_key_hex=mp_details[2]
      self.requested_amount=mp_details[3]
      self.mp_request_id=mp_details[4]
      self.requested_nig=mp_details[5]
      self.seller_safety_coef=mp_details[6]

    def get_mp_details(self,step):
      mp_details = [self.timestamp, self.buyer_public_key_hash,self.buyer_public_key_hex,self.requested_amount,self.mp_request_id]
      if self.step>=1:
          self.seller_safety_coef=GET_SELLER_SAFETY_COEF()
          mp_details.extend([self.requested_nig,self.seller_safety_coef])
      if self.step>=2:mp_details.extend([self.seller_public_key_hex,self.seller_public_key_hash])
      return mp_details

    def get_mp_info(self,step,user_public_key_hash):
        mp_details={}
        flag=False
        if self.step==step:
            if step==1 and self.buyer_public_key_hash!=user_public_key_hash:flag=True
            elif step==2 and self.buyer_public_key_hash==user_public_key_hash:flag=True
            elif step==3 and self.seller_public_key_hash==user_public_key_hash:flag=True
            if flag==True:
                mp_details = {"timestamp_nig": self.timestamp,"requester_public_key_hash": self.buyer_public_key_hash,"requester_public_key_hex": self.buyer_public_key_hex,"seller_public_key_hash": self.seller_public_key_hash,"requested_amount": self.requested_amount,"requested_currency":self.requested_currency,"requested_nig": self.requested_nig,"payment_ref": self.mp_request_name}
                if self.step>=2:
                    mp_details['seller_public_key_hex']=self.seller_public_key_hex
                    mp_details['encrypted_account']=self.encrypted_account
                    mp_details['smart_contract_ref']=self.smart_contract_ref
        return mp_details

    def step1(self,buyer_public_key_hash,buyer_public_key_hex,requested_amount):
        if self.step==0:
            self.buyer_public_key_hash=buyer_public_key_hash
            self.buyer_public_key_hex=buyer_public_key_hex
            self.requested_amount=requested_amount
            self.timestamp_nig=datetime.timestamp(datetime.utcnow())
            self.requested_nig=CONVERT_2_NIG(requested_amount,self.timestamp_nig,self.requested_currency)
            self.step=1

    def step2(self,seller_public_key_hash,seller_public_key_hex,requested_nig,encrypted_account,mp_request_signature,smart_contract_ref):
        if self.step==1:
            self.seller_public_key_hash=seller_public_key_hash
            self.seller_public_key_hex=seller_public_key_hex
            self.timestamp_nig=datetime.timestamp(datetime.utcnow())
            self.requested_nig=CONVERT_2_NIG(self.requested_amount,self.timestamp_nig,self.requested_currency)
            self.encrypted_account=encrypted_account
            self.mp_request_signature=mp_request_signature
            self.step=2
            self.smart_contract_ref=smart_contract_ref
            

    def step3(self,mp_request_signature):
        if self.step==2:
            self.mp_request_signature=mp_request_signature
            self.step=3

    def step4(self,mp_request_signature):
        if self.step==3:
            self.mp_request_signature=mp_request_signature
            self.step=4

    def validate_step(self):
        signature_decoded = binascii.unhexlify(self.mp_request_signature.encode("utf-8"))
        if self.step==2 or self.step==4:
            public_key_bytes = self.seller_public_key_hex.encode("utf-8")
        elif self.step==3:
            public_key_bytes = self.buyer_public_key_hex.encode("utf-8")
        else:
            raise ValueError('request not in predefined step')

        public_key_object = RSA.import_key(binascii.unhexlify(public_key_bytes))
        transaction_bytes = json.dumps(self.get_mp_details(self.step), indent=2).encode('utf-8')
        transaction_hash = SHA256.new(transaction_bytes)
        #print(f"@@@@@@check mp_details:{json.dumps(self.get_mp_details(self.step))} public_key_bytes:{public_key_bytes} signature:{self.mp_request_signature}")
        pkcs1_15.new(public_key_object).verify(transaction_hash, signature_decoded)
        if CONVERT_2_NIG(self.requested_amount,self.timestamp_nig,self.requested_currency)!=self.requested_nig:raise Exception('nig conversion rate error')

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
                                                      'requested_currency','next_account','buyer_public_key_hash',
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

