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
import re
from bson import json_util
import datetime

# define getdb function to switch between test and production databases
def get_db(env_path="../config/mongo.env", status="production"):
    load_dotenv(env_path)
    username = os.environ.get("MONGO_USERNAME")
    password = os.environ.get("MONGO_PASSWORD")
    host_name = os.environ.get("MONGO_HOST_NAME")

    # Determine the database name based on the context
    if status == "test":
        db_name = "unittest_db"  # Use your test database name
        print("Using test database")
    else:
        db_name = os.environ.get("MONGO_DB_NAME")
        print("Using production database")

    client = MongoClient(f"mongodb://{username}:{password}@{host_name}:27017")
    return client[db_name]

db = get_db(env_path="../config/mongo.env", status="production")

# define regexps to select module ids, crateid, etc
def regExpPatterns(s):
    mapRE = {"ModuleID": "PS_\\d+"}
    if s in mapRE.keys():
        return  mapRE[s]
    else:
        return None

def findModuleIds(istring):
    return re.findall(regExpPatterns("ModuleID"),istring)

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


def create_app(database=db):
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
    testpayload_schema = all_schemas["testpayload"]
    testRun_schema = all_schemas["testRun"]
    moduleTest_schema = all_schemas["moduleTest"]

    db = database

    modules_collection = db["modules"]
    logbook_collection = db["logbook"]
    current_cabling_map_collection = db["current_cabling_map"]
    connection_snapshot_collection = db["connection_snapshot"]
    tests_collection = db["tests"]
    cables_collection = db["cables"]
    cable_templates_collection = db["cable_templates"]
    crates_collection = db["crates"]
    testpayload_collection = db["testpayloads"]
    testRuns_collection = db["testRun"]
    moduleTests_collection = db["moduleTest"]


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
            for key in updated_data:
              if updated_data[key] == "":
                 updated_data[key] = None  # Convert empty strings to None
              elif updated_data[key] == 'None':
                 updated_data[key] = None  # Convert 'None' string back to None


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
            log = logbook_collection.find_one({"_id": ObjectId(_id)})
            if log:
                logbook_collection.delete_one({"_id": ObjectId(_id)})
                return {"message": "Log deleted"}, 200
            else:
                return {"message": "Log not found"}, 404


    # API Routes
    api.add_resource(LogbookResource, "/logbook", "/logbook/<string:_id>")


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


    class TestPayloadsResource(Resource):
        """
        Resource for handling HTTP requests related to testpayloads.

        Methods:
        - get: retrieves a testpayload entry by ID or all testpayload entries if no ID is provided
        - post: creates a new testpayload entry
        - put: updates an existing testpayload entry by ID
        - delete: deletes an existing testpayload entry by ID
        """

        def get(self, testpID=None):
            if testpID:
                entry = tests_collection.find_one({"_id": ObjectId(testpID)})
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
                validate(instance=new_entry, schema=testpayload_schema)
                result = (tests_collection.insert_one(new_entry))
                _id = str(result.inserted_id)
                return {"_id": str(_id)}, 201
            except ValidationError as e:
                return {"message": str(e)}, 400

        def put(self, testpID):
            if testID:
                updated_data = request.get_json()
                tests_collection.update_one({"_id": ObjectId(testpID)}, {"$set": updated_data})
                return {"message": "Entry updated"}, 200
            else:
                return {"message": "Entry not found"}, 404

        def delete(self, testpID):
            if testpID:
                entry = tests_collection.find_one({"_id": ObjectId(testpID)})
                if entry:
                    tests_collection.delete_one({"_id": ObjectId(testpID)})
                    return {"message": "Entry deleted"}, 200
                else:
                    return {"message": "Entry not found"}, 404
            else:
                return {"message": "Entry not found"}, 404


    api.add_resource(TestPayloadsResource, "/testpayloads", "/testpayloads/<string:testpID>")



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


    class CratesResource(Resource):
        def get(self, name=None):
            if name:
                entry = crates_collection.find_one({"name": name})
                if entry:
                    entry["_id"] = str(entry["_id"])  # convert ObjectId to string
                    return jsonify(entry)
                else:
                    return {"message": "Entry not found"}, 404
            else:
                entries = list(crates_collection.find())
           # a route for crates for now equal to cables
                for entry in entries:
                    entry["_id"] = str(entry["_id"])
                return jsonify(entries)

        def post(self):
            try:
                new_entry = request.get_json()
                # NOTE: add schema for crates
                crates_collection.insert_one(new_entry)
                return {"message": "Entry inserted"}, 201
            except ValidationError as e:
                return {"message": str(e)}, 400

        def put(self, name):
            if name:
                updated_data = request.get_json()
                crates_collection.update_one({"name": name}, {"$set": updated_data})
                return {"message": "Entry updated"}, 200
            else:
                return {"message": "Entry not found"}, 404

        def delete(self, name):
            if name:
                entry = crates_collection.find_one({"name": name})
                if entry:
                    crates_collection.delete_one({"name": name})
                    return {"message": "Entry deleted"}, 200
                else:
                    return {"message": "Entry not found"}, 404
            else:
                return {"message": "Entry not found"}, 404


    api.add_resource(CratesResource, "/crates", "/crates/<string:name>")

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
                cable_templates_collection.update_one(
                    {"type": cable_type}, {"$set": updated_data}
                )
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
    api.add_resource(
        CableTemplatesResource, "/cable_templates", "/cable_templates/<string:cable_type>"
    )

    ### CUSTOM ROUTES ###
    @app.route("/searchLogBookByText", methods=["POST"])
    def SearchLogBookByText():
            data = request.get_json()
            pattern = data.get("modules")
            rexp = re.compile(pattern, re.IGNORECASE)
            logs =logbook_collection.find({"event": rexp})
            logs1 = logbook_collection.find({"details": rexp})
            result = set()
            for i in logs:
                result.add(str(i["_id"])) 
            for i in logs1:
                result.add(str(i["_id"]))
            results = list(result)
            return  jsonify(results), 200        

        

    @app.route("/searchLogBookByModuleIDs", methods=["POST"])
    def SearchLogBookByModuleIDs():
            data = request.get_json()
            pattern = data.get("modules")
            rexp = re.compile(pattern, re.IGNORECASE)
            logs =logbook_collection.find({"involved_modules": rexp})     
    #        logs =logbook_collection.find({"involved_modules": ""})
            result = []
            for i in logs:
                result.append(str(i["_id"])) 
            return jsonify(result), 200        

    @app.route("/disconnectCables", methods=["POST"])
    def disconnect():
        """disconnect_data = {
        cable1_name: name,
        cable1_port: port,
        cable1_side: side,
        cable2_name: name,
        cable2_port: port
        }
        """
        data = request.get_json()
        cable1_name = data.get("cable1_name")
        cable1_port = data.get("cable1_port")
        cable1_side = data.get("cable1_side")
        cable2_name = data.get("cable2_name")
        cable2_port = data.get("cable2_port")

        # Fetch the cables to be connected
        cable1 = cables_collection.find_one({"name": cable1_name})
        cable2 = cables_collection.find_one({"name": cable2_name})
        # get ids
        cable1_id = cable1["_id"]
        cable2_id = cable2["_id"]

        # Disconnect a cable on the specified side and port
        cables_collection.update_one(
            {"_id": ObjectId(cable1_id)},
            {
                "$pull": {
                    cable1_side: {
                        "port": cable1_port,
                        "connectedTo": ObjectId(cable2_id),
                        "type": "cable",
                    }
                }
            },
        )

        cable2_side = "detSide" if cable1_side == "crateSide" else "crateSide"
        cables_collection.update_one(
            {"_id": ObjectId(cable2_id)},
            {
                "$pull": {
                    cable2_side: {
                        "port": cable2_port,
                        "connectedTo": ObjectId(cable1_id),
                        "type": "cable",
                    }
                }
            },
        )

        return {"message": "Cable disconnected"}, 200


    @app.route("/connectCables", methods=["POST"])
    def connect_cables():
        """connect_data = {
        cable1_name: name,
        cable1_port: port,
        cable1_side: side,
        cable2_name: name,
        cable2_port: port
        """
        data = request.get_json()
        cable1_name = data.get("cable1_name")
        cable1_port = data.get("cable1_port")
        cable1_side = data.get("cable1_side")
        cable2_name = data.get("cable2_name")
        cable2_port = data.get("cable2_port")

        # Fetch the cables to be connected
        cable1 = cables_collection.find_one({"name": cable1_name})
        cable2 = cables_collection.find_one({"name": cable2_name})
        # get ids
        cable1_id = cable1["_id"]
        cable2_id = cable2["_id"]

        # Update cable1's crateSide to connect to cable2's detSide
        cables_collection.update_one(
            {"_id": ObjectId(cable1_id)},
            {
                "$push": {
                    cable1_side: {
                        "port": cable1_port,
                        "connectedTo": ObjectId(cable2_id),
                        "type": "cable",
                    }
                }
            },
        )

        # Update cable2's detSide to connect to cable1's crateSide
        cable2_side = "detSide" if cable1_side == "crateSide" else "crateSide"
        cables_collection.update_one(
            {"_id": ObjectId(cable2_id)},
            {
                "$push": {
                    cable2_side: {
                        "port": cable2_port,
                        "connectedTo": ObjectId(cable1_id),
                        "type": "cable",
                    }
                }
            },
        )

        return {"message": "Cables connected"}, 200


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


    # Recursive function to traverse through cables
    def traverse_cables(cable, side, port):
        # Fetch all cable templates
        cable_templates = list(cable_templates_collection.find({}))
        # Determine the next port using the cable template
        cable_template = next(
            (ct for ct in cable_templates if ct["type"] == cable["type"]), None
        )
        if not cable_template:
            return [cable["name"]]  # End traversal if no matching template

        next_port = cable_template["internalRouting"].get(str(port), [])
        if not next_port:
            return [cable["name"]]  # End traversal if no matching port

        # Find connected cables and continue traversal
        path = [cable["name"]]
        # for next_port in next_ports:
        opposite_side = "detSide" if side == "crateSide" else "crateSide"
        next_cable_connection = next(
            (conn for conn in cable[opposite_side] if conn["port"] == next_port), None
        )
        if next_cable_connection:
            next_cable = cables_collection.find_one(
                {"_id": next_cable_connection["connectedTo"]}
            )
