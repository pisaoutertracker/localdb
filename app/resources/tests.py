import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from utils import get_db, tests_schema


class TestsResource(Resource):
    """
    Resource for handling HTTP requests related to tests.

    Methods:
    - get: retrieves a test entry by Name or all test entries if no Name is provided
    - post: creates a new test entry
    - put: updates an existing test entry by Name
    - delete: deletes an existing test entry by Name
    """

    def get(self, testName=None):
        tests_collection = get_db()["tests"]

        if testName:
            entry = tests_collection.find_one({"testName": testName})
            if entry:
                entry["_id"] = str(entry["_id"])  # convert ObjectId to string
                return jsonify(entry)
            else:
                return {"message": "Entry not found"}, 404
        else:
            entries = list(tests_collection.find())
            for entry in entries:
                entry["_id"] = str(entry["_id"])
            return jsonify(entries)

    def post(self):
        tests_collection = get_db()["tests"]
        try:
            new_entry = request.get_json()
            validate(instance=new_entry, schema=tests_schema)
            tests_collection.insert_one(new_entry)
            return {"message": "Entry inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, testName):
        tests_collection = get_db()["tests"]
        if testName:
            updated_data = request.get_json()
            tests_collection.update_one({"testName": testName}, {"$set": updated_data})
            return {"message": "Entry updated"}, 200
        else:
            return {"message": "Entry not found"}, 404

    def delete(self, testName):
        tests_collection = get_db()["tests"]
        if testName:
            entry = tests_collection.find_one({"testName": testName})
            if entry:
                tests_collection.delete_one({"testName": testName})
                return {"message": "Entry deleted"}, 200
            else:
                return {"message": "Entry not found"}, 404
        else:
            return {"message": "Entry not found"}, 404
