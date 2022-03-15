
setup:
	cd api; pip install .[dev]
	cd app; npm install

build:
	cd app; npm build
	mv ./build ../api/

start_api:
	cd api; ./server.py

start_app:
	cd app; npm start


