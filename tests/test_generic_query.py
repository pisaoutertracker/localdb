import unittest
from flask_testing import TestCase
import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.app import create_app, get_unittest_db

class TestGenericQueryAPI(TestCase):
    def create_app(self):
        return create_app("unittest")

    def setUp(self):
        self.app = self.create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            db = get_unittest_db()
            db.modules.drop()
            # Insert some sample modules for testing
            self.module1_data = {
                "moduleName": "MODULE_GENERIC_001",
                "position": "cleanroom",
                "status": "readyformount",
                "type": "generic_test_type_A"
            }
            self.module2_data = {
                "moduleName": "MODULE_GENERIC_002",
                "position": "testbench",
                "status": "testing",
                "type": "generic_test_type_B"
            }
            self.module3_data = {
                "moduleName": "MODULE_GENERIC_003",
                "position": "cleanroom",
                "status": "testing",
                "type": "generic_test_type_A"
            }
            self.module4_data = {
                "moduleName": "another_module",
                "position": "testbench",
                "status": "readyformount",
                "type": "generic_test_type_C"
            }
            db.modules.insert_many([self.module1_data, self.module2_data, self.module3_data, self.module4_data])

    def tearDown(self):
        with self.app.app_context():
            db = get_unittest_db()
            db.modules.drop()

    def test_generic_query_empty_filter(self):
        """Test querying with an empty filter, should return all modules."""
        response = self.client.post("/generic_module_query", json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 4)

    def test_generic_query_specific_field_match(self):
        """Test querying by a specific field that matches some modules."""
        query = {"status": "testing"}
        response = self.client.post("/generic_module_query", json=query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 2)
        for module in response.json:
            self.assertEqual(module["status"], "testing")
            self.assertIn(module["moduleName"], ["MODULE_GENERIC_002", "MODULE_GENERIC_003"])

    def test_generic_query_multiple_fields_match(self):
        """Test querying by multiple fields."""
        query = {"status": "testing", "position": "cleanroom"}
        response = self.client.post("/generic_module_query", json=query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]["moduleName"], "MODULE_GENERIC_003")
        self.assertEqual(response.json[0]["status"], "testing")
        self.assertEqual(response.json[0]["position"], "cleanroom")

    def test_generic_query_no_results(self):
        """Test querying with a filter that matches no modules."""
        query = {"status": "non_existent_status"}
        response = self.client.post("/generic_module_query", json=query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 0)
        
    def test_generic_query_invalid_filter(self):
        # this still gives a warning from pymongo, but it passes...
        # suppress the warning for this test?
        
        """Test sending a POST request with an invalid filter."""
        query = {"invalid_field": "value"}
        response = self.client.post("/generic_module_query", json=query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 0)

    def test_generic_query_no_data_provided(self):
        """Test sending a POST request with no JSON data."""
        response = self.client.post("/generic_module_query")
        self.assertEqual(response.status_code, 415)  # Flask typically returns 415 for unsupported media type
        self.assertEqual(response.json, None)

    def test_generic_query_invalid_json_payload(self):
        """Test sending a POST request with an invalid JSON payload."""
        response = self.client.post("/generic_module_query", data="not a json", content_type="application/json")
        self.assertEqual(response.status_code, 400) # Flask typically returns 400 for bad JSON
        # The exact error message might vary depending on Flask/Werkzeug version
        self.assertTrue(response.json is None)
        
    def test_regexp_patterns(self):
        # this still gives a warning from pymongo, but it passes...
        # suppress the warning for this test?
        """Test the regex patterns for module IDs, do a query with a regex on all modules names starting with 'MODULE_GENERIC_'."""
        query = {"moduleName": {"$regex": "^MODULE_GENERIC_"}}
        response = self.client.post("/generic_module_query", json=query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 3)
        for module in response.json:
            self.assertTrue(module["moduleName"].startswith("MODULE_GENERIC_"))
        
        


if __name__ == "__main__":
    unittest.main()
