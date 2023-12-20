#!/bin/bash

API_URL="http://192.168.0.45:5005/sessions"

curl -X GET -H "Content-Type: application/json" $API_URL

SESSION_ENTRY='{
    "timestamp": "2023-11-03T14:21:29",
    "operator": "John Doe",
    "description": "I tried to insert PS_88 and PS_44. and also PS_1.",
    "modulesList": ["PS_1","PS_2"]
}'

curl -X POST -H "Content-Type: application/json" -d "$SESSION_ENTRY" "$API_URL"
