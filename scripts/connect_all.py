import os
import sys
import importlib
import requests

sys.path.append("..")


from examples.cables_templates import cables_templates

API_URL="http://192.168.0.45:5000"

if __name__ == "__main__":
    
    #start connecting

    # #get a module
    # module = "PS_26_05-IPG_00102"

    # connect_data = {
    #     "cable1": module,
    #     "cable2": "B1",
    #     "port1": "power",
    #     "port2": "power"
    # }

    # req = requests.post(f"{API_URL}/connect", json=connect_data)
    # print(req.json())

    # connect_data = {
    #     "cable1": module,
    #     "cable2": "B1",
    #     "port1": "fiber",
    #     "port2": "fiber"
    # }
    # req = requests.post(f"{API_URL}/connect", json=connect_data)
    # print(req.json())

    # #connect burnin from 1 to 6 HVLV to patchpanel 1 to 6
    # for i in range(1, 7):
    #     connect_data = {
    #         "cable1": f"B{i}",
    #         "cable2": f"P001",
    #         "port1": "HVLV",
    #         "port2": f"B{i}"
    #     }
    #     req = requests.post(f"{API_URL}/connect", json=connect_data)
    #     print(req.json())

    # #patchpanl 1,2, 3 to H11, H12, H13
    # for i in range(1, 4):
    #     connect_data = {
    #         "cable1": f"P001",
    #         "cable2": f"H1{i}",
    #         "port1": f"HV{i}",
    #         "port2": "A"
    #     }
    #     req = requests.post(f"{API_URL}/connect", json=connect_data)
    #     print(req.json())

    # # connect ASLOT0 ports 1, 2, 3 to H11, H12, H13
    # for i in range(1, 4):
    #     connect_data = {
    #         "cable1": f"H1{i}",
    #         "cable2": f"ASLOT0",
    #         "port1": "A",
    #         "port2": f"{i}"
    #     }
    #     req = requests.post(f"{API_URL}/connect", json=connect_data)
    #     print(req.json())

    # # connect P001 LV1, LV2 to LRED, LBLUE
    # connect_data = {
    #     "cable1": "P001",
    #     "cable2": "LRED",
    #     "port1": "LV1",
    #     "port2": "A"
    # }
    # req = requests.post(f"{API_URL}/connect", json=connect_data)
    # print(req.json())

    # connect_data = {
    #     "cable1": "P001",
    #     "cable2": "LBLUE",
    #     "port1": "LV2",
    #     "port2": "A"
    # }
    # req = requests.post(f"{API_URL}/connect", json=connect_data)
    # print(req.json())

    # # connect LRED, LBLUE to XSLOT6 port up and down
    # connect_data = {
    #     "cable1": "LRED",
    #     "cable2": "XSLOT6",
    #     "port1": "A",
    #     "port2": "up"
    # }
    # req = requests.post(f"{API_URL}/connect", json=connect_data)
    # print(req.json())

    # connect_data = {
    #     "cable1": "LBLUE",
    #     "cable2": "XSLOT6",
    #     "port1": "A",
    #     "port2": "down"
    # }
    # req = requests.post(f"{API_URL}/connect", json=connect_data)
    # print(req.json())
    
    # # connect burnin to exapus 
    # connect_data = {
    #     "cable1": "B1",
    #     "cable2": "E51",
    #     "port1": "fiber",
    #     "port2": "A"
    # }
    # req = requests.post(f"{API_URL}/connect", json=connect_data)
    # print(req.json())

    # # exapus to extensioncord
    # connect_data = {
    #     "cable1": "E51",
    #     "cable2": "C21",
    #     "port1": "A",
    #     "port2": "A"
    # }
    # req = requests.post(f"{API_URL}/connect", json=connect_data)
    # print(req.json())

    # extension to dodecapus
    # connect_data = {
    #     "cable1": "C21",
    #     "cable2": "D31",
    #     "port1": "A",
    #     "port2": "A"
    # }
    # req = requests.post(f"{API_URL}/connect", json=connect_data)
    # print(req.json())

    # # dodecapus to FC7OT2
    # FC7OT2 = {
    #     "type": "FC7",
    #     "name": "FC7OT2",
    #     "detSide": {},
    #     "crateSide": {},
    # }
    # req = requests.post(f"{API_URL}/cables", json=FC7OT2)
    # print(req.json())

    # connect_data = {
    #     "cable1": "D31",
    #     "cable2": "FC7OT2",
    #     "port1": "P12",
    #     "port2": "OG0"
    # }
    # req = requests.post(f"{API_URL}/connect", json=connect_data)
    # print(req.json())

    # do a snapshot of the module from crateSide
    snapshot_data = {
        "cable": "PS_26_05-IPG_00102",
        "side": "crateSide"
    }
    req = requests.post(f"{API_URL}/snapshot", json=snapshot_data)
    print(req.json())