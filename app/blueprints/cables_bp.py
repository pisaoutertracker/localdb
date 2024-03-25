import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, Blueprint
from bson import ObjectId
from utils import get_db, cable_templates_schema, cables_schema

bp = Blueprint("cables_bp", __name__)


@bp.route("/connect", methods=["POST"])
def connect_cables():
    data = request.get_json()
    cables_collection = get_db()["cables"]
    modules_collection = get_db()["modules"]
    templates_collection = get_db()["cable_templates"]

    # check that data includes the necessary fields
    if "cable1" not in data or "cable2" not in data:
        return jsonify({"error": "Both cables must be specified"}), 400
    if "port1" not in data or "port2" not in data:
        return jsonify({"error": "Both cables must have ports!"}), 400

    cable1_name = data["cable1"]
    cable2_name = data["cable2"]
    port1 = data["port1"]
    port2 = data["port2"]

    module_in_detSide = False

    # Retrieve the cables from the database
    cable1 = cables_collection.find_one({"name": cable1_name})
    # excpet for the case of not found, in which case we will try to find it in modules
    if not cable1:
        cable1 = modules_collection.find_one({"moduleName": cable1_name})
        module_in_detSide = True
        # if cable 1 is module but it does not have a 'type' field, set it to 'module'
        if cable1:
            if "type" not in cable1:
                cable1["type"] = "module"
            template1 = templates_collection.find_one({"type": cable1["type"]})
        # if the cable is a module, it may not have been initialized with a crateSide
            if "crateSide" not in cable1:
                cable1["crateSide"] = {str(i): [] for i in range(1, template1["lines"] + 1)}

    cable2 = cables_collection.find_one({"name": cable2_name})
    if not cable2:
        cable2 = modules_collection.find_one({"moduleName": cable2_name})
        if cable2:
            raise Exception("Module should always be passed in detSide")

    if cable1 and cable2:
        # Retrieve the cable templates from the database
        template1 = templates_collection.find_one({"type": cable1["type"]})
        template2 = templates_collection.find_one({"type": cable2["type"]})

        if template1 and template2:
            # check that port1 and port2 are valid
            if port1 not in template1["crateSide"] or port2 not in template2["detSide"]:
                return jsonify({"error": "Invalid port"}), 400

            # Get the lines for the specified ports
            lines1 = template1["crateSide"][port1]
            lines2 = template2["detSide"][port2]

            # first check that the lines are free
            for line1 in lines1:
                if line1 != -1:
                    line1 = str(line1)
                    if cable1["crateSide"][line1] != []:
                        return (
                            jsonify(
                                {
                                    "error": f"Cable {cable1_name} line {line1} is already connected to {cable1['crateSide'][line1][0]}"
                                }
                            ),
                            400,
                        )

            for line2 in lines2:
                if line2 != -1:
                    line2 = str(line2)
                    if cable2["detSide"][line2] != []:
                        return (
                            jsonify(
                                {
                                    "error": f"Cable {cable2_name} line {line2} is already connected to {cable2['detSide'][line2][0]}"
                                }
                            ),
                            400,
                        )

            # Update the cable connections
            for line1, line2 in zip(lines1, lines2):
                if line1 != -1 and line2 != -1:
                    line1 = str(line1)
                    line2 = str(line2)
                    cable1["crateSide"][line1] = [cable2_name, int(line2)]
                    cable2["detSide"][line2] = [cable1_name, int(line1)]

            # Update the cables in the database
            if module_in_detSide:
                modules_collection.update_one(
                    {"moduleName": cable1_name}, {"$set": cable1}
                )
            else:
                cables_collection.update_one({"name": cable1_name}, {"$set": cable1})

            cables_collection.update_one({"name": cable2_name}, {"$set": cable2})

            return jsonify({"message": "Cables connected successfully"}), 200
        else:
            return jsonify({"error": "Invalid cable templates"}), 400
    else:
        return jsonify({"error": "Cables not found"}), 404


