import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, Blueprint
import re
from utils import get_db

bp = Blueprint("logbook", __name__)

@bp.route("/searchLogBookByText", methods=["POST"])
def SearchLogBookByText():
    logbook_collection = get_db()["logbook"]
    data = request.get_json()
    pattern = data.get("modules")
    rexp = re.compile(pattern, re.IGNORECASE)
    logs = logbook_collection.find({"event": rexp})
    logs1 = logbook_collection.find({"details": rexp})
    result = set()
    for i in logs:
        result.add(str(i["_id"]))
    for i in logs1:
        result.add(str(i["_id"]))
    results = list(result)
    return jsonify(results), 200


@bp.route("/searchLogBookByModuleIDs", methods=["POST"])
def SearchLogBookByModuleIDs():
    logbook_collection = get_db()["logbook"]
    data = request.get_json()
    pattern = data.get("modules")
    rexp = re.compile(pattern, re.IGNORECASE)
    logs = logbook_collection.find({"involved_modules": rexp})
    #        logs =logbook_collection.find({"involved_modules": ""})
    result = []
    for i in logs:
        result.append(str(i["_id"]))
    return jsonify(result), 200
