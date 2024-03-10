#!/bin/bash

# Redirect stdout and stderr to the log file
exec > >(tee -a ${LOG_FILE} )
exec 2>&1

LOG_FILE="output.log"
SERVER_BASE_PORT=12345
BASE_DIR="./files"
TEST_FILE="test.pdf"
TEST_FILE_LINK="https://www.fusd1.org/cms/lib/AZ01001113/Centricity/Domain/1385/harry%20potter%20chapter%201.pdf"


# Prompt user for the number of nodes
read -p "Enter the number of nodes you want to start: " NUM_NODES
read -p "Enter your python command (ex: python3, py, python): " PYTHON

# Check if the input is valid
if ! [[ "$NUM_NODES" =~ ^[0-9]+$ ]]; then
    echo "Error: Please enter a valid number."
    read -p "Enter the number of nodes you want to start: " NUM_NODES
fi



run_file_server() {
    local NUM_NODES="$1"
    local SERVER_BASE_PORT="$2"
    local BASE_DIR="$3"
    local PYTHON="$4"

    for ((i=0; i<=$NUM_NODES; i++)); do
        local PORT=$((SERVER_BASE_PORT + i))
        local DIR="$BASE_DIR/$PORT"

        # Check if directory exists
        if [ -d "$DIR" ]; then
            # If directory exists, delete its content
            echo "Deleting all existing content in directory: $DIR"
            rm -rf "${DIR}/"*
        else
            # Create the directory
            mkdir -p "$DIR"
        fi

        # Copy the file into the directory if it's not the base directory
        if [ "$DIR" != "$BASE_DIR/$SERVER_BASE_PORT" ]; then
            cp "$TEST_FILE" "$DIR/$TEST_FILE"
        fi

        # Execute Python script with provided arguments
        # "$PYTHON" FileServer.py --port="$PORT" --base_dir="$DIR" &

    done
}


# Download the file
echo "Downloading test file ..."
wget -O "$TEST_FILE" "$TEST_FILE_LINK"

# Check if download was successful
if [ $? -eq 0 ]; then
    echo "Download successful."
    run_file_server "$NUM_NODES" "$SERVER_BASE_PORT" "$BASE_DIR" "$PYTHON"

    # Delete the downloaded file
    echo "Deleting file..."
    rm "$TEST_FILE"
else
    echo "Download failed."
fi



