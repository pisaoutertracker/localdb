# localdb

The localdb RESTful API written in Flask for handling requests to the MongoDB Pisa OT Tracker DB


# update version (as root)

cd ~/serverconfig/localdb
git pull
cd ~/serverconfig

podman-compose --env ../pisaoutertracker.env down localdb 
podman-compose --env ../pisaoutertracker.env up localdb 

podman-compose --env ../pisaoutertracker.env down logs


