import sys
import os
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, Blueprint
from bson import ObjectId
from utils import get_db, cable_templates_schema, cables_schema

bp = Blueprint("add_run", __name__)

def process_run(run_key, data, testRuns_collection, modules_collection, moduleTests_collection, sessions_collection):
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
        # return error if session does not exist
        if not session:
            return (
                jsonify(
                    {
                        "message": "Session does not exist. Please try again.",
                        "sessionName": data["runSession"],
                    }
                ),
                400,
            )
        session_id = session["_id"]
        # add the session ObjectId as str to the run entryrunSession_id
        run_entry["_runSession_id"] = str(session_id)
        run_id = testRuns_collection.insert_one(run_entry).inserted_id

        # update the session entry by appending to the test_runName list
        # and to _test_run_id the ObjectId of the test run
        sessions_collection.update_one(
            {"sessionName": data["runSession"]},
            {"$push": {"test_runName": run_key, "_test_run_id": str(run_id)}},
        )

        # Process each module test
        skipped_modules_count = 0
        for board_and_optical_group, (module_key, hw_id) in data["runModules"].items():
            if module_key == -1:
                # print("a moduleID is -1, skipping")
                skipped_modules_count += 1
                continue
            else:
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
                # check if the module testName already exists
                # if it does, return an error
                if (moduleTests_collection.count_documents({"moduleTestName": moduleTestName}) != 0) & (not moduleTestName.endswith("run0")):
                    return (
                        jsonify(
                            {
                                "message": "Module test Name already exists. Please try again.",
                                "moduleTestName": moduleTestName,
                            }
                        ),
                        400,
                    )
                elif (moduleTests_collection.count_documents({"moduleTestName": moduleTestName}) != 0) & (moduleTestName.endswith("run0")):
                    # replace the entry with the new one
                    moduleTests_collection.update_one(
                        {"moduleTestName": moduleTestName}, {"$set": module_test_entry}
                    )
                    # get the ObjectId of the module test
                    test_id = moduleTests_collection.find_one({"moduleTestName": moduleTestName})["_id"]
                else:
                    test_id = moduleTests_collection.insert_one(module_test_entry).inserted_id
                    
                run_entry["moduleTestName"].append(moduleTestName)
                run_entry["_moduleTest_id"].append((test_id))

                # update the module entry by appending to the moduleTestName list
                # module test Name and to _moduleTest_id the ObjectId of the module test
                modules_collection.update_one(
                    {"moduleName": module_key},
                    {"$push": {"moduleTestName": moduleTestName, "_moduleTest_id": str(test_id)}},
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
                    "skipped_modules_count": skipped_modules_count,
                }
            ),
            201,
        )


@bp.route("/addRun", methods=["POST"])
def add_run():
    testRuns_collection = get_db()["test_runs"]
    modules_collection = get_db()["modules"]
    moduleTests_collection = get_db()["module_tests"]
    sessions_collection = get_db()["sessions"]

    data = request.get_json()

    # generate the test_runName
    # check if the runNumber is in the data
    if "runNumber" not in data:
        return jsonify({"message": "runNumber is missing"}), 400
    # check that the "runNumber" follows the format "run" + number
    if not data["runNumber"].startswith("run"):
        return jsonify({"message": "runNumber should start with 'run'"}), 400
    # check that the "runNumber" follows the format "run" + number
    if not data["runNumber"][3:].isdigit():
        return jsonify({"message": "runNumber should be 'run' followed by a number"}), 400
    run_key = data["runNumber"]
    # check if the test_runName already exists
    # if it does, return an error
    if (testRuns_collection.count_documents({"test_runName": run_key}) != 0) & ( run_key != "run0"):
        return (
            jsonify(
                {
                    "message": "Test run Name already exists. Please try again.",
                    "test_runName": run_key,
                }
            ),
            400,
        )

    if run_key != "run0":
        return process_run(run_key, data, testRuns_collection, modules_collection, moduleTests_collection, sessions_collection)
    else:
        # we are adding a run0
        # it is our test run, so if it exists, we delete it
        if testRuns_collection.count_documents({"test_runName": "run0"}) != 0:
            # get the old run0 doc
            old_run0 = testRuns_collection.find_one({"test_runName": "run0"})
            testRuns_collection.delete_one({"test_runName": "run0"})
        
            # before running the process_run, we need to remove the references to the old run0 in the modules, sessions and module_tests collections
            # remove the old run0 from the session document
            sessions_collection.update_one(
                {"sessionName": old_run0["runSession"]},
                {"$pull": {"test_runName": "run0", "_test_run_id": str(old_run0["_id"])}},
            )
            
            # remove the old run0 from the module_test documents
            for module_test_id in old_run0["_moduleTest_id"]:
                moduleTests_collection.delete_one({"_id": module_test_id})
                
            # remove the reference to the modules test from the modules collection
            # extract the module_id from moduleTestName = module_key + "__" + run_key

            for module_id in old_run0["moduleTestName"]:
                module_name = module_id.split("__")[0]
                for moduleTest, moduleTestId in zip(old_run0["moduleTestName"], old_run0["_moduleTest_id"]):
                    if moduleTest.startswith(module_name):
                        modules_collection.update_one(
                            {"moduleName": module_name},
                            {"$pull": {"moduleTestName": moduleTest, "_moduleTest_id": str(moduleTestId)}},
                            )
       
        return process_run(run_key, data, testRuns_collection, modules_collection, moduleTests_collection, sessions_collection)