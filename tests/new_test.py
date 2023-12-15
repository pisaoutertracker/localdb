import unittest
from flask_testing import TestCase
import sys
import os
from dotenv import load_dotenv

sys.path.append("..")
from app.app import (
    create_app,
    get_db,
)
from bson import ObjectId
from pymongo import MongoClient
import os

class TestAPI(TestCase):
    def create_app(self):
        return create_app("test")

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
            db.cables_templates.drop()
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
        respone = self.client.get("/modules/Module 1")
        self.assertEqual(respone.status_code, 200)
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
        response = self.client.post("/test_payloads", json=new_log)
        self.assertEqual(response.status_code, 201)

        _id = str(response.json["_id"])

        # get it back
        response = self.client.get("/test_payloads/"+str(_id))
        self.assertEqual(response.status_code, 200)
        #delete it
        response = self.client.delete("/test_payloads/"+str(_id))
        self.assertEqual(response.status_code, 200)


    def test_add_run(self):
        # Sample data
        session_entry = {
            "timestamp": "2023-11-03T14:21:29",
            "operator": "John Doe",
            "description": "I tried to insert PS_88 and PS_44. and also PS_1.",
            "modulesList": ['PS_1','PS_2'],
            "configuration": {"a":"b"},
            "log": ["uuhuh", 'pippo']
        }
        # insert it
        response = self.client.post('/sessions', json=session_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.json)
        # get the sessionKey from the response
        sessionKey = response.json['sessionKey']

        test_run_data = {
        'runDate': '1996-11-21T10:00:56',
        'runStatus': 'failed',
        'runType': 'Type1',
        'runSession': sessionKey,
        'runBoards': {
            3: 'fc7ot2',
            4: 'fc7ot3',
        },
        'runModules' : { ## (board, optical group) : (moduleID, hwIDmodule)
            'fc7ot2_optical0' : ("M123", 67),
            'fc7ot2_optical1' : ("M124", 68),
            'fc7ot3_optical2' : ("M125", 69),
        },
        'runResults' : {
            67 : "pass",
            68 : "failed",
            69 : "failed",
        },
        'runNoise' : {
            67 : {
                "SSA0": 4.348,
                "SSA4": 3.348,
                "MPA9": 2.348,
            },
            68 : {
                "SSA0": 3.348,
                "SSA1": 3.648,
            },
            69 : {
                "SSA0": 3.548,
                "SSA4": 3.248,
            }
        },
        'runConfiguration' : {"a":"b"},
        'runFile' : "link"
        }
        

        response = self.client.post('/addRun', json=test_run_data)
        self.assertEqual(response.status_code, 201)
        self.assertIn('run_id', response.json)
        self.assertIn('message', response.json)

    def test_run_get(self):
        session_entry = {
            "timestamp": "2023-11-03T14:21:29",
            "operator": "John Doe",
            "description": "I tried to insert PS_88 and PS_44. and also PS_1.",
            "modulesList": ['PS_1','PS_2'],
            "configuration": {"a":"b"},
            "log": ["uuhuh", 'pippo']
        }
        # insert it
        response = self.client.post('/sessions', json=session_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.json)
        # get the sessionKey from the response
        sessionKey = response.json['sessionKey']

        run_entry = {
        "runDate": "1996-11-21",
        "test_runID": "T53",
        "runSession": sessionKey,
        "runStatus": "failed",
        "runType": "Type1",
        "runBoards": {
            3: 'fc7ot2',
            4: 'fc7ot3',
        },
        "tests": {},
        "runFile": "link",
        "runConfiguration": {"a":"b"},
        }
        # insert it
        response = self.client.post('/test_run', json=run_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.json)
        # get it back
        response = self.client.get('/test_run/T53')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['test_runID'], 'T53')
        # modify it
        run_entry['runStatus'] = 'passed'
        response = self.client.put('/test_run/T53', json=run_entry)
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.json)
        # get all test_runs
        response = self.client.get('/test_run')
        self.assertEqual(response.status_code, 200)
        # delete it
        response = self.client.delete('/test_run/T53')
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.json)

    def test_session_resource(self):
        session_entry = {
            "timestamp": "2023-11-03T14:21:29",
            "operator": "John Doe",
            "description": "I tried to insert PS_88 and PS_44. and also PS_1.",
            "modulesList": ['PS_1','PS_2'],
            "configuration": {"a":"b"},
            "log": ["uuhuh", 'pippo']
        }
        # insert it
        response = self.client.post('/sessions', json=session_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.json)
        # get the sessionKey from the response
        sessionKey = response.json['sessionKey']
        # get it back
        response = self.client.get(f'/sessions/{sessionKey}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['sessionKey'], f'{sessionKey}')
        # modify it
        session_entry['operator'] = 'John Doe2'
        response = self.client.put(f'/sessions/{sessionKey}', json=session_entry)
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.json)
        # get all sessions
        response = self.client.get(f'/sessions')
        self.assertEqual(response.status_code, 200)
        # delete it
        response = self.client.delete(f'/sessions/{sessionKey}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.json)

    def test_module_test_analysis_resource(self):
        mta_entry = {
            "moduleTestAnalysisKey": "MTA22",
            "moduleTestKey": "MT1",
            "analysisVersion": "v1",
            "analysisResults": {"a":"b"},
            "analysisSummary": {"a":"b"},
            "analysisFile": "link"
        }
        # insert it
        response = self.client.post('/module_test_analysis', json=mta_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.json)
        # get it back
        response = self.client.get('/module_test_analysis/MTA22')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['moduleTestAnalysisKey'], 'MTA22')
        # get by Mongo _id
        _id = response.json['_id']
        response = self.client.get(f'/module_test_analysis/{_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['moduleTestAnalysisKey'], 'MTA22')
        # modify it
        mta_entry['analysisVersion'] = 'v2'
        response = self.client.put('/module_test_analysis/MTA22', json=mta_entry)
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.json)
        # get all module_test_analysis
        response = self.client.get('/module_test_analysis')
        self.assertEqual(response.status_code, 200)
        # delete it
        response = self.client.delete('/module_test_analysis/MTA22')
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.json)
    
    def test_add_analysis(self):

        mta_entry = {
            "moduleTestAnalysisKey": "MTA1",
            "moduleTestKey": "MT1",
            "analysisVersion": "v1",
            "analysisResults": {"a":"b"},
            "analysisSummary": {"a":"b"},
            "analysisFile": "link"
        }
        # insert it
        response = self.client.post('/module_test_analysis', json=mta_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.json)

        mt_entry = {
            "moduleTestKey": "MT1",
            "run": ObjectId("5f9b3b9b9d9d7b3d9d9d7b3d"),
            "module": ObjectId("5f9b3b9b9d9d7b3d9d9d7b3d"),
            "noise": {"a":"b"},
            "board": "fc7ot2",
            "opticalGroupID": 1,
        }

        # insert it
        response = self.client.post('/module_test', json=mt_entry)
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.json)

        # use the addAnalysis endpoint as get with MTA1 name
        response = self.client.get('/addAnalysis', query_string={'moduleTestAnalysisKey': 'MTA1'})        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['message'], 'Analysis MTA1 added to module test MT1')
        # get the module_test back
        response = self.client.get('/module_test/MT1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['moduleTestKey'], 'MT1')
        # check the analysis list contains MTA1
        self.assertEqual(response.json['analysesList'], ['MTA1'])
        # check that referenceAnalysis is MTA1
        self.assertEqual(response.json['referenceAnalysis'], 'MTA1')




if __name__ == "__main__":
    unittest.main()
