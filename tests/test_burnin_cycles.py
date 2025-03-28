import unittest
from flask_testing import TestCase
import sys
import os
import json
from datetime import datetime

sys.path.append("..")
from app.app import create_app, get_unittest_db
from bson import ObjectId

class TestBurninCyclesAPI(TestCase):
    def create_app(self):
        return create_app("unittest")

    def setUp(self):
        self.app = self.create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db = get_unittest_db()
            db.burnin_cycles.drop()

    def tearDown(self):
        with self.app.app_context():
            db = get_unittest_db()
            db.burnin_cycles.drop()

    def test_fetch_all_burnin_cycles_empty(self):
        """Test that an empty list is returned when no burnin cycles exist"""
        response = self.client.get("/burnin_cycles")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

    def test_insert_burnin_cycle(self):
        """Test insertion of a valid burnin cycle"""
        new_cycle = {
            "BurninCycleName": "BC001",
            "BurninCycleDate": "2023-12-20",
            "BurninCycleOperator": "John Doe",
            "BurninCycleStatus": "completed",
            "BurninCycleResults": {"temperature_stability": "passed", "failure_rate": "0%"},
            "BurninCycleModules": ["M123", "M124", "M125"],
            "BurninCycleTemperature": "25C",
            "BurninCycleHumidity": "40%",
            "BurninCycleMaxTemperature": "30C",
            "BurninCycleMinTemperature": "20C"
        }
        
        response = self.client.post("/burnin_cycles", json=new_cycle)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, {"message": "Burnin cycle inserted"})

        # Verify the cycle was inserted
        response = self.client.get("/burnin_cycles/BC001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["BurninCycleName"], "BC001")
        self.assertEqual(response.json["BurninCycleOperator"], "John Doe")
        self.assertEqual(response.json["BurninCycleModules"], ["M123", "M124", "M125"])

    def test_insert_duplicate_burnin_cycle(self):
        """Test that inserting a burnin cycle with an existing name fails"""
        new_cycle = {
            "BurninCycleName": "BC002",
            "BurninCycleDate": "2023-12-21",
            "BurninCycleModules": ["M126", "M127"]
        }
        
        # First insertion should succeed
        response = self.client.post("/burnin_cycles", json=new_cycle)
        self.assertEqual(response.status_code, 201)
        
        # Second insertion with the same name should fail
        response = self.client.post("/burnin_cycles", json=new_cycle)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already exists", response.json["message"])

    def test_insert_invalid_burnin_cycle(self):
        """Test that inserting a burnin cycle missing required fields fails"""
        invalid_cycle = {
            "BurninCycleName": "BC003",
            # Missing required fields BurninCycleDate and BurninCycleModules
            "BurninCycleOperator": "Jane Doe"
        }
        
        response = self.client.post("/burnin_cycles", json=invalid_cycle)
        self.assertEqual(response.status_code, 400)

    def test_update_burnin_cycle(self):
        """Test updating a burnin cycle"""
        # First insert a burnin cycle
        new_cycle = {
            "BurninCycleName": "BC004",
            "BurninCycleDate": "2023-12-22",
            "BurninCycleModules": ["M128", "M129"],
            "BurninCycleStatus": "in_progress"
        }
        
        response = self.client.post("/burnin_cycles", json=new_cycle)
        self.assertEqual(response.status_code, 201)
        
        # Now update it
        update_data = {
            "BurninCycleStatus": "completed",
            "BurninCycleResults": {"status": "all_passed"}
        }
        
        response = self.client.put("/burnin_cycles/BC004", json=update_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Burnin cycle updated"})
        
        # Verify the update
        response = self.client.get("/burnin_cycles/BC004")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["BurninCycleStatus"], "completed")
        self.assertEqual(response.json["BurninCycleResults"], {"status": "all_passed"})
        # Original fields should still be there
        self.assertEqual(response.json["BurninCycleModules"], ["M128", "M129"])

    def test_delete_burnin_cycle(self):
        """Test deleting a burnin cycle"""
        # First insert a burnin cycle
        new_cycle = {
            "BurninCycleName": "BC005",
            "BurninCycleDate": "2023-12-23",
            "BurninCycleModules": ["M130"]
        }
        
        response = self.client.post("/burnin_cycles", json=new_cycle)
        self.assertEqual(response.status_code, 201)
        
        # Now delete it
        response = self.client.delete("/burnin_cycles/BC005")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "Burnin cycle deleted"})
        
        # Verify it's gone
        response = self.client.get("/burnin_cycles/BC005")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json, {"message": "Burnin cycle not found"})

    def test_delete_nonexistent_burnin_cycle(self):
        """Test deleting a burnin cycle that doesn't exist"""
        response = self.client.delete("/burnin_cycles/nonexistent")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json, {"message": "Burnin cycle not found"})

    def test_get_by_id(self):
        """Test getting a burnin cycle by MongoDB ObjectId"""
        # First insert a burnin cycle
        new_cycle = {
            "BurninCycleName": "BC006",
            "BurninCycleDate": "2023-12-24",
            "BurninCycleModules": ["M131", "M132"]
        }
        
        response = self.client.post("/burnin_cycles", json=new_cycle)
        self.assertEqual(response.status_code, 201)
        
        # Get by name to retrieve the _id
        response = self.client.get("/burnin_cycles/BC006")
        self.assertEqual(response.status_code, 200)
        cycle_id = response.json["_id"]
        
        # Now get by _id
        response = self.client.get(f"/burnin_cycles/{cycle_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["BurninCycleName"], "BC006")

if __name__ == "__main__":
    unittest.main()
