from flask import current_app, g
from json import JSONEncoder
from pymongo import MongoClient
from bson import ObjectId
import json
from flask.json.provider import JSONProvider
import re
from bson import json_util
import datetime


def get_db():
    if 'db' not in g:
        g.db = MongoClient(current_app.config["MONGO_URI"])[current_app.config["MONGO_DB_NAME"]]
    return g.db

# define regexps to select module ids, crateid, etc
def regExpPatterns(s):
    mapRE = {"ModuleID": "PS_\\d+"}
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
with open("../schemas/all_schemas.json", "r") as f:
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