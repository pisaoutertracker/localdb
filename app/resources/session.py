import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from bson import ObjectId
import bson
from utils import get_db, session_schema

# a flask resource for sessions
class SessionsResource(Resource):
        """
        Resource for handling HTTP requests related to sessions.

        Methods:
        - get: retrieves a session entry by ID or all session entries if no ID is provided
        - post: creates a new session entry
        - put: updates an existing session entry by ID
        - delete: deletes an existing session entry by ID
        """

        def get(self, sessionID=None):
            sessions_collection = get_db()["sessions"]
            if sessionID:
                # first try to get by sessionID, otherwise get by _id
                entry = sessions_collection.find_one({"sessionID": sessionID})
                if not entry:
                    try:
                        sessionID_id = ObjectId(sessionID)
                        entry = sessions_collection.find_one({"_id": sessionID_id})
                    except bson.errors.InvalidId:
                        entry = None

                if entry:
                    entry["_id"] = str(entry["_id"])  # convert ObjectId to string
                    return jsonify(entry)
                else:
                    return {"message": "Entry not found"}, 404
            else:
                entries = list(sessions_collection.find())
                for entry in entries:
                    entry["_id"] = str(entry["_id"])
                return jsonify(entries)

        def post(self):
            sessions_collection = get_db()["sessions"]
            try:
                new_entry = request.get_json()
                # add to the new_entry the sessionID defined 
                # as the length of the collection + 1
                new_entry["sessionID"] = f"session{sessions_collection.count_documents({}) + 1}"
                validate(instance=new_entry, schema=session_schema)
                # if an entry with the same ID already exists, return an error
                if sessions_collection.count_documents({"sessionID": new_entry["sessionID"]}) != 0:
                    return (
                        
                            {
                                "message": "Session ID already exists. Please try again.",
                                "sessionID": new_entry["sessionID"],
                            }
                        ,
                        400,
                    )
                sessions_collection.insert_one(new_entry)
                # return the sessionID as well
                return {"message": "Entry created", "sessionID": new_entry["sessionID"]}, 201
            except ValidationError as e:
                print(e)
                return {"message": str(e)}, 400

        def put(self, sessionID):
            sessions_collection = get_db()["sessions"]
            if sessionID:
                updated_data = request.get_json()
                sessions_collection.update_one({"sessionID": sessionID}, {"$set": updated_data})
                return {"message": "Entry updated"}, 200
            else:
                return {"message": "Entry not found"}, 404

        def delete(self, sessionID):
            sessions_collection = get_db()["sessions"]
            if sessionID:
                sessions_collection.delete_one({"sessionID": sessionID})
                return {"message": "Entry deleted"}, 200
            else:
                return {"message": "Entry not found"}, 404
