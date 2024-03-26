import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from bson import ObjectId
import bson
from utils import get_db, module_schema


class ModulesResource(Resource):
    """Flask RESTful Resource for modules

    Args:
        Resource (Resource): Flask RESTful Resource
    """

    def get(self, moduleName=None):
        """
        Retrieves a module from the database based on its moduleName number, or retrieves all modules if no moduleName number is provided.

        Args:
            moduleName (int, optional): The moduleName number of the module to retrieve. Defaults to None.

        Returns:
            If moduleName is provided, returns a JSON representation of the module. If moduleName is not provided, returns a JSON representation of all modules in the database.
        """
        modules_collection = get_db()["modules"]
        if moduleName:
            module = modules_collection.find_one({"moduleName": moduleName})
            if not module:
                try:
                    moduleName_id = ObjectId(moduleName)
                    module = modules_collection.find_one({"_id": moduleName_id})
                except bson.errors.InvalidId:
                    module = None
            if module:
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
        modules_collection = get_db()["modules"]
        templates_collection = get_db()['cable_templates']

        try:
            new_module = request.get_json()
            if "type" not in new_module:
                new_module["type"] = "module"
            elif new_module["type"] != "module":
                return (
                    
                        {
                            "message": "Only modules types can be inserted. Please try again.",
                            "type": new_module["type"],
                        }
                    ,
                    400,
                )
            validate(instance=new_module, schema=module_schema)
            # if an module with the same Name already exists, return an error
            if modules_collection.count_documents({"moduleName": new_module["moduleName"]}) != 0:
                return (
                    
                        {
                            "message": "Module Name already exists. Please try again.",
                            "moduleName": new_module["moduleName"],
                        }
                    ,
                    400,
                )
            # if an module with the same hwId already exists, return an error
            # check if the new module has a hwId
            if "hwId" in new_module:
                if modules_collection.count_documents({"hwId": new_module["hwId"]}) != 0:
                    return (
                        
                            {
                                "message": "Module hwId already exists. Please try again.",
                                "hwId": new_module["hwId"],
                            }
                        ,
                        400,
                    )
            # get template from the database
            template = templates_collection.find_one({"type": new_module["type"]})
            # intialize the detSide and crateSide based on the template
            if "detSide" in template:
                new_module["detSide"] = {
                    str(i): [] for i in range(1, template["lines"] + 1)
                }
            if "crateSide" in template:
                new_module["crateSide"] = {
                    str(i): [] for i in range(1, template["lines"] + 1)
                }
            modules_collection.insert_one(new_module)
            return {"message": "Module inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, moduleName):
        """
        Updates an existing module in the database.

        Args:
            moduleName (int): The moduleName number of the module to update.

        Returns:
            If the module is successfully updated, returns a message indicating success.
        """
        modules_collection = get_db()["modules"]
        updated_data = request.get_json()
        modules_collection.update_one({"moduleName": moduleName}, {"$set": updated_data})
        return {"message": "Module updated"}, 200

    def delete(self, moduleName):
        """
        Deletes an existing module from the database.

        Args:
            moduleName (int): The moduleName number of the module to delete.

        Returns:
            If the module is successfully deleted, returns a message indicating success.
        """
        modules_collection = get_db()["modules"]
        modules_collection.delete_one({"moduleName": moduleName})
        return {"message": "Module deleted"}, 200
