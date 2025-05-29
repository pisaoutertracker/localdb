import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from bson import ObjectId
import bson
from utils import get_db, iv_scans_schema
# Flask resource for burnin cycles
class IVScansResource(Resource):
    """
    Resource for handling HTTP requests related to burnin cycles.

    Methods:
    - get: retrieves a burnin cycle entry by ID or all burnin cycle entries if no ID is provided
    - post: creates a new burnin cycle entry
    - put: updates an existing burnin cycle entry by ID
    - delete: deletes an existing burnin cycle entry by ID
    """

    def get(self, IVScanId=None): # IVScanId here is the path parameter
        iv_scans_collection = get_db()["iv_scans"]
        if IVScanId:
            # 1. Try to find by IVScanId (specific scan ID)
            entry_by_ivscanid = iv_scans_collection.find_one({"IVScanId": IVScanId})
            if entry_by_ivscanid:
                entry_by_ivscanid["_id"] = str(entry_by_ivscanid["_id"])
                return jsonify(entry_by_ivscanid) # Returns a single object

            # 2. Try to find by MongoDB _id
            try:
                obj_id = ObjectId(IVScanId)
                entry_by_oid = iv_scans_collection.find_one({"_id": obj_id})
                if entry_by_oid:
                    entry_by_oid["_id"] = str(entry_by_oid["_id"])
                    return jsonify(entry_by_oid) # Returns a single object
            except bson.errors.InvalidId:
                # IVScanId is not a valid ObjectId string, will proceed to check as nameLabel
                pass
            
            # 3. Try to find by nameLabel (module name)
            # This is reached if not found by IVScanId, and (IVScanId is not an ObjectId or not found by ObjectId)
            entries_by_module = list(iv_scans_collection.find({"nameLabel": IVScanId}))
            if entries_by_module:
                for e_mod in entries_by_module:
                    e_mod["_id"] = str(e_mod["_id"])
                return jsonify(entries_by_module) # Returns a list of objects

            # 4. If not found by any criteria
            return {"message": "IV Scan(s) or Module not found"}, 404
        else:
            # Fetch all entries if no specific IVScanId/identifier is provided
            all_entries = list(iv_scans_collection.find())
            for entry in all_entries:
                entry["_id"] = str(entry["_id"])
            return jsonify(all_entries)

    def post(self):
        iv_scans_collection = get_db()["iv_scans"]
        try:
            new_entry = request.get_json()
            validate(instance=new_entry, schema=iv_scans_schema)
            # if an entry with the same Name already exists, return an error
            if iv_scans_collection.count_documents({"IVScanId": new_entry["IVScanId"]}) != 0:
                return (
                    {
                        "message": "IV Scan already exists. Please try again.",
                        "IVScanId": new_entry["IVScanId"],
                    },
                    400,
                )
            iv_scans_collection.insert_one(new_entry)
            return {"message": "IV Scan inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, IVScanId):
        iv_scans_collection = get_db()["iv_scans"]
        if IVScanId:
            updated_data = request.get_json()
            iv_scans_collection.update_one({"IVScanId": IVScanId}, {"$set": updated_data})
            return {"message": "IV Scan updated"}, 200
        else:
            return {"message": "IV Scan not found"}, 404

    def delete(self, IVScanId):
        iv_scans_collection = get_db()["iv_scans"]
        if IVScanId:
            entry = iv_scans_collection.find_one({"IVScanId": IVScanId})
            if entry:
                iv_scans_collection.delete_one({"IVScanId": IVScanId})
                return {"message": "IV Scan deleted"}, 200
            else:
                return {"message": "IV Scan not found"}, 404
        else:
            return {"message": "IV Scan not found"}, 404
