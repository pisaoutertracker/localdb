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
    sessions_collection = get_db()["sessions"]

    data = request.get_json()

    # get the length of the testRuns collection
    # this will be used to generate the test_runName
    test_run_count = testRuns_collection.count_documents({})
    # generate the test_runName
    run_key = "run" + str(test_run_count + 1)
    # check if the test_runName already exists
    # if it does, return an error
    if testRuns_collection.count_documents({"test_runName": run_key}) != 0:
        return (
            jsonify(
                {
                    "message": "Test run Name already exists. Please try again.",
                    "test_runName": run_key,
                }
            ),
            400,
        )

    # Process test run data
    run_entry = {
        # run date includes seconds
        "runDate": datetime.datetime.strptime(data["runDate"], "%Y-%m-%dT%H:%M:%S"),
        "test_runName": run_key,
        "runSession": data["runSession"],
        "runStatus": data["runStatus"],
        "runType": data["runType"],
        "runBoards": data["runBoards"],
        "_moduleTest_id": [],
        "moduleTestName": [],
        "runFile": data["runFile"],
        "runConfiguration": data["runConfiguration"],
    }
    # get the ObjectId of the session
    session = sessions_collection.find_one({"sessionName": data["runSession"]})
    session_id = session["_id"]
    # return error if session does not exist
    if not session_id:
        return (
            jsonify(
                {
                    "message": "Session does not exist. Please try again.",
                    "sessionName": data["runSession"],
                }
            ),
            400,
        )
    # add the session ObjectId as str to the run entryrunSession_id
    run_entry["_runSession_id"] = str(session_id)
    run_id = testRuns_collection.insert_one(run_entry).inserted_id

    if "test_runName" not in session:
        session["test_runName"] = []
        session["_test_run_id"] = []
    session["test_runName"].append(run_key)
    session["_test_run_id"].append(str(run_id))

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
            {"moduleName": module_key},
            {"$set": {"hardwareName": hw_id}},
            upsert=True,
            return_document=True,
        )
        # create the module testName as
        # (module_name)__(test_runName)
        moduleTestName = module_key + "__" + run_key
        # check if the module testName already exists
        # if it does, return an error
        if moduleTests_collection.count_documents({"moduleTestName": moduleTestName}) != 0:
            return (
                jsonify(
                    {
                        "message": "Module test Name already exists. Please try again.",
                        "moduleTestName": moduleTestName,
                    }
                ),
                400,
            )
        # create the module test entry
        module_test_entry = {
            "moduleTestName": moduleTestName,
            "_test_run_id": run_id,
            "test_runName": run_key,
            "_module_id": module_doc["_id"],
            "moduleName": module_key,
            "noise": data["runNoise"][hw_id],
            "board": board,
            "opticalGroupName": optical_group,
        }
        test_id = moduleTests_collection.insert_one(module_test_entry).inserted_id
        run_entry["moduleTestName"].append(moduleTestName)
        run_entry["_moduleTest_id"].append((test_id))

        # update the module entry by appending to the moduleTests list
        #the tuple (module test Name, module test ObjectId)
        modules_collection.update_one(
            {"moduleName": module_key},
            {"$push": {"moduleTests": (moduleTestName, test_id)}},
        )

    # Update the test run with module test mongo ObjectIds and names
    testRuns_collection.update_one(
        {"_id": run_id}, {"$set": {"moduleTestName": run_entry["moduleTestName"], "_moduleTest_id": run_entry["_moduleTest_id"]}}
    )
    return (
        jsonify(
            {
                "message": "Test run and module tests added successfully",
                "test_runName": run_key,
                "run_id": str(run_id),
            }
        ),
        201,
    )
