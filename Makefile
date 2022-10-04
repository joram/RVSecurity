
setup:
	cd api; pip install .[dev]
	sudo npm install -g npm@latest
	cd app; npm install

start_server:
	cd api; ./server.py
# do this when working on the server.py co
start_client:
	cd app; npm start

# Only need to start_app if changing the client code

build:
#	cd app; npx browserslist@latest --update-db
	cd app; export NODE_OPTIONS=--openssl-legacy-provider; npm run-script build
	rm -r ./api/build
	cd app; mv ./build ../api/
# only requried for client code and want to merge with server


