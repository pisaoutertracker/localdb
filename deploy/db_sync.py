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
#API_URL = "http://192.168.0.45:5005"
API_URL = "http://localhost:5000"
MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.environ["MONGO_DB_NAME"]

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
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
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
    return parse_csv_output(output)

def get_local_modules():
    req = requests.get(f"{API_URL}/modules")
    return req.json()

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

def main():
    # Add argument parsing
    parser = argparse.ArgumentParser(description='Sync module data from central to local DB')
    parser.add_argument('--by-name', action='store_true', help='Query modules by name pattern (IBA/IPG) instead of location')
    parser.add_argument('--location', default='Pisa', help='Location to filter modules (default: Pisa)')
    args = parser.parse_args()

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    modules_collection = db["modules"]
    logging.info(f"Connected to MongoDB at {MONGO_URI} on database {DB_NAME}.")
    
    # modules_collection.delete_many({})
    
    central_modules = get_central_modules(by_name=args.by_name, location=args.location)
    local_modules = get_local_modules()
    
    # print(local_modules)
    
    logging.info(f"Central DB has {len(central_modules)} modules.")
    logging.info(f"Local DB has {len(local_modules)} modules.")
    
    local_names = set(m["moduleName"] for m in local_modules)
    missing = [m for m in central_modules if m["SERIAL_NUMBER"] not in local_names]
    logging.info(f"Missing modules: {len(missing)}")
    logging.info([m["SERIAL_NUMBER"] for m in missing])
    # restrict to a single module
    # missing = [m for m in central_modules if m["SERIAL_NUMBER"] == "PS_16_10_IPG-00005"]
    # logging.info([m["SERIAL_NUMBER"] for m in missing])
    
    parent_labels = [m["NAME_LABEL"] for m in missing]
    children = get_children_of_modules(parent_labels)
    # print(children)
    
    all_details = get_all_component_details(children)
    
    # Organize children by parent
    children_map = {}
    for child in children:
        parent = child["PARENT_NAME_LABEL"]
        children_map.setdefault(parent, []).append(child)
    
    for module in missing:
        process_module(module, children_map, all_details, modules_collection)
    
    logging.info("Sync completed.")

if __name__ == "__main__":
    main()
