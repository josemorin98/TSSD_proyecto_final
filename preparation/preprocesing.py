
from flask import Flask, request
from flask import Response
from flask import jsonify
import json
import threading
import requests
import sys
import queue
import time
import pandas as pd
import utils_balance as ub
from concurrent.futures import ThreadPoolExecutor
from csv import writer
import os
from datetime import datetime
import numpy as np

app = Flask(__name__)
app.debug = True

# Recibir los parametros
arg = sys.argv
# Estados del nodo
id_nodo = int(arg[1]) # ID posicion 1
election = False
puerto_nodo = int(arg[2]) # Puerto del contenedor
ip_container = arg[3] # ip del container
puerto_base = int(arg[5]) # puerto base
total_workers = int(arg[6]) # Total de proposer
puerto_conquer = int(arg[7]) # Puerto del conquer que reunira loa archivos

# Datos del coordinador
puerto_cor = 0
id_cor = 0
without_coordina = False
puertos_kill = []
verificar = False

# Verifica si es el coordinador
if (arg[4] == '1'):
    coordina = True
    id_cor = id_nodo
else:
    coordina = False

pet =0

# Info of aceptors
class NodeBully:
    def __init__(self,ide,ip_nodo,puerto):
        self.ide = ide
        self.ip_nodo = ip_nodo
        self.puerto = puerto
        
    def set_ide(self,ide):
        self.ide = ide
    
    def set_ip_nodo(self,ip):
        self.ip_nodo = ip
        
    def set_puerto(self,puerto):
        self.puerto = puerto

# Creamos nodo local
node_local = NodeBully(ide=id_nodo,
                       ip_nodo=ip_container,
                       puerto=puerto_nodo)

proposer_lider = NodeBully(ide=0,
                       ip_nodo='0',
                       puerto=0)

node_conquer = NodeBully(ide=0,
                        ip_nodo=ip_container,
                        puerto=puerto_conquer)

nodos_workers = list()

# ------------------------------------------ BULLY  ------------------------------------
# Inicializa otros nodos proposer para conocerlos
def init_nodos(m):
    global puerto_base
    global total_workers
    global node_local
    nodos = list()
    for x in range(total_workers):
        if (node_local.puerto != (puerto_base+x)):
            aux = NodeBully(ide=x+1,
                            ip_nodo=node_local.ip_nodo,
                            puerto=puerto_base+x)
            nodos.append(aux)
    return nodos
        
# Recibe los datos del nuevo coordinador
@app.route('/COORDINATOR', methods = ['POST'])
def fun_coordinator():
    global pet
    global election
    global proposer_lider
    # recibimos json
    message = request.get_json()
    # Actualizamos el proposer lider
    proposer_lider.set_ide(message['id'])
    proposer_lider.set_ip_nodo(message['ip'])
    proposer_lider.set_puerto(message['puerto'])
    # Coordinador llegó
    app.logger.info('------ COORDINATOR '+str(proposer_lider.ide)+' ------')
    election = False
    without_coordina = False
    pet =0
    # Comienza el proceso de verificacion
    monitor = threading.Thread(target=fun_verificar)
    monitor.start()
        
    return jsonify({'response':'RECIBIDO'})

# Hace el proceso de election
@app.route('/ELECTION',methods = ['POST'])
def fun_election():
    global election
    global node_local
    if (election==True):
        # Recibi el post
        message = request.get_json()
        # Id y puerto del nodo que hace peticion de election
        id_vecino = message['id']
        # app.logger.info('------ ELECTION CON EL NODO '+str(id_vecino) + ' ------')
        # Si el nodo actual es mayor
        if (node_local.ide>id_vecino):
            # app.logger.info('------ SOY MAYOR ------')
            return jsonify({'response':'OK'})    
        # Si el vecino es mayor
    else:
            # app.logger.info('------ SOY MENOR ------')
        return jsonify({'response':'NO'})

