
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
total_workers = int(arg[6]) # Total de workers
# puerto_conquer = int(arg[7]) # Puerto del conquer que reunira loa archivos

# Datos del coordinador
puerto_cor = 0
id_cor = 0
without_coordina = False
puertos_kill = []
verificar = False
estatus = True
# Verifica si es el coordinador
if (arg[4] == '1'):
    coordina = True
    id_cor = id_nodo
else:
    coordina = False

pet =0
inicio_global = 0
fin_global = 0

tota = np.power(2,total_workers)-1

# Info of aceptors
class NodeBully:
    def __init__(self,ide,ip_nodo,puerto,total,antesesor,sucesor):
        self.ide = ide
        self.ip_nodo = ip_nodo
        self.puerto = puerto
        self.name = ub.conc(ip_nodo, str(puerto))
        self.id_nodo = ub.hash(self.name,total)
        self.antesesor = antesesor
        self.sucesor = sucesor
        self.sucesor_port = 0
        self.antesesor_port = 0
    
    def url_request(self):
        url = 'http://'+self.name
        return url
        
    def set_ide(self,ide):
        self.ide = ide
    
    def set_ip_nodo(self,ip):
        self.ip_nodo = ip
        
    def set_puerto(self,puerto):
        self.puerto = puerto
    
    def set_antesesor(self,ante,port):
        self.antesesor = ante
        self.antesesor_port = port
        
    def set_sucesor(self,suce,port):
        self.sucesor = suce
        self.sucesor_port = port

# Creamos nodo local
node_local = NodeBully(ide=id_nodo,
                       ip_nodo=ip_container,
                       puerto=puerto_nodo,
                       total=tota,
                       antesesor=0,
                       sucesor=0)

proposer_lider = NodeBully(ide=0,
                       ip_nodo='0',
                       puerto=0,
                       total=tota,
                       antesesor=0,
                       sucesor=0)


nodos_workers = list()

# ------------------------------------------ BULLY  ------------------------------------
# Inicializa otros nodos proposer para conocerlos
# def init_nodos(m):
#     global puerto_base
#     global total_workers
#     global node_local
#     nodos = list()
#     for x in range(total_workers):
#         if (node_local.puerto != (puerto_base+x)):
#             aux = NodeBully(ide=x+1,
#                             ip_nodo=node_local.ip_nodo,
#                             puerto=puerto_base+x)
#             nodos.append(aux)
#     return nodos

# Funcion para obtener puertos
def init_nodos_chord(m):
    global puerto_base
    global node_local
    global total_workers
    nodos = list()
    total = np.power(2,m)-1
    for x in range(total_workers):
        if (x<=total_workers+1):
            if (node_local.puerto != (puerto_base+x)):
                iden = x+1
            else:
                iden=id_nodo
            aux = NodeBully(ide=iden,
                            ip_nodo=ip_container,
                            puerto=(puerto_base+x),
                            total=total,
                            antesesor=0,
                            sucesor=0)
            nodos.append(aux)
        else:
            break
    return nodos

# Recibe los datos del nuevo coordinador
@app.route('/COORDINATOR', methods = ['POST'])
def fun_coordinator():
    global pet
    global election
    global proposer_lider
    global fin_global
    global inicio_global
    global node_local
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
    if(inicio_global!=0):
        fin_global = time.time()
        append_list_as_row('./data/tiempos_bully_BaK.csv', [node_local.ide,proposer_lider.ide,(fin_global-inicio_global)])
        inicio_global=0
    # Comienza el proceso de verificacion
    monitor = threading.Thread(target=fun_verificar)
    monitor.start()
    init_chord()    
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
    global inicio_global
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
            inicio_global = time.time()
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
        init_chord()
        datas = {
        'ip':node_local.ip_nodo,
        'puerto':node_local.puerto
        }
        url = node_local.ip_nodo+':5701/save_workers'
        req = requests.post('http://'+url,data=json.dumps(datas), headers=headers)


# ------------------------------------------ START CONTAINER -----------------------------------

nodos_workers = init_nodos_chord(m=total_workers)

