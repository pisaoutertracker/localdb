import sys
import os
import io
import subprocess
import csv
import logging
import requests
from pymongo import MongoClient
from jsonschema import validate, ValidationError

from db_sync import run_rhapi_command, parse_csv_output, get_local_modules

# Constants
API_URL = "http://192.168.0.45:5000"
# API_URL = "http://localhost:5005"
MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.environ["MONGO_DB_NAME"]

def get_all_central_modules(names):
    command =  f"""python3 rhapi.py --url=https://cmsdca.cern.ch/trk_rhapi "select * from trker_cmsr.p9020 p where p.name_label IN ('{names}')" --all --login -n"""
    out = run_rhapi_command(command)
    return parse_csv_output(out)
    
def process_module(module_name, location, modules_collection):
    
    module_doc = {
        "Current Center": location,
    }
        
    try:
        modules_collection.update_one(
            {"moduleName": module_name},
            {"$set": module_doc},
            upsert=True
        )
    except ValidationError as e:
        logging.error(f"Validation error for module {module_name}: {e}")
        raise

def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    modules_collection = db["modules"]
    logging.info(f"Connected to MongoDB at {MONGO_URI} on database {DB_NAME}.")
    
    local_modules = get_local_modules()
    logging.info(f"Found {len(local_modules)} local modules to update.")
    print("Local modules:", local_modules[0])
    
    # Get NAME_LABELs from local modules
    parent_labels = [f"{m['moduleName']}" for m in local_modules]
    formatted_module_names = "', '".join(module_name.replace("'", "''") for module_name in parent_labels) # Basic SQL injection prevention for names
    print(f"Formatted module names for query: {formatted_module_names}")
    all_central_modules = get_all_central_modules(formatted_module_names)
    print(f"Found {len(all_central_modules)} central modules matching local modules.")

    for name in parent_labels:
        if name not in [m['NAME_LABEL'] for m in all_central_modules]:
            logging.warning(f"Module {name} not found in central modules. Setting to Unknown.")
        try:
            central_module_location = next((m['LOCATION'] for m in all_central_modules if m['NAME_LABEL'] == name), "Unknown")
            logging.info(f"Processing module {name} with location {central_module_location}.")
            process_module(name, central_module_location, modules_collection)
        except Exception as e:
            logging.error(f"Error processing module {name}: {e}")
            continue
    client.close()
        

    logging.info("Location sync completed.")
    
if __name__ == "__main__":
    main()
