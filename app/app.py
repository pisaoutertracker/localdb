from flask import Flask, request, jsonify, current_app, g
from flask_restful import Resource, Api
from json import JSONEncoder
from pymongo import MongoClient
from bson import json_util, ObjectId
from jsonschema import validate, ValidationError
import os
import sys
import json
from dotenv import load_dotenv
from flask.json.provider import JSONProvider
import re
from bson import json_util
import datetime
from importlib import import_module
from dotenv import load_dotenv
from flask_cors import CORS
from flask_pymongo import PyMongo

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "utils")))
# make it so that utils can be imported from anywhere
from .utils import get_db, CustomJSONProvider, get_unittest_db

# import configs as config_module
 
from .resources import (
    modules,
    logbook,
    tests,
    test_payloads,
    cables,
    crates,
    cable_templates,
    test_run,
    module_test,
    session,
    module_test_analysis,
    IV_scans,
)
from .blueprints import add_run_bp, logbook_bp, cables_bp, add_analysis_bp, webgui_bp, TBPS_blueprints
from resources.burnin_cycles import BurninCyclesResource


def create_app(config_name):
    app = Flask(__name__)
    CORS(app)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema_path = os.path.join(base_dir, "config", f"{config_name}.env")
    load_dotenv(schema_path)

    if (config_name == "unittest") & (os.environ["MONGO_DB_NAME"] != "unittest_db"):
        raise ValueError("MONGO_DB_NAME must be set to 'unittest' for unittests")
    app.config["MONGO_URI"] = os.environ["MONGO_URI"]+"/"+ os.environ["MONGO_DB_NAME"]+"?authSource=admin"
    app.config["MONGO_DB_NAME"] = os.environ["MONGO_DB_NAME"]
    app.config["TESTING"] = os.environ["TESTING"]
    api = Api(app)
    mongo = PyMongo(app)
    app.json = CustomJSONProvider(app)
    
    # needed to clean up connections after each request at the end of application context
    @app.teardown_appcontext
    def close_db_connections(exception=None):
        # Close connection from get_db()
        db = g.pop('db', None)
        if db is not None and hasattr(db, 'client'):
            db.client.close()
        
        # Close connection from get_unittest_db() if it was used
        unittest_db = g.pop('unittest_db', None)
        if unittest_db is not None and hasattr(unittest_db, 'client'):
            unittest_db.client.close()

    # Load resources
    api.add_resource(modules.ModulesResource, "/modules", "/modules/<string:moduleName>")
    api.add_resource(logbook.LogbookResource, "/logbook", "/logbook/<string:_id>")
    api.add_resource(tests.TestsResource, "/tests", "/tests/<string:testName>")
    api.add_resource(
        test_payloads.TestPayloadsResource,
        "/test_payloads",
        "/test_payloads/<string:testpName>",
    )
    api.add_resource(cables.CablesResource, "/cables", "/cables/<string:name>")
    api.add_resource(crates.CratesResource, "/crates", "/crates/<string:name>")
    api.add_resource(
        cable_templates.CableTemplatesResource,
        "/cable_templates",
        "/cable_templates/<string:cable_type>",
    )
    api.add_resource(
        test_run.TestRunResource, "/test_run", "/test_run/<string:test_runName>"
    )
    api.add_resource(
        module_test.ModuleTestsResource,
        "/module_test",
        "/module_test/<string:moduleTestName>",
    )
    api.add_resource(
        session.SessionsResource, "/sessions", "/sessions/<string:sessionName>"
    )
    api.add_resource(
        module_test_analysis.ModuleTestAnalysisResource,
        "/module_test_analysis",
        "/module_test_analysis/<string:moduleTestAnalysisName>",
    )
    api.add_resource(BurninCyclesResource, '/burnin_cycles', '/burnin_cycles/<string:burninCycleName>')
    api.add_resource(IV_scans.IVScansResource, "/iv_scans", "/iv_scans/<string:IVScanId>")
    

    # Load blueprints
    app.register_blueprint(logbook_bp.bp)
    app.register_blueprint(cables_bp.bp)
    app.register_blueprint(add_run_bp.bp)
    app.register_blueprint(add_analysis_bp.bp)
    app.register_blueprint(webgui_bp.bp)
    app.register_blueprint(TBPS_blueprints.bp)
    
    # flask-pymongo blueprint for generic mongodb queries on modules
    @app.route("/generic_module_query", methods=['POST'])
    def generic_module_query():
        data = request.get_json()
        if "query" in data:
            query= data["query"]
            projection = data.get("projection", None)
        else:
            query = data
            projection = None
        if type(query) != dict:
            return jsonify({"error": "Invalid input, expected a JSON object"}), 400
        if data is None:
            return jsonify({"error": "No data provided"}), 400
        filtered_modules = mongo.db.modules.find(query, projection) 
    
        return jsonify([json_util.loads(json_util.dumps(module)) for module in filtered_modules]), 200

    return app



if __name__ == "__main__":
    app = create_app("prod")
    app.run()
