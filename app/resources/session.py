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
        - get: retrieves a session entry by Name or all session entries if no Name is provided
        - post: creates a new session entry
        - put: updates an existing session entry by Name
        - delete: deletes an existing session entry by Name
        """

        def get(self, sessionName=None):
            sessions_collection = get_db()["sessions"]
            if sessionName:
                # first try to get by sessionName, otherwise get by _id
                entry = sessions_collection.find_one({"sessionName": sessionName})
                if not entry:
                    try:
                        sessionName_id = ObjectId(sessionName)
                        entry = sessions_collection.find_one({"_id": sessionName_id})
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
            metadata_collection = get_db()["metadata"]
            # check for the metadata object in metadata collection, and create it if it does not exist
            if metadata_collection.count_documents({"name": "metadata"}) == 0:
                metadata_collection.insert_one({"name": "metadata", "lastSessionNumber": 0})
            try:
                new_entry = request.get_json()

                # check that session collection is not empty
                # if it is, set the sessionName to session1
                if sessions_collection.count_documents({}) == 0:
                    new_entry["sessionName"] = "session1"
                    metadata_collection.update_one({"name": "metadata"}, {"$set": {"lastSessionNumber": 1}})
                # if it is not, set the sessionName to last sessionName number +1
                else:
                    last_session = metadata_collection.find_one({"name": "metadata"})["lastSessionNumber"]
                    new_entry["sessionName"] = "session" + str(last_session + 1)
                    metadata_collection.update_one({"name": "metadata"}, {"$set": {"lastSessionNumber": last_session + 1}})

                validate(instance=new_entry, schema=session_schema)
                # if an entry with the same Name already exists, return an error
                if sessions_collection.count_documents({"sessionName": new_entry["sessionName"]}) != 0:
                    return (
                        
                            {
                                "message": "Session Name already exists. Please try again.",
                                "sessionName": new_entry["sessionName"],
                            }
                        ,
                        400,
                    )
                sessions_collection.insert_one(new_entry)
                # return the sessionName as well
                return {"message": "Entry created", "sessionName": new_entry["sessionName"]}, 201
            except ValidationError as e:
                print(e)
                return {"message": str(e)}, 400

        def put(self, sessionName):
            sessions_collection = get_db()["sessions"]
            if sessionName:
                updated_data = request.get_json()
                sessions_collection.update_one({"sessionName": sessionName}, {"$set": updated_data})
                return {"message": "Entry updated"}, 200
            else:
                return {"message": "Entry not found"}, 404

        def delete(self, sessionName):
            sessions_collection = get_db()["sessions"]
            if sessionName:
                sessions_collection.delete_one({"sessionName": sessionName})
                return {"message": "Entry deleted"}, 200
            else:
                return {"message": "Entry not found"}, 404
