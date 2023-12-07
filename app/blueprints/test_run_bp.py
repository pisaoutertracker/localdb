import sys
import os
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, Blueprint
from bson import ObjectId
from utils import get_db, cable_templates_schema, cables_schema

bp = Blueprint("add_run", __name__)

@bp.route("/addRun", methods=["POST"])
def add_run():
    testRuns_collection = get_db()["test_runs"]
    modules_collection = get_db()["modules"]
    moduleTests_collection = get_db()["module_tests"]

    data = request.get_json()

    # Process test run data
    run_entry = {
        "runDate": datetime.datetime.strptime(data["runDate"], "%Y-%m-%d"),
        "runID": data["runID"],
        "runOperator": data["runOperator"],
        "runStatus": data["runStatus"],
        "runType": data["runType"],
        "runBoards": data["runBoards"],
        "tests": {},
        "runFolder": data["runROOTFile"],
        "runConfiguration": data["runConfiguration"],
    }
    run_id = testRuns_collection.insert_one(run_entry).inserted_id

    # Process each module test
    for board_and_optical_group, (module_id, hw_id) in data["runModules"].items():
        # cast hw_id to str
        hw_id = str(hw_id)
        # split board_and_optical_group into board and optical_group
        # format is board_optical0 and i want to store board and 0, without the optical
        board, optical_group = board_and_optical_group.split("_optical")
        optical_group = int(optical_group)
        # Update or find the module to get its ObjectId
        module_doc = modules_collection.find_one_and_update(
            {"moduleID": module_id},
            {"$set": {"hardwareID": hw_id}},
            upsert=True,
            return_document=True,
        )
        module_test_entry = {
            "run": run_id,
            "module": module_doc["_id"],
            "result": data["runResults"][hw_id],
            "noise": data["runNoise"][hw_id],
            "board": board,
            "opticalGroupID": optical_group,
        }
        test_id = moduleTests_collection.insert_one(module_test_entry).inserted_id
        run_entry["tests"][str(module_doc["_id"])] = test_id

    # Update the test run with module test IDs
    testRuns_collection.update_one(
        {"_id": run_id}, {"$set": {"tests": run_entry["tests"]}}
    )
    return (
        jsonify(
            {
                "message": "Test run and module tests added successfully",
                "run_id": str(run_id),
            }
        ),
        201,
    )
