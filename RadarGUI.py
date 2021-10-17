from radarwidget import RadarWidget
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt5.QtGui import *
from datetime import datetime
import numpy as np
import threading
from threading import Thread, Lock
import time
import math
import socket
import asyncio
from multiprocessing.connection import Listener
from random import randint, sample
from bitstring import BitArray

from winpcapy import WinPcapDevices
from winpcapy import WinPcapUtils
from multiprocessing import Queue
import dpkt


import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 

import ADC
import Detector
import Seguimiento

cola_recibido = []
cola_palabras = []
cola_M        = []

   
get_bin = lambda x, n: format(x, 'b').zfill(n)

binarios = np.empty([256,256], dtype=object)
for j in range(0,256):
    for i in range(0,256):
        binarios[j,i] = get_bin(j,8)+get_bin(i,8)

def packet_callback(win_pcap, param, header, pkt_data):
    eth = dpkt.ethernet.Ethernet(pkt_data) 
    
    if (False):
        print("\n terminó recepción")
        #win_pcap.stop()
    if not eth.type == 0x0801:
        return
    cola_recibido.append(eth.data)
    

# VARIABLES GLOBALES: Dir IP EVRT y Archivo donde se guarda la misma.
IP = ''
file_IP_EVRT = 0


class hiloPlot(QtCore.QThread):
    """Clase necesaria para que un thread pueda modificar elementos QT como la tabla"""
    signal_plot = QtCore.pyqtSignal()

class hiloAlerta(QtCore.QThread):
    """Clase utilizada para mostrar mensajes de alerta varios"""
    signal_errorConexion = QtCore.pyqtSignal()
    signal_alertaReinicio = QtCore.pyqtSignal()
# HILO GLOBAL HANDLER DE ALERTAS
hiloAlertas = hiloAlerta()

