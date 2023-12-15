import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from bson import ObjectId
import bson
from utils import get_db, module_test_analysis_schema

# a flask resource for module test analysis
class ModuleTestAnalysisResource(Resource):
        """
        Resource for handling HTTP requests related to module test analysis.

        Methods:
        - get: retrieves a module test analysis entry by ID or all module test analysis entries if no ID is provided
        - post: creates a new module test analysis entry
        - put: updates an existing module test analysis entry by ID
        - delete: deletes an existing module test analysis entry by ID
        """

        def get(self, moduleTestAnalysisKey=None):
            module_test_analysis_collection = get_db()["module_test_analysis"]
            if moduleTestAnalysisKey:
                # first try to get by moduleTestAnalysisKey, otherwise get by _id
                entry = module_test_analysis_collection.find_one({"moduleTestAnalysisKey": moduleTestAnalysisKey})
                if not entry:
                    try:
                        moduleTestAnalysisKey_id = ObjectId(moduleTestAnalysisKey)
                        entry = module_test_analysis_collection.find_one({"_id": moduleTestAnalysisKey_id})
                    except bson.errors.InvalidId:
                        entry = None
                if entry:
                    entry["_id"] = str(entry["_id"])  # convert ObjectId to string
                    return jsonify(entry)
                else:
                    return {"message": "Entry not found"}, 404
            else:
                entries = list(module_test_analysis_collection.find())
                for entry in entries:
                    entry["_id"] = str(entry["_id"])
                return jsonify(entries)

        def post(self):
            module_test_analysis_collection = get_db()["module_test_analysis"]
            try:
                new_entry = request.get_json()
                # add to the new_entry the moduleTestAnalysisId defined 
                # as the length of the collection + 1
                validate(instance=new_entry, schema=module_test_analysis_schema)
                # if an entry with the same Key already exists, return an error
                if module_test_analysis_collection.count_documents({"moduleTestAnalysisKey": new_entry["moduleTestAnalysisKey"]}) != 0:
                    print("moduleTestAnalysisKey already exists")
                    return (
                            {
                                "message": "Module test analysis key already exists. Please try again.",
                                "moduleTestAnalysisKey": new_entry["moduleTestAnalysisKey"],
                            }
                        ,
                        400,
                    )

                module_test_analysis_collection.insert_one(new_entry)
                # return the moduleTestAnalysisKey as well
                return {"message": "Entry created", "moduleTestAnalysisKey": new_entry["moduleTestAnalysisKey"]}, 201
            except ValidationError as e:
                print(e)
                return {"message": str(e)}, 400

        def put(self, moduleTestAnalysisKey):
            module_test_analysis_collection = get_db()["module_test_analysis"]
            if moduleTestAnalysisKey:
                updated_data = request.get_json()
                module_test_analysis_collection.update_one({"moduleTestAnalysisKey": moduleTestAnalysisKey}, {"$set": updated_data})
                return {"message": "Entry updated"}, 200
            
        def delete(self, moduleTestAnalysisKey):
            module_test_analysis_collection = get_db()["module_test_analysis"]
            if moduleTestAnalysisKey:
                entry = module_test_analysis_collection.find_one({"moduleTestAnalysisKey": moduleTestAnalysisKey})
                if entry:
                    module_test_analysis_collection.delete_one({"moduleTestAnalysisKey": moduleTestAnalysisKey})
                    return {"message": "Entry deleted"}, 200
                else:
                    return {"message": "Entry not found"}, 404