import logging
import os
import json



class StorageSharding:
    def __init__(self,storage_directory,deepth):
        from node.main import STORAGE_DIR
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
        self.filename=self.directory+f"/{key_2_store.lower()}.txt".replace("'","")

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
            #logging.info(f"**** ISSUE StorageSharding read 1 {self.filename}: {e}")
            pass
        return file_data

    def store(self,key_2_store,data_2_store):
        try:
            self.get_filename(key_2_store)
            #logging.info(f"directory:{self.directory}")
            self.store_file(data_2_store)
        except:
            try:
                #the First exception can be due to the fact that
                #the directory is not existing, let's create it
                if not os.path.exists(self.directory):
                    #the directory is not existing, let's create it
                    os.makedirs(self.directory)
                    self.store_file(data_2_store)
            except Exception as e:
                logging.info(f"**** ISSUE StorageSharding store 2 {self.directory}: {e}")

    def store_file(self,data_2_store):
        text = json.dumps(data_2_store).encode("utf-8")
        with open(self.filename, "wb") as file_obj:
            file_obj.write(text)

