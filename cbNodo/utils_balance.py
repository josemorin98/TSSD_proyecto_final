# Librerias
import pandas as pd
import numpy as np
from datetime import datetime
import time
import random
import hashlib
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture

def hash(name,total):
    name_hash = hashlib.sha1(bytes(name,encoding='utf8'))
    return int(name_hash.hexdigest(),16) % total
    

def conc(name, port):
    	# '192.168.1.1', '8000' -> '192.168.1.1:8000'
	return name + ":" +str(port)

def boolean(arg):
    if (arg=='True'):
        return True
    else:
        False
        
def par(num):
    if ((num%2)==0):
        return True
    else: 
        return False

def init_workres_array(workers):
    pet_in = []
    for i in range(workers):
        pet_in.append([])
    return pet_in

def RaoundRobin(cargas, list_to, workers):
    for x in range(len(list_to)):
        select_bin = x % workers
        cargas[select_bin].append(list_to[x])
    return cargas

def PseudoRandom(cargas, list_to, workers):
    for x in range(len(list_to)):
        select_bin = random.randint(0, workers-1)
        cargas[select_bin].append(list_to[x])
    return cargas

def TwoChoices(cargas, list_to, workers):
    select_bin = 0
    select_bin2 = 0
    aux = True
    if(workers==1):
        for x in range(len(list_to)):
            cargas[0].append(list_to[x])
    else:
        for x in range(len(list_to)):
            select_bin = random.randint(0, workers-1)
            while(aux):
                select_bin2 = random.randint(0, workers-1)
                if(select_bin != select_bin2):
                    aux = False
            if( len(cargas[select_bin]) < len(cargas[select_bin2]) ):
                cargas[select_bin].append(list_to[x])
            else:
                cargas[select_bin2].append(list_to[x])
            aux = True
    return cargas

def type_blane_cond(tipo):
    if (tipo=='Y'):
        return 'Ano'
    elif (tipo=='M'):
        return 'Mes'
    elif (tipo=='D'):
        return 'Dia'
    else:
        return 'Mes'

def read_CSV(name):
    return pd.read_csv("./data/"+name+".csv")


# Clustering-------------------------
def K_means(k,data_clima):
    # X_clima = data_clima.iloc[:,[7,8,9,10]]
    kmeans = KMeans(n_clusters=k).fit(data_clima)
    k_labels = kmeans.predict(data_clima)
    return k_labels,kmeans.n_iter_


def MixtureModel(k,data_clima):
    # X_clima = data_clima.iloc[:,[7,8,9,10]]
    modelo_gmm = GaussianMixture(
                n_components    = k,
                covariance_type = 'full',
                random_state    = 123)
    modelo_gmm.fit(data_clima)
    k_labels = modelo_gmm.predict(data_clima)
    return k_labels