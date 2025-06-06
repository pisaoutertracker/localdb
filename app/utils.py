from flask import current_app, g
from json import JSONEncoder
from pymongo import MongoClient
from bson import ObjectId
import json
import os
from flask.json.provider import JSONProvider
import re
from bson import json_util
import datetime


def get_db():
    # the current app mongo uri contains the database name after the /, we need to drop it
    mongo_uri = current_app.config["MONGO_URI"] # something like mongodb://localhost:27017/mydatabase
    # want to drop /mydatabase
    # use regex to find the last / and drop everything after it
    if mongo_uri.endswith('/'):
        mongo_uri = mongo_uri[:-1]
    if 'MONGO_DB_NAME' in current_app.config:
        mongo_uri = mongo_uri.rsplit('/', 1)[0]
    if 'db' not in g:
        g.db = MongoClient(mongo_uri)[current_app.config["MONGO_DB_NAME"]]
    return g.db

def get_unittest_db():
        # the current app mongo uri contains the database name after the /, we need to drop it
    if 'MONGO_DB_NAME' in current_app.config:
        mongo_uri = current_app.config["MONGO_URI"]
    if mongo_uri.endswith('/'):
        mongo_uri = mongo_uri[:-1]
    if 'MONGO_DB_NAME' in current_app.config:
        mongo_uri = mongo_uri.rsplit('/', 1)[0]
    if 'unittest_db' not in g:
        g.unittest_db = MongoClient(mongo_uri)["unittest_db"]
    return g.unittest_db

# define regexps to select module ids, crateid, etc
def regExpPatterns(s):
    mapRE = {"ModuleID": "PS_[0-9A-Z_\\-]+"}
    if s in mapRE.keys():
        return  mapRE[s]
    else:
        return None

def findModuleIds(istring):
    return re.findall(regExpPatterns("ModuleID"),istring)

class CustomJSONEncoder(JSONEncoder):
    """
    A custom JSON encoder that converts MongoDB ObjectIds to strings.
    and datetime objects to isoformat

    This encoder is used to ensure that MongoDB ObjectIds are properly serialized
    when returning JSON responses from a Flask REST API.
    """

    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)


class CustomJSONProvider(JSONProvider):
    """
    A custom JSON provider that uses a custom JSON encoder to serialize objects.
    """

    def dumps(self, obj, **kwargs):
        return json.dumps(obj, **kwargs, cls=CustomJSONEncoder)

    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)
    

# load schemas
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
schema_path = os.path.join(base_dir, "schemas", "all_schemas.json")
with open(schema_path, "r") as f:
    all_schemas = json.load(f)

module_schema = all_schemas["module"]
logbook_schema = all_schemas["logbook"]
current_cabling_map_schema = all_schemas["CurrentCablingMap"]
connection_snapshot_schema = all_schemas["ConnectionSnapshot"]
tests_schema = all_schemas["tests"]
cables_schema = all_schemas["cables"]
cable_templates_schema = all_schemas["cable_templates"]
testpayload_schema = all_schemas["testpayload"]
test_run_schema = all_schemas["testRun"]
module_test_schema = all_schemas["moduleTest"]
session_schema = all_schemas["session"]
module_test_analysis_schema = all_schemas["moduleTestAnalysis"]
burnin_cycles_schema = all_schemas["BurninCycles"]
iv_scans_schema = all_schemas["IVScans"]