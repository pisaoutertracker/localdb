import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from bson import ObjectId
from utils import get_db, testpayload_schema


class TestPayloadsResource(Resource):
    """
    Resource for handling HTTP requests related to testpayloads.

    Methods:
    - get: retrieves a testpayload entry by Name or all testpayload entries if no Name is provided
    - post: creates a new testpayload entry
    - put: updates an existing testpayload entry by Name
    - delete: deletes an existing testpayload entry by Name
    """

    def get(self, testpName=None):
        tests_collection = get_db()["testpayloads"]
        if testpName:
            entry = tests_collection.find_one({"_id": ObjectId(testpName)})
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
        tests_collection = get_db()["testpayloads"]
        try:
            new_entry = request.get_json()
            validate(instance=new_entry, schema=testpayload_schema)
            result = tests_collection.insert_one(new_entry)
            _id = str(result.inserted_id)
            return {"_id": str(_id)}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, testpName):
        tests_collection = get_db()["testpayloads"]
        if testpName:
            updated_data = request.get_json()
            tests_collection.update_one(
                {"_id": ObjectId(testpName)}, {"$set": updated_data}
            )
            return {"message": "Entry updated"}, 200
        else:
            return {"message": "Entry not found"}, 404

    def delete(self, testpName):
        tests_collection = get_db()["testpayloads"]
        if testpName:
            entry = tests_collection.find_one({"_id": ObjectId(testpName)})
            if entry:
                tests_collection.delete_one({"_id": ObjectId(testpName)})
                return {"message": "Entry deleted"}, 200
            else:
                return {"message": "Entry not found"}, 404
        else:
            return {"message": "Entry not found"}, 404
