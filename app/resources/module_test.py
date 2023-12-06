import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from utils import get_db, module_test_schema

# a flask resource for module_tests
class ModuleTestsResource(Resource):
        """
        Resource for handling HTTP requests related to module_tests.

        Methods:
        - get: retrieves a module_test entry by ID or all module_test entries if no ID is provided
        - post: creates a new module_test entry
        - put: updates an existing module_test entry by ID
        - delete: deletes an existing module_test entry by ID
        """

        def get(self, module_testID=None):
            module_tests_collection = get_db()["module_tests"]
            if module_testID:
                entry = module_tests_collection.find_one({"module_testID": module_testID})
                if entry:
                    entry["_id"] = str(entry["_id"])  # convert ObjectId to string
                    return jsonify(entry)
                else:
                    return {"message": "Entry not found"}, 404
            else:
                entries = list(module_tests_collection.find())
                for entry in entries:
                    entry["_id"] = str(entry["_id"])
                return jsonify(entries)

        def post(self):
            module_tests_collection = get_db()["module_tests"]
            try:
                new_entry = request.get_json()
                validate(instance=new_entry, schema=module_test_schema)
                module_tests_collection.insert_one(new_entry)
                return {"message": "Entry inserted"}, 201
            except ValidationError as e:
                return {"message": str(e)}, 400

        def put(self, module_testID):
            module_tests_collection = get_db()["module_tests"]
            if module_testID:
                updated_data = request.get_json()
                module_tests_collection.update_one({"module_testID": module_testID}, {"$set": updated_data})
                return {"message": "Entry updated"}, 200
            else:
                return {"message": "Entry not found"}, 404

        def delete(self, module_testID):
            module_tests_collection = get_db()["module_tests"]
            if module_testID:
                entry = module_tests_collection.find_one({"module_testID": module_testID})
                if entry:
                    module_tests_collection.delete_one({"module_testID": module_testID})
                    return {"message": "Entry deleted"}, 200
                else:
                    return {"message": "Entry not found"}, 404
            else:
                return {"message": "Entry not found"}, 404
