
setup:
# do this once to setup the environment
	cd server; python3 -m pip install .[dev]
	#$NVM_DIR/nvm use default
	#cd client; npm install

server_start:
# do this when working on the server.py code
# start_server in a separate cmd window; always first
	cd server; ./server.py

client_start:
# Only need to make client_start if changing the client code
# start_Client in a separate cmd window (note: server must be started first)
	cd client; npm start


build:
#this is only needed whey you're ready to deploy
	cd client; npm run-script build
	cd client; rm -Rf ../server/build; mv ./build ../server/


