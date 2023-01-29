
setup:
	cd api; pip install .[dev]
#	sudo npm install -g npm@latest
	cd app; npm install

start_server:
	cd api; ./server.py
# do this when working on the server.py co
start_client:
	cd app; npm start

# Only need to start_app if changing the client code

build:
	cd app; npm run-script build
	cd app; rm -Rf ../api/build; mv ./build ../api/