def append_list_as_row(file_name, list_of_elem):
    # Open file in append mode
    with open(file_name, 'a+', newline='\n') as write_obj:
        # Create a writer object from csv module
        csv_writer = writer(write_obj)  
        # Add contents of list as last row
        csv_writer.writerow(list_of_elem)
     

# ------------------------------------------ Balanceo de carga -----------------------------------
nodos_in_m = list()
nodos_online = list()

# Inicializar nodos para chord
def init_chord():
    global nodos_in_m
    global total_workers
    global nodos_workers
    global nodos_online
    # Obtiene los nodos para m = total_workers
    # nodos_in_m = init_nodos_chord(total_workers)
    # Se realiza un request a cada nodos para saber si estan activos
    nodos_online = info_all_nodos(nodos_workers)
    # Se confgura el sucesor y antesesor
    set_sucesor_antesesor(nodos_online)
    # app.logger.error(len(nodos_online))           

# Configuramos los nodos antesesores y sucesores
def set_sucesor_antesesor(nodos_online):
    global node_local
    pos = [x.name for x in nodos_online].index(node_local.name)
    app.logger.info('POSICION - ' + str(pos))
    if(pos == 0):
        # Soy el primero
        node_local.set_antesesor(nodos_online[-1].id_nodo, nodos_online[-1].puerto)   # Antesesor
        node_local.set_sucesor(nodos_online[1].id_nodo, nodos_online[1].puerto)        # Sucesor
    elif(pos == len(nodos_online)-1):
        # Soy el ultimo
        node_local.set_antesesor(nodos_online[pos-1].id_nodo, nodos_online[pos-1].puerto)    # Antesesor
        node_local.set_sucesor(nodos_online[0].id_nodo, nodos_online[0].puerto)              # Sucesor
    else:
        # Estoy en el intermedio
        node_local.set_antesesor(nodos_online[pos-1].id_nodo, nodos_online[pos-1].puerto)    # Antesesor
        node_local.set_sucesor(nodos_online[pos+1].id_nodo, nodos_online[pos+1].puerto)      # Sucesor
    
# Saber que nodos estan activos
def info_all_nodos(nodos):
    global puerto_nodo
    nodos_online_= list()
    #  Convierte lista de json to string
    # json_string = json.dumps([ob.__dict__ for ob in nodos])
    datas = {
        'MSJ': 'INCIO'
    }
    for x in nodos:
        if (x.puerto != node_local.puerto):
            try:
                # app.logger.error('entroooo' + x.url_request())
                req = envio_request_with_datas(url=x.url_request(),
                                           comand='/NODOS',
                                           datas=datas)
                # app.logger.error(req['response'])
                if (req['response']=='OK'): # Guardo los nodos que respondan con un OK
                    # Ultimo nodo añadido es el antesesor
                    nodos_online_.append(x)
                    
            except :
                pass
    app.logger.info('------ RECIBIDOS ------')
    nodos_online_.append(node_local)
    # app.logger.info(nodos_online_)
    nodos_online_ = sorted(nodos_online_, key=lambda chord_node : chord_node.id_nodo)
    return nodos_online_

# Recibe todos los nodos en m
@app.route('/NODOS',methods = ['POST'])
def nodos_recibidos():
    global nodos_in_m
    global estatus
    message = request.get_json()
    aux_nodos = message['MSJ']
    # app.logger.info(estatus)
    if (estatus == True):
        return jsonify({'response':'OK'})
    else:
        return jsonify({'response':'NO'})

# Envio a otro nodos con datos
def envio_request_with_datas(url,comand,datas):
    headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
    req = requests.post(url+comand,data=json.dumps(datas), headers=headers)
    return req.json() 

# Envio a otro nodo sin datos
def envio_request_witout_return(url,comand,datas):
    headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
    req = requests.post(url+comand, data=json.dumps(datas), headers=headers)
    return 1