# Funcion de verificacion del coordinator
def fun_verificar():
    global pet
    global election
    global without_coordina
    global proposer_lider
    global node_local
    
    while True:
        try:
            if (election == False):
                # Verificamos si no somos el mismo
                if (proposer_lider.puerto == node_local.puerto):
                    break
                time.sleep(5+(id_nodo))
                url = proposer_lider.ip_nodo+':'+str(proposer_lider.puerto)+'/PRUEBA'
                headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
                req = requests.post('http://'+url, headers=headers)
                # app.logger.info('------ SOY EL NODO No.'+str(id_nodo)+' - '+str(puerto_nodo)+'------')
                pet += 1
                app.logger.info('------('+str(pet)+') ACTIVO LIDER ='+str(proposer_lider.ide)+' - ('+str(node_local.puerto)+')------')
        except requests.exceptions.ConnectionError:
            # Proceso de election
            puertos_kill.append(proposer_lider.puerto)
            # Notifica a todos de election
            time.sleep(10)
            if(election == False and without_coordina == False):
                for proposer in nodos_workers:
                    if (proposer.puerto not in puertos_kill): 
                        # requests
                        # app.logger.info('------ ME DI CUENTA ------')
                        app.logger.info('------ ME DI CUENTA ('+str(node_local.ide)+') ------')
                        url = proposer.ip_nodo+':'+str(proposer.puerto)+'/PRE'
                        # url = '148.247.201.221:'+puerto+'/PRE'
                        # Enviar petricion de eleccion
                        headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
                        req = requests.post('http://'+url, headers=headers)
                        response_json = req.json()
                        app.logger.info('------ '+response_json['response']+' ('+str(proposer.ide)+') ------')
                # Inicio proceo de election
                app.logger.info('------ PROCESO ------')
                election = True
                init()
            break
    
# Verificacion de actividad
@app.route('/PRE',methods = ['POST'])
def pre():
    global election
    election = True
    without_coordina = True
    app.logger.info('------ ELECTION ------')
    return jsonify({'response':'ELECTION'})

# Verificacion de actividad
@app.route('/INICIO_ELECTION',methods = ['POST'])
def inicio_election():
    global election    
    # time.sleep(10)
    init()
    return jsonify({'response':'OK'})

# Verificacion de actividad
@app.route('/PRUEBA',methods = ['POST'])
def prueba():
    global proposer_lider
    app.logger.info('------ Verificacion '+str(proposer_lider.ide)+' ------')
    return jsonify({'response':'SI'})

def init():
    global coordina
    global proposer_lider
    global node_local
    global total_workers
    global node_conquer
    # Inicia la election
    cont=0
    for proposer in nodos_workers:
        if (node_local.puerto < proposer.puerto):
            if (proposer.puerto not in puertos_kill):
                # requests
                url = proposer.ip_nodo+':'+str(proposer.puerto)+'/ELECTION'
                # url = '148.247.201.221:'+puerto+'/ELECTION'
                datas = {
                    'id':node_local.ide,
                    'ip':node_local.ip_nodo,
                    'puerto':node_local.puerto
                }
                try:
                    headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
                    req_i = requests.post('http://'+url, data=json.dumps(datas), headers=headers)
                    # Recibir
                    responde_json_ = req_i.json()
                    # Existe uno mayor
                    if (responde_json_['response'] == 'OK'):
                        app.logger.info('------ ('+str(proposer.puerto)+') OK ------')
                        # Se manda notifiacion al primer mayor
                        if(cont==0):
                            mayor_puerto = proposer.puerto
                            mayor_ip = proposer.ip_nodo
                            cont = 1
                except requests.exceptions.ConnectionError:
                    print('')
    # Envia la notificion al siguiente puerto mayor a que haga la election
    if (cont == 1):
        url = mayor_ip+':'+str(mayor_puerto)+'/INICIO_ELECTION'
        # url = '148.247.201.221:'+mayor_puerto+'/INICIO_ELECTION'
        try:
            headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
            req = requests.post('http://'+url, data=json.dumps(datas), headers=headers)
            # Recibir
            responde_json = req.json()
            # Existe uno mayor
            if (responde_json['response'] == 'OK'):
                app.logger.info('------ NODO NUEVO PARA ELECTION '+str(mayor_puerto)+' ------')
                # # Se manda notifiacion al primer mayor
                # if(cont==0):
                #     mayor_puerto = puerto
                #     cont = 1
        except requests.exceptions.ConnectionError:
            print('')   
    else:
        # Soy el nuevo coordinador
        proposer_lider = node_local
        coordina = True
        app.logger.info('------ SOY EL NUEVO COORDINATOR No.'+str(node_local.ide)+'------')
        for proposer in nodos_workers:
            if (proposer.puerto not in puertos_kill):
        # for puerto in puertos:
            # if (puerto not in puertos_kill):
                # requests
                url = proposer.ip_nodo+':'+str(proposer.puerto)+'/COORDINATOR'
                # url = '148.247.201.221:'+puerto+'/COORDINATOR'
                datas = {
                    'id':node_local.ide,
                    'ip':node_local.ip_nodo,
                    'puerto':node_local.puerto
                }
                headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
                req = requests.post('http://'+url, data=json.dumps(datas), headers=headers)
                # Recibir
                responde_json = req.json()
                app.logger.info('------ SE NOTIFICO AL NODO '+str(proposer.puerto) + ' - ' + responde_json['response']+' ------')
        # Se notifica al conquer cuantos son en total
        num_works = total_workers-len(np.unique(puertos_kill))
        app.logger.info(str(total_workers) + ' - '+ str(len(np.unique(puertos_kill))) + ' = ' + str(num_works))
        datas = {'works':num_works}
        url = "http://"+node_conquer.ip_nodo+':'+str(node_conquer.puerto)+'/workers'
        req = requests.post(url, data=json.dumps(datas), headers=headers)
        

