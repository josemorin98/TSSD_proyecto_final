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
import glob
import os

arg = sys.argv
workers= int(arg[1])
ip= arg[2]
port = int(arg[3])
cont_workers = 0
status_wait = True
# Inicicalizar Flask
# from flask import Flask
app = Flask(__name__)
app.debug = True
app.config['PROPAGATE_EXCEPTIONS'] = True

class nodo_bak:
    def __init__(self,ip,puerto):
        self.ip = ip
        self.puerto = puerto
    
    def update_nodo(self,ip,puerto):
        self.ip = ip
        self.puerto = puerto
    
    def get_url(self):
        url = 'http://'+self.ip+':'+str(self.puerto)
        return url
    
bak_principal = nodo_bak(ip=ip,puerto=port)

def enviar_datos(url,datas):
    headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
    requests.post(url, data=json.dumps(datas), headers=headers)
    return 1

@app.route('/bak',methods = ['POST'])
def bak():
    global bak_principal
    message = request.get_json()
    bak_principal.update_nodo(message['ip'],message['puerto'])
    app.logger.info('..............' + bak_principal.get_url())
    return jsonify({'response':'Update nodo BaK'})

@app.route('/workers',methods = ['POST'])
def workers_num():
    global workers
    message = request.get_json()
    workers = message['works']
    app.logger.info('.............. total de workers = ' + str(workers))
    return jsonify({'response':'Update workers'})

@app.route('/join',methods = ['POST'])
def k_dividir():
    global cont_workers
    global status_wait
    global bak_principal
    
    if(status_wait==True and cont_workers==0):
        cont_workers=1
        status_wait=False
    # Si es menor entonces sumamos
    elif (status_wait==False and cont_workers<workers):
        cont_workers = cont_workers + 1
    # Ya son todos
    app.logger.info('************************ Llego el  ' + str(cont_workers) + ' de ' + str(workers))
    if(status_wait==False and cont_workers==workers):
        message = request.get_json()
        # Reiniciamos el contador y el estado
        status_wait = True
        cont_workers=0
        path='./data/'
        all_files = glob.glob(os.path.join(path, "DataPreproces_*.csv"))
        df_from_each_file = (pd.read_csv(f, sep=',') for f in all_files)
        df_merged  = pd.concat(df_from_each_file, ignore_index=True)
        df_merged = df_merged.iloc[: , 1:]
        name="DataPreproces_marge.csv"
        df_merged.to_csv("./data/"+name)
        app.logger.info('************************ Se realizó el Marge')
        # enviar datos
        # url = "http://"+ip+":"+str(port)+"/recibir"
        data = {"K": message['K'],
                "name":message['name']}
        url = bak_principal.get_url()
        rq = enviar_datos(url+"/recibir",data)
        return jsonify({'response':'Marge_DataProces'})
    
    return jsonify({'response':'Wait more'})
    
# Prueba
@app.route('/Prueba')
def prueba():
    app.logger.error('Si llegooooooo')
    return jsonify({'hola':"SI"})


if __name__ == '__main__':
    app.run(host= '0.0.0.0',debug=True)

# path = "/home/morin/Escritorio/Proyecto_Final_TSSD/Files/"


# prueba = pd.read_csv(path+'ID_1_Port_5600_LD=RR_DLB=Antena.csv')
# proces_prueba = Preprocesing_data(prueba,'ID_1_Port_5600_LD=RR_DLB=Antena.csv')
# print(proces_prueba)