# Retorna nodos vecinos disponibles
def dame_n_nodos(peers):
    global node_local
    global total_workers
    global nodos_online
    if (peers<total_workers+1):
        # peers necesarios son menos o igual a los disponibles
        if(peers==1):
            puertos = list()
            ids = list()
            puertos.append(node_local.sucesor_port)
            ids.append(node_local.sucesor)
            return puertos, ids
        # mis dos vecinos
        elif(peers==2):
            puertos = list()
            ids = list()
            puertos.append(node_local.sucesor_port)
            puertos.append(node_local.antesesor_port)
            ids.append(node_local.sucesor)
            ids.append(node_local.antesesor)
            return puertos, ids
        # si es par
        elif (ub.par(peers)):
            dib = peers/2
            # Se envia al nodo suscesor y antesesor
            puertos_suc = list()
            puertos_ante = list()
            id_suc = list()
            id_ante = list()
            datas = {
                'id_solicitante': node_local.id_nodo,
                'num':dib,
                'ids':id_suc,
                'puertos':puertos_suc,
                'tipo':'S'
            }
            # sucesor
            req = envio_request_with_datas('http://'+node_local.ip_nodo+':'+str(node_local.sucesor_port),'/IP_NODO',datas)
            puertos_suc = req['puertos']
            id_suc=req['ids']
            # antesesor
            datas = {
                'id_solicitante': node_local.id_nodo,
                'num':dib,
                'ids':id_ante,
                'puertos':puertos_ante,
                'tipo':'A'
            }
            req = envio_request_with_datas('http://'+node_local.ip_nodo+':'+str(node_local.antesesor_port),'/IP_NODO',datas)
            puertos_ante = req['puertos']
            id_ante = req['ids']            
            return (puertos_suc+puertos_ante),(id_suc+id_ante)
        # Es impar
        elif(ub.par(peers)==False):
            dib = (peers-1)/2
            # Se envia al nodo suscesor y antesesor
            puertos_suc = list()
            puertos_ante = list()
            id_suc = list()
            id_ante = list()
            datas = {
                'id_solicitante': node_local.id_nodo,
                'num':dib+1,
                'ids':id_suc,
                'puertos':puertos_suc,
                'tipo':'S'
            }
            # sucesor
            app.logger.error('********************************************** ' + 'http://'+node_local.ip_nodo+':'+str(node_local.sucesor_port))
            req_suc = envio_request_with_datas('http://'+node_local.ip_nodo+':'+str(node_local.sucesor_port),'/IP_NODO',datas)
            puertos_suc = req_suc['puertos']
            id_suc = req_suc['ids']
            # app.logger.error('Sucesor')
            # app.logger.error(puertos_suc)
            # antesesor
            datas = {
                'id_solicitante': node_local.id_nodo,
                'num':dib,
                'ids':id_ante,
                'puertos':puertos_ante,
                'tipo':'A'
            }
            req_ante = envio_request_with_datas('http://'+node_local.ip_nodo+':'+str(node_local.antesesor_port),'/IP_NODO',datas)
            puertos_ante = req_ante['puertos']
            id_ante = req_ante['ids']
            # app.logger.error('Antesesor')
            # app.logger.error(puertos_ante)
            # app.logger.error((puertos_suc+puertos_ante))
            return (puertos_suc+puertos_ante),(id_suc+id_ante)
    else:
        puertos = list()
        ids = list()
        for x in nodos_online:
            if(node_local.id_nodo!=x.id_nodo):
                puertos.append(x.puerto)
                ids.append(x.id_nodo)
        return puertos,ids
 
@app.route('/IP_NODO',methods=['POST'])
def ip_port_nodo():
    global node_local
    message = request.get_json()
    id_manager = message['id_solicitante']
    num = message['num']-1
    puertos_dis = message['ids']
    id_dis = message['puertos']
    tipo = message['tipo']
    
    
    # Si mi vecino es el utlimo
    if(num <= 0.0):
        # Me añado
        puertos_dis.append(node_local.puerto)
        id_dis.append(node_local.id_nodo)
        # Retorno la lista de id y puertos
        datas = {
            'ids':id_dis,
            'puertos':puertos_dis
        }
        return jsonify(datas)
    else:
    # No soy el ultimo
        datas = {
            'id_solicitante': id_manager,
            'ids':id_dis,
            'puertos':puertos_dis,
            'tipo':tipo,
            'num':num
        }
        if(tipo=='S'):
            # app.logger.error('+++++++++++++++++++++++++++++++++++ http://'+node_local.ip_nodo+':'+str(node_local.sucesor_port))
            req = envio_request_with_datas('http://'+node_local.ip_nodo+':'+str(node_local.sucesor_port),'/IP_NODO',datas)
        elif(tipo=='A'):
            req = envio_request_with_datas('http://'+node_local.ip_nodo+':'+str(node_local.antesesor_port),'/IP_NODO',datas)
        # guardar lo que retorne de listas llenas
        puertos_dis = req['puertos']
        id_dis = req['ids']
        # Me almaceno yo
        puertos_dis.append(node_local.puerto)
        id_dis.append(node_local.id_nodo)
        # Hago json de salida
        datas = {
            'ids':id_dis,
            'puertos':puertos_dis
        }
        # retorno actualizados
        return jsonify(datas)

   
