import logging
import time

def log_time(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logging.debug(f"{func.__name__} executed in {elapsed:.4f} seconds")
        return result
    return wrapper