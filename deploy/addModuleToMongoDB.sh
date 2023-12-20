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

#add these two as well: 
# -Bari01(lgbt v0) :       PS_40_05-IBA_00001
# LpGBT: 1216106599
UPDATED_MODULE4='{
    "moduleName": "PS_40_05-IBA_00001",
    "position": "lab",
    "logbook": {"entry": "Initial setup"},
    "local_logbook": {"entry": "Local setup"},
    "ref_to_global_logbook": [],
    "status": "operational",
    "overall_grade": "A",
    "hwId": 1216106599,
    "tests": []
}
'

# -Bari04(lgbt v1) :       PS_26_05-IBA_00004
# LpGBT: 3142643356
UPDATED_MODULE5='{
    "moduleName": "PS_26_05-IBA_00004",
    "position": "lab",
    "logbook": {"entry": "Initial setup"},
    "local_logbook": {"entry": "Local setup"},
    "ref_to_global_logbook": [],
    "status": "operational",
    "overall_grade": "A",
    "hwId": 3142643356,
    "tests": []
}
'

echo $UPDATED_MODULE1

# Send a PUT request using curl

curl -X POST -H "Content-Type: application/json" -d "$UPDATED_MODULE1" "$API_URL"
curl -X POST -H "Content-Type: application/json" -d "$UPDATED_MODULE2" "$API_URL"
curl -X POST -H "Content-Type: application/json" -d "$UPDATED_MODULE3" "$API_URL"
curl -X POST -H "Content-Type: application/json" -d "$UPDATED_MODULE4" "$API_URL"
curl -X POST -H "Content-Type: application/json" -d "$UPDATED_MODULE5" "$API_URL"