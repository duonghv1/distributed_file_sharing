#!/bin/bash

# Define the log file path
LOG_FILE="output.log"

# Redirect stdout and stderr to the log file
exec > >(tee -a ${LOG_FILE} )
exec 2>&1

# Prompt user for the number of nodes
read -p "Enter the number of nodes you want to start: " NUM_NODES

read -p "Enter your python command (ex: python3, py, python): " PYTHON

# Check if the input is valid
if ! [[ "$NUM_NODES" =~ ^[0-9]+$ ]]; then
    echo "Error: Please enter a valid number."
    read -p "Enter the number of nodes you want to start: " NUM_NODES
fi

SERVER_BASE_PORT=12345
BASE_DIR="./files"


# Execute the Python script with provided arguments
for ((i=0; i<=$NUM_NODES; i++)); do
    PORT=$((SERVER_BASE_PORT + i))
    DIR="$BASE_DIR_$PORT"
    $PYTHON FileServer.py --port="$PORT" --base_dir="$DIR" &
done

