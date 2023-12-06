import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from bson import ObjectId
from utils import get_db, logbook_schema, findModuleIds


class LogbookResource(Resource):
        """
        A class representing a RESTful resource for logbook entries.

        Attributes:
        -----------
        None

        Methods:
        --------
        get(_id=None):
            Retrieves a logbook entry with the specified _id, or all logbook entries if no _id is provided.

        post():
            Inserts a new logbook entry into the database.

        put(_id):
            Updates an existing logbook entry with the specified _id.

        delete(_id):
            Deletes an existing logbook entry with the specified _is.
        """
        def get(self, _id=None):
            """
            Retrieves a logbook entry with the specified _id, or all logbook entries if no _id is provided.

            Parameters:
            -----------
            timestamp : str, optional
                The _id of the logbook entry to retrieve.

            Returns:
            --------
            dict or list
                A dictionary representing the logbook entry with the specified _id, or a list of all logbook entries if no timestamp is provided.
            """
            logbook_collection = get_db()["logbook"]
            if _id:
                log = logbook_collection.find_one({"_id": ObjectId(_id)})
                if log:
                    log["_id"] = str(log["_id"])  # convert ObjectId to string
                    return jsonify(log)
                else:
                    return {"message": "Log not found"}, 404
            else:
                logs = list(logbook_collection.find())
                for log in logs:
                    log["_id"] = str(log["_id"])
                return jsonify(logs)

        def post(self):
            """
            Inserts a new logbook entry into the database.

            Parameters:
            -----------
            None

            Returns:
            --------
            dict
                A dictionary containing the _id of the new entry
            """
            logbook_collection = get_db()["logbook"]
            try:
                new_log = request.get_json()
                
                validate(instance=new_log, schema=logbook_schema)
    #
    # check involved modules
    #
                im = []
                key = "involved_modules"
                det = "details"
                d = ""
                modules_in_the_details = []
                if key in  new_log:
                    im = new_log["involved_modules"]
                if det in new_log:
                    d = new_log["details"]
                    modules_in_the_details = findModuleIds(d) 
                new_log[key] = im + list(set(modules_in_the_details) - set(im))
                logbook_collection.insert_one(new_log)
                return {"_id": str(new_log["_id"])}, 201
            except ValidationError as e:
                return {"message": str(e)}, 400

        def put(self, _id):
            """
            Updates an existing logbook entry with the specified _id (as a string).

            Parameters:
            -----------
            timestamp : str
                The _id of the logbook entry to update.

            Returns:
            --------
            dict
                A dictionary containing a message indicating that the logbook entry was successfully updated.
            """
            logbook_collection = get_db()["logbook"]
            updated_data = request.get_json()
            logbook_collection.update_one({"_id": ObjectId(_id)}, {"$set": updated_data})
            return {"message": "Log updated"}, 200

        def delete(self, _id):
            """
            Deletes an existing logbook entry with the specified timestamp.

            Parameters:
            -----------
            timestamp : str
                The _id of the logbook entry to delete.

            Returns:
            --------
            dict
                A dictionary containing a message indicating that the logbook entry was successfully deleted.
            """
            logbook_collection = get_db()["logbook"]
            log = logbook_collection.find_one({"_id": ObjectId(_id)})
            if log:
                logbook_collection.delete_one({"_id": ObjectId(_id)})
                return {"message": "Log deleted"}, 200
            else:
                return {"message": "Log not found"}, 404