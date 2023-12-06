import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, current_app
from flask_restful import Resource
from utils import get_db, cable_templates_schema


class CableTemplatesResource(Resource):
    def get(self, cable_type=None):
        cable_templates_collection = get_db()["cable_templates"]
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
        cable_templates_collection = get_db()["cable_templates"]
        try:
            new_entry = request.get_json()
            validate(instance=new_entry, schema=cable_templates_schema)
            cable_templates_collection.insert_one(new_entry)
            return {"message": "Template inserted"}, 201
        except ValidationError as e:
            return {"message": str(e)}, 400

    def put(self, cable_type):
        cable_templates_collection = get_db()["cable_templates"]
        if cable_type:
            updated_data = request.get_json()
            cable_templates_collection.update_one(
                {"type": cable_type}, {"$set": updated_data}
            )
            return {"message": "Template updated"}, 200
        else:
            return {"message": "Template not found"}, 404

    def delete(self, cable_type):
        cable_templates_collection = get_db()["cable_templates"]
        if cable_type:
            result = cable_templates_collection.delete_one({"type": cable_type})
            if result.deleted_count > 0:
                return {"message": "Template deleted"}, 200
            else:
                return {"message": "Template not found"}, 404
        else:
            return {"message": "Template not found"}, 404
