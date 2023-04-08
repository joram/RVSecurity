FROM python:3.10-slim-buster AS reactbase
RUN python3 -m pip install --upgrade pip
RUN apt-get update && apt-get install build-essential -y

WORKDIR /app/rvsecurity/server
COPY server/setup.py .
RUN python3 -m pip install --use-pep517 .

FROM reactbase
WORKDIR /app/rvsecurity
COPY server/build server/build/.
COPY server/server.py server/.
COPY server/server_calcs.py server/.
COPY server/mqttclient.py server/.
COPY server/dgn_variables.json server/.
COPY server/constants.json server/.

WORKDIR /app/rvsecurity/server

#ENV UVICORN_PORT=80
#RUN python3 -m pip install --use-pep517 .[dev]
CMD python3 server.py
