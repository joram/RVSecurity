#FROM python:3.10-slim-buster
#RUN python3 -m pip install --upgrade pip
FROM react-base

WORKDIR /app/rvsecurity

COPY server/build server/build/.
COPY server/server.py server/.
COPY server/mqttwebclient.py server/.
COPY server/setup.py server/.
COPY server/dgn_variables.json server/.

WORKDIR /app/rvsecurity/server

#RUN python3 -m pip install --use-pep517 .[dev]
CMD python3 server.py
