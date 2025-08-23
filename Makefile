setup:
# do this once to setup the environment
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	cd server; ../venv/bin/pip install .[dev]
	cd client; npm install --legacy-peer-deps

server_start:
# do this when working on the server.py code
# start_server in a separate cmd window; always first
	cd server; ../venv/bin/python ./server.py

client_start:
# Only need to make client_start if changing the client code
# start_Client in a separate cmd window (note: server must be started first)
	cd client; npm start

constants_copy:
# Copies constants in xx.js file in client to xx.json file in server
# Assumes very simple JS file of just constants
# Example format:
#	export const IPADDR= "192.168.2.177";
#	export const PORT= "8000";
#	...
	python3 constantscopy.py client/src/constants.js server/constants.json


build: constants_copy
#this is only needed when you're ready to deploy locally (non-Docker)
	cd client; npm run-script build
	cd client; rm -Rf ../server/build; mv ./build ../server/


