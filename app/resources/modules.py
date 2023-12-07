import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from utils import get_db, module_schema


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
        modules_collection = get_db()["modules"]
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
        modules_collection = get_db()["modules"]
        try:
            new_module = request.get_json()
            validate(instance=new_module, schema=module_schema)
            modules_collection.insert_one(new_module)
            retrive = jsonify(modules_collection.find_one({"moduleID": new_module["moduleID"]}))
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
        modules_collection = get_db()["modules"]
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
        modules_collection = get_db()["modules"]
        modules_collection.delete_one({"moduleID": moduleID})
        return {"message": "Module deleted"}, 200
