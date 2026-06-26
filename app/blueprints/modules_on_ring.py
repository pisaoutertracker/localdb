import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flask import jsonify, Blueprint
from utils import get_db

bp = Blueprint("modules_on_ring", __name__)


@bp.route("/modules_on_ring", methods=["GET"])
def get_modules_on_ring():
    modules_collection = get_db()["modules"]
    cursor = modules_collection.find(
        {"status": "MOUNTED", "details.LOCATION": "IT-Pisa[INFN Pisa]"},
        # get also the LOCATION attributre living under "details"
        {"_id": 0, "moduleName": 1, "mounted_on": 1, "details.LOCATION": 1},
    )
    return jsonify(list(cursor)), 200
