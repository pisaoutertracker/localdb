import sys
import os
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from jsonschema import validate, ValidationError
from flask import request, jsonify, Blueprint
from bson import ObjectId
from utils import get_db

bp = Blueprint("add_analysis", __name__)

# creare la funzione /addAnalysis che prende in input la chiave del module test analysis PS_26_05-IBA_00102__run67__V1 e
# trova il module test con la chiave PS_26_05-IBA_00102__run67 
# e aggiunge l'analisi alla lista delle analisi di quel  module_test e la mette a reference_analysis
@bp.route("/addAnalysis", methods=["GET"])
def addAnalysis():
    module_test_analysis_collection = get_db()["module_test_analysis"]
    module_tests_collection = get_db()["module_tests"]

    # get the moduleTestAnalysisName from the request
    moduleTestAnalysisName = request.args.get("moduleTestAnalysisName")
    # get the module_test_analysis entry from the collection
    module_test_analysis = module_test_analysis_collection.find_one({"moduleTestAnalysisName": moduleTestAnalysisName})
    # get the module_testName from the module_test_analysis entry
    module_testName = module_test_analysis["moduleTestName"]
    # get the module_test entry from the collection
    module_test = module_tests_collection.find_one({"moduleTestName": module_testName})
    # add the analysis to the list of analyses of the module_test
    # if the list of analyses doesn't exist, create it
    if "analysesList" not in module_test:
        module_test["analysesList"] = []
    module_test["analysesList"].append(moduleTestAnalysisName)
    # set the reference_analysis of the module_test to the analysis
    module_test["referenceAnalysis"] = moduleTestAnalysisName
    # drop the _id from module_test so that it can be inserted in the collection
    module_test.pop("_id")
    # update the module_test entry in the collection
    module_tests_collection.update_one({"moduleTestName": module_testName}, {"$set": module_test})
    return {"message": f"Analysis {moduleTestAnalysisName} added to module test {module_testName}"}, 200