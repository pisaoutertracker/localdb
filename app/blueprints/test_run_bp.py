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

    # get the length of the testRuns collection
    # this will be used to generate the test_runID
    test_run_count = testRuns_collection.count_documents({})
    # generate the test_runID
    run_key = "run" + str(test_run_count + 1)
    # check if the test_runID already exists
    # if it does, return an error
    if testRuns_collection.count_documents({"test_runID": run_key}) != 0:
        return (
            jsonify(
                {
                    "message": "Test run ID already exists. Please try again.",
                    "test_runID": run_key,
                }
            ),
            400,
        )

    # Process test run data
    run_entry = {
        # run date includes seconds
        "runDate": datetime.datetime.strptime(data["runDate"], "%Y-%m-%dT%H:%M:%S"),
        "test_runID": run_key,
        "runSession": data["runSession"],
        "runStatus": data["runStatus"],
        "runType": data["runType"],
        "runBoards": data["runBoards"],
        "tests": [],
        "analysisList": [],
        "referenceAnalysis": "",
        "runFile": data["runFile"],
        "runConfiguration": data["runConfiguration"],
    }
    # get the ObjectId of the session
    session_id = get_db()["sessions"].find_one({"sessionKey": data["runSession"]})["_id"]
    # return error if session does not exist
    if not session_id:
        return (
            jsonify(
                {
                    "message": "Session does not exist. Please try again.",
                    "sessionKey": data["runSession"],
                }
            ),
            400,
        )
    # add the session ObjectId as str to the run entryrunSession_id
    run_entry["runSession_id"] = str(session_id)
    run_id = testRuns_collection.insert_one(run_entry).inserted_id

    # Process each module test
    for board_and_optical_group, (module_key, hw_id) in data["runModules"].items():
        # cast hw_id to str
        hw_id = str(hw_id)
        # split board_and_optical_group into board and optical_group
        # format is board_optical0 and i want to store board and 0, without the optical
        board, optical_group = board_and_optical_group.split("_optical")
        optical_group = int(optical_group)
        # Update or find the module to get its ObjectId
        module_doc = modules_collection.find_one_and_update(
            {"moduleID": module_key},
            {"$set": {"hardwareID": hw_id}},
            upsert=True,
            return_document=True,
        )
        # create the module testID as
        # (module_name)__(test_runID)
        moduleTestKey = module_key + "__" + run_key
        # check if the module testID already exists
        # if it does, return an error
        if moduleTests_collection.count_documents({"moduleTestKey": moduleTestKey}) != 0:
            return (
                jsonify(
                    {
                        "message": "Module test ID already exists. Please try again.",
                        "moduleTestKey": moduleTestKey,
                    }
                ),
                400,
            )
        # create the module test entry
        module_test_entry = {
            "moduleTestKey": moduleTestKey,
            "run": run_id,
            "module": module_doc["_id"],
            "noise": data["runNoise"][hw_id],
            "board": board,
            "opticalGroupID": optical_group,
        }
        test_id = moduleTests_collection.insert_one(module_test_entry).inserted_id
        run_entry["tests"].append((moduleTestKey, test_id))

        # update the module entry by appending to the moduleTests list
        #the tuple (module test ID, module test ObjectId)
        modules_collection.update_one(
            {"moduleID": module_key},
            {"$push": {"moduleTests": (moduleTestKey, test_id)}},
        )

    # Update the test run with module test mongo ObjectIds
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
