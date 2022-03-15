# RVSecurity

## Setup Dev Environment
- move to location where you want the clone to exist
- `git clone git@github.com:joram/RVSecurity.git`


now you have a folder of code called `RVSecurity`

## Want to Commit to Cloud Changes
- `git status` to list the changed files (in red)
- `git add .` to stage them all
- `git status` will list all staged changes (all in green)
- `git commit -m "<descriptive message>"` to create a commit
- `git push origin main` Push all commits into Cloud main

## Want to pull down changes
- `git pull origin main'  Brings down all Cloud main cahnges

## React and API Server commands
- app/App.jsx file contains most of the React code
- api/server.py contains the server code
- to rebuild compiled versoin of the app: 'make build'
  - `npm build`  in the app folder
  - copies the build folder from app to api
- to start the server (assuming make works) `make start_api`
- to start the app (assuming make works) `make start_app`
- after develeopment loop when ready to deploy: 'make build' (don't foget to commit to cloud)
- Webpage location:  http://localhost:3000
- api documentation page: http://localhost:8000/docs


## Terminology
- API - code that runs on the webpage server
- Applicaiton - web code that runs on the persons computer hitting the web page 