<<<<<<< HEAD
    return path


def find_starting_cable(starting_point_name, starting_side, starting_port):
    """
    Find the starting cable and port based on the given starting point name, side, and port.
=======
            if next_cable:
                path.extend(
                    traverse_cables(
                        next_cable, opposite_side, next_cable_connection["port"]
                    )
                )
        return path
>>>>>>> addRun

    def find_starting_cable(starting_point_name, starting_side, starting_port):
        """
        Find the starting cable and port based on the given starting point name, side, and port.

        Args:
            starting_point_name (str): The name of the starting point (either a module, crate, or cable).
            starting_side (str): The side of the starting cable to search for the port.
            starting_port (str): The starting port to find.

        Returns:
            tuple: A tuple containing the starting cable and port. If the starting point is not found, returns (None, None).
        """
        starting_point = (
            modules_collection.find_one({"moduleID": starting_point_name})
            or crates_collection.find_one({"name": starting_point_name})
            or cables_collection.find_one({"name": starting_point_name})
        )

        if not starting_point:
            return None, None

        if "connectedTo" in starting_point:
            connected_cable_id = ObjectId(starting_point["connectedTo"])
            starting_cable = cables_collection.find_one({"_id": connected_cable_id})
            if starting_cable:
                starting_port = next(
                    (conn["port"] for conn in starting_cable[starting_side] if str(conn["connectedTo"]) == str(starting_point["_id"])),
                    None
                )
                return starting_cable, starting_port
        else:
            return starting_point, starting_port  # Default port for a cable

        return None, None

    def traverse_cables(starting_point_name, starting_cable, starting_side, starting_port, cable_templates):
        """
        Traverses through a network of cables starting from a given point and returns the path.

        Args:
            starting_point_name (str): The name of the starting point.
            starting_cable (dict): The starting cable.
            starting_side (str): The starting side ("detSide" or "crateSide").
            starting_port (int): The starting port.
            cable_templates (list): A list of cable templates.

        Returns:
            list: The path of cables and connected components.

        """
        path = [starting_point_name]
        next_cable = starting_cable
        next_port = starting_port
        other_side = "crateSide" if starting_side == "detSide" else "detSide"

        while next_cable:
            path.append(next_cable["name"]) if next_cable[
                "name"
            ] != starting_point_name else None
            # Determine the next port using the cable template
            cable_template = next(
                (ct for ct in cable_templates if ct["type"] == next_cable["type"]), None
            )
            if starting_side == "detSide":
                next_port = int(cable_template["internalRouting"].get(str(next_port), None))
            else:
                next_port = int(
                    next(
                        (
                            port
                            for port, connection in cable_template[
                                "internalRouting"
                            ].items()
                            if next_port == connection
                        ),
                        None,
                    )
                )
            if not next_port:
                break

            next_cable_id = next(
                (
                    conn["connectedTo"]
                    for conn in next_cable[other_side]
                    if conn["port"] == next_port
                ),
                None,
            )
            previous_cable = next_cable
            next_cable = cables_collection.find_one({"_id": ObjectId(next_cable_id)})
            if not next_cable:
                # reached end of cables, append the crate if starting from a detSide
                if starting_side == "detSide":
                    next_crate_id = next(
                        (
                            conn["connectedTo"]
                            for conn in previous_cable[other_side]
                            if conn["port"] == next_port
                        ),
                        None,
                    )
                    next_crate = crates_collection.find_one(
                        {"_id": ObjectId(next_crate_id)}
                    )
                    if next_crate:
                        path.append(next_crate["name"])
                # reached end of cables, append the module if starting from crateSide
                else:
                    next_module_id = next(
                        (
                            conn["connectedTo"]
                            for conn in previous_cable[other_side]
                            if conn["port"] == next_port
                        ),
                        None,
                    )
                    next_module = modules_collection.find_one(
                        {"_id": ObjectId(next_module_id)}
                    )
                    if next_module:
                        path.append(next_module["moduleID"])
                break

            # else continue traversal
            next_port = next(
                (
                    conn["port"]
                    for conn in next_cable[starting_side]
                    if str(conn["connectedTo"]) == str(previous_cable["_id"])
                ),
                None,
            )

        return path

    @app.route("/cablingSnapshot", methods=["POST"])
    def new_cabling_snapshot():
        """
        Endpoint for creating a new cabling snapshot.

        Parameters:
        - starting_point_name (str): The name of the starting point.
        - starting_side (str): The side of the starting point.
        - starting_port (int, optional): The starting port number (default is 1).

        Returns:
        - dict: A dictionary containing the cabling path.

        Raises:
        - 404: If the starting point is not found.
        """
        data = request.get_json()
        starting_point_name = data.get("starting_point_name")
        starting_side = data.get("starting_side")
        starting_port = data.get("starting_port", 1)
        
        # Fetch all cable templates
        cable_templates = list(cable_templates_collection.find({}))

        starting_cable, starting_port = find_starting_cable(starting_point_name, starting_side, starting_port)

        if not starting_cable:
            return {"message": "Starting point not found"}, 404

        path = traverse_cables(starting_point_name, starting_cable, starting_side, starting_port, cable_templates)

        return {"cablingPath": path}, 200

    @app.route('/addRun', methods=['POST'])
    def add_run():
        data = request.get_json()

        # Process test run data
        run_entry = {
            'runDate': datetime.datetime.strptime(data['runDate'], '%Y-%m-%d'),
            'runID': data['runID'],
            'runOperator': data['runOperator'],
            'runStatus': data['runStatus'],
            'runType': data['runType'],
            'runBoards': data['runBoards'],
            'tests': {},
            'runFolder': data['runROOTFile'],
            'runConfiguration': data['runConfiguration']
        }
        run_id = testRuns_collection.insert_one(run_entry).inserted_id

        # Process each module test
        for board_and_optical_group, (module_id, hw_id) in data['runModules'].items():
            # cast hw_id to str
            hw_id = str(hw_id)
            #split board_and_optical_group into board and optical_group
            # format is board_optical0 and i want to store board and 0, without the optical
            board, optical_group = board_and_optical_group.split('_optical')
            optical_group = int(optical_group)
            # Update or find the module to get its ObjectId
            module_doc = modules_collection.find_one_and_update(
                {'moduleID': module_id},
                {'$set': {'hardwareID': hw_id}},
                upsert=True,
                return_document=True
            )
            module_test_entry = {
                'run': run_id,
                'module': module_doc['_id'],
                'result': data['runResults'][hw_id],
                'noise': data['runNoise'][hw_id],
                'board': board,
                'opticalGroupID': optical_group
            }
            test_id = moduleTests_collection.insert_one(module_test_entry).inserted_id
            run_entry['tests'][str(module_doc['_id'])] = test_id

        # Update the test run with module test IDs
        testRuns_collection.update_one({'_id': run_id}, {'$set': {'tests': run_entry['tests']}})

        return jsonify({'message': 'Test run and module tests added successfully', 'run_id': str(run_id)}), 201
    
    return app

if __name__ == "__main__":
#    app.run(host="0.0.0.0", port=5005, debug=False)
    app = create_app()
    app.run(host="0.0.0.0", port=5005, debug=False)
