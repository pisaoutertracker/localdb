import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, Blueprint
from bson import ObjectId
from utils import get_db, cable_templates_schema, cables_schema

bp = Blueprint("cables_bp", __name__)


@bp.route("/disconnectCables", methods=["POST"])
def disconnect():
    """disconnect_data = {
    cable1_name: name,
    cable1_port: port,
    cable1_side: side,
    cable2_name: name,
    cable2_port: port
    }
    """
    cables_collection = get_db()["cables"]
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


@bp.route("/connectCables", methods=["POST"])
def connect_cables():
    """connect_data = {
    cable1_name: name,
    cable1_port: port,
    cable1_side: side,
    cable2_name: name,
    cable2_port: port
    """
    cables_collection = get_db()["cables"]
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


# Recursive function to traverse through cables
def traverse_cables(cable, side, port):
    cable_templates_collection = get_db()["cable_templates"]
    cables_collection = get_db()["cables"]
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
        if next_cable:
            path.extend(
                traverse_cables(
                    next_cable, opposite_side, next_cable_connection["port"]
                )
            )
    return path


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
    modules_collection = get_db()["modules"]
    crates_collection = get_db()["crates"]
    cables_collection = get_db()["cables"]
    starting_point = (
        modules_collection.find_one({"moduleName": starting_point_name})
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
                (
                    conn["port"]
                    for conn in starting_cable[starting_side]
                    if str(conn["connectedTo"]) == str(starting_point["_id"])
                ),
                None,
            )
            return starting_cable, starting_port
    else:
        return starting_point, starting_port  # Default port for a cable

    return None, None


def traverse_cables(
    starting_point_name, starting_cable, starting_side, starting_port, cable_templates
):
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
    modules_collection = get_db()["modules"]
    crates_collection = get_db()["crates"]
    cables_collection = get_db()["cables"]
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
                    path.append(next_module["moduleName"])
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


@bp.route("/cablingSnapshot", methods=["POST"])
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
    cable_templates_collection = get_db()["cable_templates"]
    data = request.get_json()
    starting_point_name = data.get("starting_point_name")
    starting_side = data.get("starting_side")
    starting_port = data.get("starting_port", 1)

    # Fetch all cable templates
    cable_templates = list(cable_templates_collection.find({}))

    starting_cable, starting_port = find_starting_cable(
        starting_point_name, starting_side, starting_port
    )

    if not starting_cable:
        return {"message": "Starting point not found"}, 404

    path = traverse_cables(
        starting_point_name,
        starting_cable,
        starting_side,
        starting_port,
        cable_templates,
    )

    return {"cablingPath": path}, 200
