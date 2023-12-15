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

    # get the moduleTestAnalysisKey from the request
    moduleTestAnalysisKey = request.args.get("moduleTestAnalysisKey")
    # get the module_test_analysis entry from the collection
    module_test_analysis = module_test_analysis_collection.find_one({"moduleTestAnalysisKey": moduleTestAnalysisKey})
    # get the module_testKey from the module_test_analysis entry
    module_testKey = module_test_analysis["moduleTestKey"]
    # get the module_test entry from the collection
    module_test = module_tests_collection.find_one({"moduleTestKey": module_testKey})
    # add the analysis to the list of analyses of the module_test
    # if the list of analyses doesn't exist, create it
    if "analysesList" not in module_test:
        module_test["analysesList"] = []
    module_test["analysesList"].append(moduleTestAnalysisKey)
    # set the reference_analysis of the module_test to the analysis
    module_test["referenceAnalysis"] = moduleTestAnalysisKey
    # drop the _id from module_test so that it can be inserted in the collection
    module_test.pop("_id")
    # update the module_test entry in the collection
    module_tests_collection.update_one({"moduleTestKey": module_testKey}, {"$set": module_test})
    return {"message": f"Analysis {moduleTestAnalysisKey} added to module test {module_testKey}"}, 200