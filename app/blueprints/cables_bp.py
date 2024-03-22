import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, Blueprint
from bson import ObjectId
from utils import get_db, cable_templates_schema, cables_schema

bp = Blueprint("cables_bp", __name__)


@bp.route('/connect', methods=['POST'])
def connect_cables():
    data = request.get_json()
    cables_collection = get_db()['cables']
    modules_collection = get_db()['modules']
    templates_collection = get_db()['cable_templates']

    cable1_name = data['cable1']
    cable2_name = data['cable2']
    port1 = data['port1']
    port2 = data['port2']

    # Retrieve the cables from the database
    try:
        cable1 = cables_collection.find_one({'name': cable1_name})
    # excpet for the case of not found, in which case we will try to find it in modules
    except Exception as e:
        cable1 = modules_collection.find_one({'name': cable1_name})
    try:
        cable2 = cables_collection.find_one({'name': cable2_name})
    except Exception as e:
        raise Exception("Module should always be passed in detSide")

    if cable1 and cable2:
        # Retrieve the cable templates from the database
        template1 = templates_collection.find_one({'type': cable1['type']})
        template2 = templates_collection.find_one({'type': cable2['type']})

        if template1 and template2:
            # Get the lines for the specified ports
            lines1 = template1['crateSide'][port1]
            lines2 = template2['detSide'][port2]

            # Update the cable connections
            for line1, line2 in zip(lines1, lines2):
                if line1 != -1 and line2 != -1:
                    line1 = str(line1)
                    line2 = str(line2)
                    cable1['crateSide'][line1] = [cable2_name, int(line2)]
                    cable2['detSide'][line2] = [cable1_name, int(line1)]

            # Update the cables in the database
            cables_collection.update_one({'name': cable1_name}, {'$set': cable1})
            cables_collection.update_one({'name': cable2_name}, {'$set': cable2})

            return jsonify({'message': 'Cables connected successfully'}), 200
        else:
            return jsonify({'error': 'Invalid cable templates'}), 400
    else:
        return jsonify({'error': 'Cables not found'}), 404

@bp.route('/disconnect', methods=['POST'])
def disconnect_cables():
    data = request.get_json()
    cables_collection = get_db()['cables']
    modules_collection = get_db()['modules']
    cable1_name = data['cable1']
    cable2_name = data['cable2']

    # Retrieve the cables from the database
    try:
        cable1 = cables_collection.find_one({'name': cable1_name})
    except Exception as e:
        cable1 = modules_collection.find_one({'name': cable1_name})
    try:
        cable2 = cables_collection.find_one({'name': cable2_name})
    except Exception as e:
        raise Exception("Module should always be passed in detSide")

    if cable1 and cable2:
        # Disconnect the cables
        for line, connection in cable1['crateSide'].items():
            if connection[0] == cable2_name:
                cable1['crateSide'][str(line)] = []
                cable2['detSide'][str(connection[1])] = []

        # Update the cables in the database
        cables_collection.update_one({'name': cable1_name}, {'$set': cable1})
        cables_collection.update_one({'name': cable2_name}, {'$set': cable2})

        return jsonify({'message': 'Cables disconnected successfully'}), 200
    else:
        return jsonify({'error': 'Cables not found'}), 404
