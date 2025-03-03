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
        # Stage 2: Unwind the moduleTests array
        {
            "$unwind": {
                "path": "$moduleTests",
                "preserveNullAndEmptyArrays": True
            }
        },
        # Stage 3: Extract test ID from the moduleTests array
        {
            "$addFields": {
                "testId": { "$arrayElemAt": ["$moduleTests", 1] },
                "testName": { "$arrayElemAt": ["$moduleTests", 0] }
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
                    "name": "$testName",
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


@bp.route("/fetch_module_results/<module_name>", methods=["GET"])
def fetch_module_results(module_name):
    if not module_name:
        return jsonify({"error": "Module name is required"}), 400

    db = get_db()
    modules_collection = db["modules"]
    module = get_module_with_related_data(modules_collection, module_name)
    return module, 200 if module else 404
