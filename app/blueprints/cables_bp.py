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
    """
    Connects two cables together based on the provided data.

    This route expects a JSON payload with the following fields:
    - "cable1": The name of the first cable.
    - "cable2": The name of the second cable.
    - "port1": The port number of the first cable.
    - "port2": The port number of the second cable.

    The function performs the following steps:
    1. Checks if the necessary fields are present in the data.
    2. Retrieves the cables from the database.
    3. If a cable is not found in the cables collection, it tries to find it in the modules collection.
    4. If a cable is a module and does not have a 'type' field, it sets it to 'module'.
    5. If a cable is a module and does not have a 'crateSide' field, it initializes it with an empty dictionary.
    6. Retrieves the cable templates from the database.
    7. Checks if the provided ports are valid.
    8. Checks if the lines for the specified ports are free.
    9. Updates the cable connections.
    10. Updates the cables in the database.

    Returns:
    - If the cables are successfully connected, returns a JSON response with a "message" field indicating success (status code 200).
    - If the necessary fields are missing in the data, returns a JSON response with an "error" field indicating the missing fields (status code 400).
    - If the cables or cable templates are not found, returns a JSON response with an "error" field indicating the missing cables or templates (status code 404).
    - If the provided ports are invalid or the lines are already connected, returns a JSON response with an "error" field indicating the issue (status code 400).
    """
    # Function code goes here
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
                cable1["crateSide"] = {
                    str(i): [] for i in range(1, template1["lines"] + 1)
                }

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
    """
    Disconnects two cables or modules in a database.

    This function takes in a JSON payload containing the names of two cables or modules to be disconnected,
    along with optional port numbers for each cable. It retrieves the cables or modules from the database,
    checks if the necessary fields are present in the payload, and verifies the validity of the ports if provided.
    If the cables or modules are found and the ports are valid, it updates the cable connections in the database
    and returns a success message. If any errors occur during the disconnection process, appropriate error messages
    are returned.

    Returns:
        A JSON response containing a success message if the cables or modules are disconnected successfully,
        or an error message if any errors occur during the disconnection process.
    """
    
    data = request.get_json()
    cables_collection = get_db()["cables"]
    modules_collection = get_db()["modules"]
    templates_collection = get_db()["cable_templates"]

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
                cable1["crateSide"] = {
                    str(i): [] for i in range(1, template1["lines"] + 1)
                }

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
                if len(connection)> 0 and connection[0] == cable2_name:
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


