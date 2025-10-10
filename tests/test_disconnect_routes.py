import unittest
from flask_testing import TestCase
import sys
import os
import json
# jsonify stuff
from flask import jsonify

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.app import create_app, get_unittest_db
from examples.cables_templates import cables_templates


class TestGenericQueryAPI(TestCase):
    def create_app(self):
        return create_app("unittest")

    def setUp(self):
        self.app = self.create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db = get_unittest_db()
            db.modules.drop()
                        
            for template in cables_templates:
                db.cable_templates.insert_one(template)
        
    def tearDown(self):
        with self.app.app_context():
            db = get_unittest_db()
            db.modules.drop()
            db.cables.drop()
            db.cable_templates.drop()
            
    def test_connect_all_ports_dodecapus_to_exapus_to_module(self):
          # 1. Create some cables and modules
        # Insert some sample modules for testing
        burnin = {
            "name": "B1",
            "type": "burninslot",
            "detSide": {},
            "crateSide": {},
            }
        patch_panel = {
            "name": "P001",
            "type": "patchpanel",
            "detSide": {},
            "crateSide": {},
        }
        caen_HV = {
            "name": "ASLOT0",
            "type": "caenHV",
            "detSide": {},
            "crateSide": {},
        }
        caen_LV = {
            "name": "XSLOT6",
            "type": "caenLV",
            "detSide": {},
            "crateSide": {},
        }
        response = self.client.post("/cables", json=burnin)
        self.assertEqual(response.status_code, 201)
        response = self.client.post("/cables", json=patch_panel)
        self.assertEqual(response.status_code, 201)
        response = self.client.post("/cables", json=caen_HV)
        self.assertEqual(response.status_code, 201)
        response = self.client.post("/cables", json=caen_LV)
        self.assertEqual(response.status_code, 201)
                # define a module
        new_module = {
            "moduleName": "modulecabletest",
            "position": "cleanroom",
            "status": "readyformount",
            # ... (other properties)
        }

        response = self.client.post("/modules", json=new_module)
        self.assertEqual(response.status_code, 201)
        
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

        #fetch exapus and print it
        response = self.client.get("/cables/E31")
        self.assertEqual(response.status_code, 200)
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
        
        # connect_data = {
        #     "cable1": "modulecabletest",
        #     "cable2": "E31",
        #     "port1": "fiber",
        #     "port2": "1",
        # }
        # response = self.client.post("/connect", json=connect_data)
        # self.assertEqual(response.status_code, 200)
        # self.assertEqual(response.json, {"message": "Cables connected successfully"})
        # # Check if cables are connected correctly
        # response = self.client.get("/modules/modulecabletest")
        # self.assertEqual(response.status_code, 200)
        # self.assertEqual(
        #     response.json["crateSide"],
        #     {"1": ["E31", 1], "2": ["E31", 2], "3": [], "4": []},
        # )
        
        # connect module to burnin on all 4 ports
        connect_data = {
            "cable1": "modulecabletest",
            "cable2": "B1",
            "port1": "fiber",
            "port2": "fiber",
        }
        response = self.client.post("/connect", json=connect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Cables connected successfully"})
        connect_data = {
            "cable1": "modulecabletest",
            "cable2": "B1",
            "port1": "power",
            "port2": "power",
        }
        response = self.client.post("/connect", json=connect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Cables connected successfully"})
        
        # get module and check its connections
        response = self.client.get("/modules/modulecabletest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["crateSide"],
            {"1": ["B1", 1], "2": ["B1", 2], "3": ["B1", 3], "4": ["B1", 4]},
        )

        # connect burnin slot to patch panel on port 3, 4
        connect_data = {
            "cable1": "B1",
            "cable2": "P001",
            "port1": "HVLV",
            "port2": "B1",
        }
        response = self.client.post("/connect", json=connect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Cables connected successfully"})
        
        # connect burning slot to exapus on port 1, 2
        connect_data = {
            "cable1": "B1",
            "cable2": "E31",
            "port1": "fiber",
            "port2": "1",
        }
        response = self.client.post("/connect", json=connect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Cables connected successfully"})

        # check burnin slot
        response = self.client.get("/cables/B1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["crateSide"],
            {"1": ["E31", 1], "2": ["E31", 2], "3": ["P001", 1], "4": ["P001", 13]},
        )
        self.assertEqual(
            response.json["detSide"],
            {"1": ["modulecabletest", 1], "2": ["modulecabletest", 2], "3": ["modulecabletest", 3], "4": ["modulecabletest", 4]},
        )
        
    def test_disconnect_all_ports_exapus(self):
        
        self.test_connect_all_ports_dodecapus_to_exapus_to_module()
        
        #check first status of exapus
        response = self.client.get("/cables/E31")
        self.assertEqual(response.status_code, 200)
        # and the dodecapus
        response = self.client.get("/cables/D31")
        self.assertEqual(response.status_code, 200)
        # 3. Disconnect all ports of E31
        disconnect_data = {
            "cable": "E31"
        }
        response = self.client.post("/disconnect_all", json=disconnect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "All ports disconnected successfully"})
        # Check if E31 is disconnected
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
        self.assertEqual(response.json["detSide"], empty_side)
        # let's also check that the exapus is disconnected from the burnin slot
        response = self.client.get("/cables/B1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["crateSide"],
            {"1": [], "2": [], "3": ["P001", 1], "4": ["P001", 13]},
        )
        self.assertEqual(
            response.json["detSide"],
            {"1": ["modulecabletest", 1], "2": ["modulecabletest", 2], "3": ["modulecabletest", 3], "4": ["modulecabletest", 4]},
        )


    def test_disconnect_all_ports_module(self):
        
        self.test_connect_all_ports_dodecapus_to_exapus_to_module()
        
        #check first status of exapus
        response = self.client.get("/cables/E31")
        self.assertEqual(response.status_code, 200)
        # and the dodecapus
        response = self.client.get("/cables/D31")
        self.assertEqual(response.status_code, 200)
        # and the module
        response = self.client.get("/modules/modulecabletest")
        self.assertEqual(response.status_code, 200)
        # 3. Disconnect all ports of modulecabletest
        disconnect_data = {
            "cable": "modulecabletest"
        }
        response = self.client.post("/disconnect_all", json=disconnect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "All ports disconnected successfully"})
        # Check if module is disconnected
        response = self.client.get("/modules/modulecabletest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["crateSide"],
            {"1": [], "2": [], "3": [], "4": []},
        )

    def test_disconnect_crateSide_module(self):
        """Test disconnecting only crateSide of a module"""
        self.test_connect_all_ports_dodecapus_to_exapus_to_module()
        
        # Disconnect only crateSide of module
        disconnect_data = {
            "cable": "modulecabletest"
        }
        response = self.client.post("/disconnect_all_crateSide", json=disconnect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "All ports disconnected successfully"})
        
        # Check if module crateSide is disconnected
        response = self.client.get("/modules/modulecabletest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["crateSide"],
            {"1": [], "2": [], "3": [], "4": []},
        )
        
        # Check that B1 detSide is also disconnected (since module was connected there)
        response = self.client.get("/cables/B1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["detSide"],
            {"1": [], "2": [], "3": [], "4": []},
        )
        
        # Check that B1 crateSide is still connected
        self.assertEqual(
            response.json["crateSide"],
            {"1": ["E31", 1], "2": ["E31", 2], "3": ["P001", 1], "4": ["P001", 13]},
        )

    def test_disconnect_crateSide_burnin(self):
        """Test disconnecting only crateSide of burnin slot"""
        self.test_connect_all_ports_dodecapus_to_exapus_to_module()
        
        # Disconnect only crateSide of B1
        disconnect_data = {
            "cable": "B1"
        }
        response = self.client.post("/disconnect_all_crateSide", json=disconnect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "All ports disconnected successfully"})
        
        # Check if B1 crateSide is disconnected
        response = self.client.get("/cables/B1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["crateSide"],
            {"1": [], "2": [], "3": [], "4": []},
        )
        
        # Check that B1 detSide is still connected
        self.assertEqual(
            response.json["detSide"],
            {"1": ["modulecabletest", 1], "2": ["modulecabletest", 2], "3": ["modulecabletest", 3], "4": ["modulecabletest", 4]},
        )
        
        # check that the module crateSide is still connected to burnin
        response = self.client.get("/modules/modulecabletest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["crateSide"],
            {"1": ["B1", 1], "2": ["B1", 2], "3": ["B1", 3], "4": ["B1", 4]},
        )
        
        # Check that E31 detSide is disconnected (was connected to B1 crateSide)
        response = self.client.get("/cables/E31")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["detSide"]["1"], []
        )
        self.assertEqual(
            response.json["detSide"]["2"], []
        )
        
        # Check that P001 detSide is disconnected
        response = self.client.get("/cables/P001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["detSide"]["1"], []
        )
        self.assertEqual(
            response.json["detSide"]["13"], []
        )

    def test_disconnect_detSide_burnin(self):
        """Test disconnecting only detSide of burnin slot"""
        self.test_connect_all_ports_dodecapus_to_exapus_to_module()
        
        # Disconnect only detSide of B1
        disconnect_data = {
            "cable": "B1"
        }
        response = self.client.post("/disconnect_all_detSide", json=disconnect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "All ports disconnected successfully"})
        
        # Check if B1 detSide is disconnected
        response = self.client.get("/cables/B1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["detSide"],
            {"1": [], "2": [], "3": [], "4": []},
        )
        
        # Check that B1 crateSide is still connected
        self.assertEqual(
            response.json["crateSide"],
            {"1": ["E31", 1], "2": ["E31", 2], "3": ["P001", 1], "4": ["P001", 13]},
        )
        
        # Check that module crateSide is disconnected (was connected to B1 detSide)
        response = self.client.get("/modules/modulecabletest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["crateSide"],
            {"1": [], "2": [], "3": [], "4": []},
        )
        
    def test_disconnect_detSide_patchpanel(self):
        """Test disconnecting only detSide of patch panel"""
        self.test_connect_all_ports_dodecapus_to_exapus_to_module()
        
        # get and print PP now
        response = self.client.get("/cables/P001")
        self.assertEqual(response.status_code, 200)
        # Disconnect only detSide of P001
        disconnect_data = {
            "cable": "P001"
        }
        response = self.client.post("/disconnect_all_detSide", json=disconnect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "All ports disconnected successfully"})
        
        # Check if P001 detSide is disconnected
        response = self.client.get("/cables/P001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["detSide"],
            {'1': [], '2': [], '3': [], '4': [], '5': [], '6': [], '7': [], '8': [], '9': [], '10': [], '11': [], '12': [], '13': [], '14': [], '15': [], '16': [], '17': [], '18': [], '19': [], '20': [], '21': [], '22': [], '23': [], '24': []},
        )
        
        
        # Check that B1 crateSide is not connected to P001
        response = self.client.get("/cables/B1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["crateSide"],
            {"1": ["E31", 1], "2": ["E31", 2], "3": [], "4": []},
        )
        
        # check that the module crateSide is still connected to burnin
        response = self.client.get("/modules/modulecabletest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json["crateSide"],
            {"1": ["B1", 1], "2": ["B1", 2], "3": ["B1", 3], "4": ["B1", 4]},
        )
