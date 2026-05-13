#!/bin/bash

# start ollama server
ollama serve &

# wait for ollama to start
echo "waiting for ollama server..."
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done
echo "ollama server is up"

# pull gemma if needed or keep alive
# ollama pull gemma

# keep the container running
wait
