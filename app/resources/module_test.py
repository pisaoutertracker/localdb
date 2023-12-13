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

        def get(self, moduleTestKey=None):
            module_tests_collection = get_db()["module_tests"]
            if moduleTestKey:
                # first try to get by moduleTestKey, otherwise get by _id
                entry = module_tests_collection.find_one({"moduleTestKey": moduleTestKey})
                if not entry:
                    entry = module_tests_collection.find_one({"_id": moduleTestKey})

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

        def put(self, moduleTestKey):
            module_tests_collection = get_db()["module_tests"]
            if moduleTestKey:
                updated_data = request.get_json()
                module_tests_collection.update_one({"moduleTestKey": moduleTestKey}, {"$set": updated_data})
                return {"message": "Entry updated"}, 200
            else:
                return {"message": "Entry not found"}, 404

        def delete(self, moduleTestKey):
            module_tests_collection = get_db()["module_tests"]
            if moduleTestKey:
                entry = module_tests_collection.find_one({"moduleTestKey": moduleTestKey})
                if entry:
                    module_tests_collection.delete_one({"moduleTestKey": moduleTestKey})
                    return {"message": "Entry deleted"}, 200
                else:
                    return {"message": "Entry not found"}, 404
            else:
                return {"message": "Entry not found"}, 404
