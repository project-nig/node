import logging
import os
import json

from common.master_state_readiness import master_state_readiness

class StorageSharding:
    def __init__(self,storage_directory,deepth):
        from common.values import STORAGE_DIR
        self.storage_directory = STORAGE_DIR+storage_directory
        self.deepth=deepth
        self.directory=None
        self.filename=None

    def get_directory(self,key_2_store):
        directory=self.storage_directory
        for i in range(0,self.deepth):
            directory+=f"/{str(key_2_store)[0:i+1].lower()}"
        self.directory=directory

    def get_filename(self,key_2_store):
        self.get_directory(key_2_store)
        #self.filename=self.directory+f"/{key_2_store.lower()}.txt".replace("'","")
        #self.filename=self.directory+f"/{key_2_store.lower()}".replace("'","")
        from common.values import MY_NODE
        if MY_NODE.startswith('local'):self.filename=self.directory+f"\{key_2_store.lower()}".replace("'","")
        if MY_NODE.startswith('server'):self.filename=self.directory+f"/{key_2_store.lower()}".replace("'","")

    def read(self,key_2_store) -> list:
        file_data=None
        self.get_filename(key_2_store)
        #logging.info(f"opening filename: {self.filename}")
        try:
            with open(self.filename, "rb") as file_obj:
                file_data_str = file_obj.read()
                if len(file_data_str):
                    file_data = json.loads(file_data_str)
        except Exception as e:
            #logging.info(f"**** ISSUE StorageSharding read 1 {self.filename} {e}")
            pass
        return file_data

    def store(self,key_2_store,data_2_store):
        try:
            self.get_filename(key_2_store)
            self.store_file(data_2_store)
        except Exception as e:
            #logging.info(f"**** ISSUE StorageSharding store 1 {key_2_store}: {e}")
            try:
                #the First exception can be due to the fact that
                #the directory is not existing, let's create it
                if not os.path.exists(self.directory):
                    #the directory is not existing, let's create it
                    os.makedirs(self.directory)
                self.store_file(data_2_store)
            except Exception as e:
                logging.info(f"**** ISSUE StorageSharding store 2 {self.directory}: {e}")


    def delete(self,key_2_store,master_state_readiness):
        #let's block MasterState
        #while master_state_readiness.block() is False:
        #    #let's wait until MasterState is released by another thread
        #    pass
        try:
            self.get_filename(key_2_store)
            self.delete_file()

        except Exception as e:
            logging.info(f"**** ISSUE StorageSharding delete 1 {key_2_store}: {e}")

        #let's release MasterState
        #master_state_readiness.release()
           
    
    def setup_directory(self):
        #this function ensure that the Directory is well created at restart
        if not os.path.exists(self.storage_directory):
            #the directory is not existing, let's create it
            os.makedirs(self.storage_directory)
       
    def store_file(self,data_2_store):
        text = json.dumps(data_2_store).encode("utf-8")
        with open(self.filename, "wb") as file_obj:
            file_obj.write(text)

    def delete_file(self):
        logging.info(f"**** Deletion of file {self.filename}")
        os.remove(self.filename)

