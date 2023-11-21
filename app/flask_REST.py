from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from json import JSONEncoder
from pymongo import MongoClient
from bson import json_util, ObjectId
from jsonschema import validate, ValidationError
import pymongo
import os
import json
from dotenv import load_dotenv
from flask.json.provider import JSONProvider


class CustomJSONEncoder(JSONEncoder):
    """
    A custom JSON encoder that converts MongoDB ObjectIds to strings.

    This encoder is used to ensure that MongoDB ObjectIds are properly serialized
    when returning JSON responses from a Flask REST API.
    """

    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(self, obj)


class CustomJSONProvider(JSONProvider):
    """
    A custom JSON provider that uses a custom JSON encoder to serialize objects.
    """

    def dumps(self, obj, **kwargs):
        return json.dumps(obj, **kwargs, cls=CustomJSONEncoder)

    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)


app = Flask(__name__)
api = Api(app)
app.json = CustomJSONProvider(app)
# Load the schema
with open("../schemas/all_schemas.json", "r") as f:
    all_schemas = json.load(f)

module_schema = all_schemas["module"]
logbook_schema = all_schemas["logbook"]
current_cabling_map_schema = all_schemas["CurrentCablingMap"]
connection_snapshot_schema = all_schemas["ConnectionSnapshot"]
tests_schema = all_schemas["tests"]
cables_schema = all_schemas["cables"]
cable_templates_schema = all_schemas["cable_templates"]

load_dotenv("../config/mongo.env")
username = os.environ.get("MONGO_USERNAME")
password = os.environ.get("MONGO_PASSWORD")
db_name = os.environ.get("MONGO_DB_NAME")
host_name = os.environ.get("MONGO_HOST_NAME")

print(f"username: {username}, password: {password}")
client = MongoClient(f"mongodb://{username}:{password}@{host_name}:27017")
db = client[db_name]
# we already have a database called "test" from the previous example
# db = client['test']
# we also have a collection called "modules" from the previous example
modules_collection = db["modules"]
logbook_collection = db["logbook"]
current_cabling_map_collection = db["current_cabling_map"]
connection_snapshot_collection = db["connection_snapshot"]
tests_collection = db["tests"]
cables_collection = db["cables"]
cable_templates_collection = db["cable_templates"]


