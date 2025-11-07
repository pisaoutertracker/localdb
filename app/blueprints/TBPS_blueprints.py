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

@bp.route("/fetch_all_module_test_results_optimized", methods=["GET"])
def fetch_all_module_test_results_optimized():
    """
    Optimized endpoint with server-side filtering and pagination.
    
    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 25)
    - search: Search query for test names (optional)
    - run_types: Comma-separated list of run types to filter (optional)
    - hide_session1: Hide tests from session1 (default: false, accepts 'true'/'false')
    - filters_only: Only return available filters, not data (default: false)
    """
    db = get_db()
    module_tests_collection = db["module_tests"]
    
    # Check if only filters are requested
    filters_only = request.args.get('filters_only', 'false').lower() == 'true'
    
    if filters_only:
        # Just return available filter options
        result = get_all_module_test_with_session_data(module_tests_collection)
        module_tests_list = result["module_tests_list"]
        
        unique_run_types = sorted(list(set(item.get("runType") for item in module_tests_list if item.get("runType"))))
        
        return {
            "available_filters": {
                "run_types": unique_run_types
            }
        }, 200
    
    # Parse parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    search_query = request.args.get('search', '').strip().lower()
    run_types_param = request.args.get('run_types', '').strip()
    hide_session1 = request.args.get('hide_session1', 'false').lower() == 'true'
    
    # Parse run types filter
    run_types_filter = []
    if run_types_param:
        run_types_filter = [rt.strip() for rt in run_types_param.split(',') if rt.strip()]
    
    # Get all module tests with related data
    result = get_all_module_test_with_session_data(module_tests_collection)
    module_tests_list = result["module_tests_list"]
    
    # Apply filters
    filtered_list = []
    for item in module_tests_list:
        # Filter by session
        if hide_session1 and item.get("sessionName") == "session1":
            continue
        
        # Filter by run types
        if run_types_filter and item.get("runType") not in run_types_filter:
            continue
        
        # Filter by search query
        if search_query and search_query not in item.get("moduleTestName", "").lower():
            continue
        
        filtered_list.append(item)
    
    # Apply pagination
    total_items = len(filtered_list)
    total_pages = max(1, (total_items + per_page - 1) // per_page)
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    paginated_list = filtered_list[start_idx:end_idx]
    
    # Create optimized response (only send what's needed)
    response = {
        "tests": paginated_list,
        "pagination": {
            "total_items": total_items,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }
    }
    
    return response, 200


@bp.route("/fetch_session_testing_flow/<session_name>", methods=["GET"])
def fetch_session_testing_flow(session_name):
    """
    Fetch the complete testing flow for all modules in a session using MongoDB aggregation.
    Returns module tests and burn-in cycles sorted by timestamp for visualization.
    
    This uses two efficient pipelines (one for test runs, one for burn-in cycles) then
    combines the results in Python. The matrix building is done in Python as it requires
    complex nested logic that's more readable and maintainable in Python than in MongoDB.
    """
    if not session_name:
        return jsonify({"error": "Session name is required"}), 400

    try:
        db = get_db()
        
        # First, get basic session info
        sessions_collection = db["sessions"]
        session = sessions_collection.find_one({"sessionName": session_name}, 
                                              {"operator": 1, "timestamp": 1, "description": 1, "modulesList": 1})
        
        if not session:
            return jsonify({"error": f"Session {session_name} not found"}), 404
        
        modules_list = session.get("modulesList", [])
        
        # PIPELINE 1: Get all test runs with their module tests in a single aggregation
        test_runs_collection = db["test_runs"]
        test_events_pipeline = [
            # Match runs for this session
            {"$match": {"runSession": session_name}},
            
            # Unwind module test IDs to process each separately
            {"$unwind": {"path": "$moduleTestName", "preserveNullAndEmptyArrays": False}},
            
            # Lookup the actual module test document
            {"$lookup": {
                "from": "module_tests",
                "localField": "moduleTestName",
                "foreignField": "moduleTestName",
                "as": "moduleTestDoc"
            }},
            
            # Unwind the lookup result
            {"$unwind": {"path": "$moduleTestDoc", "preserveNullAndEmptyArrays": False}},
            
            # Project only the fields we need for the visualization
            {"$project": {
                "_id": 0,
                "type": {"$literal": "test"},
                "timestamp": "$runDate",
                "module_name": "$moduleTestDoc.moduleName",
                "test_type": "$runType",
                "test_name": "$moduleTestName",
                "run_name": "$test_runName",
                "event_name": "$runType"
            }},
            
            # Sort by timestamp
            {"$sort": {"timestamp": 1}}
        ]
        
        module_test_events = list(test_runs_collection.aggregate(test_events_pipeline))
        
        # PIPELINE 2: Get all burn-in cycles for this session
        burnin_cycles_collection = db["burnin_cycles"]
        burnin_events_pipeline = [
            # Match cycles that contain the session name
            {"$match": {"BurninCycleName": {"$regex": f".*{session_name}.*"}}},
            
            # Unwind the modules array to create one event per module
            {"$unwind": {"path": "$BurninCycleModules", "preserveNullAndEmptyArrays": False}},
            
            # Project the fields we need, including temperature label generation
            {"$project": {
                "_id": 0,
                "type": {"$literal": "cycle"},
                "timestamp": "$BurninCycleDate",
                "module_name": "$BurninCycleModules",
                "cycle_name": "$BurninCycleName",
                "temperatures": "$BurninCycleTemperatures",
                # Create event_name with temperature info
                "event_name": {
                    "$cond": {
                        "if": {"$and": [
                            {"$ifNull": ["$BurninCycleTemperatures.low", False]},
                            {"$ifNull": ["$BurninCycleTemperatures.high", False]}
                        ]},
                        "then": {
                            "$concat": [
                                "Cycle ",
                                {"$toString": "$BurninCycleTemperatures.low"},
                                "°C/",
                                {"$toString": "$BurninCycleTemperatures.high"},
                                "°C"
                            ]
                        },
                        "else": "Cycle"
                    }
                }
            }},
            
            # Sort by timestamp
            {"$sort": {"timestamp": 1}}
        ]
        
        burnin_events = list(burnin_cycles_collection.aggregate(burnin_events_pipeline))
        
        # Combine and sort all events (MongoDB did most of the work!)
        all_events = module_test_events + burnin_events
        
        # Sort by timestamp - handle both datetime objects and strings
        def get_timestamp(event):
            ts = event.get("timestamp")
            if ts is None:
                return datetime.datetime.min
            if isinstance(ts, str):
                try:
                    return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
                except:
                    return datetime.datetime.min
            return ts
        
        all_events.sort(key=get_timestamp)
        
        # Build a time-segmented structure with test type aggregation
        # First, identify burn-in cycles to use as segment boundaries
        cycle_events = [e for e in all_events if e.get("type") == "cycle"]
        test_events = [e for e in all_events if e.get("type") == "test"]
        
        # Create segments: each segment is either a group of tests or a burn-in cycle
        segments = []
        
        if not cycle_events:
            # No cycles, all tests in one segment
            if test_events:
                segments.append({
                    "type": "test_group",
                    "events": test_events,
                    "start_time": get_timestamp(test_events[0]) if test_events else None,
                    "end_time": get_timestamp(test_events[-1]) if test_events else None
                })
        else:
            # Add test segment before first cycle
            first_cycle_time = get_timestamp(cycle_events[0])
            tests_before_first_cycle = [e for e in test_events if get_timestamp(e) < first_cycle_time]
            if tests_before_first_cycle:
                segments.append({
                    "type": "test_group",
                    "events": tests_before_first_cycle,
                    "start_time": get_timestamp(tests_before_first_cycle[0]),
                    "end_time": get_timestamp(tests_before_first_cycle[-1])
                })
            
            # Interleave cycles and test groups
            for i, cycle in enumerate(cycle_events):
                # Add the cycle itself
                segments.append({
                    "type": "cycle",
                    "event": cycle,
                    "timestamp": get_timestamp(cycle)
                })
                
                # Add tests between this cycle and the next (or end)
                current_cycle_time = get_timestamp(cycle)
                if i < len(cycle_events) - 1:
                    next_cycle_time = get_timestamp(cycle_events[i + 1])
                    tests_in_segment = [e for e in test_events 
                                       if current_cycle_time < get_timestamp(e) < next_cycle_time]
                else:
                    # Tests after last cycle
                    tests_in_segment = [e for e in test_events 
                                       if get_timestamp(e) > current_cycle_time]
                
                if tests_in_segment:
                    segments.append({
                        "type": "test_group",
                        "events": tests_in_segment,
                        "start_time": get_timestamp(tests_in_segment[0]),
                        "end_time": get_timestamp(tests_in_segment[-1])
                    })
        
        # Now build the column structure
        # Each segment becomes columns (test types for test_group, single column for cycle)
        columns = []
        
        for seg_idx, segment in enumerate(segments):
            if segment["type"] == "cycle":
                # Single column for the cycle
                cycle_event = segment["event"]
                columns.append({
                    "type": "cycle",
                    "column_id": f"seg_{seg_idx}_cycle",
                    "event_name": cycle_event.get("event_name"),
                    "timestamp": segment["timestamp"],
                    "cycle_event": cycle_event
                })
            else:  # test_group
                # Group tests by test_type within this segment
                test_types_in_segment = {}
                for event in segment["events"]:
                    test_type = event.get("test_type", "Unknown")
                    if test_type not in test_types_in_segment:
                        test_types_in_segment[test_type] = []
                    test_types_in_segment[test_type].append(event)
                
                # Create a column for each test type in this segment
                for test_type, type_events in sorted(test_types_in_segment.items()):
                    columns.append({
                        "type": "test_group",
                        "column_id": f"seg_{seg_idx}_{test_type}",
                        "test_type": test_type,
                        "event_name": test_type,
                        "start_time": segment["start_time"],
                        "end_time": segment["end_time"],
                        "test_events": type_events  # All events of this type in this segment
                    })
        
        # Build the flow matrix with the new column structure
        module_flows = {module: [] for module in modules_list}
        
        for event in all_events:
            module_name = event.get("module_name")
            if module_name in module_flows:
                module_flows[module_name].append(event)
        
        flow_matrix = []
        for module in modules_list:
            row = {"module_name": module, "columns": {}}
            
            for col_idx, column in enumerate(columns):
                col_key = f"col_{col_idx}"
                
                if column["type"] == "cycle":
                    # Check if this module participated in this cycle
                    cycle_event = column["cycle_event"]
                    if module == cycle_event.get("module_name"):
                        row["columns"][col_key] = {
                            "present": True,
                            "type": "cycle",
                            "event_name": cycle_event.get("event_name"),
                            "cycle_name": cycle_event.get("cycle_name"),
                            "temperatures": cycle_event.get("temperatures")
                        }
                    else:
                        row["columns"][col_key] = {"present": False}
                        
                else:  # test_group
                    # Find all tests of this type for this module in this segment
                    test_type = column["test_type"]
                    module_tests_in_column = [
                        e for e in column["test_events"]
                        if e.get("module_name") == module
                    ]
                    
                    if module_tests_in_column:
                        row["columns"][col_key] = {
                            "present": True,
                            "type": "test_group",
                            "test_type": test_type,
                            "count": len(module_tests_in_column),
                            "tests": module_tests_in_column  # List of all tests
                        }
                    else:
                        row["columns"][col_key] = {"present": False}
            
            flow_matrix.append(row)
        
        response = {
            "session_name": session_name,
            "session_info": {
                "operator": session.get("operator"),
                "timestamp": session.get("timestamp"),
                "description": session.get("description")
            },
            "modules": modules_list,
            "columns": columns,  # New structured column info
            "flow_matrix": flow_matrix
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        # Log the error for debugging
        import traceback
        print(f"Error in fetch_session_testing_flow: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