# Coordinador
if (coordina==True):
    # global node_local
    proposer_lider = node_local
    # Notifico que es el coordinador
    app.logger.info('------ SOY EL COORDINADOR - No.'+str(node_local.ide) + ' ------')
    time.sleep(5)
    app.logger.info(str(nodos_workers)+' lista ------- ')
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
    
    # Comienza inicio de chord
    init_chord()
    datas = {
        'ip':node_local.ip_nodo,
        'puerto':node_local.puerto
        }
    url = node_local.ip_nodo+':5701/save_workers'
    req = requests.post('http://'+url,data=json.dumps(datas), headers=headers)
    # crate_fingerTable()


# ------------------------------------------ Balanceo de carga -----------------------------------

@app.route('/RECIBIR_BALAANCE',methods = ['POST'])
def k_dividir():
    global node_local
    global total_workers
    global nodos_online
    message = request.get_json()

    # Recibe los datos    
    k_ = message['K']
    data_balance = 'D'
    type_balance = 'RR'
    type_cluster = 'Kmeans'
    # need_peers = message['workers']
    need_peers = total_workers
    # tiempo inicial
    inicio = time.time()
    # Atrae lo puertos
    puertos_o,ids = dame_n_nodos(need_peers)
    app.logger.info('--------------------------------------------------'+str(len(puertos_o))+ ' - ' + str(len(ids)))
    # timpo final
    fin = time.time()
    # añadir tiempos a csv
    append_list_as_row('./data/tiempos_busqueda.csv', [need_peers,(fin-inicio)])
    app.logger.error(fin-inicio)
    
    init_data = ub.init_workres_array(need_peers)
    data_clus = ub.read_CSV(message['name']) # DataPreprocess
    
    # numero AÑOS DIAS O MESES
    type_balance_str = ub.type_blane_cond(data_balance)
    list_balance = data_clus[type_balance_str].unique()
    
    if (type_balance=='RR'): # Balanceador Round Robin
        init_data = ub.RaoundRobin(init_data,list_balance,need_peers)
    elif (type_balance=='PS'):# Balanceador PseudoRandom
        init_data = ub.PseudoRandom(init_data,list_balance,need_peers)
    elif (type_balance=='TC'):# Balanceador TwoChoices
        init_data = ub.TwoChoices(init_data,list_balance,need_peers)
    else:# Balanceador Round Robin
        init_data = ub.RaoundRobin(init_data,list_balance,need_peers)
    
    # app.logger.error(puertos_online)
    peticiones = []
    # inicio=time.time()
    
    # with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
    
    for x in range(need_peers):
        if (len(init_data[x])>0):
            concac=[]
            for val in init_data[x]:
                # app.logger.info(val)
                concac.append(data_clus[data_clus[type_balance_str]==val])
            data_fin = pd.concat(concac)
            name = "ID_"+str(ids[x])+"_Port_"+str(puertos_o[x])+"_LD="+type_balance+"_DLB="+data_balance
            data_fin.to_csv("./data/"+name+".csv")
            data_clus_n = {"K": k_,
                "name": name,
                "type_cluster":type_cluster,
                "need":need_peers
                }
                
            url = "http://"+node_local.ip_nodo+":"+str(puertos_o[x])
            req = envio_request_witout_return(url,"/CLUSTERING",data_clus_n)
                # process = Thread(target=envio_request_witout_return,args=(url,"/CLUSTERING",data_clus_n))
                # process.start()
                # peticiones.append(process)
                # peticiones.append(multiprocessing.Process(target=envio_request_witout_return,args=(url,"/CLUSTERING",data_clus_n)))
                # executor.submit(envio_request_witout_return,url,"/CLUSTERING",data_clus_n)
            app.logger.error('-----'+str(fin-inicio))
        # for pet in peticiones:        
        #     pet.join()
    return jsonify({'response':'SI'}) 

