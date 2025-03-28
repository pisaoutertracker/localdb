import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from bson import ObjectId
import bson
from utils import get_db, burnin_cycles_schema
# Flask resource for burnin cycles
class BurninCyclesResource(Resource):
    """
    Resource for handling HTTP requests related to burnin cycles.

    Methods:
    - get: retrieves a burnin cycle entry by ID or all burnin cycle entries if no ID is provided
    - post: creates a new burnin cycle entry
    - put: updates an existing burnin cycle entry by ID
    - delete: deletes an existing burnin cycle entry by ID
    """

    def get(self, burninCycleName=None):
        burnin_cycles_collection = get_db()["burnin_cycles"]
        if burninCycleName:
            # first try to get by burninCycleName, otherwise get by _id
            entry = burnin_cycles_collection.find_one({"BurninCycleName": burninCycleName})
            if not entry:
                try: 
                    burninCycleName_id = ObjectId(burninCycleName)
                    entry = burnin_cycles_collection.find_one({"_id": burninCycleName_id})
                except bson.errors.InvalidId: 
                    entry = None
            if entry:
                entry["_id"] = str(entry["_id"])  # convert ObjectId to string
                return jsonify(entry)
            else:
                return {"message": "Burnin cycle not found"}, 404
        else:
            entries = list(burnin_cycles_collection.find())
            for entry in entries:
                entry["_id"] = str(entry["_id"])
            return jsonify(entries)

    def post(self):
        burnin_cycles_collection = get_db()["burnin_cycles"]
        try:
            new_entry = request.get_json()
            validate(instance=new_entry, schema=burnin_cycles_schema)
            # if an entry with the same Name already exists, return an error
            if burnin_cycles_collection.count_documents({"BurninCycleName": new_entry["BurninCycleName"]}) != 0:
                return (
                    {
                        "message": "Burnin cycle already exists. Please try again.",
                        "BurninCycleName": new_entry["BurninCycleName"],
                    },
                    400,
                )
            burnin_cycles_collection.insert_one(new_entry)
            return {"message": "Burnin cycle inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, burninCycleName):
        burnin_cycles_collection = get_db()["burnin_cycles"]
        if burninCycleName:
            updated_data = request.get_json()
            burnin_cycles_collection.update_one({"BurninCycleName": burninCycleName}, {"$set": updated_data})
            return {"message": "Burnin cycle updated"}, 200
        else:
            return {"message": "Burnin cycle not found"}, 404

    def delete(self, burninCycleName):
        burnin_cycles_collection = get_db()["burnin_cycles"]
        if burninCycleName:
            entry = burnin_cycles_collection.find_one({"BurninCycleName": burninCycleName})
            if entry:
                burnin_cycles_collection.delete_one({"BurninCycleName": burninCycleName})
                return {"message": "Burnin cycle deleted"}, 200
            else:
                return {"message": "Burnin cycle not found"}, 404
        else:
            return {"message": "Burnin cycle not found"}, 404
