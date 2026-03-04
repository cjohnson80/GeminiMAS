import threading
import functools
from collections import OrderedDict

# Lightweight Cache Implementation for Celeron
class LightweightLRUCache:
    def __init__(self, capacity=50):
        self.cache = OrderedDict()
        self.capacity = capacity

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args):
            if args in self.cache:
                self.cache.move_to_end(args)
                return self.cache[args]
            result = func(*args)
            self.cache[args] = result
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
            return result
        return wrapper

# Threading constraint for Celeron (2 threads max)
THREAD_POOL = threading.BoundedSemaphore(2)
