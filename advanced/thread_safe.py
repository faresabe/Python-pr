import heapq
import threading
from itertools import count
from queue import Empty 

class Threadsafe:
    def __init__(self):
        self._heap = []
        self._counter =count()
        self._cond=threading.Condition()

    def put(self,item,priority):
        with self._cond:
            heapq.heappush(self._heap,(priority,next(self._counter),item))
            self._cond.notify()

    def get(self):
        with self._cond:
            while not self._heap:
                self._cond.wait()
            item = heapq.heappop(self._heap)[2]
            return item

    def get_nowait(self):
        with self._cond:
          if not self._heap:
            raise Empty
          return heapq.heappop(self._heap)[2]

    def empty(self):
     with self._cond:
        return not self._heap

    def qsize(self):
     with self._cond:
        return len(self._heap)


    