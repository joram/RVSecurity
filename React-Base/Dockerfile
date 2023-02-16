FROM python:3.10-slim-buster
RUN python3 -m pip install --upgrade pip
RUN apt-get update && apt-get install build-essential -y
COPY setup.py .
RUN python3 -m pip install --use-pep517 .
