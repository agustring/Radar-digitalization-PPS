# -*- coding: utf-8 -*-
"""
Created on Wed Apr 28 13:26:37 2021

@author: Snoopi
"""
#"Realtek PCIe GBE Family Controller"

from winpcapy import WinPcapDevices
from winpcapy import WinPcapUtils
import numpy as np

import dpkt
import time
import datetime
# from multiprocessing import Queue
import threading
#import ploteo

get_bin = lambda x, n: format(x, 'b').zfill(n)

binarios = np.empty([256,256], dtype=object)
for j in range(0,256):
    for i in range(0,256):
        binarios[j,i] = get_bin(j,8)+get_bin(i,8)
  

# Condiciones para sincronizacion de la variable de secuencia
c = threading.Condition()
SEQ_ctrl = 1      


def packet_callback(win_pcap, param, header, pkt_data):
    eth = dpkt.ethernet.Ethernet(pkt_data) 
    
    if (parar_recepción):
        print("\n terminó recepción")
        win_pcap.stop()
    if not eth.type == 0x0801:
        return
    cola_recibido.append(eth.data)
    

def desepaquetar():
    while not cola_recibido.qsize()==0 or not parar_recepción:
        
        if not cola_recibido.empty():    
            
            data = cola_recibido.get()
            
            palabras = np.empty(int(len(data)/4),dtype=object)
            for i in range(0,len(data),4):
                palabras[int(i/4)] = binarios[data[i+3],data[i+2]]+binarios[data[i+1],data[i]]
                
            cola_palabras.put(palabras)
    print("\n terminó desempaquetado")
            
        

def armar_M():
    
    global cont
    
    fila,columna = 0,0
    primer_HM =False
    primer_TRG=False
    w=9000 #el valor 143*19 calculado la cantidad de paquetes entre TRG y TRG  #Muestras por TRG
    h=6000 #Cantidad de TRGs (en este caso = cantidad de BI)
    M=np.zeros((h+1,w+3))#Matriz con los datos recibidos por el EVR
    #SEQ_ctrl=-1

    while not primer_HM  or not primer_TRG:
        if not cola_palabras == 0:            
            palabras = cola_palabras.get()
            for palabra in palabras:
                SEQ=int(palabra[0:2],2)
                HM=int(palabra[2:3]) #Bit de HM   espera 1er hm
                TRG=int(palabra[8:13],2) #Bits de TRG
                CFAR= palabra[13:] #Bits de CFAR
                if HM:
                    print("llego HM")
                    primer_HM = True
                if primer_HM and TRG:
                    primer_TRG = True
                    break
                
    global SEQ_ctrl

    M[fila,0:19-TRG]=np.array(list(CFAR[TRG:19]))
    columna=19-TRG
            
    # Comienzo a tomar el tiempo
    string = ""
    #start_time =  time.time()

    # Variable de control de sincronizacion
    adquirido = 0

    while 1==1:  
        if not cola_palabras.qsize()==0: 
            start_time =  time.time()
            palabras = cola_palabras.get()
            for palabra in palabras:
                         
                SEQ=int(palabra[0:2],2) #Separa los primeros dos bits (secuencia)
                HM=int(palabra[2:3]) #Bit de HM
                # BI=int(palabra[3:8],2) #Bits de BI
                TRG=int(palabra[8:13],2) #Bits de TRG
                CFAR=  palabra[13:] #Bits de CFAR   #"1111111111111111111" 
                if (not SEQ==SEQ_ctrl):
                    string = string + "SEQ: " + str(SEQ) + ", SEQ_ctrl: " + STR(SEQ_ctrl) + "\n"

                while (adquirido == 0):
                    c.acquire()
                    SEQ_ctrl=(SEQ_ctrl+1) % 4
                    adquirido = 1

                c.release()
                adquirido = 0

                if CFAR=="0000000000000000000":  #Si se reciben todos ceros no se carga a M ya que los valores de esta son cero    #"0000000000000000000"
                    if not TRG:                  #Pero si se actualizan los valores de fila y columna
                        columna += 19
                    else:
                        fila,columna=fila+1,19-TRG  
                else:
                    if not TRG:
                        M[fila,columna:columna+19]=np.array(list(CFAR))
                        columna += 19
                    else:
                        M[fila,columna:columna+TRG]=np.array(list(CFAR[0:TRG]))
                        fila,columna=fila+1,19-TRG
                        M[fila,0:19-TRG]=np.array(list(CFAR[TRG:19]))
                        
                if w-19 <= columna:
                    columna=w-19
                
               
                if fila>=4062:
                    print(M)
                    M[4060,10]=1
                    cola_M.put(M[:4061,:8073])
                    M=np.zeros((h+1,w+3))
                    fila,columna = 0,0        
            
                # Este timer basa su uso en segundos
                seconds = time.time() - start_time
                #print('Tiempo consumido:', time.strftime("%H:%M:%S",time.gmtime(seconds)))
                #print(string)
                


def check_SEQ():
    SEQ_ctrl=-1
    print("largo",cola_palabras.qsize())
    while not cola_palabras.empty():
        palabras = cola_palabras.get()
        for palabra in palabras: #para cada palabra del paquete
            SEQ=int(palabra[0:2],2) #Separa los primeros dos bits (secuencia)
            if (not SEQ==SEQ_ctrl and not SEQ_ctrl==-1):
                print("ERROR de control")
            SEQ_ctrl=SEQ+1 & 3
    print("termino el check")

###Agustin
def crear_palabra():
    t = time.time()
    palabra = np.array([],dtype=bool)
    #Orden: SEQ/HM/BI/TRG/CFAR


####  Que device están disponibles ############

with WinPcapDevices() as devices:
    for device in devices:
        print(device.description)
        
## Elejir la placa que se va a utilizar #######

my_device = "Realtek PCIe GBE Family Controller" 

#"Realtek PCIe GBE Family Controller"  "Realtek Ethernet Controller"
                
###############################################

list_cont = []
list_TRG = []
global cont
cont = 0

start = time.time()

cola_recibido = []
cola_palabras = []
cola_M        = []


parar_recepción   = False

hilo_recibir       = threading.Thread(target=WinPcapUtils.capture_on, args=(my_device,packet_callback), daemon=True)
hilo_desempaquetar = threading.Thread(target=desepaquetar, args=(), daemon=True)
hilo_armar_M       = threading.Thread(target=armar_M, args=(), daemon=True)


hilo_recibir.start()



time.sleep(4)   #Tiempo que toma para recibir.

hilo_desempaquetar.start()  #para un funcionamiento contínuo, se debe desplazar a la línea 23 [yo]
hilo_armar_M.start() #para un funcionamiento contínuo, se debe desplazar a la línea 24 [yo]


hilo_armar_M.join()
#plot = ploteo.ploteo(w=8073,h=2032)  #plotea off line [yo]
time.sleep(10)
