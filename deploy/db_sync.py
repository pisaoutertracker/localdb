import subprocess
import csv
import io
import requests
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import logging

CONFIG_NAME = "test"
load_dotenv(f"../config/{CONFIG_NAME}.env")

# Constants
API_URL = "http://192.168.0.45:5005"
MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.environ["MONGO_DB_NAME"]

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_rhapi_command(command):
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    return result.stdout

def parse_csv_output(output):
    csv_reader = csv.DictReader(io.StringIO(output))
    return list(csv_reader)

def get_central_modules():
    command = """python3 rhapi.py --url=https://cmsdca.cern.ch/trk_rhapi "select * from trker_cmsr.p9020 p where p.location LIKE 'IT-Pisa[INFN Pisa]'" --all --login -n"""
    output = run_rhapi_command(command)
    return parse_csv_output(output)

def get_local_modules():
    req = requests.get(f"{API_URL}/modules")
    return req.json()

def get_module_children(parent_name_label):
    command = f"""python3 rhapi.py --url=https://cmsdca.cern.ch/trk_rhapi "select * from trker_cmsr.trkr_relationships_v p where p.parent_name_label='{parent_name_label}'" -n --login"""
    output = run_rhapi_command(command)
    return parse_csv_output(output)

def get_module_identifier(module):
    if "SERIAL_NUMBER" in module:
        return module["SERIAL_NUMBER"]
    # elif "CHILD_SERIAL_NUMBER" in module:
    #     return module["CHILD_SERIAL_NUMBER"]
    elif "CHILD_COMPONENT" in module and "CHILD_ID" in module:
        return f"{module['CHILD_COMPONENT']}_{module['CHILD_ID']}"
    else:
        logging.warning(f"Unable to determine identifier for module: {module}")
        return None

def process_module(module, mongo_collection, is_child=False):
    module_identifier = get_module_identifier(module)
    if not module_identifier:
        logging.error(f"Skipping module due to missing identifier: {module}")
        return None

    logging.info(f"Processing {'child ' if is_child else ''}module {module_identifier}...")

    module_doc = {
        "moduleName": module_identifier,
        "details": module,
        "children": []
    }

    if not is_child and "NAME_LABEL" in module:
        # we should be able to get childrens of a child as well, not only of a module
        children = get_module_children(module["NAME_LABEL"])
        for child in children:
            # this is ok, but we should actually get the info from a query on the children table
            child_doc = process_module(child, mongo_collection, is_child=True)
            if child_doc:
                # change from child_doc["moduleName"] to child_doc["childName"]
                child_doc["childName"] = child_doc.pop("moduleName")
                module_doc["children"].append(child_doc)

    if not is_child:
        # Only insert top-level modules into MongoDB
        mongo_collection.update_one(
            {"moduleName": module_doc["moduleName"]},
            {"$set": module_doc},
            upsert=True
        )

    return module_doc

def main():
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    modules_collection = db["modules"]
    logging.info("Connected to MongoDB.")
    
    # remove all module from local
    # modules_collection.delete_many({})
    # print all modules
    for module in modules_collection.find():
        print(module)

    # Get modules from central and local DBs
    central_modules = get_central_modules()
    local_modules = get_local_modules()

    logging.info(f"Central DB has {len(central_modules)} modules.")
    logging.info(f"Local DB has {len(local_modules)} modules.")

    # Find missing modules
    local_module_names = set(module["moduleName"] for module in local_modules)
    missing_modules = [module for module in central_modules if module["SERIAL_NUMBER"] not in local_module_names]
    logging.info(f"Found {len(missing_modules)} missing modules.")

    # Process and insert missing modules
    processed_modules = 0
    for module in missing_modules:
        process_module(module, modules_collection)
        processed_modules += 1

    logging.info(f"Sync completed. {processed_modules} top-level modules added or updated.")

if __name__ == "__main__":
    main()