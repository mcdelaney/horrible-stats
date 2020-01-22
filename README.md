# Scripts and Utilities for Managing the Worst Server in DCS: http://ahorribleserver.com

## Overview
The horrible-stats project provides a web-based statistic and diagnostic service
for server members.  To accomplish this, it includes the following:
- A log-replication batch file to be run on the instance hosting the mission, located
at `scripts/log-copier.bat`.  Once running, on a 5 minute interval, the script checks
for new Tacview, SlMod Mission Stat, and FrameTimeExport logs, and replicates them
to a Google-Cloud-Storage (GCS) bucket: `gs://horrible-stats/`.
- A Postgres database serving as the registrar for gcs-file processing, and
datastore for processed records.
- A Lua-to-Python translation program, allowing the output of SlMod Lua stats-files
to be converted python dictionaries, suitable for storage as JSON in Postgres.
We use `Lupa` to accomplish this dark magic.
- A `fastapi` web-server.  All views are rendered server-side with Jinja templates.
Currently, the following endpoints are available:
  - `/`: Summary statistics for all server members.
  - `/weapons`: Weapon efficiency statistics.
  - `/survivability`: Kill/Loss statistics.
  - `/check_db_stats`: Triggers a background task to reconcile available files in GCS
  with the database, processing new files if any are found.
  - `/tacview`: NOT YET IMPLEMENTED.

## Development

### Requirements:
- Docker: https://hub.docker.com/editions/community
- Docker-compose (I _think_ this comes bundled with regular docker now.)
- A GCS service account key.  
The key should be placed in the project root, and titled `dcs-storage-gcs.json`.
Contact @mcdelaney for access instructions.

Local development requires Docker and docker-compose.  
Once the docker daemon is running, from the project directory, simply run:
```
docker-compose up --build
```
This will build images and launch the database and app containers serving the site at `0.0.0.0:8000`.
By default, the app will load in live-reload mode with the current directory mounted
as a volume.  This means that changes made to the project code will trigger a hot-reload
of the local site in real-time, enabling rapid iteration.

### Testing
Tests!
We should have them!
Because I am lazy, we don't have any now!
When we do, we will use pytest!
This is a very bad situation!

### Deploying
Production consists of a GCS hosted k8s cluster.  Deployments are not currently automated.
When you are ready to push new code, run `./scripts/local-build-and-redeploy.sh`.
This will literally push to prod, right now.  Don't do this unless you are sure. But don't worry too much, because I haven't given anyone else credentials to authenticate against the cluster...
I will automate this process in the future.