# ------------------------------------------ Carga de Trabajo -----------------------------------
def prueba_clus(k_,type_cluster,data_clima,name,wor):
    # app.logger.error(k_)
    data_p =data_clima.iloc[:,[7,8,9,10]]
    for k in k_:
        # KMEANS
        if (type_cluster=="Kmeans"):
            # llamado del clustering
            inicio = time.time()
            k_labels,it = ub.K_means(k,data_p)
            cluster="Kmeans"
            fin = time.time()
            app.logger.error('------ '+str(cluster)+" = "+str(fin-inicio) + ' ------')
        elif (type_cluster=="GM"):
            inicio = time.time()
            k_labels = ub.MixtureModel(k,data_p)
            cluster="GaussianMixture"
            fin = time.time()
            app.logger.error('------ '+str(cluster)+" = "+str(fin-inicio) + ' ------')
        else:
            inicio = time.time()
            k_labels,it = ub.K_means(k,data_p)
            cluster="Kmeans"
            fin = time.time()
            app.logger.error('------ '+str(cluster)+" = "+str(fin-inicio) + ' ------')
        # data send
        append_list_as_row('./data/tiempos_carga.csv', [wor,cluster,(fin-inicio)])
        data_clima['clase']=k_labels
        data_clima.to_csv("./data/results/Clus_"+name+"_DataClust_K="+str(k)+"_"+str(cluster)+".csv")
        return 1
 
 
# cLustering
@app.route('/CLUSTERING',methods = ['POST'])
def clustering():
    message = request.get_json()
    # recibir K
    k_ = message['K']
    name = message['name']
    app.logger.info('----------------------------- ' + str(name))
    type_cluster = message['type_cluster']
    wor = message['need']
    
    data_clima = ub.read_CSV(name)
    # data_p =data_clima.iloc[:,[7,8,9,10]]
    # prueba_clus(k_,type_cluster,data_p,name,wor)
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        # app.logger.info('executoooooor')
        executor.submit(prueba_clus,k_,type_cluster,data_clima,name,wor)
        # app.logger.info(executor.result())
    # multi = multiprocessing.Process(target=prueba_clus,args=(k_,type_cluster,data_clima,name))
    # multi.start()
    # for k in k_:
    #     # KMEANS
    #     if (type_cluster=="Kmeans"):
    #         # llamado del clustering
    #         inicio = time.time()
    #         k_labels,it = K_means(k,data_p)
    #         cluster="Kmeans"
    #         fin = time.time()
    #         app.logger.error('------ '+str(cluster)+" = "+str(fin-inicio) + ' - '+str(it) +' ------')
    #     elif (type_cluster=="GM"):
    #         inicio = time.time()
    #         k_labels = MixtureModel(k,data_p)
    #         cluster="GaussianMixture"
    #         fin = time.time()
    #         app.logger.error('------ '+str(cluster)+" = "+str(fin-inicio) + ' ------')
    #     else:
    #         inicio = time.time()
    #         k_labels,it = K_means(k,data_p)
    #         cluster="Kmeans"
    #         fin = time.time()
    #         app.logger.error('------ '+str(cluster)+" = "+str(fin-inicio) + ' - '+str(it) +' ------')
    #     # data send
    #     append_list_as_row('./data/tiempos_carga.csv', [wor,cluster,(fin-inicio)])
    #     data_clima["clase"]=k_labels
    #     data_clima.to_csv("./data/results/Clus_"+name+"_DataClust_K="+str(k)+"_"+str(cluster)+".csv")
    
    return jsonify({'response':'CLUSTERING TERMINADO'})



        
if __name__ == '__main__':
    app.run(host= '0.0.0.0',debug=True)
