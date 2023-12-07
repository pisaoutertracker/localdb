import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from utils import get_db, test_run_schema


# a flask resource for test_runs
class TestRunResource(Resource):
    """
    Resource for handling HTTP requests related to test_runs.

    Methods:
    - get: retrieves a test_run entry by ID or all test_run entries if no ID is provided
    - post: creates a new test_run entry
    - put: updates an existing test_run entry by ID
    - delete: deletes an existing test_run entry by ID
    """

    def get(self, test_runID=None):
        test_runs_collection = get_db()["test_runs"]
        if test_runID:
            entry = test_runs_collection.find_one({"test_runID": test_runID})
            if entry:
                entry["_id"] = str(entry["_id"])  # convert ObjectId to string
                return jsonify(entry)
            else:
                return {"message": "Entry not found"}, 404
        else:
            entries = list(test_runs_collection.find())
            for entry in entries:
                entry["_id"] = str(entry["_id"])
            return jsonify(entries)

    def post(self):
        test_runs_collection = get_db()["test_runs"]
        try:
            new_entry = request.get_json()
            validate(instance=new_entry, schema=test_run_schema)
            test_runs_collection.insert_one(new_entry)
            return {"message": "Entry inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, test_runID):
        test_runs_collection = get_db()["test_runs"]
        if test_runID:
            updated_data = request.get_json()
            test_runs_collection.update_one(
                {"test_runID": test_runID}, {"$set": updated_data}
            )
            return {"message": "Entry updated"}, 200
        else:
            return {"message": "Entry not found"}, 404

    def delete(self, test_runID):
        test_runs_collection = get_db()["test_runs"]
        if test_runID:
            entry = test_runs_collection.find_one({"test_runID": test_runID})
            if entry:
                test_runs_collection.delete_one({"test_runID": test_runID})
                return {"message": "Entry deleted"}, 200
            else:
                return {"message": "Entry not found"}, 404
        else:
            return {"message": "Entry not found"}, 404