# ------------------------------------------ START CONTAINER -----------------------------------

nodos_workers = init_nodos(m=total_workers)

def append_list_as_row(file_name, list_of_elem):
    # Open file in append mode
    with open(file_name, 'a+', newline='\n') as write_obj:
        # Create a writer object from csv module
        csv_writer = writer(write_obj)  
        # Add contents of list as last row
        csv_writer.writerow(list_of_elem)
        
# Coordinador
if (coordina==True):
    # global node_local
    
    proposer_lider = node_local
    # Notifico que es el coordinador
    app.logger.info('------ SOY EL COORDINADOR - No.'+str(node_local.ide) + ' ------')
    time.sleep(10)
    app.logger.info(str(len(nodos_workers))+' lista ------- ')
    for proposer in nodos_workers:
        if (proposer.puerto not in puertos_kill):            
            # requests
            # node_local.ip_nodo
            url = proposer.ip_nodo+':'+str(proposer.puerto)+'/COORDINATOR'
            app.logger.info(url)
            # url = '148.247.201.221:'+puerto+'/COORDINATOR'
            datas = {
                'id':node_local.ide,
                'ip':node_local.ip_nodo,
                'puerto':node_local.puerto
            }
            headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
            req = requests.post('http://'+url, data=json.dumps(datas), headers=headers)
            # Recibir
            responde_json = req.json()
            app.logger.info('------ SE NOTIFICO AL NODO '+str(proposer.ide) + ' - ' + responde_json['response']+' ------')
            

# ------------------------------------------ Balanceo de carga -----------------------------------
@app.route('/preprocer',methods=['POST'])
def preproces():
    global nodos_workers
    global total_workers
    
    message = request.get_json()
    need_peers = total_workers-len(np.unique(puertos_kill))
    # Atrae lo puertos
    # puertos_o,ids = dame_n_nodos(need_peers)
    # timpo final
    # fin = time.time()
    # añadir tiempos a csv
    # append_list_as_row('./data/tiempos_busqueda.csv', [need_peers,(fin-inicio)])
    # app.logger.error(fin-inicio)
    
    init_data = ub.init_workres_array(need_peers)
    data_clus = ub.read_CSV(message['name']) # DataPreprocess
    
    # numero AÑOS DIAS O MESES
    type_balance = 'RR'
    type_balance_str = 'Topoforma'
    list_balance = data_clus[type_balance_str].unique()
    
    if (type_balance=='RR'): # Balanceador Round Robin
        init_data = ub.RaoundRobin(init_data,list_balance,need_peers)    
    else:# Balanceador Round Robin
        init_data = ub.RaoundRobin(init_data,list_balance,need_peers)
    
    x = 0
    app.logger.info('----------------------- '+str(need_peers))
    for aceptor in nodos_workers:
        try:
            if (aceptor.puerto not in puertos_kill):
                concac=[]
                app.logger.info('----------------------- '+str(init_data[x]))
                for val in init_data[x]:
                    concac.append(data_clus[data_clus[type_balance_str]==val])
                data_fin = pd.concat(concac)
                name = "ID_"+str(aceptor.ide)+"_Port_"+str(aceptor.puerto)+"_LD="+type_balance+"_DLB=Antena"
                data_fin.to_csv("./data/"+name+".csv")
                url = aceptor.ip_nodo+':'+str(aceptor.puerto)+'/clean'
                datas = {
                    'work': need_peers,
                    "K": message['K'],
                    "name": name
                }
                # Hace la peticion
                headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
                req = requests.post('http://'+url, data=json.dumps(datas), headers=headers)
                responde_json = req.json()
                app.logger.info('------------ Worker '+str(aceptor.ide) + ' - ' + responde_json['response']+' ------')
                x=x+1
        # en caso de que uno falle
        except requests.exceptions.ConnectionError:
            app.logger.info('------ Worker '+str(aceptor.ide) + ' - FALLO  ------')
    return jsonify({'response':'SI'}) 


