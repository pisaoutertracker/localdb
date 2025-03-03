import unittest
from flask_testing import TestCase
from flask import jsonify
import sys
import os
from dotenv import load_dotenv
import json

sys.path.append("..")
from app.app import (
    create_app,
    get_db,
)
from examples.cables_templates import cables_templates
from bson import ObjectId
from pymongo import MongoClient
import os


class TestAPI(TestCase):
    def create_app(self):
        return create_app("unittest")

    def setUp(self):
        self.app = self.create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db = get_db()
            db.modules.drop()
            db.logbook.drop()
            db.current_cabling_map.drop()
            db.tests.drop()
            db.testpayloads.drop()
            db.cables.drop()
            db.cable_templates.drop()
            db.crates.drop()
            db.test_runs.drop()
            db.module_tests.drop()
            db.sessions.drop()
            db.module_test_analysis.drop()

    def tearDown(self):
        with self.app.app_context():
            db = get_db()
            db.modules.drop()
            db.logbook.drop()
            db.current_cabling_map.drop()
            db.tests.drop()
            db.testpayloads.drop()
            db.cables.drop()
            db.cables_templates.drop()
            db.crates.drop()
            db.test_runs.drop()
            db.module_tests.drop()
            db.sessions.drop()
            db.module_test_analysis.drop()

    def test_fetch_all_modules_empty(self):
        response = self.client.get("/modules")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

    def test_insert_module(self):
        self.test_insert_cable_templates()

        new_module = {
            "moduleName": "INV001",
            "position": "cleanroom",
            "status": "readyformount",
            # ... (other properties)
        }
        response = self.client.post("/modules", json=new_module)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"message": "Module inserted"})

        response = self.client.get("/modules/INV001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["moduleName"], "INV001")
        
        # now do a test put changing the status
        new_module_status = {
            "status": "mounted",
        }
        response = self.client.put("/modules/INV001", json=new_module_status)
        self.assertEqual(response.status_code, 200)
        # check if the status is changed
        response = self.client.get("/modules/INV001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "mounted")
        # print(response.json)
        #check that the other properties are still there
        self.assertEqual(response.json["position"], "cleanroom")
             

    def test_fetch_specific_module_not_found(self):
        response = self.client.get("/modules/INV999")
        self.assertEqual(response.status_code, 404)

    def test_delete_module_not_found(self):
        response = self.client.delete("/modules/INV999")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Module deleted"})

    # def test_insert_log(self):
    #     new_log = {
    #         "timestamp": "2023-11-03T14:21:29Z",
    #         "event": "Module added",
    #         "operator": "John Doe",
    #         "station": "pccmslab1",
    #         "sessionid": "TESTSESSION1",
    #     }
    #     response = self.client.post("/logbook", json=new_log)
    #     self.assertEqual(response.status_code, 201)

    def test_fetch_log_not_found(self):
        response = self.client.get("/logbook/123456789012123456789012")
        self.assertEqual(response.status_code, 404)

    def test_delete_log_not_found(self):
        response = self.client.delete("/logbook/123456789012123456789012")
        self.assertEqual(response.status_code, 404)

    # def test_delete_log(self):
    #     # First, let's insert a log entry
    #     new_log = {
    #         "timestamp": "2023-11-03T14:21:29Z",
    #         "event": "Module added",
    #         "operator": "John Doe",
    #         "station": "pccmslab1",
    #         "sessionid": "TESTSESSION1",
    #     }
    #     _id = ((self.client.post("/logbook", json=new_log)).json)["_id"]
    #     # Now, let's delete it
    #     response = self.client.delete("/logbook/" + str(_id))
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.json, {"message": "Log deleted"})

    def test_insert_cable_templates(self):
        # read cables.json from the examples folder
        cable_templates = cables_templates

        for template in cable_templates:
            response = self.client.post("/cable_templates", json=template)
            self.assertEqual(response.status_code, 201)
            self.assertIn("message", response.json)
            self.assertEqual(response.json["message"], "Template inserted")

            cable_type = template["type"]
            response = self.client.get(f"/cable_templates/{cable_type}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["type"], cable_type)

    def test_insert_cable_no_connections(self):

        self.test_insert_cable_templates()

        new_cable = {"name": "E31", "type": "exapus", "detSide": {}, "crateSide": {}}

        response = self.client.post("/cables", json=new_cable)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"message": "Entry inserted"})

        # Assuming you have an endpoint to fetch a cable by its name or another unique identifier
        response = self.client.get(f"/cables/{new_cable['name']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], new_cable["name"])
        self.assertEqual(response.json["type"], new_cable["type"])

        # try insertion with invalid types
        new_cable2 = {
            "name": "D33",
            "type": "dodecapussone",
            "detSide": {},
            "crateSide": {},
        }
        response = self.client.post("/cables", json=new_cable2)
        self.assertEqual(response.status_code, 400)

    def test_create_connect_disconnect_cables(self):

        self.test_insert_cable_templates()

        # 1. Create some cables
        new_cable = {"name": "E31", "type": "exapus", "detSide": {}, "crateSide": {}}

        new_cable1 = {
            "name": "D31",
            "type": "dodecapus",
            "detSide": {},
            "crateSide": {},
        }

        response = self.client.post("/cables", json=new_cable)
        self.assertEqual(response.status_code, 201)
        response = self.client.post("/cables", json=new_cable1)
        self.assertEqual(response.status_code, 201)

        # 2. Connect them
        connect_data = {
            "cable1": "E31",
            "port1": "1",
            "cable2": "D31",
            "port2": "A",
        }
        response = self.client.post("/connect", json=connect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Cables connected successfully"})

        # Check if cables are connected correctly
        response = self.client.get("/cables/E31")
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json["crateSide"],
            jsonify(
                {
                    1: ["D31", 1],
                    2: ["D31", 2],
                    3: ["D31", 3],
                    4: ["D31", 4],
                    5: ["D31", 5],
                    6: ["D31", 6],
                    7: ["D31", 7],
                    8: ["D31", 8],
                    9: ["D31", 9],
                    10: ["D31", 10],
                    11: ["D31", 11],
                    12: ["D31", 12],
                }
            ).json,
        )

        # 3. Disconnect them
        disconnect_data = {
            "cable1": "E31",
            "cable2": "D31",
            "port1": "1",
            "port2": "A",
        }

        response = self.client.post("/disconnect", json=disconnect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Cables disconnected successfully"})
        # Check if cables are disconnected correctly
        response = self.client.get("/cables/E31")
        self.assertEqual(response.status_code, 200)
        empty_side = {
            "1": [],
            "2": [],
            "3": [],
            "4": [],
            "5": [],
            "6": [],
            "7": [],
            "8": [],
            "9": [],
            "10": [],
            "11": [],
            "12": [],
        }
        self.assertEqual(response.json["crateSide"], empty_side)
        response = self.client.get("/cables/D31")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["detSide"], empty_side)

        # define a module
        new_module = {
            "moduleName": "modulecabletest",
            "position": "cleanroom",
            "status": "readyformount",
            # ... (other properties)
        }

        response = self.client.post("/modules", json=new_module)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"message": "Module inserted"})

        # 4. Connect a cable to a module
        connect_data = {
            "cable1": "modulecabletest",
            "cable2": "E31",
            "port1": "fiber",
            "port2": "1",
        }
        response = self.client.post("/connect", json=connect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Cables connected successfully"})
        # Check if cables are connected correctly
        response = self.client.get("/modules/modulecabletest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["crateSide"],
            {"1": ["E31", 1], "2": ["E31", 2], "3": [], "4": []},
        )

        # 5. Disconnect the cable from the module
        disconnect_data = {
            "cable1": "modulecabletest",
            "cable2": "E31",
            "port1": "fiber",
            "port2": "1",
        }
        response = self.client.post("/disconnect", json=disconnect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Cables disconnected successfully"})
        # Check if cables are disconnected correctly
        response = self.client.get("/modules/modulecabletest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["crateSide"], {"1": [], "2": [], "3": [], "4": []}
        )

    def test_connect_failures(self):

        self.test_insert_cable_templates()

        # 1. Create some cables
        new_cable = {"name": "E32", "type": "exapus", "detSide": {}, "crateSide": {}}

        new_cable1 = {
            "name": "D32",
            "type": "dodecapus",
            "detSide": {},
            "crateSide": {},
        }

        response = self.client.post("/cables", json=new_cable)
        self.assertEqual(response.status_code, 201)
        response = self.client.post("/cables", json=new_cable1)
        self.assertEqual(response.status_code, 201)

        # try connection without ports
        connect_data = {
            "cable1": "E32",
            "cable2": "D32",
        }
        response = self.client.post("/connect", json=connect_data)
        self.assertEqual(response.status_code, 400)

        # try connection with invalid ports
        connect_data = {
            "cable1": "E32",
            "port1": "Z",
            "cable2": "D32",
            "port2": "A",
        }
        response = self.client.post("/connect", json=connect_data)
        self.assertEqual(response.status_code, 400)

        # try connection with invalid cables
        connect_data = {
            "cable1": "E33",
            "port1": "1",
            "cable2": "D32",
            "port2": "A",
        }
        response = self.client.post("/connect", json=connect_data)
        self.assertEqual(response.status_code, 404)

        # update the cables to already have a connection
        new_cable["crateSide"] = {"1": ["D32", 1]}
        new_cable1["detSide"] = {"1": ["E32", 1]}
        response = self.client.put("/cables/E32", json=new_cable)
        self.assertEqual(response.status_code, 200)
        response = self.client.put("/cables/D32", json=new_cable1)
        self.assertEqual(response.status_code, 200)

        # try connection with already connected cables
        connect_data = {
            "cable1": "E32",
            "port1": "1",
            "cable2": "D32",
            "port2": "A",
        }
        response = self.client.post("/connect", json=connect_data)
        self.assertEqual(response.status_code, 400)

    def test_disconnect_failures(self):

        self.test_insert_cable_templates()

        # 1. Create some cables
        new_cable = {"name": "E33", "type": "exapus", "detSide": {}, "crateSide": {}}

        new_cable1 = {
            "name": "D33",
            "type": "dodecapus",
            "detSide": {},
            "crateSide": {},
        }

        response = self.client.post("/cables", json=new_cable)
        self.assertEqual(response.status_code, 201)
        response = self.client.post("/cables", json=new_cable1)

        # try disconnection with invalid ports
        disconnect_data = {
            "cable1": "E33",
            "cable2": "D33",
            "port1": "1",
            "port2": "A",
        }
        response = self.client.post("/disconnect", json=disconnect_data)
        self.assertEqual(response.status_code, 400)

        # try disconnection with invalid cables
        disconnect_data = {
            "cable1": "E34",
            "cable2": "D33",
            "port1": "1",
            "port2": "A",
        }
        response = self.client.post("/disconnect", json=disconnect_data)
        self.assertEqual(response.status_code, 404)

        # try disconnection with already disconnected cables
        disconnect_data = {
            "cable1": "E33",
            "cable2": "D33",
            "port1": "1",
            "port2": "A",
        }
        response = self.client.post("/disconnect", json=disconnect_data)
        self.assertEqual(response.status_code, 400)

    def test_cabling_snapshot(self):

        self.test_insert_cable_templates()

        # 1. Create some cables 
        hv_cables = [
        {"type": "HV", "name": "H11", "detSide": {}, "crateSide": {}},
        {"type": "HV", "name": "H12", "detSide": {}, "crateSide": {}},
        {"type": "HV", "name": "H13", "detSide": {}, "crateSide": {}},
    ]

        for cable in hv_cables:
            res = self.client.post("/cables", json=cable)
            self.assertEqual(res.status_code, 201)

        patch_panel = {
            "type": "patchpanel",
            "name": "P001",
            "detSide": {},
            "crateSide": {},
        }
        
        res = self.client.post("/cables", json=patch_panel)
        self.assertEqual(res.status_code, 201)

        caen_HV = []
        for i in range(0, 1):
            caen_HV.append(
                {
                    "type": "caenHV",
                    "name": f"ASLOT{i}",
                    "detSide": {},
                    "crateSide": {},
                }
            )
        
        for cable in caen_HV:
            res = self.client.post("/cables", json=cable)
            self.assertEqual(res.status_code, 201)


        caen_LV = []
        for i in range(6, 8):
            caen_LV.append(
                {
                    "type": "caenLV",
                    "name": f"XSLOT{i}",
                    "detSide": {},
                    "crateSide": {},
                }
            )
        
        for cable in caen_LV:
            res = self.client.post("/cables", json=cable)
            self.assertEqual(res.status_code, 201)

        lv_cable = [{
            "type": "LV",
            "name": "LRED",
            "detSide": {},
            "crateSide": {},
        },
        {
            "type": "LV",
            "name": "LBLUE",
            "detSide": {},
            "crateSide": {},
        }]

        for cable in lv_cable:
            res = self.client.post("/cables", json=cable)
            self.assertEqual(res.status_code, 201)

        burnin_slots = []
        for i in range(1, 11):
            burnin_slots.append(
                {
                    "type": "burninslot",
                    "name": f"B{i}",
                    "detSide": {},
                    "crateSide": {},
                }
            )

        for cable in burnin_slots:
            res = self.client.post("/cables", json=cable)
            self.assertEqual(res.status_code, 201)

        dodecapus = {
            "type": "dodecapus",
            "name": "D31",
            "detSide": {},
            "crateSide": {},
        }

        res = self.client.post("/cables", json=dodecapus)
        self.assertEqual(res.status_code, 201)

        extension_cords = {
            "type": "extensioncord",
            "name": "C21",
            "detSide": {},
            "crateSide": {},
        }
        res = self.client.post("/cables", json=extension_cords)
        self.assertEqual(res.status_code, 201)

        exapus = {
            "type": "exapus",
            "name": "E51",
            "detSide": {},
            "crateSide": {},
        }
        res = self.client.post("/cables", json=exapus)
        self.assertEqual(res.status_code, 201)

        FC7OT2 = {
        "type": "FC7",
        "name": "FC7OT2",
        "detSide": {},
        }

        res = self.client.post("/cables", json=FC7OT2)
        self.assertEqual(res.status_code, 201)

        module = {
            "moduleName": "PS_26_05-IPG_00102",
            "position": "cleanroom",
            "status": "readyformount",
        }
        res = self.client.post("/modules", json=module)
        self.assertEqual(res.status_code, 201)


        # now connect all
        module = "PS_26_05-IPG_00102"

        connect_data = {
            "cable1": module,
            "cable2": "B1",
            "port1": "power",
            "port2": "power"
        }

        req = self.client.post("/connect", json=connect_data)
        self.assertEqual(req.status_code, 200)

        connect_data = {
            "cable1": module,
            "cable2": "B1",
            "port1": "fiber",
            "port2": "fiber"
        }
        req = self.client.post("/connect", json=connect_data)
        self.assertEqual(req.status_code, 200)

        #connect burnin from 1 to 6 HVLV to patchpanel 1 to 6
        for i in range(1, 7):
            connect_data = {
                "cable1": f"B{i}",
                "cable2": f"P001",
                "port1": "HVLV",
                "port2": f"B{i}"
            }
            req = self.client.post("/connect", json=connect_data)
            self.assertEqual(req.status_code, 200)
        #patchpanl 1,2, 3 to H11, H12, H13
        for i in range(1, 4):
            connect_data = {
                "cable1": f"P001",
                "cable2": f"H1{i}",
                "port1": f"HV{i}",
                "port2": "A"
            }
            req = self.client.post("/connect", json=connect_data)
            self.assertEqual(req.status_code, 200)

        # connect ASLOT0 ports 1, 2, 3 to H11, H12, H13
        for i in range(1, 4):
            connect_data = {
                "cable1": f"H1{i}",
                "cable2": f"ASLOT0",
                "port1": "A",
                "port2": f"{i}"
            }
            req = self.client.post("/connect", json=connect_data)
            self.assertEqual(req.status_code, 200)

        # connect P001 LV1, LV2 to LRED, LBLUE
        connect_data = {
            "cable1": "P001",
            "cable2": "LRED",
            "port1": "LV1",
            "port2": "A"
        }
        req = self.client.post("/connect", json=connect_data)
        self.assertEqual(req.status_code, 200)

        connect_data = {
            "cable1": "P001",
            "cable2": "LBLUE",
            "port1": "LV2",
            "port2": "A"
        }
        req = self.client.post("/connect", json=connect_data)
        self.assertEqual(req.status_code, 200)

        # connect LRED, LBLUE to XSLOT6 port up and down
        connect_data = {
            "cable1": "LRED",
            "cable2": "XSLOT6",
            "port1": "A",
            "port2": "up"
        }
        req = self.client.post("/connect", json=connect_data)
        self.assertEqual(req.status_code, 200)

        connect_data = {
            "cable1": "LBLUE",
            "cable2": "XSLOT6",
            "port1": "A",
            "port2": "down"
        }
        req = self.client.post("/connect", json=connect_data)
        self.assertEqual(req.status_code, 200)

        # connect burnin to exapus 
        connect_data = {
            "cable1": "B1",
            "cable2": "E51",
            "port1": "fiber",
            "port2": "1"
        }
        req = self.client.post("/connect", json=connect_data)
        self.assertEqual(req.status_code, 200)

        # exapus to extensioncord
        connect_data = {
            "cable1": "E51",
            "cable2": "C21",
            "port1": "1",
            "port2": "A"
        }
        req = self.client.post("/connect", json=connect_data)
        self.assertEqual(req.status_code, 200)

        # extension to dodecapus
        connect_data = {
            "cable1": "C21",
            "cable2": "D31",
            "port1": "A",
            "port2": "A"
        }
        req = self.client.post("/connect", json=connect_data)
        self.assertEqual(req.status_code, 200)

        connect_data = {
            "cable1": "D31",
            "cable2": "FC7OT2",
            "port1": "P12",
            "port2": "OG0"
        }
        req = self.client.post("/connect", json=connect_data)
        self.assertEqual(req.status_code, 200)

        # do a snapshot of the module from crateSide
        snapshot_data = {
            "cable": "PS_26_05-IPG_00102",
            "side": "crateSide"
        }
        req = self.client.post("/snapshot", json=snapshot_data)
        self.assertEqual(req.json["1"]["connections"][-1]["cable"], "FC7OT2")
        # print formatted json
        # formatted = json.dumps(req.json, indent=4)
        # print(formatted)

        # do a snapshot of the module from crateSide
        snapshot_data = {
            "cable": "FC7OT2",
            "side": "detSide"
        }
        req = self.client.post("/snapshot", json=snapshot_data)
        self.assertEqual(req.json["1"]["connections"][-1]["cable"], "PS_26_05-IPG_00102")
        # print formatted json
        # formatted = json.dumps(req.json, indent=4)
        # print(formatted)


    # Snapshot from Cable (crateSide)
    # def test_LogBookSearchByText(self):
    #     new_log = {
    #         "timestamp": "2023-11-03T14:21:29Z",
    #         "event": "Module added",
    #         "operator": "John Doe",
    #         "event": "pippo",
    #         "station": "pccmslab1",
    #         "sessionid": "TESTSESSION1",
    #         "involved_modules": ["PS_1", "PS_2"],
    #     }
    #     response = self.client.post("/logbook", json=new_log)
    #     new_log2 = {
    #         "timestamp": "2023-11-03T14:21:29Z",
    #         "event": "Module added",
    #         "operator": "John Do2",
    #         "details": "pippo",
    #         "station": "pccmslab1",
    #         "sessionid": "TESTSESSION2",
    #         "involved_modules": ["MS_1", "MS_2"],
    #     }
    #     response = self.client.post("/logbook", json=new_log2)

    #     logbook_entries = self.client.post(
    #         "/searchLogBookByText", json={"modules": "pi.*o"}
    #     )
    #     self.assertEqual(logbook_entries.status_code, 200)
    #     self.assertEqual(len(logbook_entries.json), 2)

    # def test_LogBookSearchByModuleNames(self):
    #     # insert a few entriesi for testing
    #     new_log = {
    #         "timestamp": "2023-11-03T14:21:29Z",
    #         "event": "Module added",
    #         "operator": "John Doe",
    #         "station": "pccmslab1",
    #         "sessionid": "TESTSESSION1",
    #         "involved_modules": ["PS_1", "PS_2"],
    #     }
    #     response = self.client.post("/logbook", json=new_log)
    #     new_log2 = {
    #         "timestamp": "2023-11-03T14:21:29Z",
    #         "event": "Module added",
    #         "operator": "John Doe",
    #         "station": "pccmslab1",
    #         "sessionid": "TESTSESSION1",
    #         "involved_modules": ["MS_1", "MS_2"],
    #     }
    #     response = self.client.post("/logbook", json=new_log2)

    #     logbook_entries = self.client.post(
    #         "/searchLogBookByModuleNames", json={"modules": "PS.*"}
    #     )
    #     self.assertEqual(logbook_entries.status_code, 200)
    #     self.assertEqual(len(logbook_entries.json), 1)

    # def test_insert_log_2(self):
    #     new_log = {
    #         "timestamp": "2023-10-03T14:21:29Z",
    #         "event": "Module added",
    #         "operator": "John Doe",
    #         "station": "pccmslab1",
    #         "involved_modules": ["PS_1", "PS_2"],
    #         "sessionid": "TESTSESSION1",
    #         "details": " I tried to insert PS_88 and PS_44. and also PS_1.",
    #     }
    #     response = self.client.post("/logbook", json=new_log)
    #     self.assertEqual(response.status_code, 201)

    #     #
    #     # now I try to get it back, and I check the involved_modules
    #     #
    #     _id = str((response.json)["_id"])
    #     response = self.client.get("/logbook/" + _id)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(len(response.json["involved_modules"]), 4)

    #################
    def test_insert_get_delete_testpayload(self):
        new_log = {
            "sessionName": "testsession000",
            "remoteFileList": [
                "http://cernbox.cern.ch/pippo_pluto",
                "http://cernbox.cern.ch/cappero",
            ],
            "details": " I tried to insert PS_88 and PS_44. and also PS_1.",
        }
        response = self.client.post("/test_payloads", json=new_log)
        self.assertEqual(response.status_code, 201)

        _id = str(response.json["_id"])

        # get it back
        response = self.client.get("/test_payloads/" + str(_id))
        self.assertEqual(response.status_code, 200)
        # delete it
        response = self.client.delete("/test_payloads/" + str(_id))
        self.assertEqual(response.status_code, 200)

    def test_add_run(self):
        # Sample data
        session_entry = {
            "timestamp": "2023-11-03T14:21:29",
            "operator": "John Doe",
            "description": "I tried to insert PS_88 and PS_44. and also PS_1.",
            "modulesList": ["PS_1", "PS_2"],
            "configuration": {"a": "b"},
            "log": ["uuhuh", "pippo"],
        }
        # insert it
        response = self.client.post("/sessions", json=session_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn("message", response.json)
        # get the sessionName from the response
        sessionName = response.json["sessionName"]

        test_run_data = {
            "runDate": "1996-11-21T10:00:56",
            "runStatus": "failed",
            "runType": "Type1",
            "runSession": sessionName,
            "runBoards": {
                3: "fc7ot2",
                4: "fc7ot3",
            },
            "runModules": {  ## (board, optical group) : (moduleName, hwNamemodule)
                "fc7ot2_optical0": ("M123", 67),
                "fc7ot2_optical1": ("M124", 68),
                "fc7ot3_optical2": ("M125", 69),
            },
            "runResults": {
                67: "pass",
                68: "failed",
                69: "failed",
            },
            "runNoise": {
                67: {
                    "SSA0": 4.348,
                    "SSA4": 3.348,
                    "MPA9": 2.348,
                },
                68: {
                    "SSA0": 3.348,
                    "SSA1": 3.648,
                },
                69: {
                    "SSA0": 3.548,
                    "SSA4": 3.248,
                },
            },
            "runConfiguration": {"a": "b"},
            "runFile": "link",
        }

        response = self.client.post("/addRun", json=test_run_data)
        self.assertEqual(response.status_code, 201)
        self.assertIn("run_id", response.json)
        self.assertIn("message", response.json)

        # now test again a test_run_data with moduleName = -1
        test_run_data = {
            "runDate": "1996-11-21T11:00:56",
            "runStatus": "failed",
            "runType": "Type1",
            "runSession": sessionName,
            "runBoards": {
                3: "fc7ot2",
                4: "fc7ot3",
            },
            "runModules": {  ## (board, optical group) : (moduleName, hwNamemodule)
                "fc7ot2_optical0": (-1, 67),
                "fc7ot2_optical1": (-1, 68),
                "fc7ot3_optical2": (-1, 69),
            },
            "runResults": {
                67: "pass",
                68: "failed",
                69: "failed",
            },
            "runNoise": {
                67: {
                    "SSA0": 4.348,
                    "SSA4": 3.348,
                    "MPA9": 2.348,
                },
                68: {
                    "SSA0": 3.348,
                    "SSA1": 3.648,
                },
                69: {
                    "SSA0": 3.548,
                    "SSA4": 3.248,
                },
            },
            "runConfiguration": {"a": "b"},
            "runFile": "link",
        }

        response = self.client.post("/addRun", json=test_run_data)
        self.assertEqual(response.status_code, 201)
        self.assertIn("run_id", response.json)
        skipped = response.json["skipped_modules_count"]
        self.assertEqual(skipped, 3)

    def test_run_get(self):
        session_entry = {
            "timestamp": "2023-11-03T14:21:29",
            "operator": "John Doe",
            "description": "I tried to insert PS_88 and PS_44. and also PS_1.",
            "modulesList": ["PS_1", "PS_2"],
            "configuration": {"a": "b"},
            "log": ["uuhuh", "pippo"],
        }
        # insert it
        response = self.client.post("/sessions", json=session_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn("message", response.json)
        # get the sessionName from the response
        sessionName = response.json["sessionName"]

        run_entry = {
            "runDate": "1996-11-21",
            "test_runName": "T53",
            "runSession": sessionName,
            "runStatus": "failed",
            "runType": "Type1",
            "runBoards": {
                3: "fc7ot2",
                4: "fc7ot3",
            },
            "_moduleTest_id": [],
            "moduleTestName": [],
            "runFile": "link",
            "runConfiguration": {"a": "b"},
        }
        # insert it
        response = self.client.post("/test_run", json=run_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn("message", response.json)
        # get it back
        response = self.client.get("/test_run/T53")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["test_runName"], "T53")
        # modify it
        run_entry["runStatus"] = "passed"
        response = self.client.put("/test_run/T53", json=run_entry)
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json)
        # get all test_runs
        response = self.client.get("/test_run")
        self.assertEqual(response.status_code, 200)
        # delete it
        response = self.client.delete("/test_run/T53")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json)

    def test_session_resource(self):
        session_entry = {
            "timestamp": "2023-11-03T14:21:29",
            "operator": "John Doe",
            "description": "I tried to insert PS_88 and PS_44. and also PS_1.",
            "modulesList": ["PS_1", "PS_2"],
            "configuration": {"a": "b"},
            "log": ["uuhuh", "pippo"],
        }
        # insert it
        response = self.client.post("/sessions", json=session_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn("message", response.json)
        # get the sessionName from the response
        sessionName = response.json["sessionName"]
        # get it back
        response = self.client.get(f"/sessions/{sessionName}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["sessionName"], f"{sessionName}")
        # modify it
        session_entry["operator"] = "John Doe2"
        response = self.client.put(f"/sessions/{sessionName}", json=session_entry)
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json)
        # get all sessions
        response = self.client.get(f"/sessions")
        self.assertEqual(response.status_code, 200)
        # delete it
        response = self.client.delete(f"/sessions/{sessionName}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json)

    def test_module_test_analysis_resource(self):
        mta_entry = {
            "moduleTestAnalysisName": "MTA22",
            "moduleTestName": "MT1",
            "analysisVersion": "v1",
            "analysisResults": {"a": "b"},
            "analysisSummary": {"a": "b"},
            "analysisFile": "link",
        }
        # insert it
        response = self.client.post("/module_test_analysis", json=mta_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn("message", response.json)
        # get it back
        response = self.client.get("/module_test_analysis/MTA22")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["moduleTestAnalysisName"], "MTA22")
        # get by Mongo _id
        _id = response.json["_id"]
        response = self.client.get(f"/module_test_analysis/{_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["moduleTestAnalysisName"], "MTA22")
        # modify it
        mta_entry["analysisVersion"] = "v2"
        response = self.client.put("/module_test_analysis/MTA22", json=mta_entry)
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json)
        # get all module_test_analysis
        response = self.client.get("/module_test_analysis")
        self.assertEqual(response.status_code, 200)
        # delete it
        response = self.client.delete("/module_test_analysis/MTA22")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.json)

    def test_add_analysis(self):

        mta_entry = {
            "moduleTestAnalysisName": "MTA1",
            "moduleTestName": "MT1",
            "analysisVersion": "v1",
            "analysisResults": {"a": "b"},
            "analysisSummary": {"a": "b"},
            "analysisFile": "link",
        }
        # insert it
        response = self.client.post("/module_test_analysis", json=mta_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn("message", response.json)

        mt_entry = {
            "moduleTestName": "MT1",
            "_test_run_id": ObjectId("5f9b3b9b9d9d7b3d9d9d7b3d"),
            "test_runName": "T53",
            "_module_id": ObjectId("5f9b3b9b9d9d7b3d9d9d7b3d"),
            "moduleName": "M123",
            "noise": {"a": "b"},
            "board": "fc7ot2",
            "opticalGroupName": 1,
        }

        # insert it
        response = self.client.post("/module_test", json=mt_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn("message", response.json)

        # use the addAnalysis endpoint as get with MTA1 name
        response = self.client.get(
            "/addAnalysis", query_string={"moduleTestAnalysisName": "MTA1"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["message"], "Analysis MTA1 added to module test MT1"
        )
        # get the module_test back
        response = self.client.get("/module_test/MT1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["moduleTestName"], "MT1")
        # check the analysis list contains MTA1
        self.assertEqual(response.json["analysesList"], ["MTA1"])
        # check that referenceAnalysis is MTA1
        self.assertEqual(response.json["referenceAnalysis"], "MTA1")

    def test_fetch_module_results(self):
        self.test_insert_cable_templates()

        # 1. Create test data for all collections
        
        # Create a session
        session_data = {
            "sessionName": "TestSession123",
            "timestamp": "2023-12-15T10:00:00",
            "operator": "Test Operator",
            "description": "Test session for module results",
            "modulesList": ["TestModule001"],
            "configuration": {"setting1": "value1", "setting2": "value2"},
            "log": ["Log entry 1", "Log entry 2"]
        }
        session_response = self.client.post("/sessions", json=session_data)
        self.assertEqual(session_response.status_code, 201)
        session_name = session_response.json["sessionName"]
        
        # Create a second session
        session_data2 = {
            "sessionName": "TestSession456",
            "timestamp": "2023-12-16T10:00:00",
            "operator": "Another Operator",
            "description": "Second test session",
            "modulesList": ["TestModule001"],
            "configuration": {"setting1": "different", "setting3": "new_value"},
            "log": ["Second session log entry"]
        }
        session_response2 = self.client.post("/sessions", json=session_data2)
        self.assertEqual(session_response2.status_code, 201)
        session_name2 = session_response2.json["sessionName"]
        
        # Create test runs - one for each session
        test_run_data = {
            "test_runName": "TestRun001",
            "runDate": "2023-12-15T11:00:00",
            "runStatus": "completed",
            "runType": "qualification",
            "runSession": session_name,
            "runBoards": {
                "1": "fc7ot1"
            },
            "_moduleTest_id": [],  # Will be updated later
            "moduleTestName": [],  # Will be updated later
            "runFile": "http://example.com/test-data-001.root",
            "runConfiguration": {"config1": "val1", "config2": "val2"}
        }
        run_response = self.client.post("/test_run", json=test_run_data)
        self.assertEqual(run_response.status_code, 201)
        
        test_run_data2 = {
            "test_runName": "TestRun002",
            "runDate": "2023-12-16T11:00:00",
            "runStatus": "completed",
            "runType": "thermal_cycle",
            "runSession": session_name2,
            "runBoards": {
                "1": "fc7ot2"
            },
            "_moduleTest_id": [],  # Will be updated later
            "moduleTestName": [],  # Will be updated later
            "runFile": "http://example.com/test-data-002.root",
            "runConfiguration": {"temperature": 35, "cycles": 10}
        }
        run_response2 = self.client.post("/test_run", json=test_run_data2)
        self.assertEqual(run_response2.status_code, 201)
        
        # Create a module with required fields
        module_data = {
            "moduleName": "TestModule001",
            "position": "testbench",
            "status": "testing",
            "type": "module",  # Required field according to schema
            "moduleTests": [],  # Will be populated with test names
            # "crateSide": {"1": [], "2": [], "3": [], "4": []}
        }
        module_response = self.client.post("/modules", json=module_data)
        self.assertEqual(module_response.status_code, 201)
        
        # Create multiple module tests for the module
        # Test 1 - Qualification test
        module_test_data1 = {
            "moduleTestName": "ModuleTest001",
            "_test_run_id": ObjectId("5f9b3b9b9d9d7b3d9d9d7b3d"),  # Placeholder ObjectId
            "test_runName": "TestRun001",
            "_module_id": ObjectId("5f9b3b9b9d9d7b3d9d9d7b3d"),  # Placeholder ObjectId
            "moduleName": "TestModule001",
            "noise": {"channel1": 2.5, "channel2": 3.1},
            "board": "fc7ot1",
            "opticalGroupName": 0
        }
        module_test_response1 = self.client.post("/module_test", json=module_test_data1)
        self.assertEqual(module_test_response1.status_code, 201)
        
        # get the ObjectId of the created module test
        module_test_id1 = self.client.get("/module_test/ModuleTest001").json["_id"]

        # Test 2 - Thermal cycle test
        module_test_data2 = {
            "moduleTestName": "ModuleTest002",
            "_test_run_id": ObjectId("5f9b3b9b9d9d7b3d9d9d7b3e"),  # Different placeholder ObjectId
            "test_runName": "TestRun002",
            "_module_id": ObjectId("5f9b3b9b9d9d7b3d9d9d7b3d"),  # Same module ID
            "moduleName": "TestModule001",
            "noise": {"channel1": 2.7, "channel2": 3.3, "channel3": 2.9},
            "board": "fc7ot2",
            "opticalGroupName": 1
        }
        module_test_response2 = self.client.post("/module_test", json=module_test_data2)
        self.assertEqual(module_test_response2.status_code, 201)
        module_test_id2 = self.client.get("/module_test/ModuleTest002").json["_id"]
        
        # Update the module with test references
        update_module = {
            "moduleTests": [["ModuleTest001", str(module_test_id1)], ["ModuleTest002", str(module_test_id2
            )]]
        }
        update_module_response = self.client.put("/modules/TestModule001", json=update_module)
        self.assertEqual(update_module_response.status_code, 200)
        
        # Update test runs with module test references
        update_run1 = {
            "_moduleTest_id": [str(ObjectId("5f9b3b9b9d9d7b3d9d9d7b3d"))],
            "moduleTestName": ["ModuleTest001"]
        }
        update_run_response1 = self.client.put("/test_run/TestRun001", json=update_run1)
        self.assertEqual(update_run_response1.status_code, 200)
        
        update_run2 = {
            "_moduleTest_id": [str(ObjectId("5f9b3b9b9d9d7b3d9d9d7b3e"))],
            "moduleTestName": ["ModuleTest002"]
        }
        update_run_response2 = self.client.put("/test_run/TestRun002", json=update_run2)
        self.assertEqual(update_run_response2.status_code, 200)
        
        # Create analyses for both tests
        # Analysis for Test 1
        analysis_data1 = {
            "moduleTestAnalysisName": "Analysis001",
            "moduleTestName": "ModuleTest001",
            "moduleTest_id": str(ObjectId("5f9b3b9b9d9d7b3d9d9d7b3d")),
            "analysisVersion": "v1.0",
            "analysisResults": {"metric1": 95.2, "metric2": 87.9},
            "analysisSummary": {"summary": "All tests passed", "status": "PASS"},
            "analysisFile": "http://example.com/analysis-001.json"
        }
        analysis_response1 = self.client.post("/module_test_analysis", json=analysis_data1)
        self.assertEqual(analysis_response1.status_code, 201)
        
        # Analysis for Test 2
        analysis_data2 = {
            "moduleTestAnalysisName": "Analysis002",
            "moduleTestName": "ModuleTest002",
            "moduleTest_id": str(ObjectId("5f9b3b9b9d9d7b3d9d9d7b3e")),
            "analysisVersion": "v1.0",
            "analysisResults": {"metric1": 92.1, "metric2": 85.3, "thermal_stability": "good"},
            "analysisSummary": {"summary": "Thermal cycle completed", "status": "PASS"},
            "analysisFile": "http://example.com/analysis-002.json"
        }
        analysis_response2 = self.client.post("/module_test_analysis", json=analysis_data2)
        self.assertEqual(analysis_response2.status_code, 201)
        
        # Update module tests with analysis references
        update_test1 = {
            "analysesList": ["Analysis001"],
            "referenceAnalysis": "Analysis001"
        }
        update_test_response1 = self.client.put("/module_test/ModuleTest001", json=update_test1)
        self.assertEqual(update_test_response1.status_code, 200)
        
        update_test2 = {
            "analysesList": ["Analysis002"],
            "referenceAnalysis": "Analysis002"
        }
        update_test_response2 = self.client.put("/module_test/ModuleTest002", json=update_test2)
        self.assertEqual(update_test_response2.status_code, 200)
        
        # 2. Call the endpoint and verify the response
        response = self.client.get("/fetch_module_results/TestModule001")
        self.assertEqual(response.status_code, 200)
        result = response.json
        
        # 3. Verify that the response contains all expected data
        self.assertEqual(result["moduleName"], "TestModule001")
        self.assertTrue("tests" in result)
        self.assertEqual(len(result["tests"]), 2, "Expected exactly two tests in the results")
        
        # Sort tests by name to ensure consistent ordering for assertions
        tests = sorted(result["tests"], key=lambda x: x["name"])
        
        # Verify first test (ModuleTest001)
        test1 = tests[0]
        self.assertEqual(test1["name"], "ModuleTest001")
        self.assertEqual(test1["details"]["board"], "fc7ot1")
        
        # Verify run data for test1
        self.assertTrue("run" in test1)
        self.assertEqual(test1["run"]["test_runName"], "TestRun001")
        self.assertEqual(test1["run"]["runType"], "qualification")
        
        # Verify session data for test1
        self.assertTrue("session" in test1)
        self.assertEqual(test1["session"]["operator"], "Test Operator")
        
        # Verify analysis data for test1
        self.assertTrue("analysis" in test1)
        self.assertEqual(test1["analysis"]["moduleTestAnalysisName"], "Analysis001") 
        self.assertEqual(test1["analysis"]["analysisSummary"]["status"], "PASS")
        
        # Verify second test (ModuleTest002)
        test2 = tests[1]
        self.assertEqual(test2["name"], "ModuleTest002")
        self.assertEqual(test2["details"]["board"], "fc7ot2")
        
        # Verify run data for test2
        self.assertTrue("run" in test2)
        self.assertEqual(test2["run"]["test_runName"], "TestRun002")
        self.assertEqual(test2["run"]["runType"], "thermal_cycle")
        
        # Verify session data for test2
        self.assertTrue("session" in test2)
        self.assertEqual(test2["session"]["operator"], "Another Operator")
        
        # Verify analysis data for test2
        self.assertTrue("analysis" in test2)
        self.assertEqual(test2["analysis"]["moduleTestAnalysisName"], "Analysis002")
        self.assertEqual(test2["analysis"]["analysisSummary"]["status"], "PASS")
        self.assertIn("thermal_stability", test2["analysis"]["analysisResults"])


if __name__ == "__main__":
    unittest.main()
