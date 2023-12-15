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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "utils")))
# make it so that utils can be imported from anywhere
from .utils import get_db, CustomJSONProvider

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
)
from .blueprints import logbook_bp, cables_bp, test_run_bp, add_analysis_bp


def create_app(config_name):
    app = Flask(__name__)

    load_dotenv(f"../config/{config_name}.env")
    app.config["MONGO_URI"] = os.environ["MONGO_URI"]
    app.config["MONGO_DB_NAME"] = os.environ["MONGO_DB_NAME"]
    app.config["TESTING"] = os.environ["TESTING"]
    api = Api(app)
    app.json = CustomJSONProvider(app)

    # Load resources
    api.add_resource(modules.ModulesResource, "/modules", "/modules/<string:moduleID>")
    api.add_resource(logbook.LogbookResource, "/logbook", "/logbook/<string:_id>")
    api.add_resource(tests.TestsResource, "/tests", "/tests/<string:testID>")
    api.add_resource(
        test_payloads.TestPayloadsResource,
        "/test_payloads",
        "/test_payloads/<string:testpID>",
    )
    api.add_resource(cables.CablesResource, "/cables", "/cables/<string:name>")
    api.add_resource(crates.CratesResource, "/crates", "/crates/<string:name>")
    api.add_resource(
        cable_templates.CableTemplatesResource,
        "/cable_templates",
        "/cable_templates/<string:cable_type>",
    )
    api.add_resource(
        test_run.TestRunResource, "/test_run", "/test_run/<string:test_runID>"
    )
    api.add_resource(
        module_test.ModuleTestsResource,
        "/module_test",
        "/module_test/<string:moduleTestKey>",
    )
    api.add_resource(
        session.SessionsResource, "/sessions", "/sessions/<string:sessionKey>"
    )
    api.add_resource(
        module_test_analysis.ModuleTestAnalysisResource,
        "/module_test_analysis",
        "/module_test_analysis/<string:moduleTestAnalysisKey>",
    )

    # Load blueprints
    app.register_blueprint(logbook_bp.bp)
    app.register_blueprint(cables_bp.bp)
    app.register_blueprint(test_run_bp.bp)
    app.register_blueprint(add_analysis_bp.bp)

    return app


if __name__ == "__main__":
    app = create_app("prod")
    app.run()
