import numpy as np
import time
from multiprocessing import Queue
import threading
import random

cola_recibido = Queue()

trg = "00000"
bi = "00000"
seq = "00"
adconv = ""
palabra = ""
escribiendo = False
recibido = False

def bear():
    global bi
    global recibido
    t = time.time_ns()
    while 1:
        bi = "00000"
        recibido = False
        # time.sleep(488.1E-6)
        comp = time.time_ns() - t
        if comp > 488.1E3:
            while not (recibido):
                if escribiendo:
                    bi = "10011"
                else:
                    bi = "00001"
            t = time.time_ns()


b = threading.Thread(target=bear, name='Bearing Increment', daemon=True)
b.start()

while 1:
    pass