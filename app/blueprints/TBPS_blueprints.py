# on a new GET method, we:
# 1. given the module name, we get the module doc
# 2. we perform a join query to get the module_test (listed under the module "moduleTest" entry), module_test_run  and module_test_analysis
# 3. we return all the contents

import sys
import os
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, Blueprint
from bson import ObjectId
from utils import get_db, cable_templates_schema, cables_schema

bp = Blueprint("fetch_TBPS_data", __name__)

def get_module_with_related_data(modules_collection, module_name):
    pipeline = [
        # Stage 1: Match the specific module by name
        {
            "$match": {
                "moduleName": module_name
            }
        },
        # Stage 2: Unwind the _moduleTest_id array
        {
            "$unwind": {
                "path": "$_moduleTest_id",
                "preserveNullAndEmptyArrays": True
            }
            
        },
        # Stage 3: Define the testId field as the single entries in the _moduleTests_id array
        {
            "$addFields": {
                "testId": "$_moduleTest_id"
            }
        },
        # convert the testId to an ObjectId
        {
            "$addFields": {
                "testId": { "$toObjectId": "$testId" }
            }
        },
        # Stage 4: Lookup the moduleTests documents using the extracted ID
        {
            "$lookup": {
                "from": "module_tests",
                "localField": "testId",
                "foreignField": "_id",
                "as": "testDetails"
            }
        },
        # Stage 5: Add first test detail to the document
        {
            "$addFields": {
                "testDetail": { "$arrayElemAt": ["$testDetails", 0] }
            }
        },
        # Stage 6: Lookup the test_run document
        {
            "$lookup": {
                "from": "test_runs",
                "localField": "testDetail.test_runName",
                "foreignField": "test_runName",
                "as": "testRun"
            }
        },
        # Stage 7: Add test run to document
        {
            "$addFields": {
                "run": { "$arrayElemAt": ["$testRun", 0] }
            }
        },
        # Stage 8: Lookup the session
        {
            "$lookup": {
                "from": "sessions",
                "localField": "run.runSession",
                "foreignField": "sessionName",
                "as": "sessionData"
            }
        },
        # Stage 9: Add session to document
        {
            "$addFields": {
                "session": { "$arrayElemAt": ["$sessionData", 0] }
            }
        },
        # Stage 10: Get the last analysis ID
        {
            "$addFields": {
                "lastAnalysisId": { 
                    "$arrayElemAt": ["$testDetail.analysesList", -1] 
                }
            }
        },
        # Stage 11: Lookup the analysis
        {
            "$lookup": {
                "from": "module_test_analysis",
                "localField": "lastAnalysisId",
                "foreignField": "moduleTestAnalysisName",
                "as": "analysisData"
            }
        },
        # Stage 12: Add analysis to document
        {
            "$addFields": {
                "analysis": { "$arrayElemAt": ["$analysisData", 0] }
            }
        },
        # Stage 13: Create a combined test document
        {
            "$addFields": {
                "combinedTest": {
                    "name": "$testDetail.moduleTestName",
                    "id": "$testId",
                    "details": "$testDetail",
                    "run": "$run",
                    "session": "$session",
                    "analysis": "$analysis"
                }
            }
        },
        # Stage 14: Group back to rebuild the module with all tests
        {
            "$group": {
                "_id": "$_id",
                "moduleName": { "$first": "$moduleName" },
                "position": { "$first": "$position" },
                "status": { "$first": "$status" },
                "type": { "$first": "$type" },
                "crateSide": { "$first": "$crateSide" },
                "tests": { "$push": "$combinedTest" }
            }
        },
        # Stage 15: Clean up by removing unnecessary fields
        {
            "$project": {
                "moduleTests": 0
            }
        }
    ]
    
    result = modules_collection.aggregate(pipeline)
    return list(result)[0] if result else None