class ModulesResource(Resource):
    """Flask RESTful Resource for modules

    Args:
        Resource (Resource): Flask RESTful Resource
    """

    def get(self, moduleID=None):
        """
        Retrieves a module from the database based on its moduleID number, or retrieves all modules if no moduleID number is provided.

        Args:
            moduleID (int, optional): The moduleID number of the module to retrieve. Defaults to None.

        Returns:
            If moduleID is provided, returns a JSON representation of the module. If moduleID is not provided, returns a JSON representation of all modules in the database.
        """
        if moduleID:
            module = modules_collection.find_one({"moduleID": moduleID})
            if module:
                # module["_id"] = str(module["_id"])  # convert ObjectId to string
                return jsonify(module)
                # return json.dumps(module, default=json_util.default)
            else:
                return {"message": "Module not found"}, 404
        else:
            modules = list(modules_collection.find())
            # for module in modules:
            #     module["_id"] = str(module["_id"])
            return jsonify(modules)

    def post(self):
        """
        Inserts a new module into the database.

        Returns:
            If the module is successfully inserted, returns a message indicating success. If the module fails validation, returns an error message.
        """
        try:
            new_module = request.get_json()
            validate(instance=new_module, schema=module_schema)
            modules_collection.insert_one(new_module)
            return {"message": "Module inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, moduleID):
        """
        Updates an existing module in the database.

        Args:
            moduleID (int): The moduleID number of the module to update.

        Returns:
            If the module is successfully updated, returns a message indicating success.
        """
        updated_data = request.get_json()
        modules_collection.update_one({"moduleID": moduleID}, {"$set": updated_data})
        return {"message": "Module updated"}, 200

    def delete(self, moduleID):
        """
        Deletes an existing module from the database.

        Args:
            moduleID (int): The moduleID number of the module to delete.

        Returns:
            If the module is successfully deleted, returns a message indicating success.
        """
        modules_collection.delete_one({"moduleID": moduleID})
        return {"message": "Module deleted"}, 200


# API Routes
api.add_resource(ModulesResource, "/modules", "/modules/<string:moduleID>")


class LogbookResource(Resource):
    """
    A class representing a RESTful resource for logbook entries.

    Attributes:
    -----------
    None

    Methods:
    --------
    get(timestamp=None):
        Retrieves a logbook entry with the specified timestamp, or all logbook entries if no timestamp is provided.

    post():
        Inserts a new logbook entry into the database.

    put(timestamp):
        Updates an existing logbook entry with the specified timestamp.

    delete(timestamp):
        Deletes an existing logbook entry with the specified timestamp.
    """

    def get(self, timestamp=None):
        """
        Retrieves a logbook entry with the specified timestamp, or all logbook entries if no timestamp is provided.

        Parameters:
        -----------
        timestamp : str, optional
            The timestamp of the logbook entry to retrieve.

        Returns:
        --------
        dict or list
            A dictionary representing the logbook entry with the specified timestamp, or a list of all logbook entries if no timestamp is provided.
        """
        if timestamp:
            log = logbook_collection.find_one({"timestamp": timestamp})
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
            A dictionary containing a message indicating that the logbook entry was successfully inserted.
        """
        try:
            new_log = request.get_json()
            validate(instance=new_log, schema=logbook_schema)
            logbook_collection.insert_one(new_log)
            return {"message": "Log inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, timestamp):
        """
        Updates an existing logbook entry with the specified timestamp.

        Parameters:
        -----------
        timestamp : str
            The timestamp of the logbook entry to update.

        Returns:
        --------
        dict
            A dictionary containing a message indicating that the logbook entry was successfully updated.
        """
        updated_data = request.get_json()
        logbook_collection.update_one({"timestamp": timestamp}, {"$set": updated_data})
        return {"message": "Log updated"}, 200

    def delete(self, timestamp):
        """
        Deletes an existing logbook entry with the specified timestamp.

        Parameters:
        -----------
        timestamp : str
            The timestamp of the logbook entry to delete.

        Returns:
        --------
        dict
            A dictionary containing a message indicating that the logbook entry was successfully deleted.
        """
        log = logbook_collection.find_one({"timestamp": timestamp})
        if log:
            logbook_collection.delete_one({"timestamp": timestamp})
            return {"message": "Log deleted"}, 200
        else:
            return {"message": "Log not found"}, 404


# API Routes
api.add_resource(LogbookResource, "/logbook", "/logbook/<string:timestamp>")


class TestsResource(Resource):
    """
    Resource for handling HTTP requests related to tests.

    Methods:
    - get: retrieves a test entry by ID or all test entries if no ID is provided
    - post: creates a new test entry
    - put: updates an existing test entry by ID
    - delete: deletes an existing test entry by ID
    """

    def get(self, testID=None):
        if testID:
            entry = tests_collection.find_one({"testID": testID})
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
        try:
            new_entry = request.get_json()
            validate(instance=new_entry, schema=tests_schema)
            tests_collection.insert_one(new_entry)
            return {"message": "Entry inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, testID):
        if testID:
            updated_data = request.get_json()
            tests_collection.update_one({"testID": testID}, {"$set": updated_data})
            return {"message": "Entry updated"}, 200
        else:
            return {"message": "Entry not found"}, 404

    def delete(self, testID):
        if testID:
            entry = tests_collection.find_one({"testID": testID})
            if entry:
                tests_collection.delete_one({"testID": testID})
                return {"message": "Entry deleted"}, 200
            else:
                return {"message": "Entry not found"}, 404
        else:
            return {"message": "Entry not found"}, 404


api.add_resource(TestsResource, "/tests", "/tests/<string:testID>")


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
        try:
            new_entry = request.get_json()
            validate(instance=new_entry, schema=cables_schema)
            cables_collection.insert_one(new_entry)
            return {"message": "Entry inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, name):
        if name:
            updated_data = request.get_json()
            cables_collection.update_one({"name": name}, {"$set": updated_data})
            return {"message": "Entry updated"}, 200
        else:
            return {"message": "Entry not found"}, 404

    def delete(self, name):
        if name:
            entry = cables_collection.find_one({"name": name})
            if entry:
                cables_collection.delete_one({"name": name})
                return {"message": "Entry deleted"}, 200
            else:
                return {"message": "Entry not found"}, 404
        else:
            return {"message": "Entry not found"}, 404


api.add_resource(CablesResource, "/cables", "/cables/<string:name>")

# Define the schema for validation

class CableTemplatesResource(Resource):
    def get(self, cable_type=None):
        if cable_type:
            entry = cable_templates_collection.find_one({"type": cable_type})
            if entry:
                entry["_id"] = str(entry["_id"])
                return jsonify(entry)
            else:
                return {"message": "Template not found"}, 404
        else:
            entries = list(cable_templates_collection.find())
            for entry in entries:
                entry["_id"] = str(entry["_id"])
            return jsonify(entries)

    def post(self):
        try:
            new_entry = request.get_json()
            validate(instance=new_entry, schema=cable_templates_schema)
            cable_templates_collection.insert_one(new_entry)
            return {"message": "Template inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, cable_type):
        if cable_type:
            updated_data = request.get_json()
            cable_templates_collection.update_one({"type": cable_type}, {"$set": updated_data})
            return {"message": "Template updated"}, 200
        else:
            return {"message": "Template not found"}, 404

    def delete(self, cable_type):
        if cable_type:
            result = cable_templates_collection.delete_one({"type": cable_type})
            if result.deleted_count > 0:
                return {"message": "Template deleted"}, 200
            else:
                return {"message": "Template not found"}, 404
        else:
            return {"message": "Template not found"}, 404

# Add the resource to the API
api.add_resource(CableTemplatesResource, "/cable_templates", "/cable_templates/<string:cable_type>")

### CUSTOM ROUTES ###


@app.route("/addTest", methods=["POST"])
def addTest():
    # NOTE must be rewritten as "addRun"
    """1) create a new test from the json given by the request
    2) for every module in the modules_list field of the test object, update that module in the module collection and add the testID of the current test into the tests property of the modules (which is a list of moudule ids)
    """
    try:
        new_entry = request.get_json()
        validate(instance=new_entry, schema=tests_schema)
        tests_collection.insert_one(new_entry)

        for moduleID in new_entry["modules_list"]:
            modules_collection.update_one(
                {"moduleID": moduleID}, {"$push": {"tests": new_entry["testID"]}}
            )
        return {"message": "Entry inserted"}, 201

    except ValidationError as e:
        return {"message": str(e)}, 400


@app.route("/cablingMap", methods=["POST"])
def cabling_map():
    request_data = request.get_json()
    detector_side_cables = request_data.get("detSide", [])
    crate_side_cables = request_data.get("crateSide", [])
    map_of_cabling = {}

    for cable_id in detector_side_cables:
        current_cable_id = cables_collection.find_one({"cableID": cable_id})["cableID"]
        map_of_cabling[current_cable_id] = ["detSide", current_cable_id]
        next_cable_in_chain = cables_collection.find_one({"detSide": current_cable_id})

        while next_cable_in_chain is not None:
            map_of_cabling[current_cable_id].append(next_cable_in_chain["cableID"])
            next_cable_in_chain = cables_collection.find_one(
                {"detSide": next_cable_in_chain["cableID"]}
            )

        map_of_cabling[current_cable_id].append("crateSide")

    for cable_id in crate_side_cables:
        current_cable_id = cables_collection.find_one({"cableID": cable_id})["cableID"]
        map_of_cabling[current_cable_id] = ["crateSide", current_cable_id]
        next_cable_in_chain = cables_collection.find_one(
            {"crateSide": current_cable_id}
        )

        while next_cable_in_chain is not None:
            map_of_cabling[current_cable_id].append(next_cable_in_chain["cableID"])
            next_cable_in_chain = cables_collection.find_one(
                {"crateSide": next_cable_in_chain["cableID"]}
            )

        map_of_cabling[current_cable_id].append("detSide")

    return jsonify(map_of_cabling)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=False)