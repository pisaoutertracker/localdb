# localdb

The localdb RESTful API written in Flask for handling requests to the MongoDB Pisa OT Tracker DB


# update version (as root)

```
cd ~/serverconfig/localdb
git pull
cd ~/serverconfig

# stop and restart the docker container
podman-compose --env ../pisaoutertracker.env down localdb 
podman-compose --env ../pisaoutertracker.env up localdb -d

#check logs to see that it started
podman-compose --env ../pisaoutertracker.env logs localdb
```