def get_session_with_related_data(sessions_collection, session_name):
    pipeline = [
        # Stage 1: Match the specific session by name
        {
            "$match": {
                "sessionName": session_name
            }
        },
        # Stage 2: Unwind the _test_run_id array
        {
            "$unwind": {
                "path": "$_test_run_id",
                "preserveNullAndEmptyArrays": True
            }
        },
        # Stage 3: Define the runId field as the single entries in the _test_run_id array
        {
            "$addFields": {
                "runId": "$_test_run_id"
            }
        },
        # Convert the runId to an ObjectId
        {
            "$addFields": {
                "runId": { "$toObjectId": "$runId" }
            }
        },
        # Stage 4: Lookup the test_runs documents using the extracted ID
        {
            "$lookup": {
                "from": "test_runs",
                "localField": "runId",
                "foreignField": "_id",
                "as": "runDetails"
            }
        },
        # Stage 5: Add first run detail to the document
        {
            "$addFields": {
                "runDetail": { "$arrayElemAt": ["$runDetails", 0] }
            }
        },
        # Stage 6: Unwind the _moduleTest_id array from the run
        {
            "$unwind": {
                "path": "$runDetail._moduleTest_id",
                "preserveNullAndEmptyArrays": True
            }
        },
        # Stage 7: Define the moduleTestId field
        {
            "$addFields": {
                "moduleTestId": "$runDetail._moduleTest_id"
            }
        },
        # Convert the moduleTestId to an ObjectId
        {
            "$addFields": {
                "moduleTestId": { "$toObjectId": "$moduleTestId" }
            }
        },
        # Stage 8: Lookup the moduleTests documents
        {
            "$lookup": {
                "from": "module_tests",
                "localField": "moduleTestId",
                "foreignField": "_id",
                "as": "moduleTestDetails"
            }
        },
        # Stage 9: Add module test to document
        {
            "$addFields": {
                "moduleTest": { "$arrayElemAt": ["$moduleTestDetails", 0] }
            }
        },
        # Stage 10: Lookup the module document
        {
            "$lookup": {
                "from": "modules",
                "localField": "moduleTest.moduleName",
                "foreignField": "moduleName",
                "as": "moduleData"
            }
        },
        # Stage 11: Add module to document
        {
            "$addFields": {
                "module": { "$arrayElemAt": ["$moduleData", 0] }
            }
        },
        # Stage 12: Get the last analysis ID
        {
            "$addFields": {
                "lastAnalysisId": { 
                    "$arrayElemAt": ["$moduleTest.analysesList", -1] 
                }
            }
        },
        # Stage 13: Lookup the analysis
        {
            "$lookup": {
                "from": "module_test_analysis",
                "localField": "lastAnalysisId",
                "foreignField": "moduleTestAnalysisName",
                "as": "analysisData"
            }
        },
        # Stage 14: Add analysis to document
        {
            "$addFields": {
                "analysis": { "$arrayElemAt": ["$analysisData", 0] }
            }
        },
        # Stage 15: Create a combined module test document with run info
        {
            "$addFields": {
                "combined_module_test": {
                    "module_test_name": "$moduleTest.moduleTestName",
                    "module_test_id": "$moduleTest._id",
                    "module_test_data": "$moduleTest",
                    "module": "$module",
                    "run": {
                        "name": "$runDetail.test_runName",
                        "id": "$runDetail._id",
                        "data": "$runDetail"
                    },
                    "analysis": "$analysis"
                }
            }
        },
        # Stage 16: Group directly to final session structure with a single module_tests array
        {
            "$group": {
                "_id": "$_id",
                "sessionName": { "$first": "$sessionName" },
                "operator": { "$first": "$operator" },
                "timestamp": { "$first": "$timestamp" },
                "description": { "$first": "$description" },
                "configuration": { "$first": "$configuration" },
                "modulesList": { "$first": "$modulesList" },
                "log": { "$first": "$log" },
                # Include both runs and module_tests as separate arrays
                "runs": {
                    "$addToSet": {
                        "run_id": "$runDetail._id",
                        "run_name": "$runDetail.test_runName",
                        "run_date": "$runDetail.runDate",
                        "run_type": "$runDetail.runType",
                        "run_status": "$runDetail.runStatus"
                    }
                },
                "module_tests": { "$push": "$combined_module_test" }
            }
        },
        # Stage 17: Final projection to clean up the output
        {
            "$project": {
                "_id": 0,
                "sessionName": 1,
                "operator": 1,
                "timestamp": 1,
                "description": 1,
                "configuration": 1,
                "modulesList": 1,
                "log": 1,
                "runs": 1,
                "module_tests": 1
            }
        }
    ]
    
    result = sessions_collection.aggregate(pipeline)
    return list(result)[0] if result else None

def get_module_test_with_session_data(module_tests_collection, module_test_id):
    pipeline = [
        # Stage 1: Match the specific module test by ID
        {
            "$match": {
                "moduleTestName": module_test_id
            }
        },
        # Stage 2: Lookup the test run
        {
            "$lookup": {
                "from": "test_runs",
                "localField": "test_runName",
                "foreignField": "test_runName",
                "as": "run"
            }
        },
        # Stage 3: Add run to document
        {
            "$addFields": {
                "run": { "$arrayElemAt": ["$run", 0] }
            }
        },
        # Stage 4: Lookup the session
        {
            "$lookup": {
                "from": "sessions",
                "localField": "run.runSession",
                "foreignField": "sessionName",
                "as": "session"
            }
        },
        # Stage 5: Add session to document
        {
            "$addFields": {
                "session": { "$arrayElemAt": ["$session", 0] }
            }
        },
        # Stage 6: Get the last analysis ID
        {
            "$addFields": {
                "lastAnalysisId": { 
                    "$arrayElemAt": ["$analysesList", -1] 
                }
            }
        },
        # Stage 7: Lookup the analysis
        {
            "$lookup": {
                "from": "module_test_analysis",
                "localField": "lastAnalysisId",
                "foreignField": "moduleTestAnalysisName",
                "as": "analysis"
            }
        },
        # Stage 8: Add analysis to document
        {
            "$addFields": {
                "analysis": { "$arrayElemAt": ["$analysis", 0] },
                "analysisFile": "$analysis.analysisFile",
                "sessionName": "$session.sessionName"
            }
        },
        # Stage 10: Group back to rebuild the module test with all related data
        {
            "$group": {
                "_id": "$_id",
                "moduleTest": { "$first": "$$ROOT" }
            }
        },
        # Stage 11: Clean up by removing unnecessary fields
        {
            "$project": {
                "_id": 0,
                "moduleTest.analysesList": 0
            }
        }
    ]
    
    result = module_tests_collection.aggregate(pipeline)
    return list(result)[0] if result else None

