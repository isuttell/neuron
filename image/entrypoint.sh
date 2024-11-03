#!/bin/bash
set -e

./start_all.sh
./novnc_startup.sh

python http_server.py > /tmp/server_logs.txt 2>&1 &

python -m neuron_server > /tmp/stdout.log &

echo "Agent is ready and at <http://localhost:5000>"

# Keep the container running
tail -f /dev/null
