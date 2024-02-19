import socket
import threading
import time
import os
import json
import filestore
from kademlia.network import Server
import asyncio
import argparse

class PeerNetwork:
    def __init__(self, base_directory, broadcast_port=9001, bootstrap_addr=("0.0.0.0", 9000), interval=5):
        self.base_directory = base_directory
        self.broadcast_port = broadcast_port
        self.interval = interval

        self.file_store = filestore.FileStore(base_directory)
        self.debug = False
        self.kademlia_server = Server()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.init_kademlia(bootstrap_addr))
        loop.run_until_complete(self.share_files())
        self.run()
        loop.run_forever()

    async def init_kademlia(self, boostrap_addr):
        await self.kademlia_server.listen(self.broadcast_port)
        await self.kademlia_server.bootstrap([boostrap_addr])

    async def share_files(self):
        for file in self.file_store.get_files():
            await self.kademlia_server.set(file['hash'], self.serialize(file))
            print(f"Shared file: {file}")

    async def find_file(self, file_hash):
        file_data = await self.kademlia_server.get(file_hash)
        return file_data

    def serialize(self, data):
        """Serializes the given data to a JSON string."""
        return json.dumps(data).encode('utf-8')

    def deserialize(self, data):
        """Decodes the given JSON string to reconstruct the original data."""
        return json.loads(data.decode('utf-8'))

    def log(self, message):
        """Prints message when debug mode is enabled."""
        if self.debug:
            print(message)

    def command_prompt(self):
        """Prompts user for file hash to request. Returns the file that the user requests, and the list of peers with that file."""
        requested_file = input("Enter the file hash to request (or type 'exit' to quit): ").strip()
        if requested_file.lower() == 'exit':
            return True  # Exit the loop to terminate the command prompt thread
        else:
            file = asyncio.run(self.find_file(requested_file))
            if file:
                file_metadata = self.deserialize(file)
                print(f"Discovered file: {file_metadata}")
            else:
                print(f"File not found")

    def refresh_local_files(self):
        """Refreshes local files available for sharing."""
        while True:
            self.file_store.load_files()
            time.sleep(self.interval)

    def process_user_input(self):
        while True:
            if self.command_prompt():
                break

    def run(self):
        """Starts the peer network services."""
        threading.Thread(target=self.refresh_local_files).start()
        threading.Thread(target=self.process_user_input).start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a peer node and share files.")
    parser.add_argument("--port", type=int, help="The port to listen on.")
    parser.add_argument("--bootstrap", type=str, help="The address of the bootstrap node.")
    base_directory = './files/'  # Adjust as per your directory structure
    args = parser.parse_args()
    if args.port and args.bootstrap:
        bootstrap_ip, bootstrap_port = args.bootstrap.split(":")
        bootstrap_addr = (bootstrap_ip, int(bootstrap_port))
        peer_network = PeerNetwork(base_directory, broadcast_port=args.port, bootstrap_addr=bootstrap_addr)