@bp.route("/snapshot", methods=["POST"])
def snapshot():
    """
    Retrieves a snapshot of cable connections based on the provided data.

    The function takes in a JSON object containing the cable name and side
    to run the snapshot on. It retrieves the cables from the database, checks
    and returns a JSON object representing the connections between cables.

    Args:
        None

    Returns:
        A JSON object representing the cable connections. The structure of the
        JSON object is as follows:
        {
            line_number: {
                "connections": [
                    {
                        "cable": "cable_name",
                        "line": line_number
                    },
                    ...
                ]
            },
            ...
        }

    Raises:
        - 400 Bad Request: If the necessary fields (cable and side) are not specified
        - 400 Bad Request: If an invalid side is provided
        - 404 Not Found: If the specified cable is not found
        - 400 Bad Request: If an invalid cable template is encountered
    """
    
    data = request.get_json()
    cables_collection = get_db()["cables"]
    modules_collection = get_db()["modules"]
    templates_collection = get_db()["cable_templates"]

    # check that data includes the necessary fields
    if "cable" not in data or "side" not in data:
        return jsonify({"error": "Cable, port and side must be specified"}), 400

    cable1_name = data["cable"]
    side = data["side"]
    port = data.get("port")  # Port is optional

    if side not in ["crateSide", "detSide"]:
        return jsonify({"error": "Invalid side"}), 400
    
    otherSide = "crateSide" if side == "detSide" else "detSide"

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

    if not cable1:
        return jsonify({"error": "Cable not found"}), 404

    template1 = templates_collection.find_one({"type": cable1["type"]})

    if not template1:
        return jsonify({"error": "Invalid cable template"}), 400

    cables_visited = []
    cables_visited.append(cable1_name)

    # Get the lines for all the ports
    lines1 = template1["lines"]
    all_lines = [line for line in range(1, lines1 + 1)]

    # If port is specified, filter lines to only include those from the specified port
    if port:
        if side == "crateSide" and "crateSide" in template1:
            if port in template1["crateSide"]:
                all_lines = [line for line in template1["crateSide"][port] if line != -1]
            else:
                return jsonify({"error": f"Port {port} not found in crateSide"}), 400
        elif side == "detSide" and "detSide" in template1:
            if port in template1["detSide"]:
                all_lines = [line for line in template1["detSide"][port] if line != -1]
            else:
                return jsonify({"error": f"Port {port} not found in detSide"}), 400

    # snapshot is a dict
    snapshot = {}
    # since we can have multiple lines per port, we can have multiple cables
    # so we keep track of the current line
    for line in all_lines:
        snapshot[line] = {}

        # When port is specified, use it directly instead of searching
        if port:
            if side == "crateSide":
                snapshot[line]["crate_port"] = port
            elif side == "detSide":
                snapshot[line]["det_port"] = port
        else:
            # Original behavior when no port is specified
            if "crateSide" in template1:
                for p, tlines in template1["crateSide"].items():
                    if line in tlines:
                        snapshot[line]["crate_port"] = p
                        break
            
            if "detSide" in template1:
                for p, tlines in template1["detSide"].items():
                    if line in tlines:
                        snapshot[line]["det_port"] = p
                        break

        snapshot[line]["connections"] = []
        current_cable = cable1

        if side not in current_cable:
            continue
        if current_cable[side] == {}:
            continue
        if current_cable[side][str(line)] == []:
            continue

        next_cable = cables_collection.find_one(
            {"name": current_cable[side][str(line)][0]}
        )

        # if the next cable search is empty, search in modules
        if not next_cable:
            next_cable = modules_collection.find_one(
                {"moduleName": current_cable[side][str(line)][0]}
            )

        next_line = current_cable[side][str(line)][1]
        next_template = templates_collection.find_one({"type": next_cable["type"]})

        crate_ports = []
        det_ports = []

        #
        if "crateSide" in next_template:
            for p, lines in next_template["crateSide"].items():
                if next_line in lines:
                    crate_ports.append(p)
                
        if "detSide" in next_template:
            for p, lines in next_template["detSide"].items():
                if next_line in lines:
                    det_ports.append(p)

        # append the next cable and line
        snapshot[line]["connections"].append(
            {
                "cable": current_cable[side][str(line)][0],
                "line": next_line,
                "det_port": det_ports,
                "crate_port": crate_ports,
            }
        )
        while True:
            # update the current cable, port, and line
            current_cable = next_cable
            current_line = next_line

            if side not in current_cable:
                break
            if current_cable[side] == {}:
                break
            if current_cable[side][str(current_line)] == []:
                break


            next_cable = cables_collection.find_one(
                {"name": current_cable[side][str(current_line)][0]}
            )

            # if the next cable search is empty, search in modules
            if not next_cable:
                next_cable = modules_collection.find_one(
                    {"moduleName": current_cable[side][str(current_line)][0]}
                )

            if not next_cable:
                break

            # get the lines
            next_line = current_cable[side][str(current_line)][1]
            next_template = templates_collection.find_one({"type": next_cable["type"]})


            # if next_cable["name"] starts with F it means it's an FC7
            # and we should log which port the line corresponds to
            crate_ports = []
            det_ports = []

            if "crateSide" in next_template:
                for p, lines in next_template["crateSide"].items():
                    if next_line in lines:
                        crate_ports.append(p)
                        

            if "detSide" in next_template:
                for p, lines in next_template["detSide"].items():
                    if next_line in lines:
                        det_ports.append(p)

            snapshot[line]["connections"].append(
                {
                    "cable": current_cable[side][str(current_line)][0],
                    "line": next_line,
                    "det_port": det_ports,
                    "crate_port": crate_ports,
                }
            )

    return (jsonify(snapshot), 200)
