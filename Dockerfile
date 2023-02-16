#FROM python:3.10-slim-buster
#RUN python3 -m pip install --upgrade pip
FROM buster310

WORKDIR /app/rvsecurity

COPY server/build server/.
COPY server/server.py server/.
COPY server/mqttwebclient.py server/.
COPY server/setup.py server/.
COPY server/dgn_variables.json server/.

WORKDIR /app/rvsecurity/server

#RUN python3 -m pip install --use-pep517 .[dev]
#RUN python3 -m pip install "fastapi[all]" .
#RUN python3 -m pip install pydantic
#RUN python3 -m pip install starlette
CMD python3 server.py