def Preprocesing_data(data_cl,name_file,K_,work):
    inicio = time.time()
      # Lectura de archivos
    data_clima =  data_cl
    print('Lectura...Listo')

    # ELiminacion de columnas nulas y remplazo de valores Null a Nan
    data_clima_clus = data_clima.copy()
    data_clima_clus = data_clima_clus.drop(['Codigo','Hidroregion','Topoforma','Differential_max','Differential_min','Humedad', 'Presion_barometrica', 'Precipitacion', 'Radiacion_solar', 'Etiqueta_clase'], axis=1)
    data_clima_clus = data_clima_clus.replace('Null',None)
    data_clima_clus = data_clima_clus.replace('NaN',None)
    print('Eliminacion...Listo')

    # Relleno de valores faltantes
    data_clima_clus = data_clima_clus.fillna({'Temp_mean_emas': -99.0,})
    for x in range (len(data_clima_clus)):
        if ((data_clima_clus.loc[x,'Temp_max_emas'] == -99.0) or (np.isnan(data_clima_clus.loc[x,'Temp_max_emas'])) or (data_clima_clus.loc[x,'Temp_max_emas'] > data_clima_clus.loc[x,'Temp_max_merra']+5) or (data_clima_clus.loc[x,'Temp_max_emas'] < data_clima_clus.loc[x,'Temp_max_merra']-5)): 
            data_clima_clus.loc[x,'Temp_max_emas'] = data_clima_clus.loc[x,'Temp_max_merra']
        if ((data_clima_clus.loc[x,'Temp_min_emas'] == -99.0) or (np.isnan(data_clima_clus.loc[x,'Temp_min_emas'])) or (data_clima_clus.loc[x,'Temp_min_emas'] > data_clima_clus.loc[x,'Temp_min_merra']+5) or (data_clima_clus.loc[x,'Temp_min_emas'] < data_clima_clus.loc[x,'Temp_min_merra']-5)):
            data_clima_clus.loc[x,'Temp_min_emas'] = data_clima_clus.loc[x,'Temp_min_merra']
        if ((data_clima_clus.loc[x,'Temp_mean_emas'] == -99.0)):
            data_clima_clus.loc[x,'Temp_mean_emas'] = data_clima_clus.loc[x,'Temp_mean_merra']
    data_clima_clus.Temp_mean_emas = data_clima_clus.Temp_mean_emas.astype(np.float64)
    print('Relleno...Listo')

    # Separacion de fecha
    years=[]
    months=[]
    days=[]
    all = data_clima_clus.iloc[:,2]
    for x in all:
        date_time_obj = datetime.strptime(x, '%d/%M/%Y')
        years.append(date_time_obj.strftime("%Y"))
        months.append(date_time_obj.strftime("%M"))
        days.append(str(date_time_obj.strftime("%d")))
    data_clima_clus = data_clima_clus.drop(columns='Fecha')
    data_clima_clus.insert(1,"Ano",years,True)
    data_clima_clus.insert(2,"Mes",months,True)
    data_clima_clus.insert(3,"Dia",days,True)
    print('Fecha...Listo')

    name_fin = 'DataPreproces_'+name_file
    # Create csv
    # data_clima_clus.to_csv("./"+name+".csv")
    app.logger.error('----------------------'+name_fin)
    data_clima_clus = data_clima_clus.iloc[: , 1:]
    data_clima_clus.to_csv("./data/"+name_fin+".csv")
    fin = time.time()
    
    # envio
    append_list_as_row('./data/tiempos_pre.csv', [work,(fin-inicio)])
    url = "http://"+node_conquer.ip_nodo+':'+str(node_conquer.puerto)+'/join'
    headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
    # app.logger.error(url)
    data = {"K": K_,
               "name":'DataPreproces_'+name_file}
    app.logger.error('----------------------'+url)
    requests.post(url, data=json.dumps(data), headers=headers)
    return data_clima_clus

def append_list_as_row(file_name, list_of_elem):
    # Open file in append mode
    with open(file_name, 'a+', newline='') as write_obj:
        # Create a writer object from csv module
        csv_writer = writer(write_obj)
        # Add contents of list as last row in the csv file
        csv_writer.writerow(list_of_elem)
        
@app.route('/clean', methods = ['POST'])
def preprocesing():
    global node_conquer
    message = request.get_json()
    name_file = message['name']
    data_file = ub.read_CSV(name_file)
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        # app.logger.info('executoooooor')
        # executor.submit(prueba_clus,k_,type_cluster,data_clima,name,wor)
    # with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        executor.submit(Preprocesing_data,data_file,name_file,message['K'],message['work'])
        
    # data_2 = Preprocesing_data(data_file,name_file)
    
    # data_2,name = Preprocesing(data_file)
    #     append_list_as_row('./data/tiempos_pre.csv', [message['work'],(fin-inicio)])
    #     url = "http://"+node_conquer.ip_nodo+':'+str(node_conquer.puerto)+'/join'
    #     headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
    # # app.logger.error(url)
    #     data = {"K": message['K'],
    #            "name":'DataPreproces_'+name_file}
    #     app.logger.error('----------------------'+url)
    #     requests.post(url, data=json.dumps(data), headers=headers)
    return jsonify({'response':"OK"})

        
if __name__ == '__main__':
    app.run(host= '0.0.0.0',debug=True)
