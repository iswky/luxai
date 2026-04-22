#!/bin/bash

echo "Starting Ollama..."
ollama serve &

if ollama list | grep -q "agent"; then
  echo "Model already exists"
else
  ollama create agent -f /models/Modelfile
fi

wait