
setup:
# do this once to setup the environment
	cd api; pip install .[dev]
	$NVM_DIR/nvm use default
	cd app; npm install

server_start:
# do this when working on the server.py code
# start_server in a separate cmd window; always first
	cd api; ./server.py

client_start:
# Only need to start_app if changing the client code
# start_Client in a separate cmd window (note: server must be started first)
	cd app; npm start


build:
#this is only needed whey you're ready to deploy
	cd app; npm run-script build
	cd app; rm -Rf ../api/build; mv ./build ../api/


