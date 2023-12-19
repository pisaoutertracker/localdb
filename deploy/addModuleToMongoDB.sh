#!/bin/bash

API_URL="http://192.168.0.45:5005/modules"

curl -X GET -H "Content-Type: application/json" $API_URL

# Define the data to update as a JSON string
##Perugia 102
UPDATED_MODULE1='{
    "moduleName": "PS_26_05-IBA_00102",
    "position": "lab",
    "logbook": {"entry": "Initial setup"},
    "local_logbook": {"entry": "Local setup"},
    "ref_to_global_logbook": [],
    "status": "operational",
    "overall_grade": "A",
    "hwId": 2762808384,
    "tests": []
}
'
##Perugia 103
UPDATED_MODULE2='{
    "moduleName": "PS_26_10-IPG_00103",
    "position": "lab",
    "logbook": {"entry": "Initial setup"},
    "local_logbook": {"entry": "Local setup"},
    "ref_to_global_logbook": [],
    "status": "operational",
    "overall_grade": "A",
    "hwId": 749637543,
    "tests": []
}
'
##Bari 102
UPDATED_MODULE3='{
    "moduleName": "PS_26_05-IPG_00102",
    "position": "lab",
    "logbook": {"entry": "Initial setup"},
    "local_logbook": {"entry": "Local setup"},
    "ref_to_global_logbook": [],
    "status": "operational",
    "overall_grade": "A",
    "hwId": 3962125297,
    "tests": []
}
'

echo $UPDATED_MODULE1

# Send a PUT request using curl

curl -X POST -H "Content-Type: application/json" -d "$UPDATED_MODULE1" "$API_URL"
curl -X POST -H "Content-Type: application/json" -d "$UPDATED_MODULE2" "$API_URL"
curl -X POST -H "Content-Type: application/json" -d "$UPDATED_MODULE3" "$API_URL"