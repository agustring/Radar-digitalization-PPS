###Agustin
# import numpy as np
import time

matrix = []

#Función para comparar 2 arreglos
def compare(a, b):
    if len(a) == len(b):
        for i in range(len(b)):
            if a[i] == b[i]:
                pass
            else:
                return False
        return True
    else:
        return False

#Función para pasar índice a binario de 5 bits
def aBin(a):
    b = bin(a)[2:len(bin(a))]
    c = [False, False, False, False, False]
    for i in range(len(b)):
        p = 5-len(bin(a))+i #Índice modificado
        if b[i]=='1':
            c[p] = True
        elif b[i]=='0':
            c[p]=False
    return c
            
#Se ingresan la cantidad de datos que se quieren utilizar y el tiempo mínimo en ns
def general(buffer_siz3=2e5, master_tim3=0):
    
    global matrix
    palabra = []
    cfar = []
    bi = []
    trg = []
    seq = []
    
    cant_trg=0
    cant_bi=0
    t=time.time_ns()
    i=0
    
    while i<buffer_siz3:
        
        cfar[:] = [False, False, False, False, False, False, 
                   False, False, False, False, False, False, 
                   False, False, False, False, False, False, 
                   False] #Son 19
        cant_trg+=19
        cant_bi+=19
        
        #Rota la secuencia
        if compare(seq[1:3], [False, False]):
            seq[1:3] = [False, True]
        elif compare(seq[1:3], [False, True]):
            seq[1:3] = [True, False]
        elif compare(seq[1:3], [True, False]):
            seq[1:3] = [False, False]
            
        if cant_trg >= 8183-18:
            cfar[8183-cant_trg] = True
            trg[:]=aBin(8183-cant_trg)
            cant_trg=18-(8183-cant_trg)
            t+=1
        else:
            trg[:]=[False, False, False, False, False]
            
        if t==4073: #Heading North Mark (cada 4073 triggers = 2 segs)
            seq[0]=True
            t=0
            # print(len(matrix)) #Mínimo 2e6 iteraciones
            
        if cant_bi >= 8134-18:
            cfar[8134-cant_bi] = True
            bi[:] = aBin(8134-cant_bi)
            cant_bi=18-(8134-cant_bi)
            # print(len(matrix)) #Para buscar donde estan
        else:
            bi[:]= [False, False, False, False, False]
        
        # palabra = np.concatenate((seq, bi, trg, cfar))
        palabra[0:18]= cfar[:]
        palabra[18:23]= trg[:]
        palabra[23:28]= bi[:]
        palabra[28:31]= seq[:]

        matrix.append(palabra)
        palabra = []
        i+=1
        
    while time.time_ns()-t<master_tim3:
        pass
    return matrix

#Cuatro trgs y 2 segs
xd = general(buffer_siz3=100*100) 