@bp.route("/disconnect", methods=["POST"])
def disconnect_cables():
    data = request.get_json()
    cables_collection = get_db()["cables"]
    modules_collection = get_db()["modules"]
    templates_collection = get_db()["cable_templates"]

    # check that data includes the necessary fields
    if "cable1" not in data or "cable2" not in data:
        return jsonify({"error": "Both cables must be specified"}), 400
    
    cable1_name = data["cable1"]
    cable2_name = data["cable2"]

    module_in_detSide = False
    # Retrieve the cables from the database
    cable1 = cables_collection.find_one({"name": cable1_name})
    if not cable1:
        cable1 = modules_collection.find_one({"moduleName": cable1_name})
        module_in_detSide = True
        if cable1:
            if "type" not in cable1:
                cable1["type"] = "module"
            template1 = templates_collection.find_one({"type": cable1["type"]})
            if "crateSide" not in cable1:
                cable1["crateSide"] = {str(i): [] for i in range(1, template1["lines"] + 1)}

    cable2 = cables_collection.find_one({"name": cable2_name})
    if not cable2:
        cable2 = modules_collection.find_one({"moduleName": cable2_name})
        if cable2:
            raise Exception("Module should always be passed in detSide")

    if not cable1 or not cable2:
        return jsonify({"error": "Cables not found"}), 404

    # check if data includes ports
    if "port1" in data and "port2" in data:
        port1 = data["port1"]
        port2 = data["port2"]
        # Retrieve the cable templates from the database
        template1 = templates_collection.find_one({"type": cable1["type"]})
        template2 = templates_collection.find_one({"type": cable2["type"]})

        if template1 and template2:
            # check that port1 and port2 are valid
            if port1 not in template1["crateSide"] or port2 not in template2["detSide"]:
                return jsonify({"error": "Invalid port"}), 400

            # Get the lines for the specified ports
            lines1 = template1["crateSide"][port1]
            lines2 = template2["detSide"][port2]

            # Update the cable connections
            for line1, line2 in zip(lines1, lines2):
                if line1 != -1 and line2 != -1:
                    line1 = str(line1)
                    line2 = str(line2)
                    if cable1["crateSide"][line1] == [cable2_name, int(line2)]:
                        cable1["crateSide"][line1] = []
                        cable2["detSide"][line2] = []
                    else:
                        return (
                            jsonify(
                                {
                                    "error": "Cables are not connected, so I cannot disconnect them"
                                }
                            ),
                            400,
                        )

            # Update the cables in the database
            if module_in_detSide:
                modules_collection.update_one(
                    {"moduleName": cable1_name}, {"$set": cable1}
                )
            else:
                cables_collection.update_one({"name": cable1_name}, {"$set": cable1})
            cables_collection.update_one({"name": cable2_name}, {"$set": cable2})

            return jsonify({"message": "Cables disconnected successfully"}), 200
        else:
            return jsonify({"error": "Invalid cable templates"}), 400

    elif "port1" not in data and "port2" not in data:
        if cable1 and cable2:
            # Disconnect the cables
            for line, connection in cable1["crateSide"].items():
                if connection[0] == cable2_name:
                    cable1["crateSide"][str(line)] = []
                    cable2["detSide"][str(connection[1])] = []

        # Update the cables in the database
        if module_in_detSide:
            modules_collection.update_one({"moduleName": cable1_name}, {"$set": cable1})
        else:
            cables_collection.update_one({"name": cable1_name}, {"$set": cable1})
        cables_collection.update_one({"name": cable2_name}, {"$set": cable2})

        return jsonify({"message": "Cables disconnected successfully"}), 200

    # if we get a port for one cable and not the other return an error
    else:
        return (
            jsonify(
                {"error": "Both cables must have ports, or no ports should be passed!"}
            ),
            400,
        )
