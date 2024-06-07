import copy

class Memory:
        def __init__(self,module_name):
            self.__module_name=module_name

        def set_memory_process(self,obj_list_init,smart_contract_memory_init):
            #obj_list=[obj_class,obj_name,[attribut1,attribut2,...],[attribut1_value,attribut2_value,...]]
            # ex: obj_list=[token,'token',['token_total','token_name','balanceOf']]
            value_list=[]
            obj_list = copy.deepcopy(obj_list_init)
            #print(f"CHECK obj_list:{obj_list}")
            for attribut in obj_list[2]:
                attribut_value=getattr(obj_list[0],attribut)
                attribut_value_init=self.get_smart_contract_memory_init_attribut_value(obj_list[1],attribut,smart_contract_memory_init)
                if attribut_value_init is None or attribut_value!=attribut_value_init:
                    #there is at least a new value for this attribut, we need to add it on the memory
                    for attribut2 in obj_list[2]:value_list.append(getattr(obj_list[0],attribut2))
                    break
            if value_list!=[]:
                #there is value to be stored on the memory
                obj_list.append(value_list)
                obj_list.insert(1,obj_list[0].__class__.__name__)
                obj_list.pop(0)
                #print(f"CHECK obj_list NEW value")
                return obj_list
            else:
                #there is no new value to be stored on the memory
                #print(f"CHECK obj_list NO value")
                return None
        
        def get_smart_contract_memory_init_attribut_value(self,obj_name,attribut,smart_contract_memory_init):
            #obj_list=[obj_class,obj_name,[attribut1,attribut2,...],[attribut1_value,attribut2_value,...]]
            #smart_contract_memory_init=[obj_list1,obj_list2,..]
            obj_list_attribut_value=None
            for obj_list in smart_contract_memory_init:
                if obj_name==obj_list[1]:
                    for i in range(0,len(obj_list[2])):
                        obj_list_attribut=obj_list[2][i]
                        obj_list_attribut_value=obj_list[3][i]
                        if attribut==obj_list_attribut:
                            return obj_list_attribut_value
                            break




class MemoryList:
    def __init__(self,module_name):
        self.module_name=module_name
        self.obj_name_check=[]
        self.memory_obj_list=[]

    def get_memory_obj_list(self,smart_contract_memory_init):
        memory_obj_list_live=[]
        for obj_list in self.memory_obj_list:
            memory_obj=Memory(self.module_name)
            obj_list_checked=memory_obj.set_memory_process(obj_list,smart_contract_memory_init)
            if obj_list_checked is not None:memory_obj_list_live.append(obj_list_checked)
        return memory_obj_list_live

    def add(self,obj_list):
        #obj_list=[obj_class,obj_name,[attribut1,attribut2,...],[attribut1_value,attribut2_value,...]]
        # ex: obj_list=[token,'token',['token_total','token_name','balanceOf']]
        if obj_list[1] not in self.obj_name_check: 
            self.obj_name_check.append(obj_list[1])
            self.memory_obj_list.append(obj_list)



globals()['local_var']=locals()



memory_list=MemoryList("common.smart_contract")
sender="sender_public_key_hash2"
block_PoH="31c848b22ba809cf7914c6073d7fe834f518f9f6420e402ab317a28aed155309"

class BlockVote:
    def __init__(self,block_PoH):
        self.block_PoH=block_PoH
        self.vote_list=[]
        self.slash_list=[]

    def check_vote(self,node):
        if node in self.vote_list or node in self.slash_list:return False
        else:return True

    def vote(self,node):
        if node not in self.vote_list:self.vote_list.append(node)
        if node in self.slash_list:self.slash_list.remove(node)

    def slash(self,node):
        if node not in self.slash_list:self.slash_list.append(node)
        if node in self.vote_list:self.vote_list.remove(node)

    def vote_ratio(self):
        self.ratio=float((1+len(self.vote_list)-len(self.slash_list))/3)
        return self.ratio

    def validated(self):
        self.vote_ratio()
        total_vote=len(self.vote_list)+len(self.slash_list)
        if self.ratio>=0.66 and total_vote>=2:return True
        else:return False

block_vote=BlockVote(block_PoH)
memory_list.add([block_vote,'block_vote',['block_PoH','vote_list','slash_list']])
123456

check_obj_dic={}
def get_obj_by_name(obj_name):
    result=None
    try:
        result=globals()['local_var'][obj_name]
    except:
        obj_list=LOAD_OBJ(obj_name)
        try:
            obj_list[1]=globals()['local_var'][obj_list[0]]()
        except Exception as e:
            print(f"@@@@@@ ERROR 2: {obj_list[0]} {e}")
        for i in range(len(obj_list[2])):
            setattr(obj_list[1],obj_list[2][i],obj_list[3][i])
        globals()[obj_name]=obj_list[1]
        result=obj_list[1]
    return result
globals()['get_obj_by_name']=locals()['get_obj_by_name']

memory_obj_list=[['BlockVote', 'block_vote', ['block_PoH', 'vote_list', 'slash_list'], ['31c848b22ba809cf7914c6073d7fe834f518f9f6420e402ab317a28aed155309', ['127.0.0.1:5000'], []]]]
for obj_list in memory_obj_list:
    obj_name=str(obj_list[1])
    try:
        check_obj_dic[obj_name]
    except Exception as e:
        try:
            obj_list[1]=locals()[obj_name]
        except Exception as e:
            obj_list[1]=locals()[obj_list[0]]()
        check_obj_dic[obj_name]=True

        for i in range(len(obj_list[2])):
            setattr(obj_list[1],obj_list[2][i],obj_list[3][i])
        globals()[obj_name]=obj_list[1]
node="127.0.0.2:5000"
memory_obj_2_load=['block_vote']
block_vote.vote(node)
memory_list.add([block_vote,'block_vote',['block_PoH','vote_list','slash_list']])
print(memory_list.get_memory_obj_list([['BlockVote', 'block_vote', ['block_PoH', 'vote_list', 'slash_list'], ['31c848b22ba809cf7914c6073d7fe834f518f9f6420e402ab317a28aed155309', ['127.0.0.1:5000'], []]]]))
print(f"vote_list: {block_vote.vote_list}")
