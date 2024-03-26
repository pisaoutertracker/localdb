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
        templates_collection = get_db()['cable_templates']

        try:
            new_entry = request.get_json()
            validate(instance=new_entry, schema=cables_schema)
            # if any cable with the same name already exists, return an error
            if cables_collection.find_one({"name": new_entry["name"]}):
                return {"message": "Entry already exists"}, 400
            
            # Retrieve the cable templates from the database
            template = new_entry['type']
            template = templates_collection.find_one({'type': template})
            if not template:
                return {"message": "Template not found"}, 400
            
            # get lines number from the template
            lines = template['lines']
            # if the template has a detSide, initialize it as 'line_number': []
            if 'detSide' in template:
                if new_entry["detSide"] == {}:
                    new_entry['detSide'] = {str(i): [] for i in range(1, lines + 1)}
                else:
                    return {"message": "side should be initialized as empty"}, 400
            
            # if the template has a crateSide, initialize it as 'port': []
            if 'crateSide' in template:
                if new_entry["crateSide"] == {}:
                    new_entry['crateSide'] = {str(i): [] for i in range(1, lines + 1)}
                else:
                    return {"message": "side should be initialized as empty"}, 400
            
            cables_collection.insert_one(new_entry)
            return {"message": "Entry inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, name):
        cables_collection = get_db()["cables"]
        if name:
            updated_data = request.get_json()
            # update the cable entry with the new data
            # but leave the 
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
