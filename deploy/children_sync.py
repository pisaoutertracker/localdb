import sys
import os
import logging
import requests
from pymongo import MongoClient
from jsonschema import validate, ValidationError

# Constants
# API_URL = "http://192.168.0.45:5000"
API_URL = "http://localhost:5005"
MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = os.environ["MONGO_DB_NAME"]

# Import common functions from db_sync
from db_sync import (
    get_children_of_modules, get_all_component_details,
    process_children, module_schema
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_local_modules():
    req = requests.get(f"{API_URL}/modules")
    return req.json()

def update_module_children(module, children_map, all_component_details, mongo_collection):
    module_id = module["moduleName"]
    if not module_id:
        logging.error(f"No moduleName for module: {module}")
        return

    children = children_map.get(module_id, [])
    
    # Only update the children field
    update_doc = {
        "children": process_children(children, all_component_details)
    }
    
    # check if the module already has the field "children", if the two fields are the same, then skip the update
    if module.get("children") == update_doc["children"]:
        logging.info(f"Children for module {module_id} are already up to date.")
        return
    
    # if children is empty, then set it to None
    if not update_doc["children"]:
        update_doc["children"] = None
        
        logging.info(f"Children for module {module_id} are empty, set to None. Maybe the module is not in the central DB? Check the module name.")
        

    # try:
        # Validate the full document
        # full_doc = {**module, **update_doc}
        # validate(instance=full_doc, schema=module_schema)
        
    mongo_collection.update_one(
        {"moduleName": module_id},
        {"$set": update_doc},
        upsert=True
    )
    logging.info(f"Updated children for module {module_id}")
    # except ValidationError as e:
    #     logging.error(f"Validation error for module {module_id}: {e}")
    #     raise

def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    modules_collection = db["modules"]
    logging.info("Connected to MongoDB.")

    # # clear the modules collection
    # modules_collection.delete_many({})
    # #     # as a test, add the addtional field "test1" to the module with moduleName "PS_26_05_IPG-00001"
    # # # create it if it doesn't exist
    # modules_collection.update_one(
    #     {"moduleName": "PS_26_IPG-10005"},
    #     {"$set": {"test1": "test1", "position": "cleanroom", "type": "module"}},
    #     upsert=True
    # )
    
    local_modules = get_local_modules()
    logging.info(f"Found {len(local_modules)} local modules to update.")

    # Get NAME_LABELs from local modules
    parent_labels = [m["moduleName"] for m in local_modules]
    
    # print the updated document
    # print(modules_collection.find_one({"moduleName": "PSU_26_05_IPG-00001"}))

    if not parent_labels:
        logging.error("No valid names found in local modules")
        return

    # Get children information from central DB
    children = get_children_of_modules(parent_labels)
    all_details = get_all_component_details(children)
    # Organize children by parent
    children_map = {}
    for child in children:
        parent = child["PARENT_NAME_LABEL"]
        children_map.setdefault(parent, []).append(child)

    # Update each local module's children
    for module in local_modules:
        update_module_children(module, children_map, all_details, modules_collection)

    logging.info("Children sync completed.")
    
    # print the updated document
    # print(modules_collection.find_one({"moduleName": "PSU_26_05_IPG-00001"}))
    # print the module with moduleName "PS_26_IPG-10005"
    # print(modules_collection.find_one({"moduleName": "PS_26_IPG-10005"}))

if __name__ == "__main__":
    main()
