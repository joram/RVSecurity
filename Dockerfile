# Multi-stage build for RV Security monitoring application
FROM node:16-slim AS reactbuild
WORKDIR /app/client
COPY client/package*.json ./
# Install with legacy peer deps for compatibility with d3 packages
RUN npm install --legacy-peer-deps
COPY client/ ./
RUN npm run build

# Constants copy stage - ensures client constants are synced to server
FROM python:3.11-slim AS constants
WORKDIR /app
COPY constantscopy.py ./
COPY client/src/constants.js ./client/src/
COPY server/constants.json ./server/
RUN python3 constantscopy.py client/src/constants.js server/constants.json

FROM python:3.11-slim AS reactbase
RUN python3 -m pip install --upgrade pip
RUN apt-get update && apt-get install build-essential -y
RUN apt-get update && apt-get install -y git

WORKDIR /app/rvsecurity/server
COPY server/setup.py .
RUN python3 -m pip install --use-pep517 .

FROM reactbase
WORKDIR /app/rvsecurity
# Copy the built React app from the build stage
COPY --from=reactbuild /app/client/build server/build/.
# Copy the synchronized constants from constants stage
COPY --from=constants /app/server/constants.json server/.
# Copy server files
COPY server/server.py server/.
COPY server/server_calcs.py server/.
# Copy Kasa power strip controller
COPY server/kasa_power_strip.py server/.
# Copy USB hub controller module
COPY usbhub_ascii.py server/.
#COPY server/mqttclient.py server/.
#COPY server/dgn_variables.json server/.

WORKDIR /app/rvsecurity/server

# Use JSON format for better signal handling
CMD ["python3", "server.py"]
