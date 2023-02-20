#FROM python:3.10-slim-buster
#RUN python3 -m pip install --upgrade pip
#RUN apt-get update && apt-get install build-essential -y
#COPY setup.py .
#RUN python3 -m pip install --use-pep517 .
FROM react-base

WORKDIR /app/rvsecurity

COPY server/build server/build/.
COPY server/server.py server/.
COPY server/mqttclient.py server/.
COPY server/setup.py server/.
COPY server/dgn_variables.json server/.

WORKDIR /app/rvsecurity/server

#RUN python3 -m pip install --use-pep517 .[dev]
CMD python3 server.py
