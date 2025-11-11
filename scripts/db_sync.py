import subprocess
import csv
import io
import sys
import requests
from pymongo import MongoClient
import os
import logging
from jsonschema import validate, ValidationError
import argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.utils import module_schema

# Constants
API_URL = os.environ["API_URL"]
MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.environ["MONGO_DB_NAME"]

# Directory where rhapi.py is located (same as this script)
RHAPI_DIR = os.path.dirname(os.path.abspath(__file__))

PARTS_TABLES = {
    "PS Module": "p9020",
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
    # Change to the directory where rhapi.py is located
    result = subprocess.run(command, capture_output=True, text=True, shell=True, cwd=RHAPI_DIR)
    if result.returncode != 0:
        logging.error(f"Command failed: {command}\n{result.stderr}")
    return result.stdout

def parse_csv_output(output):
    csv_reader = csv.DictReader(io.StringIO(output))
    return list(csv_reader)

def get_central_modules(by_name=False, location="Pisa"):
    if by_name:
        command = """python3 rhapi.py --url=https://cmsdca.cern.ch/trk_rhapi "select * from trker_cmsr.p9020 p where p.name_label LIKE '%IBA%' OR p.name_label LIKE '%IPG%'" --all --login -n"""
    else:
        command = f"""python3 rhapi.py --url=https://cmsdca.cern.ch/trk_rhapi "select * from trker_cmsr.p9020 p where p.location LIKE 'IT-{location}[INFN {location}]'" --all --login -n"""
    output = run_rhapi_command(command)
    
    if not output or not output.strip():
        logging.error(f"No output received from central DB query. Command: {command}")
        return []
    
    try:
        modules = parse_csv_output(output)
        # Validate that we got actual module data
        if modules and len(modules) > 0:
            # Check if the first module has expected fields
            first_module = modules[0]
            if 'SERIAL_NUMBER' not in first_module or not first_module.get('SERIAL_NUMBER'):
                logging.error(f"Invalid module data received. First row: {first_module}")
                return []
        return modules
    except Exception as e:
        logging.error(f"Failed to parse central DB output: {e}")
        logging.error(f"Output was: {output[:500]}")  # Log first 500 chars
        return []

def get_local_modules(db_name):
    if db_name == "prod_db":
        req = requests.get(f"{API_URL}/modules")
        return req.json()

    else: # the api does not support other dbs than prod_db
        client = MongoClient(MONGO_URI)
        db = client[db_name]
        modules_collection = db["modules"]
        return list(modules_collection.find({}, {"_id": 0}))

def get_children_of_modules(parent_labels, PSROH=False):
    labels = "', '".join(parent_labels)
    if PSROH:
        command = f"""python3 rhapi.py --url=https://cmsdca.cern.ch/trk_rhapi "select * from trker_cmsr.trkr_relationships_v r where r.parent_serial_number in ('{labels}')" --all --login -n"""
    else:
        command = f"""python3 rhapi.py --url=https://cmsdca.cern.ch/trk_rhapi "select * from trker_cmsr.trkr_relationships_v r where r.parent_name_label in ('{labels}')" --all --login -n"""
    output = run_rhapi_command(command)
    return parse_csv_output(output)

def get_component_details_in_bulk(component_type, identifiers):
    if component_type not in PARTS_TABLES:
        logging.warning(f"Unknown component type: {component_type}. No details will be fetched.")
        return {}
    # print(component_type, identifiers)
    table = PARTS_TABLES[component_type]
    id_field = "NAME_LABEL" if component_type == "MaPSA" or component_type == "PS-s Sensor" or component_type == "PS-p Sensor" or component_type == "MPA Chip" else "SERIAL_NUMBER"
    ids = "', '".join(identifiers)
    # if component_type == "PS Read-out Hybrid":
    #     print(ids)
    command = f"""python3 rhapi.py --url=https://cmsdca.cern.ch/trk_rhapi "select * from trker_cmsr.{table} p where p.{id_field} in ('{ids}')" --all --login -n"""
    output = run_rhapi_command(command)
    details = parse_csv_output(output)
    if component_type == "MaPSA":
        # MaPSA has two children: PS-p Sensor and MPA Chip
        # for all MaPSA components, fetch the information of their children with a children query
        children = get_children_of_modules(identifiers)
        mapsa_children_map = {}
        for child in children:
            parent = child["PARENT_NAME_LABEL"]
            mapsa_children_map.setdefault(parent, []).append(child)
            
        children_details = get_all_component_details(children)
        for detail in details:
            cid = detail["NAME_LABEL"]
            detail["children"] = process_children(mapsa_children_map.get(cid, []), children_details)
            
    if component_type == "PS Read-out Hybrid":
        # PS Read-out Hybrid has a child: lpGBT Chip
        children = get_children_of_modules(identifiers, PSROH=True)
        for child in children:
            parent = child["PARENT_SERIAL_NUMBER"]
            for detail in details:
                if detail["SERIAL_NUMBER"] == parent:
                    # Store lpGBT as single child
                    detail["children"] = {"lpGBT": child}
                    break
            
    return {detail[id_field]: detail for detail in details}

def get_all_component_details(children):
    components_by_type = {}
    for child in children:
        ctype = child["CHILD_COMPONENT"]
        if ctype == "PS-s Sensor" or ctype == "MaPSA" or ctype == "PS-p Sensor" or ctype == "MPA Chip":
            cid = child["CHILD_NAME_LABEL"]
        else:
            cid = child["CHILD_SERIAL_NUMBER"]
        if not cid:
            raise ValueError(f"Missing identifier for child: {child}")
        if ctype and cid:
            components_by_type.setdefault(ctype, set()).add(cid)
    all_details = {}
    for ctype, ids in components_by_type.items():
        # print(ctype, ids)
        details = get_component_details_in_bulk(ctype, ids)
        all_details.update(details)
    return all_details


def process_children(children, all_component_details):
    processed = {}

    for child in children:
        ctype = child["CHILD_COMPONENT"]
        if ctype == "PS-s Sensor" or ctype == "MaPSA" or ctype == "PS-p Sensor" or ctype == "MPA Chip":
            cid = child["CHILD_NAME_LABEL"]
        else:
            cid = child["CHILD_SERIAL_NUMBER"]
        if not cid:
            logging.warning(f"Missing identifier for child: {child}")
            continue

        details = all_component_details.get(cid)
        # Check if details were found before proceeding
        if details is None:
            logging.warning(f"Details not found for component {cid} of type {ctype}. Skipping this child.")
            continue

        # Check for subcomponents only if details exist and have 'children' key
        if "children" in details: # Use direct check instead of .keys()
            # this means that the part has subcomponents, we move them on the same level as the parent to make them full children of the module
            for subcomponent in details["children"]:
                processed[subcomponent] = details["children"][subcomponent]
            del details["children"]
            
        # Create child_doc only if details were found (which is guaranteed by the check above)
        child_doc = {
            "childName": cid,
            "childType": ctype,
            "details": details,
        }
            
        # Handle multiple components of same type (MPA Chips in MaPSA)
        if ctype in processed:
            if isinstance(processed[ctype], list):
                processed[ctype].append(child_doc)
            else:
                # Convert to list if second instance found
                processed[ctype] = [processed[ctype], child_doc]
        else:
            processed[ctype] = child_doc

    return processed

def process_module(module, children_map, all_component_details, mongo_collection):
    """Process a NEW module - creates full document with all fields"""
    module_id = module.get("SERIAL_NUMBER")
    if not module_id:
        logging.error(f"No SERIAL_NUMBER for module: {module}")
        return
    children = children_map.get(module["NAME_LABEL"], [])
    module_doc = {
        "moduleName": module_id,
        "details": module,
        "children": process_children(children, all_component_details),
        "type": "module",
        "position": "cleanroom"
    }

    try:
        validate(instance=module_doc, schema=module_schema)
        mongo_collection.update_one(
            {"moduleName": module_id},
            {"$set": module_doc},
            upsert=True
        )
    except ValidationError as e:
        logging.error(f"Validation error for module {module_id}: {e}")
        raise

def update_existing_module(module, children_map, all_component_details, mongo_collection):
    """Update an EXISTING module - only updates details and children fields"""
    module_id = module.get("SERIAL_NUMBER")
    if not module_id:
        logging.error(f"No SERIAL_NUMBER for module: {module}")
        return
    
    children = children_map.get(module["NAME_LABEL"], [])
    
    # Only update details and children, preserve all other fields
    update_doc = {
        "details": module,
        "children": process_children(children, all_component_details)
    }
    
    try:
        # Validate the fields we're updating (create a minimal doc for validation)
        validation_doc = {
            "moduleName": module_id,
            "details": module,
            "children": process_children(children, all_component_details),
            "type": "module",
            "position": "cleanroom"
        }
        validate(instance=validation_doc, schema=module_schema)
        
        # Only update the specified fields, preserve everything else
        mongo_collection.update_one(
            {"moduleName": module_id},
            {"$set": update_doc}
        )
    except ValidationError as e:
        logging.error(f"Validation error for module {module_id}: {e}")
        raise

def get_modules_by_serial_numbers(serial_numbers):
    """Get module details from central DB by serial numbers (for modules that may have moved)"""
    if not serial_numbers:
        return []
    
    # Split into batches if too many (SQL query length limit)
    batch_size = 100 # adjust as needed
    all_modules = []
    
    for i in range(0, len(serial_numbers), batch_size):
        batch = serial_numbers[i:i+batch_size]
        serials = "', '".join(batch)
        command = f"""python3 rhapi.py --url=https://cmsdca.cern.ch/trk_rhapi "select * from trker_cmsr.p9020 p where p.serial_number in ('{serials}')" --all --login -n"""
        output = run_rhapi_command(command)
        
        if output and output.strip():
            try:
                modules = parse_csv_output(output)
                all_modules.extend(modules)
            except Exception as e:
                logging.error(f"Failed to parse modules by serial numbers: {e}")
    
    return all_modules

def main():
    # Add argument parsing
    parser = argparse.ArgumentParser(description='Sync module data from central to local DB')
    parser.add_argument('--by-name', action='store_true', help='Query modules by name pattern (IBA/IPG) instead of location')
    parser.add_argument('--location', default='Pisa', help='Location to filter modules (default: Pisa)')
    args = parser.parse_args()

    # Log all environment variables and configuration
    logging.info("="*80)
    logging.info("ENVIRONMENT CONFIGURATION:")
    logging.info("="*80)
    logging.info(f"API_URL: {API_URL}")
    logging.info(f"MONGO_URI: {MONGO_URI}")
    logging.info(f"DB_NAME: {DB_NAME}")
    logging.info(f"Arguments: by_name={args.by_name}, location={args.location}")
    logging.info(f"Python executable: {sys.executable}")
    logging.info(f"Working directory: {os.getcwd()}")
    logging.info("="*80)

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    modules_collection = db["modules"]
    logging.info(f"Connected to MongoDB at {MONGO_URI} on database {DB_NAME}.")
    
    # Step 1: Get modules from central DB by location/name
    logging.info(f"STEP 1/5: Querying central DB for modules in location/pattern...")
    central_modules_by_location = get_central_modules(by_name=args.by_name, location=args.location)
    
    # Step 2: Get all local modules
    logging.info(f"STEP 2/5: Fetching all modules from local DB...")
    local_modules = get_local_modules(DB_NAME)
    logging.info(f"Local DB has {len(local_modules)} modules.")
    
    # Step 3: Determine which modules to sync
    local_names = set(m["moduleName"] for m in local_modules)
    central_names_by_location = set(m["SERIAL_NUMBER"] for m in central_modules_by_location)
    
    # Modules to import (new ones from location query)
    missing = [m for m in central_modules_by_location if m["SERIAL_NUMBER"] not in local_names]
    # now the not missing ones are the ones to update
    existing = [m for m in central_modules_by_location if m["SERIAL_NUMBER"] in local_names]

    # Modules to update (existing in local, need fresh data from central)
    # Query central DB for ALL local modules (even if moved elsewhere)
    logging.info(f"STEP 3/5: Querying central DB for existing local modules (including moved ones)...")
    # will be local_names minus those already in central_names_by_location
    local_serials_not_in_Pisa = list(local_names - central_names_by_location)
    print(f"Local serials not in Pisa: {len(local_serials_not_in_Pisa), local_serials_not_in_Pisa}")
    modules_not_in_Pisa_from_central = get_modules_by_serial_numbers(local_serials_not_in_Pisa)
    
    logging.info(f"Central DB (by location) has {len(central_modules_by_location)} modules.")
    logging.info(f"New modules to import: {len(missing)}")
    logging.info(f"Existing modules to update: {len(modules_not_in_Pisa_from_central)+len(existing)}")\
    # print all lenghts for debugging
    print(f"Missing: {len(missing)}, Not in Pisa from central: {len(modules_not_in_Pisa_from_central)}, Existing: {len(existing)}")
    
    if missing:
        logging.info(f"New modules: {[m['SERIAL_NUMBER'] for m in missing]}")
    
    if not missing and not modules_not_in_Pisa_from_central and not existing:
        logging.info("No modules to process. Sync completed.")
        return
    
    # Step 4: Get children and component details for ALL modules (bulk query - efficient!)
    # Combine both new and existing for a single bulk query
    all_modules = missing + modules_not_in_Pisa_from_central + existing
    logging.info(f"STEP 4/5: Fetching children and component details from central DB for {len(all_modules)} modules...")
    parent_labels = [m["NAME_LABEL"] for m in all_modules]
    children = get_children_of_modules(parent_labels)
    all_details = get_all_component_details(children)
    
    # Organize children by parent
    children_map = {}
    for child in children:
        parent = child["PARENT_NAME_LABEL"]
        children_map.setdefault(parent, []).append(child)
    
    # Step 5: Process modules with progress tracking
    total_to_process = len(missing) + len(modules_not_in_Pisa_from_central) + len(existing)
    logging.info(f"STEP 5/5: Processing {total_to_process} modules ({len(missing)} new, {len(modules_not_in_Pisa_from_central)+len(existing)} updates)...")

    processed_count = 0
    
    # First, process NEW modules (full insert with all fields)
    for i, module in enumerate(missing, 1):
        module_id = module.get("SERIAL_NUMBER", "unknown")
        logging.info(f"Progress: {i}/{total_to_process} - Importing NEW module {module_id}")
        process_module(module, children_map, all_details, modules_collection)
        processed_count += 1
    
    # Second, update EXISTING modules (only details and children fields)
    for i, module in enumerate(modules_not_in_Pisa_from_central + existing, len(missing) + 1):
        module_id = module.get("SERIAL_NUMBER", "unknown")
        logging.info(f"Progress: {i}/{total_to_process} - Updating EXISTING module {module_id}")
        update_existing_module(module, children_map, all_details, modules_collection)
        processed_count += 1
    
    logging.info(f"Sync completed successfully. Imported {len(missing)} new module(s), updated {len(modules_not_in_Pisa_from_central)+len(existing)} existing module(s).")

if __name__ == "__main__":
    main()