# Clase RadarGUI ---------------------
#   Logica del radar.
aux=Lock()
w=6074 #Muestras por TRG - Calculos del SIMURAD
h=8183 #Cantidad de TRGs (en este caso = cantidad de BI) - Calculos del SIMURAD
class RadarGUI(QtWidgets.QMainWindow):
    

    """
    
    En esta clase se encuentra toda la lógica del radar.
    Se crean las variables adc, det y seg necesarias para simular los seguimientos.
    Se crea una matriz de 3000x20000 que representa el rango de alcance del radar (distancia en millas x angulo).
    vueltaRadar simula el retardo en tiempo entre vuelta y vuelta del radar.
    seguimientosActivos almacena la cantidad de seguimientos activos en cada momento, para mantener ordenada la tabla.
    Los semáforos mutexSeg, mutexM y mutexInicioSeg son utilizados para sincronizar actualizaciones de los seguimientos en el radar y sus valores en tabla.
    mutexFile es un semáforo utilizado para controlar el acceso al archivo de logs.
    botones_fin_track es un arreglo de botones, utilizado para indicar que se desea dejar un seguimiento.
    """

    # Conjunto de objetos utilizados, se inicializan en el programa.
    global adc
    det=None
    seg=None

    w=6074 #Muestras por TRG - Calculos del SIMURAD
    h=8183 #Cantidad de TRGs (en este caso = cantidad de BI) - Calculos del SIMURAD
    M=np.zeros((w,h),dtype=int)#Matriz con los datos recibidos por el EVR 
    
    # Matriz donde se simulan los blancos.
    Filas = 6074
    Columnas = 8183
    #M=np.zeros((Filas,Columnas),dtype=int)
    
    # Valor utilizado en un sleep para simular el retardo entre vuelta de radar.
    vueltaRadar = 1.90

    # Utilizado en multiples chequeos.
    seguimientosActivos = 0
    maximaSeguimientos = 8  # Se corresponde con la capacidad de la tabla tambien.

    # Se crean mutexes para poder sincronizar las actualizaciones de los seguimientos con las actualizaciones en tabla
    mutexSeg = Lock()
    mutexM = Lock()
    mutexInicioSeg = Lock()
    

    # Mutex para la escritura en el archivo
    mutexFile = Lock()

    # Auxiliares para nuevos seguimientos.
    nuevoDis = -1
    nuevoAng = -1

    # Encargado de los seguimientos.
    hiloPlotMySeg = hiloPlot()
    

    def __init__(self):
        super(RadarGUI, self).__init__()
        uic.loadUi('RadarGUI.ui', self)
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.show()
        
        

        # Inicializacion de mutexes
        self.mutexSeg.acquire()
        self.mutexInicioSeg.acquire()        
        #self.mutexSocket.acquire()

        # Oyentes de radar y de umbral
        self.RadarWidget.canvas.mpl_connect('button_press_event', self.onclick)
        self.slider_umbral.valueChanged.connect(self.actualizarUmbral)  
        self.menu_configurar.triggered.connect(self.dialogEVRTHandler)

        # Inicializacion del archivo de logs y del label de la hora.
        hoy=datetime.today()
        diaDeHoy=hoy.strftime('%d-%m-%Y')
        self.file=open(diaDeHoy+'.log','a+')
        self.escrituraEnLogs('---------------------------- DIA: %s ----------------------------' % diaDeHoy)
        self.escrituraEnLogs('ID\t\tDISTANCIA\tANGULO\t\tVELOCIDAD\tHORA')
        
        # Config de IP EVRT
        self.IP_EVRT_config()

        # TESTING: Utilizados a la hora de definir el tamaño de la matriz de blancos.
        self.matTriggers = 3000
        self.matMuestras = 20000
        
        # Necesarios para la simulacion del seguimiento, para cuando se conecte al simurad los parametros del adc se reciben de él.
        self.adc = ADC.ADC(0,0,0,0,0)
        self.det = Detector.Detector(self.adc)
        self.seg = Seguimiento.Seguimiento(self.det)
        
        # Actualizacion radarWidget con valores de adc.
        self.RadarWidget.setParametrosADC(self.adc.RMillaMuestra, self.adc.RTA)

        # Se inicializan los botones para dejar de seguir un movil y los hilos del programa.
        self.iniHilos()

        
    def dialogEVRTHandler(self):
        """
        Utilizada para mostrar una ventana emergente donde le permita al usuario settear la IP a utilizar en la EVRT, para crear el socket de comunicación con la RSC.
        """
        Dialog = DialogEVRT()
        Dialog.exec_()     
        

    def iniHilos(self):
        """
        Se declaran las variables necesarias para la simulacion de cada seguimiento. Cuando se esté conectado al simurad, los parametros del adc se reciben de este.
        Se inician los hilos de ejecución del programa.
        hiloHora está constantemente actualizando la hora y mostrándola en la esquina superior derecha del programa, además esta hora es utilizada para imprimir en tabla.
        hiloCargaMatriz crea una nueva matriz con la posición de los blancos.
        hiloPlotMain envía una señal para que se dibuje la matriz y los seguimientos
        seguimientoHilo controla los seguimientos activos.
        hiloCreacionSeguimiento es el encargado de gestionar posibles nuevos seguimientos.
        hiloSocket es el encargado de enviar paquete con seguimientos activos desde EVRT a RSC.
        """   	

        # Actualiza la hora actual y la muestra.
        hiloHora = Thread(target=self.updateHora, daemon=True)

        # Envia signal al hiloPlot para que dibuje matriz y seguimientos.
        hiloPlotMain = Thread(target=self.plotMain, daemon=True)

        # Controlador de los seguimientos activos.
        seguimientoHilo = Thread(target=self.seguimientoHilo, daemon=True)

        # Encargado de gestionar posibles nuevos seguimientos.
        hiloCreacionSeguimiento = Thread(target=self.creacionSeguimiento, daemon=True)   

        hilo_recibir       = Thread(target=WinPcapUtils.capture_on, args=(my_device,packet_callback), daemon=True)
        hilo_armar_M       = Thread(target=self.armar_M, args=(), daemon=True)     
        
                
        # Inicio de todos
        hiloHora.start()
        hiloPlotMain.start()
        seguimientoHilo.start()
        hiloCreacionSeguimiento.start()

        hilo_recibir.start()
        hilo_armar_M.start()

        self.hiloPlotMySeg.start()
        # Hilo global para mensajes de alerta
        global hiloAlertas
        hiloAlertas.signal_alertaReinicio.connect(self.alertaReinicioWork)
        hiloAlertas.signal_errorConexion.connect(self.errorConexionWork)
        hiloAlertas.start()
        
    def alertaReinicioWork(self):
        """
        Notifica al usuario de que debe reiniciar la aplicación para que el cambio de IP tenga efecto.
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle('Importante')
        msg.setText('Reinicie la aplicacion para que \nlos cambios surtan efecto.')
        msg.exec_()


    def errorConexionWork(self):
        """
        Notifica al usuario de que ocurrió un error al crear el socket.
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle('Importante')
        msg.setText('Error al crear el socket \nverifique que la IP sea correcta.')
        msg.exec_()


        
    def seguimientoHilo(self):
        """
        Recorre los seguimientos activos, para actualizar su tracking. En caso de perder el móvil, imprime un mensaje en la parte inferior derecha del programa, y lo anota en el archivo de logs.
        Actualiza el arreglo de seguimientos activos.
        """        
        while(1 > 0):
            self.mutexSeg.acquire()
            # Se recorren todos los seguimientos activos en el momento, para actualizar su tracking.
            # Si se perdió, se escribe en los logs del dia y posteriormente se elimina de los tracks.
            for ID in range(0,self.seguimientosActivos,1):
                self.seg.actualizarTracks(ID)                
                if(self.seg.TrackList[ID].Perdido):
                    self.escrituraEnLogs('****************** Se perdio el seguimiento con ID: '+str(ID+1)+' ******************')
                    self.sePerdioUno()
            todosTracks = np.array(self.seg.TrackList[0:self.seguimientosActivos])
            # Se eliminan aquellos seguimientos perdidos.
            for t in todosTracks:
                if (t.Perdido):                
                    self.seg.eliminarTrack(t.TrackID)
                    self.seguimientosActivos -=1
                    #self.botones_fin_track[self.seguimientosActivos].setVisible(False)    
                    #self.botones_fin_track[self.seguimientosActivos].setEnabled(False)
            self.mutexM.release()
        

    def plotMain(self):
        """
        Emite la señal al worker y duerme el tiempo restante de la vueltaRadar
        """    
        while (1 > 0):
            aux.acquire()
            self.hiloPlotMySeg.signal_plot.emit()
            #time.sleep(self.vueltaRadar)
                
                

    def dejarDeSeguir(self):
        """
        Captura el evento del click en dejar de seguir un seguimiento y actualiza tanto la tabla como los seguimientos activos.
        """
        # Encuentra cual fue el boton presionado y setea su tracking como perdido.
        # Posteriormente, el hilo que se encarga de actualizar los tracks lo encontrara perdido. Allí se dejara de seguir.
        sender = self.sender()
        nombre_boton = sender.objectName()
        tid = int(nombre_boton[-1])-1
        if (self.seg.TrackList[tid] != None):
            self.seg.TrackList[tid].Perdido = True        

    def onclick(self,event):
        """
        Comienza la búsqueda de un blanco en la zona clickeada por el usuario. En caso de encontrarlo se realiza un seguimiento y se comienza a mostrar por tabla. Si no lo encuentra, muestra un mensaje por pantalla.
        """
        try:
            # Se consiguen los valores distancia y angulo en la posicion del clickeo.
            self.limpiarPerdidosLabel()
            if(self.seguimientosActivos == self.maximaSeguimientos):
                self.label_perdidos.setText('Capacidad maxima de seguimientos alcanzada')
            else:
                dis = '%.0f'%(event.ydata)
                ang = math.degrees(event.xdata)
                if(ang < 0):
                    ang = 360 + ang
                ang = '%.0f'%(ang)
                self.nuevoDis = dis
                self.nuevoAng = ang
                self.mutexInicioSeg.release()
        except TypeError:
            pass

    def creacionSeguimiento(self):
        """
        Crea un nuevo seguimiento en la zona del radar donde clickeo el usuario. Si está lo suficientemente cerca de un móvil, comienza a seguirlo e informar sobre sus movimientos. De no encontrar nada cerca de donde se clickeo, muestra un mensaje por pantalla.
        """
        while(1):
            # Cuando el metodo 'onclick' libera el mutex, este metodo intenta agregar un nuevo seguimiento, si es que hay blanco.
            self.mutexInicioSeg.acquire()
            self.seg.iniciarTrack(float(self.nuevoDis),float(self.nuevoAng))
            self.seg.actualizarTracks(self.seguimientosActivos)
            t = self.seg.TrackList[self.seguimientosActivos]
            # Una vez agregado el nuevo track y luego de actualizar su tracking, verifica si está perdido
            # En caso de que esté perdido, lo elimina de los tracking activos.
            if (not t.Perdido):
                self.escrituraEnLogs('****************** Se inicio el seguimiento con ID: '+str(t.TrackID+1)+' ******************')
                self.seguimientosActivos +=1
                #self.botones_fin_track[t.TrackID].setEnabled(True)                
                #self.botones_fin_track[t.TrackID].setVisible(True)                
            else:
                self.seg.eliminarTrack(t.TrackID)
                self.showNoSeEncontro()

    # --------------------------
    # Metodos auxiliares varios.
    def escrituraEnLogs(self,texto):
        """
        Conjunto de operaciones para escribir un string recibido en el archivo de logs.
        """
        self.mutexFile.acquire()
        #self.file.write(texto+'\n')
        #self.file.flush()
        self.mutexFile.release()

    
    def actualizarUmbral(self):
        """
        Actualiza el valor del umbral según el slider.
        """
        self.valorUmbral=self.slider_umbral.value()

    def limpiarPerdidosLabel(self):
        """
        Limpia el label utilizado para notificar al usuario sobre seguimientos perdidos/no encontrados.
        """
        self.label_perdidos.setText('')

    def sePerdioUno(self):
        """
        Mensaje a mostrar cuando se pierde un seguimiento
        """
        self.label_perdidos.setText('Se perdio un seguimiento')

    def showNoSeEncontro(self):
        """
        Mensaje en caso de no encontrar un seguimiento donde se clickeo
        """
        self.label_perdidos.setText('No se encontro el seguimiento')
        
    def updateHora(self):
        """
        Actualiza la hora y la muestra en la esquina superior derecha
        """
        while(1):
            hoy = datetime.today()        
            self.label_hora.setText(hoy.strftime('%H:%M:%S'))
            time.sleep(1)
        
    
    def IP_EVRT_config(self):
        """
        Settea la IP inicial, si existe una en el archivo de cfg, la carga, caso contrario deja LOCALHOST por default.
        """
        global file_IP_EVRT
        global IP  

    def plotWorker(self,M):
        """
        Borra los blancos del radar y los vuelve a dibujar en sus posiciones actualizadas.
        También actualiza los datos en tabla para cada uno de los seguimientos activos.
        Al momento de actualizar la tabla, se escriben los mismos datos en el archivo de logs del día, y se envía esta información por socket a la pc WinXP.
        """
        self.RadarWidget.borrarPuntos()
        self.RadarWidget.plotearM(M)
        # Se genera una copia de los seguimientos (para lidiar con condiciones de carrera entre modificaciones y lecturas)
        #  VER TAMAñO DEL DATO.
        #t = time.time()
        TrackListCopy = np.copy(self.seg.TrackList)
        #print(time.time()-t)
        self.tabla_datos.clearContents()
        current_time = self.label_hora.text()
        # Recorremos los seguimientos activos para plotear en radar y en tabla.
        # El paquete con los seguimientos para enviar al otro terminal se arma aca.
        self.paqueteSocket = '('
        #t=time.time()
        for t in TrackListCopy:
            tAng = '%.2f'%(t.Pos[1])
            tDis = '%.2f'%(t.Pos[0])
            self.RadarWidget.plotear(float(tAng)/360*2*math.pi,float(tDis),500,'green',0.75)
            self.RadarWidget.canvas.ax.annotate(int(t.TrackID)+1, xy = (float(tAng)/360*2*math.pi,float(tDis)), color = 'white', fontsize = 12)
            tVel = '%.2f'%(math.sqrt(t.Vel[0]*t.Vel[0]+t.Vel[1]*t.Vel[1])*60*60)
            item0=QTableWidgetItem(tDis)
            item0.setTextAlignment(QtCore.Qt.AlignCenter)
            item1=QTableWidgetItem(tAng)
            item1.setTextAlignment(QtCore.Qt.AlignCenter)
            item2=QTableWidgetItem(tVel)
            item2.setTextAlignment(QtCore.Qt.AlignCenter)
            item3=QTableWidgetItem(current_time)
            item3.setTextAlignment(QtCore.Qt.AlignCenter)
            self.tabla_datos.setItem(int(t.TrackID), 0, item0)
            self.tabla_datos.setItem(int(t.TrackID), 1, item1)
            self.tabla_datos.setItem(int(t.TrackID), 2, item2)
            self.tabla_datos.setItem(int(t.TrackID), 3, item3)
            # Escritura en logs del dia.
            #self.escrituraEnLogs(str(t.TrackID+1)+'\t\t'+str(tDis)+'\t\t'+str(tAng)+'\t\t'+str(tVel)+'\t\t'+current_time)
            self.paqueteSocket = self.paqueteSocket + (tDis+'|'+tAng+'|'+tVel)
            self.paqueteSocket = self.paqueteSocket + ('&')
        #print(time.time()-t)
        self.paqueteSocket = self.paqueteSocket + (')')
        # if (self.mutexSocket.locked()):
        #     self.mutexSocket.release()
        self.RadarWidget.canvas.draw()

    def encode_booleans(bool_lst):
        res = 0
        for i, bval in enumerate(bool_lst):
            res += int(bval) << i
        return res

    def decode_booleans(intval, bits):
        res = []
        for bit in xrange(bits):
            mask = 1 << bit
            res.append((intval & mask) == mask)
        return res

    def armar_M(self):
    
        fila,columna = 0,0
        primer_HM =False
        primer_TRG=False
        SEQ_ctrl=-1

        while not primer_HM  or not primer_TRG:
             if not len(cola_recibido)==0:            
                data = cola_recibido.pop()
                palabras = np.empty(int(len(data)/4),dtype=object)
                for i in range(0,len(data),4):
                    palabras[int(i/4)] = binarios[data[i+3],data[i+2]]+binarios[data[i+1],data[i]]
                for palabra in palabras:
                    SEQ=int(palabra[0:2],2)
                    HM=int(palabra[2:3]) #Bit de HM            
                    TRG=int(palabra[8:13],2) #Bits de TRG
                    CFAR= palabra[13:] #Bits de CFAR
                    # if TRG:
                    #     print(TRG)
                    if HM:
                        print("llego HM")
                        primer_HM = True
                        break
                    if primer_HM and TRG:
                        primer_TRG = True
                        break
                    
        SEQ_ctrl = 1
        M=np.zeros((w,h),dtype=int).astype(int)
        M[fila,0:19-TRG]=np.array(list(CFAR[TRG:19]))
        columna=19-TRG

        cantidadCambios = 0
        start = time.time()
        cont = 0

        integer_list2 = []
        inicio=0
        #file = open('Datos.txt','wb')

        #file = open('Datos.txt','rb')
        cant = 0
        while 1:               
            if not len(cola_recibido)==0:        
                data = cola_recibido.pop()
                data = np.frombuffer(data,dtype=('u4'))

                x = (((data[:,None] & (1 << np.arange(32))[::-1])) > 0).astype(int)  # ORDEN IZQUIERDA MSB
                
                arreglo = []

                for i in range(0,len(x)):
                    SEC=x[i][0:2]
                    HM=x[i][2] #Bit de HM
                    BI=x[i][3:8] #Bits de BI
                    TRG=x[i][8:13] #Bits de TRG
                    CFAR=list(x[i][13:32]) #Bits de CFAR

                    if (HM==1):
                        #print(time.time() - start)
                        columna=1
                        fila=0
                        #print("Cantidad de cambios por HM: "+str(cantidadCambios))
                        cantidadCambios = 0

                        start=time.time()
                        self.plotWorker(M)
                        print(time.time() - start)

                        #start = time.time()

                    if not (1 in TRG):
                        for i in range(0,19):
                            if (M[fila,columna+i] != CFAR[i]):
                                    if not (1 in BI):
                                        M[fila,columna+i] = CFAR[i]
                                        cantidadCambios+=1
                        columna+=19
                        
                    else:
                        if not (1 in BI):
                            fila += 1
                            columna=1
                        else:        
                            fila += 1
                            columna=1                  
                                 
        
if __name__ == "__main__":
    
    with WinPcapDevices() as devices:
        for device in devices:
            print(device.description)
        
    ## Elejir la placa que se va a utilizar #######

    my_device = "Realtek PCIe GbE Family Controller"
                    
    ###############################################

    list_cont = []
    list_TRG = []

    app = QtWidgets.QApplication(sys.argv)
    x = RadarGUI() 
    app.exec_()
