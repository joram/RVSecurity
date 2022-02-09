
setup:
	cd api; pip install .[dev]
	cd app; yarn install

build:
	cd app; yarn build
	mv ./build ../api/

start_api:
	cd api; uvicorn server:app --reload

start_app:
	cd app; yarn start


