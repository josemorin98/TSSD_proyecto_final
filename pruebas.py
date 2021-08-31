import requests
import json
import threading
import time



headers = {'PRIVATE-TOKEN': '<your_access_token>', 'Content-Type':'application/json'}
# Envio al conquer el bak
data_file = {
    'ip':'192.168.0.14',
    'puerto':5701
}
url = '192.168.0.14:5700/bak'
req = requests.post('http://'+url,data=json.dumps(data_file), headers=headers)

datas = {
        'K':[3,4],
        # 'data_balance':'D',
        # 'type_balance':'RR',
        # 'name':'DataPreproces',
        # 'type_cluster':'Kmeans',
        'name':'Diferencial_EMAS-MERRA_'
        # 'workers':int(arg[2])
        }
url = '192.168.0.14:5603/preprocer'
req = requests.post('http://'+url,data=json.dumps(datas), headers=headers)



# datas = {
#         'ip':'192.168.0.14',
#         'puerto':4000
#         }
# url = '192.168.0.14:5701/save_workers'
# req = requests.post('http://'+url,data=json.dumps(datas), headers=headers)
# json_r = req.json()
# print(json_r['response'])

# url = '192.168.0.12:4011/RECIBIR_BALAANCE'
# for x in range(25):
#     print(x)
#     req = requests.post('http://'+url,data=json.dumps(datas), headers=headers)
#     json_r = req.json()
#     print(json_r['response'])
#     time.sleep(3)

