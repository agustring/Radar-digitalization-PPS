# -*- coding: utf-8 -*-
"""
Created on Wed Sep 29 14:44:48 2021

@author: agust
"""


# def real_generar():
#     def trigger():
#         global trg
#         global recibido_trg
#         t = time.time_ns()
#         while 1:
#             recibido_trg = False
#             if time.time_ns() - t > ctte_trg:
#                 while not recibido_trg:
#                     if escribiendo:
#                         trg[:] = [1, 0, 0, 1, 1]
#                     else:
#                         trg[:] = [0, 0, 0, 0, 1]
#                 trg[:] = [0, 0, 0, 0, 0]
#                 t = time.time_ns()
#             else:
#                 trg[:] = [0, 0, 0, 0, 0]
            

#     t = threading.Thread(target=trigger, name='Trigger', daemon=True)

#     def bear():
#         global bi
#         global recibido_bi
#         t = time.time_ns()
#         while 1:
#             recibido_bi = False

#             if time.time_ns() - t > ctte_bi:
#                 while not (recibido_bi):
#                     if escribiendo:
#                         bi[:] = [1, 0, 0, 1, 1]
#                     else:
#                         bi[:] = [0, 0, 0, 0, 1]
#                 bi[:] = [0, 0, 0, 0, 0]
#                 t = time.time_ns()
#             else:
#                 bi[:] = [0, 0, 0, 0, 0]
            
            
#     b = threading.Thread(target=bear, name='Bearing Increment', daemon=True)

#     def hm():
#         global seq
#         global recibido_h
#         t = time.time()
#         while 1:
#             recibido_h = False

#             if time.time() - t > 2:
#                 while not recibido_h:
#                     seq[2] = True
#                 t = time.time()
#             else:
#                 seq[2] = False

#     h = threading.Thread(target=hm, name='Heading North Mark', daemon=True)

#     def crear_palabra():

#         global bi
#         global trg
#         global adconv
#         global palabra
#         global recibido_bi
#         global recibido_trg
#         global recibido_h
#         global matrix
#         global escribiendo

#         i = 0

#         while i < 201:

#             # up = 0
#             # down = 17
#             i += 1
            
#             adconv[:] = False
            
#             if compare(bi, [0, 0, 0, 0, 1]):
#                 adconv[0] = True

#             if compare(trg, [0, 0, 0, 0, 1]):
#                 adconv[1] = True

#             escribiendo = True
            
#             if compare(seq[0:1], [0, 0]):
#                 seq[0:1] = [0, 1]
#             elif compare(seq[0:1], [0, 1]):
#                 seq[0:1] = [1, 0]
#             elif compare(seq[0:1], [1, 0]):
#                 seq[0:1] = [0, 0]

#             if compare(bi, [1, 0, 0, 1, 1]):
#                 adconv[16] = True

#             if compare(trg, [1, 0, 0, 1, 1]):
#                 adconv[17] = True

#             palabra = np.concatenate((seq, bi, trg, adconv))
            
#             recibido_h = True
#             recibido_bi = True
#             recibido_trg = True
#             escribiendo = False

#             matrix.append(palabra)

#     c = threading.Thread(target=crear_palabra, name='32bit Word Creator', daemon=True)

#     t.start()
#     b.start()
#     h.start()
#     c.start()


# real_generar()

# while len(matrix)<200:
#     pass