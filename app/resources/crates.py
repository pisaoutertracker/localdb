import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from utils import get_db

# NOTE: add schema for crates


# a route for crates for now equal to cables
class CratesResource(Resource):
    def get(self, name=None):
        crates_collection = get_db()["crates"]
        if name:
            entry = crates_collection.find_one({"name": name})
            if entry:
                entry["_id"] = str(entry["_id"])  # convert ObjectId to string
                return jsonify(entry)
            else:
                return {"message": "Entry not found"}, 404
        else:
            entries = list(crates_collection.find())
            for entry in entries:
                entry["_id"] = str(entry["_id"])
            return jsonify(entries)

    def post(self):
        crates_collection = get_db()["crates"]
        try:
            new_entry = request.get_json()
            # NOTE: add schema for crates
            crates_collection.insert_one(new_entry)
            return {"message": "Entry inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, name):
        crates_collection = get_db()["crates"]
        if name:
            updated_data = request.get_json()
            crates_collection.update_one({"name": name}, {"$set": updated_data})
            return {"message": "Entry updated"}, 200
        else:
            return {"message": "Entry not found"}, 404

    def delete(self, name):
        crates_collection = get_db()["crates"]
        if name:
            entry = crates_collection.find_one({"name": name})
            if entry:
                crates_collection.delete_one({"name": name})
                return {"message": "Entry deleted"}, 200
            else:
                return {"message": "Entry not found"}, 404
        else:
            return {"message": "Entry not found"}, 404
