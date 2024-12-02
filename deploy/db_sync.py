import subprocess
import csv
import io
import requests
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import logging


# Constants
#API_URL = "http://192.168.0.45:5005"
API_URL = "http://localhost:5000"
MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.environ["MONGO_DB_NAME"]

PARTS_TABLES = {
    "PS-s Sensor": "p1160",
    "PS Baseplate": "p11820",
    "PS Front-end Hybrid": "p6740",
    "PS Read-out Hybrid": "p6760",
    "PS Power Hybrid": "p10200",
    "VTRx+": "p15800",
    "VTRx": "p4260",
    "MaPSA": "p11480",
    # and its two children:
    "PS-p Sensor": "p1200",
    "MPA Chip": "p11420"
}

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

def get_component_details(component_type, serial_number):
    if component_type not in PARTS_TABLES:
        logging.warning(f"Unknown component type: {component_type}")
        return None
    table = PARTS_TABLES[component_type]
    command = f"""python3 rhapi.py --url=https://cmsdca.cern.ch/trk_rhapi "select * from trker_cmsr.{table} p where p.serial_number='{serial_number}'" --all --login -n"""
    output = run_rhapi_command(command)
    details = parse_csv_output(output)
    return details[0] if details else None

def get_module_identifier(module):
    if "SERIAL_NUMBER" in module:
        return module["SERIAL_NUMBER"]
    elif "CHILD_SERIAL_NUMBER" in module and module["CHILD_SERIAL_NUMBER"]:
        return module["CHILD_SERIAL_NUMBER"]
    elif "CHILD_NAME_LABEL" in module and module["CHILD_NAME_LABEL"]:
        return module["CHILD_NAME_LABEL"]
    elif "CHILD_COMPONENT" in module and "CHILD_ID" in module:
        return f"{module['CHILD_COMPONENT']}_{module['CHILD_ID']}"
    else:
        logging.warning(f"Unable to determine identifier for module: {module}")
        return None

def get_component_details(component_type, identifier):
    if component_type not in PARTS_TABLES:
        logging.warning(f"Unknown component type: {component_type}")
        return None
    table = PARTS_TABLES[component_type]
    # Use NAME_LABEL for MaPSA, SERIAL_NUMBER for others
    id_field = "name_label" if component_type == "MaPSA" else "serial_number"
    command = f"""python3 rhapi.py --url=https://cmsdca.cern.ch/trk_rhapi "select * from trker_cmsr.{table} p where p.{id_field}='{identifier}'" --all --login -n"""
    output = run_rhapi_command(command)
    details = parse_csv_output(output)
    return details[0] if details else None

def process_children(parent_name_label):
    children = get_module_children(parent_name_label)
    processed_children = []
    for child in children:
        child_type = child["CHILD_COMPONENT"]
        child_identifier = child["CHILD_SERIAL_NUMBER"] if child["CHILD_SERIAL_NUMBER"] else child["CHILD_NAME_LABEL"]
        logging.debug("Child type: ", child_type)
        logging.debug("Child identifier: ", child_identifier)
        if not child_identifier:
            logging.warning(f"Skipping child due to missing identifier: {child}")
            continue
        child_details = get_component_details(child_type, child_identifier)
        if child_details:
            child_doc = {
                "childName": child_identifier,
                "childType": child_type,
                "details": child_details,
                "children": []
            }
            if child_type == "MaPSA":
                print("Processing MaPSA children")
                child_doc["children"] = process_children(child_identifier)
            processed_children.append(child_doc)
    return processed_children

def process_module(module, mongo_collection):
    module_identifier = get_module_identifier(module)
    if not module_identifier:
        logging.error(f"Skipping module due to missing identifier: {module}")
        return None

    logging.info(f"Processing module {module_identifier}...")

    module_doc = {
        "moduleName": module_identifier,
        "details": module,
        "children": []
    }

    if "NAME_LABEL" in module:
        module_doc["children"] = process_children(module["NAME_LABEL"])

    # Insert top-level module into MongoDB
#    mongo_collection.update_one(
#        {"moduleName": module_doc["moduleName"]},
#        {"$set": module_doc},
#        upsert=True
#    )
    
    return module_doc

def main():
    # Connect to MongoDB
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    modules_collection = db["modules"]
    logging.info("Connected to MongoDB.")
    
    # remove all documents from the collection
    # modules_collection.delete_many({})
    # Print all modules
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
