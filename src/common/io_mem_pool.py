import json
import logging
import os



class MemPool:
    def __init__(self):
        #self.file_name = os.environ["MEMPOOL_DIR"]
        from common.values import MEMPOOL_DIR
        self.mempool_file_name = MEMPOOL_DIR

    def get_transactions_from_memory(self) -> list:
        logging.info("Getting transaction from memory")
        current_mem_pool_list = []
        try:
            with open(self.mempool_file_name, "rb") as file_obj:
            
                current_mem_pool_str = file_obj.read()
                if len(current_mem_pool_str):
                    current_mem_pool_list = json.loads(current_mem_pool_str)
        except Exception as e:
            logging.info(f"****ERROR while reading MEMPOOL")
            logging.exception(e)
        return current_mem_pool_list

    def store_transactions_in_memory(self, transactions: list):
        logging.info("Storing transaction in memory")
        text = json.dumps(transactions).encode("utf-8")
        try:
            with open(self.mempool_file_name, "wb") as file_obj:
                file_obj.write(text)

        except Exception as e:
            logging.info(f"**** Transaction3: {e}")
            logging.exception(e)


    def clear_transactions_from_memory(self):
        logging.info("Clearing transaction from memory")
        open(self.mempool_file_name, 'w').close()