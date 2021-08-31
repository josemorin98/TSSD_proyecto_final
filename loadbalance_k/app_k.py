# Librerias
import pandas as pd
import numpy as np
from datetime import datetime
# Librerias Flask
from flask import Flask, request
from flask import render_template
from flask import Response
from flask import jsonify
import json
import sys
import random
import requests
import threading
import time
from csv import writer

arg = sys.argv
workers= int(arg[1])
ip= arg[2]
port = int(arg[3])
puerto_base = int(arg[4])
nodos_workers = list()
rangos = list()
# Inicicalizar Flask
# from flask import Flask
app = Flask(__name__)
app.debug = True
app.config['PROPAGATE_EXCEPTIONS'] = True

class Nodo:
    def __init__(self,ip,puerto):
        self.ip = ip
        self.puerto = puerto
    
    def update_nodo(self,ip,puerto):
        self.ip = ip
        self.puerto = puerto
    
    def get_url(self):
        url = 'http://'+self.ip+':'+str(self.puerto)
        return url
    
def init_workres_array(workers):
    pet_in = list()
    for i in range(workers):
        pet_in.append([])
    return pet_in

def RaoundRobin(cargas, traza, workers):
    for x in range(len(traza)):
        select_bin = x % workers
        cargas[select_bin].append(traza[x])
    return cargas

def enviar_datos(url,datas):
    headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
    requests.post(url, data=json.dumps(datas), headers=headers)

@app.route('/recibir',methods = ['POST'])
def k_dividir():
    global workers
    global nodos_workers
    # inicio = time.time()
    # Rwcibe los datos
    message = request.get_json()
    k_ = message['K']
    workers_ = len(nodos_workers)
    # genera los balaneacdores vacios
    init_k = init_workres_array(workers_)
    # Divide las cargas entre los n workers
    init_k = RaoundRobin(init_k,k_,workers_)
    # Despliega los balanceos
    # Calculo de las ip
    peticiones = []
    for x in range(workers_):
        if (len(init_k[x])>0):
            # url = "http://"+ip+":"+str(port)+str(x*100)+"/recibir"
            data = {"K": init_k[x],
                    "name":message['name']}
            url=nodos_workers[x].get_url()+'/RECIBIR_BALAANCE'
            aux = threading.Thread(target=enviar_datos,args=(url,data))
            aux.start() 
    # fin = time.time()
    # app.logger.error("Balance K ------- = "+str(fin-inicio))
    # append_list_as_row('./data/tiempos_BaK.csv', [workers,(fin-inicio)])
    return jsonify({'response':'Hecho'})

def append_list_as_row(file_name, list_of_elem):
    # Open file in append mode
    with open(file_name, 'a+', newline='') as write_obj:
        # Create a writer object from csv module
        csv_writer = writer(write_obj)
        # Add contents of list as last row in the csv file
        csv_writer.writerow(list_of_elem)   
# Prueba
@app.route('/save_workers',methods = ['POST'])
def prueba():
    global nodos_workers
    global rangos
    global workers
    # recibe mensajes
    message = request.get_json()
    ip_ = message['ip']
    puerto_ = message['puerto']
    no = Nodo(ip_,puerto_)
    app.logger.info('----- workers=' + str(workers))
    for nodo in nodos_workers:
        app.logger.info('........ guardado = ' + nodo.get_url())
    # encuentra la posicion
    app.logger.info('----- llego =' + ip_ + ' - ' + str(puerto_))
    for val in range(workers):
        # ultima posicion
        app.logger.info('----- rangos =' + str(rangos[val]) + ' - ' + str(val))
        if ((val+1)==workers):
            # se encuentra en la posicion val
            nodos_workers[val] = no
            app.logger.info('-----   Url =' + nodos_workers[val].get_url())
            return jsonify({'response':'Guardado'})
        elif (puerto_>=rangos[val] and puerto_<=rangos[val+1]):
            # se encuentra en la posicion val
            nodos_workers[val] = no
            app.logger.info('***** Url=' + nodos_workers[val].get_url())
            return jsonify({'response':'Guardado'})

@app.route('/see_workers',methods = ['POST'])
def prueba_see():
    global nodos_workers
    for nodo in nodos_workers:
        app.logger.info('----- Url=' + nodo.get_url())
    return jsonify({'response':'Hecho'})
    
def init_rangos():
    rangos_ = list()
    no = Nodo(ip,port)
    for x in range(workers):
        nodos_workers.append(no)
        ran = puerto_base+(x*100)
        rangos_.append(ran)
    return rangos_

rangos = init_rangos()

if __name__ == '__main__':
    app.run(host= '0.0.0.0',debug=True)