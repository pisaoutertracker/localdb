import unittest
from flask_testing import TestCase
import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.app import create_app, get_unittest_db
from bson import ObjectId

class TestIVScansAPI(TestCase):
    def create_app(self):
        return create_app("unittest")

    def setUp(self):
        self.app = self.create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db = get_unittest_db()
            db.iv_scans.drop()

        self.sample_scan_1 = {
            "nameLabel": "PS_MODULE_01", # Module identifier
            "date": "2024-01-15T10:00:00",
            "comment": "Initial test",
            "location": "Lab A",
            "inserter": "Manual",
            "runType": "STANDARD_IV",
            "station": "TestBench1",
            "averageTemperature": 22.5,
            "averageHumidity": 45.0,
            "sessionName": "Session_001",
            "IVScanId": "IVS001", # Scan's own unique ID
            "data": {
                "VOLTS": [-10.0, -20.0],
                "CURRNT_NAMP": [100.0, 200.0],
                "TEMP_DEGC": [22.5, 22.5],
                "RH_PRCNT": [45.0, 45.0],
                "TIME": ["2024-01-15T09:55:00", "2024-01-15T09:56:00"]
            }
        }
        self.sample_scan_2 = {
            "nameLabel": "PS_MODULE_02", # Different module
            "date": "2024-01-16T11:00:00",
            "comment": "Follow-up test",
            "IVScanId": "IVS002",
            "sessionName": "Session_001",
            "data": { "VOLTS": [-5.0], "CURRNT_NAMP": [50.0], "TEMP_DEGC": [23.0], "RH_PRCNT": [48.0], "TIME": ["2024-01-16T10:50:00"]}
        }
        self.sample_scan_3_module_1 = { # Another scan for PS_MODULE_01
            "nameLabel": "PS_MODULE_01",
            "date": "2024-01-17T12:00:00",
            "comment": "Second test for module 1",
            "IVScanId": "IVS003",
            "sessionName": "Session_001",
            "data": { "VOLTS": [-15.0], "CURRNT_NAMP": [150.0], "TEMP_DEGC": [22.8], "RH_PRCNT": [45.5], "TIME": ["2024-01-17T11:55:00"]}
        }
        self.sample_scan_4 = {'nameLabel': 'PS_26_IPG-10008', 'date': '2025-05-29 11:50:54', 'comment': 'quick_test measurement', 'location': 'Pisa', 'inserter': 'thermal', 'runType': 'IV_TEST', 'station': 'cleanroom', 'averageTemperature': 20.099999999999998, 'averageHumidity': 0.14460236858474082, 'sessionName': 'session0', 'IVScanId': 'HV0.6_PS_26_IPG-10008_quick_test', 'data': {'VOLTS': [-0.385, -10.69, -20.379999, -30.184999], 'CURRNT_NAMP': [-90.0, -50.0, -30.0, -10.0], 'TEMP_DEGC': [20.1, 19.7, 20.3, 20.3], 'RH_PRCNT': [0.14813525707178937, 0.14813525707178937, 0.14106948009769227, 0.14106948009769227], 'TIME': ['2025-05-29 09:50:34', '2025-05-29 09:50:41', '2025-05-29 09:50:48', '2025-05-29 09:50:54']}}


    def tearDown(self):
        with self.app.app_context():
            db = get_unittest_db()
            db.iv_scans.drop()

    def test_fetch_all_iv_scans_empty(self):
        """Test fetching all IV scans when the collection is empty."""
        response = self.client.get("/iv_scans")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

    def test_insert_iv_scan(self):
        """Test insertion of a valid IV scan."""
        response = self.client.post("/iv_scans", json=self.sample_scan_4)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"message": "IV Scan inserted"})

        # Verify the scan was inserted by fetching it by IVScanId
        response = self.client.get(f"/iv_scans/{self.sample_scan_4['IVScanId']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["nameLabel"], self.sample_scan_4["nameLabel"])
        self.assertEqual(response.json["IVScanId"], self.sample_scan_4["IVScanId"])
        self.assertEqual(response.json["date"], self.sample_scan_4["date"])

    def test_get_by_iv_scan_id(self):
        """Test fetching an IV scan by its IVScanId."""
        self.client.post("/iv_scans", json=self.sample_scan_1)
        response = self.client.get(f"/iv_scans/{self.sample_scan_1['IVScanId']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["IVScanId"], self.sample_scan_1["IVScanId"])

    def test_get_nonexistent_iv_scan_by_id(self):
        """Test fetching a non-existent IV scan by IVScanId."""
        response = self.client.get("/iv_scans/NONEXISTENTSCANID")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json, {"message": "IV Scan(s) or Module not found"})
    
    def test_insert_duplicate_iv_scan(self):
        """Test that inserting an IV scan with an existing IVScanId fails."""
        # First insertion should succeed
        response = self.client.post("/iv_scans", json=self.sample_scan_1)
        self.assertEqual(response.status_code, 201)
        
        # Second insertion with the same IVScanId should fail
        response = self.client.post("/iv_scans", json=self.sample_scan_1)
        self.assertEqual(response.status_code, 400)
        self.assertIn("IV Scan already exists", response.json["message"])

    def test_insert_invalid_iv_scan(self):
        """Test that inserting an IV scan missing required fields fails."""
        invalid_scan = self.sample_scan_1.copy()
        del invalid_scan["nameLabel"]  # nameLabel is a required field
        
        response = self.client.post("/iv_scans", json=invalid_scan)
        self.assertEqual(response.status_code, 400)
        self.assertIn("'nameLabel' is a required property", response.json["message"])

    def test_update_iv_scan(self):
        """Test updating an existing IV scan."""
        # First insert an IV scan
        self.client.post("/iv_scans", json=self.sample_scan_1)
        
        update_data = {
            "comment": "Updated comment after re-test",
            "averageTemperature": 23.0
        }
        
        response = self.client.put(f"/iv_scans/{self.sample_scan_1['IVScanId']}", json=update_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "IV Scan updated"})
        
        # Verify the update
        response = self.client.get(f"/iv_scans/{self.sample_scan_1['IVScanId']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["comment"], "Updated comment after re-test")
        self.assertEqual(response.json["averageTemperature"], 23.0)
        # Original fields should still be there if not updated
        self.assertEqual(response.json["nameLabel"], self.sample_scan_1["nameLabel"])

    def test_delete_iv_scan(self):
        """Test deleting an existing IV scan."""
        # First insert an IV scan
        self.client.post("/iv_scans", json=self.sample_scan_1)
        
        # Now delete it
        response = self.client.delete(f"/iv_scans/{self.sample_scan_1['IVScanId']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "IV Scan deleted"})
        
        # Verify it's gone
        response = self.client.get(f"/iv_scans/{self.sample_scan_1['IVScanId']}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json, {"message": "IV Scan(s) or Module not found"})

    def test_delete_nonexistent_iv_scan(self):
        """Test deleting an IV scan that doesn't exist."""
        response = self.client.delete("/iv_scans/NONEXISTENTSCANID")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json, {"message": "IV Scan not found"}) # Delete is specific

    def test_get_by_mongo_id(self):
        """Test fetching an IV scan by its MongoDB ObjectId."""
        # First insert an IV scan
        self.client.post("/iv_scans", json=self.sample_scan_1)
        
        # Get by IVScanId to retrieve the _id
        response_get_by_name = self.client.get(f"/iv_scans/{self.sample_scan_1['IVScanId']}")
        self.assertEqual(response_get_by_name.status_code, 200)
        mongo_id = response_get_by_name.json["_id"]
        
        # Now get by _id (MongoDB ObjectId)
        response_get_by_mongo_id = self.client.get(f"/iv_scans/{mongo_id}")
        self.assertEqual(response_get_by_mongo_id.status_code, 200)
        self.assertEqual(response_get_by_mongo_id.json["IVScanId"], self.sample_scan_1["IVScanId"])
        self.assertEqual(response_get_by_mongo_id.json["_id"], mongo_id)

    def test_get_nonexistent_iv_scan_by_mongo_id(self):
        """Test fetching a non-existent IV scan by a valid but non-matching MongoDB ObjectId."""
        non_existent_mongo_id = str(ObjectId()) # Generate a valid but likely non-existent ObjectId
        response = self.client.get(f"/iv_scans/{non_existent_mongo_id}")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json, {"message": "IV Scan(s) or Module not found"})

    def test_get_iv_scan_with_invalid_mongo_id_format(self):
        """Test fetching an IV scan with an invalid format for MongoDB ObjectId."""
        invalid_mongo_id = "thisisnotanobjectid"
        response = self.client.get(f"/iv_scans/{invalid_mongo_id}")
        # This will first try to find by IVScanId, then fail ObjectId conversion, then try as nameLabel
        self.assertEqual(response.status_code, 404) 
        self.assertEqual(response.json, {"message": "IV Scan(s) or Module not found"})

    def test_get_by_module_name_single_scan(self):
        """Test fetching scans by module name (nameLabel) where one scan exists for the module."""
        self.client.post("/iv_scans", json=self.sample_scan_2) # PS_MODULE_02
        
        response = self.client.get(f"/iv_scans/{self.sample_scan_2['nameLabel']}")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]["nameLabel"], self.sample_scan_2["nameLabel"])
        self.assertEqual(response.json[0]["IVScanId"], self.sample_scan_2["IVScanId"])

    def test_get_by_module_name_multiple_scans(self):
        """Test fetching scans by module name (nameLabel) where multiple scans exist for the module."""
        self.client.post("/iv_scans", json=self.sample_scan_1) # PS_MODULE_01
        self.client.post("/iv_scans", json=self.sample_scan_3_module_1) # PS_MODULE_01
        self.client.post("/iv_scans", json=self.sample_scan_2) # PS_MODULE_02 (should not be returned)
        
        response = self.client.get(f"/iv_scans/{self.sample_scan_1['nameLabel']}") # Fetch PS_MODULE_01
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, list)
        self.assertEqual(len(response.json), 2)
        # Check if both scans for PS_MODULE_01 are present
        iv_scan_ids_returned = {scan["IVScanId"] for scan in response.json}
        self.assertIn(self.sample_scan_1["IVScanId"], iv_scan_ids_returned)
        self.assertIn(self.sample_scan_3_module_1["IVScanId"], iv_scan_ids_returned)
        for scan in response.json:
            self.assertEqual(scan["nameLabel"], self.sample_scan_1["nameLabel"])

    def test_get_by_module_name_no_scans_found(self):
        """Test fetching scans by a module name (nameLabel) that does not exist."""
        response = self.client.get("/iv_scans/UNKNOWN_MODULE")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json, {"message": "IV Scan(s) or Module not found"})

    def test_get_by_identifier_priority_ivscanid_over_namelabel(self):
        """Test IVScanId match takes priority over nameLabel match."""
        # scan1 has IVScanId="IVS001", nameLabel="PS_MODULE_01"
        # scan2 has IVScanId="IVS002", nameLabel="IVS001" (nameLabel is same as scan1's IVScanId)
        self.client.post("/iv_scans", json=self.sample_scan_1)
        scan_with_conflicting_nameLabel = self.sample_scan_2.copy()
        scan_with_conflicting_nameLabel["nameLabel"] = self.sample_scan_1["IVScanId"] # "IVS001"
        scan_with_conflicting_nameLabel["IVScanId"] = "IVS_CONFLICT_NL"
        self.client.post("/iv_scans", json=scan_with_conflicting_nameLabel)

        # Request "/iv_scans/IVS001"
        # Should match sample_scan_1 by IVScanId, not scan_with_conflicting_nameLabel by nameLabel
        response = self.client.get(f"/iv_scans/{self.sample_scan_1['IVScanId']}")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, dict) # Single object for IVScanId match
        self.assertEqual(response.json["IVScanId"], self.sample_scan_1["IVScanId"])
        self.assertEqual(response.json["nameLabel"], self.sample_scan_1["nameLabel"])


    def test_get_by_identifier_priority_objectid_over_namelabel(self):
        """Test MongoDB _id match takes priority over nameLabel match if identifier is a valid ObjectId string."""
        # Insert scan1, get its _id
        post_response = self.client.post("/iv_scans", json=self.sample_scan_1)
        self.assertEqual(post_response.status_code, 201)
        
        get_response = self.client.get(f"/iv_scans/{self.sample_scan_1['IVScanId']}")
        self.assertEqual(get_response.status_code, 200)
        mongo_id_scan1 = get_response.json["_id"]

        # Insert scan2 whose nameLabel is the string representation of scan1's _id
        scan_with_conflicting_nameLabel = self.sample_scan_2.copy()
        scan_with_conflicting_nameLabel["nameLabel"] = mongo_id_scan1 
        scan_with_conflicting_nameLabel["IVScanId"] = "IVS_CONFLICT_NL_OID"
        self.client.post("/iv_scans", json=scan_with_conflicting_nameLabel)

        # Request "/iv_scans/<mongo_id_scan1>"
        # Should match sample_scan_1 by _id, not scan_with_conflicting_nameLabel by nameLabel
        response = self.client.get(f"/iv_scans/{mongo_id_scan1}")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, dict) # Single object for _id match
        self.assertEqual(response.json["_id"], mongo_id_scan1)
        self.assertEqual(response.json["IVScanId"], self.sample_scan_1["IVScanId"])


if __name__ == "__main__":
    unittest.main()
