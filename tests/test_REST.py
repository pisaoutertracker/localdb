import unittest
from flask_testing import TestCase
import sys

sys.path.append("..")
from app.flask_REST import (
    app,
    db,
)
from bson import ObjectId


class TestAPI(TestCase):
    def create_app(self):
        app.config["TESTING"] = True
        app.config["MONGODB_SETTINGS"] = {
            "db": "unittest_db"  # replace with your test database name
        }
        return app

    def setUp(self):
        db.modules.drop()
        db.logbook.drop()
        db.current_cabling_map.drop()
        db.tests.drop()
        db.testpayloads.drop()
        db.cables.drop()
        db.cables_templates.drop()
        db.crates.drop()

    def tearDown(self):
        db.modules.drop()
        db.logbook.drop()
        db.current_cabling_map.drop()
        db.tests.drop()
        db.testpayloads.drop()
        db.cables.drop()
        db.cables_templates.drop()
        db.crates.drop()

    def test_fetch_all_modules_empty(self):
        response = self.client.get("/modules")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

    def test_insert_module(self):
        new_module = {
            "moduleID": "INV001",
            "position": "cleanroom",
            "status": "readyformount",
            # ... (other properties)
        }
        response = self.client.post("/modules", json=new_module)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"message": "Module inserted"})

        response = self.client.get("/modules/INV001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["moduleID"], "INV001")

    def test_fetch_specific_module_not_found(self):
        response = self.client.get("/modules/INV999")
        self.assertEqual(response.status_code, 404)

    def test_delete_module_not_found(self):
        response = self.client.delete("/modules/INV999")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Module deleted"})

    def test_insert_log(self):
        new_log = {
            "timestamp": "2023-11-03T14:21:29Z",
            "event": "Module added",
            "operator": "John Doe",
            "station": "pccmslab1",
            "sessionid": "TESTSESSION1"
        }
        response = self.client.post("/logbook", json=new_log)
        self.assertEqual(response.status_code, 201)

    def test_fetch_log_not_found(self):
        response = self.client.get("/logbook/123456789012123456789012")
        self.assertEqual(response.status_code, 404)

    def test_delete_log_not_found(self):
        response = self.client.delete("/logbook/123456789012123456789012")
        self.assertEqual(response.status_code, 404)

    def test_delete_log(self):
        # First, let's insert a log entry
        new_log = {
            "timestamp": "2023-11-03T14:21:29Z",
            "event": "Module added",
            "operator": "John Doe",
            "station": "pccmslab1",
            "sessionid": "TESTSESSION1"
        }
        _id = ((self.client.post("/logbook", json=new_log)).json)["_id"]
        # Now, let's delete it
        response = self.client.delete("/logbook/"+str(_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Log deleted"})

    def test_insert_and_retrieve_test(self):
        new_test = {
            "testID": "T001",
            "modules_list": ["M1", "M2"],
            "testType": "Type1",
            "testDate": "2023-11-01",
            "testStatus": "completed",
            "testResults": {},
        }

        # Insert
        response = self.client.post("/tests", json=new_test)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json(), {"message": "Entry inserted"})

        # Retrieve
        response = self.client.get("/tests/T001")
        retrieved_test = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(retrieved_test["testID"], "T001")

    def test_delete_test(self):
        # Delete
        new_test = {
            "testID": "T001",
            "modules_list": ["M1", "M2"],
            "testType": "Type1",
            "testDate": "2023-11-01",
            "testStatus": "completed",
            "testResults": {},
        }

        # Insert
        insert = self.client.post("/tests", json=new_test)
        response = self.client.delete("/tests/T001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"message": "Entry deleted"})

        # Verify Deletion
        response = self.client.get("/tests/T001")
        self.assertEqual(response.status_code, 404)

        """    def newTest(self):
        try:
            new_entry = request.get_json()
            validate(instance=new_entry, schema=tests_schema)
            tests_collection.insert_one(new_entry)
        
            for moduleID in new_entry["modules_list"]:
                modules_collection.update_one({"moduleID": moduleID}, {"$push": {"tests": new_entry["testID"]}})
            return {"message": "Entry inserted"}, 201
        
        except ValidationError as e:
            return {"message": str(e)}, 400
        """

    def test_addTest(self):
        new_test = {
            "testID": "T001",
            "modules_list": ["M1", "M2"],
            "testType": "Type1",
            "testDate": "2023-11-01",
            "testStatus": "completed",
            "testResults": {},
        }
        # create modules
        new_module = {
            "moduleID": "M1",
            "position": "cleanroom",
            "status": "readyformount",
            # ... (other properties)
        }
        response = self.client.post("/modules", json=new_module)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"message": "Module inserted"})
        new_module = {
            "moduleID": "M2",
            "position": "cleanroom",
            "status": "readyformount",
            # ... (other properties)
        }
        response = self.client.post("/modules", json=new_module)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"message": "Module inserted"})

        response = self.client.post("/addTest", json=new_test)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json(), {"message": "Entry inserted"})

        # check if the test was inserted in the modules
        response = self.client.get("/modules/M1")
        retrieved_module = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(retrieved_module["tests"], ["T001"])

    def test_insert_cable_templates(self):
        cable_templates = [
            {
                "type": "exapus",
                "internalRouting": {
                    "1": [1, 2],
                    "2": [3, 4],
                    "3": [5, 6],
                    "4": [7, 8],
                    "5": [9, 10],
                    "6": [11, 12],
                },
            },
            {
                "type": "extfib",
                "internalRouting": {
                    "1": 1,
                    "2": 2,
                    "3": 3,
                    "4": 4,
                    "5": 5,
                    "6": 6,
                    "7": 7,
                    "8": 8,
                    "9": 9,
                    "10": 10,
                    "11": 11,
                    "12": 12,
                },
            },
            {
                "type": "dodecapus",
                "internalRouting": {
                    "1": 3,
                    "2": 6,
                    "3": 9,
                    "4": 12,
                    "5": 2,
                    "6": 5,
                    "7": 8,
                    "8": 11,
                    "9": 1,
                    "10": 4,
                    "11": 7,
                    "12": 10,
                },
            },
        ]

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
        new_cable = {
            "name": "Test Cable",
            "type": "exapus",
            "detSide": [],  # No connections on the detector side
            "crateSide": [],  # No connections on the crate side
        }
        response = self.client.post("/cables", json=new_cable)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"message": "Entry inserted"})

        # Assuming you have an endpoint to fetch a cable by its name or another unique identifier
        response = self.client.get(f"/cables/{new_cable['name']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], new_cable["name"])
        self.assertEqual(response.json["type"], new_cable["type"])
        self.assertListEqual(response.json["detSide"], new_cable["detSide"])
        self.assertListEqual(response.json["crateSide"], new_cable["crateSide"])

    def test_create_connect_disconnect_cables(self):
        # 1. Create some cables
        cables = [
            {"name": "Cable 1", "type": "12-to-1", "detSide": [], "crateSide": []},
            {"name": "Cable 2", "type": "12-to-1", "detSide": [], "crateSide": []},
        ]
        for cable in cables:
            response = self.client.post("/cables", json=cable)
            self.assertEqual(response.status_code, 201)

        # 2. Connect them
        connect_data = {
            "cable1_name": "Cable 1",
            "cable1_port": 1,
            "cable1_side": "crateSide",
            "cable2_name": "Cable 2",
            "cable2_port": 1,
        }
        response = self.client.post("/connectCables", json=connect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Cables connected"})

        # Check if cables are connected correctly
        response = self.client.get("/cables/Cable 1")
        self.assertEqual(response.status_code, 200)
        # Fetch Cable 2's ObjectId for comparison
        cable2_response = self.client.get("/cables/Cable 2")
        cable2_id = cable2_response.json["_id"]
        connection_exists = any(
            conn["port"] == 1 and conn["connectedTo"] == cable2_id
            for conn in response.json["crateSide"]
        )
        self.assertTrue(connection_exists)

        # 3. Disconnect them
        disconnect_data = {
            "cable1_name": "Cable 1",
            "cable1_port": 1,
            "cable1_side": "crateSide",
            "cable2_name": "Cable 2",
            "cable2_port": 1,
        }
        response = self.client.post("/disconnectCables", json=disconnect_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Cable disconnected"})

        # Check if cables are disconnected correctly
        response = self.client.get("/cables/Cable 1")
        self.assertEqual(response.status_code, 200)
        connection_not_exists = all(
            conn["port"] != 1 or conn["connectedTo"] != cable2_id
            for conn in response.json["crateSide"]
        )
        self.assertTrue(connection_not_exists)

    def test_cabling_snapshot(self):
        # 1. Create module, crate, and cables
        cables = [
            {"name": "Cable 3", "type": "extfib", "detSide": [], "crateSide": []},
            {"name": "Cable 4", "type": "extfib", "detSide": [], "crateSide": []},
        ]
        for cable in cables:
            self.client.post("/cables", json=cable)
        
        # get the cables ids
        cable3_response = self.client.get("/cables/Cable 3").json
        cable3_id = cable3_response["_id"]
        cable4_response = self.client.get("/cables/Cable 4").json
        cable4_id = cable4_response["_id"]

        module = {
            "moduleID": "Module 1",
            "position": "cleanroom",
            "status": "readyformount",
            "connectedTo": cable3_id,
        }
        crate = {"name": "Crate 1", "connectedTo": cable4_id}

        module_insert = self.client.post("/modules", json=module)
        crate_insert = self.client.post("/crates", json=crate)

        # get crate and module ids
        module_id = self.client.get("/modules/Module 1").json["_id"]
        crate_id = self.client.get("/crates/Crate 1").json["_id"]
        # add module and crate to the cables
        crate_conn= {
            "port": 1,
            "connectedTo": crate_id,
            "type": "crate"
        }
        module_conn= {
            "port": 2,
            "connectedTo": module_id,
            "type": "module"
        }
        # update cables
        cable3_response["detSide"].append(module_conn)
        cable4_response["crateSide"].append(crate_conn)
        assert cable4_id == cable4_response["_id"]
        # pop _id
        cable3_response.pop("_id")
        cable4_response.pop("_id")

        self.client.put(f"/cables/Cable 4", json=cable4_response)
        self.client.put(f"/cables/Cable 3", json=cable3_response)
        # check that insertions were successful
        response = self.client.get("/cables/Cable 3")
        self.assertEqual(response.status_code, 200)
        connection_exists = any(
            conn["port"] == 2 and conn["connectedTo"] == module_id
            for conn in response.json["detSide"]
        )
        self.assertTrue(connection_exists)
        response = self.client.get("/cables/Cable 4")
        self.assertEqual(response.status_code, 200)
        connection_exists = any(
            conn["port"] == 1 and conn["connectedTo"] == crate_id
            for conn in response.json["crateSide"]
        )
        self.assertTrue(connection_exists)
        
        # 2. Connect the cables
        connect_data = {
            "cable1_name": "Cable 3",
            "cable1_port": 2,
            "cable1_side": "crateSide",
            "cable2_name": "Cable 4",
            "cable2_port": 1,
        }
        self.client.post("/connectCables", json=connect_data)
        # check if cables are connected correctly
        response = self.client.get("/cables/Cable 3")
        self.assertEqual(response.status_code, 200)
        connection_exists = any(
            conn["port"] == 2 and conn["connectedTo"] == cable4_id
            for conn in response.json["crateSide"]
        )
        self.assertTrue(connection_exists)

        # 3. Perform the three snapshots
        # Snapshot from Module
        snapshot_module = self.client.post(
            "/cablingSnapshot",
            json={"starting_point_name": "Module 1", "starting_side": "detSide"},
        )

        self.assertEqual(snapshot_module.status_code, 200)
        self.assertEqual(snapshot_module.json["cablingPath"], ["Module 1", "Cable 3", "Cable 4", "Crate 1"]) 
        
        # Snapshot from Crate
        snapshot_crate = self.client.post(
            "/cablingSnapshot",
            json={"starting_point_name": "Crate 1", "starting_side": "crateSide"},
        )
        self.assertEqual(snapshot_crate.status_code, 200)
        self.assertEqual(snapshot_crate.json["cablingPath"], ["Crate 1", "Cable 4", "Cable 3", "Module 1"])

        # Snapshot from Cable (detSide)
        snapshot_cable_det = self.client.post(
            "/cablingSnapshot",
            json={
                "starting_point_name": "Cable 3",
                "starting_side": "detSide",
                "starting_port": 2,
            },
        )
        self.assertEqual(snapshot_cable_det.status_code, 200)
        self.assertEqual(snapshot_cable_det.json["cablingPath"], ["Cable 3", "Cable 4", "Crate 1"])

        # Snapshot from Cable (crateSide)
    def test_LogBookSearchByText(self):
        new_log = {
            "timestamp": "2023-11-03T14:21:29Z",
            "event": "Module added",
            "operator": "John Doe",
            "event": "pippo",
            "station": "pccmslab1",
            "sessionid": "TESTSESSION1",
            "involved_modules": ['PS_1','PS_2']
        }
        response = self.client.post("/logbook", json=new_log)
        new_log2 = {
            "timestamp": "2023-11-03T14:21:29Z",
            "event": "Module added",
            "operator": "John Do2",
            "details": "pippo",
            "station": "pccmslab1",
            "sessionid": "TESTSESSION2",
            "involved_modules": ['MS_1','MS_2']
        }
        response = self.client.post("/logbook", json=new_log2)

        logbook_entries = self.client.post(
            "/searchLogBookByText",
            json={
                "modules": "pi.*o"
            }
        )
        self.assertEqual(logbook_entries.status_code, 200) 
        self.assertEqual(len(logbook_entries.json),2)




    def test_LogBookSearchByModuleIDs(self):
        #insert a few entriesi for testing
        new_log = {
            "timestamp": "2023-11-03T14:21:29Z",
            "event": "Module added",
            "operator": "John Doe",
            "station": "pccmslab1",
            "sessionid": "TESTSESSION1",
            "involved_modules": ['PS_1','PS_2']
        }
        response = self.client.post("/logbook", json=new_log)
        new_log2 = {
            "timestamp": "2023-11-03T14:21:29Z",
            "event": "Module added",
            "operator": "John Doe",
            "station": "pccmslab1",
            "sessionid": "TESTSESSION1",
            "involved_modules": ['MS_1','MS_2']
        }
        response = self.client.post("/logbook", json=new_log2)

        logbook_entries = self.client.post(
            "/searchLogBookByModuleIDs",
            json={
                "modules": "PS.*"
            }
        )
        self.assertEqual(logbook_entries.status_code, 200) 
        self.assertEqual(len(logbook_entries.json),1)


    def test_insert_log_2(self):
        new_log = {
            "timestamp": "2023-10-03T14:21:29Z",
            "event": "Module added",
            "operator": "John Doe",
            "station": "pccmslab1",
            "involved_modules": ['PS_1','PS_2'],
            "sessionid": "TESTSESSION1",
            "details": " I tried to insert PS_88 and PS_44. and also PS_1."
        }
        response = self.client.post("/logbook", json=new_log)
        self.assertEqual(response.status_code, 201)

#
# now I try to get it back, and I check the involved_modules
#
        _id = str((response.json)["_id"])
        response = self.client.get("/logbook/"+_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["involved_modules"]),4)
#################
    def test_insert_get_delete_testpayload(self):
        new_log = {
            "sessionID": "testsession000",
            "remoteFileList": ['http://cernbox.cern.ch/pippo_pluto','http://cernbox.cern.ch/cappero'],
            "details": " I tried to insert PS_88 and PS_44. and also PS_1."
        }
        response = self.client.post("/testpayloads", json=new_log)
        self.assertEqual(response.status_code, 201)

        _id = str(response.json["_id"])

        # get it back
        response = self.client.get("/testpayloads/"+str(_id))
        self.assertEqual(response.status_code, 200)
        #delete it
        response = self.client.delete("/testpayloads/"+str(_id))
        self.assertEqual(response.status_code, 200)






if __name__ == "__main__":
    unittest.main()
