import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from utils import get_db, cables_schema


class CablesResource(Resource):
    """
    Represents the RESTful API for interacting with the cables collection in the database.

    Methods:
    - get(name): retrieves a single cable entry by ID or all cable entries if no ID is provided.
    - post(): creates a new cable entry in the database.
    - put(name): updates an existing cable entry in the database by ID.
    - delete(name): deletes an existing cable entry from the database by ID.
    """

    def get(self, name=None):
        cables_collection = get_db()["cables"]
        if name:
            entry = cables_collection.find_one({"name": name})
            if entry:
                entry["_id"] = str(entry["_id"])  # convert ObjectId to string
                return jsonify(entry)
            else:
                return {"message": "Entry not found"}, 404
        else:
            entries = list(cables_collection.find())
            for entry in entries:
                entry["_id"] = str(entry["_id"])
            return jsonify(entries)

    def post(self):
        cables_collection = get_db()["cables"]
        try:
            new_entry = request.get_json()
            validate(instance=new_entry, schema=cables_schema)
            cables_collection.insert_one(new_entry)
            return {"message": "Entry inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, name):
        cables_collection = get_db()["cables"]
        if name:
            updated_data = request.get_json()
            cables_collection.update_one({"name": name}, {"$set": updated_data})
            return {"message": "Entry updated"}, 200
        else:
            return {"message": "Entry not found"}, 404

    def delete(self, name):
        cables_collection = get_db()["cables"]
        if name:
            entry = cables_collection.find_one({"name": name})
            if entry:
                cables_collection.delete_one({"name": name})
                return {"message": "Entry deleted"}, 200
            else:
                return {"message": "Entry not found"}, 404
        else:
            return {"message": "Entry not found"}, 404
