# Librerias
import pandas as pd
import numpy as np
from datetime import datetime
import time
import random


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