def get_all_module_test_with_session_data(module_tests_collection):
    pipeline = [
        # Stage 1: Lookup the test run
        {
            "$lookup": {
                "from": "test_runs",
                "localField": "test_runName",
                "foreignField": "test_runName",
                "as": "run"
            }
        },
        # Stage 2: Add run to document
        {
            "$addFields": {
                "run": { "$arrayElemAt": ["$run", 0] }
            }
        },
        # Stage 3: Lookup the session
        {
            "$lookup": {
                "from": "sessions",
                "localField": "run.runSession",
                "foreignField": "sessionName",
                "as": "session"
            }
        },
        # Stage 4: Add session to document
        {
            "$addFields": {
                "session": { "$arrayElemAt": ["$session", 0] }
            }
        },
        # Stage 5: Get the last analysis ID
        {
            "$addFields": {
                "lastAnalysisId": { 
                    "$arrayElemAt": ["$analysesList", -1] 
                }
            }
        },
        # Stage 6: Lookup the analysis
        {
            "$lookup": {
                "from": "module_test_analysis",
                "localField": "lastAnalysisId",
                "foreignField": "moduleTestAnalysisName",
                "as": "analysis"
            }
        },
        # Stage 7: Add analysis to document and extract run date
        {
            "$addFields": {
                "analysis": { "$arrayElemAt": ["$analysis", 0] },
                "analysisFile": "$analysis.analysisFile",
                "sessionName": "$session.sessionName",
                "runDate": "$run.runDate",
                "runType": "$run.runType",
            }
        },
        # Stage 8: Sort by runDate (latest first)
        {
            "$sort": {
                "runDate": -1
            }
        },
        # Stage 9: Final projection to clean up the output
        {
            "$project": {
                "_id": 1,
                "moduleTestName": 1,
                "test_runName": 1,
                "runDate": 1,
                "runType": 1,
                "moduleName": 1,
                "noise": 1,
                "run": 1,
                "session": 1,
                "analysis": 1,
                "analysisFile": 1,
                "sessionName": 1,
                "dataPath": 1,
                "moduleTestLog": 1
            }
        }
    ]
    
    result = list(module_tests_collection.aggregate(pipeline))
    
    # Convert to dictionary with moduleTestName as keys
    module_tests_dict = {item["moduleTestName"]: item for item in result}
    
    return {
        "module_tests_list": result,
        "module_tests_dict": module_tests_dict
    }


@bp.route("/fetch_module_results/<module_name>", methods=["GET"])
def fetch_module_results(module_name):
    if not module_name: 
        return jsonify({"error": "Module name is required"}), 400

    db = get_db()
    modules_collection = db["modules"]
    module = get_module_with_related_data(modules_collection, module_name)
    return module, 200 if module else 404

@bp.route("/fetch_session_results/<session_name>", methods=["GET"])
def fetch_session_results(session_name):
    if not session_name:
        return jsonify({"error": "Session name is required"}), 400

    db = get_db()
    sessions_collection = db["sessions"]
    session = get_session_with_related_data(sessions_collection, session_name)
    return session, 200 if session else 404

@bp.route("/fetch_module_test_results/<module_test_id>", methods=["GET"])
def fetch_module_test_results(module_test_id):
    if not module_test_id:
        return jsonify({"error": "Module test ID is required"}), 400

    db = get_db()
    module_tests_collection = db["module_tests"]
    module_test = get_module_test_with_session_data(module_tests_collection, module_test_id)
    return module_test, 200 if module_test else 404

@bp.route("/fetch_all_module_test_results", methods=["GET"])
def fetch_all_module_test_results():
    db = get_db()
    module_tests_collection = db["module_tests"]
    
    # Optional pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    
    # Get all module tests with related data
    result = get_all_module_test_with_session_data(module_tests_collection)
    
    # Basic pagination implementation
    module_tests_list = result["module_tests_list"]
    total_items = len(module_tests_list)
    # The list is already sorted by runDate in descending order by the pipeline
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated_list = module_tests_list[start_idx:end_idx]
    
    # Create a paginated response
    response = {
        "module_tests": {
            # "as_list": paginated_list,
            "all_names": [item["moduleTestName"] for item in module_tests_list],
            "all_types": [item["runType"] for item in module_tests_list],
            "unique_types": list(set(item["runType"] for item in module_tests_list)),
            "is_from_session1": [item["sessionName"] == "session1" for item in module_tests_list],
            "current_names": [item["moduleTestName"] for item in paginated_list],
            "as_dict": {item["moduleTestName"]: item for item in paginated_list}
        },
        "pagination": {
            "total_items": total_items,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_items + per_page - 1) // per_page
        }
    }
    
    return response, 200 if module_tests_list else 404
