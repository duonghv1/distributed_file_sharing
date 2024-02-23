import asyncio
import requests
import argparse
import aioconsole
import filestore
from kademlia.network import Server
from utils import serialize, deserialize

PUBLIC_IP_GETTER = "https://checkip.amazonaws.com"


class PeerNetwork:
    def __init__(self, base_directory, port=9001, bootstrap_addr=("0.0.0.0", 9000), interval=5):
        self.base_directory = base_directory
        self.ip = requests.get(PUBLIC_IP_GETTER).text.strip()
        self.port = port
        self.interval = interval
        self.file_store = filestore.FileStore(base_directory)
        self.debug = False
        self.kademlia_server = Server()

        asyncio.run(self.run(bootstrap_addr))

    async def init_kademlia(self, boostrap_addr):
        await self.kademlia_server.listen(self.port)
        await self.kademlia_server.bootstrap([boostrap_addr])

    async def share_files(self):
        for file_hash, file in self.file_store.get_files().items():
            await self.kademlia_server.set(file_hash, file.metadata(serialized=True))
            share_chunk_coroutines = []
            for chunk_hash in file.chunk_hashes:
                share_chunk_coroutines.append(self.share_chunk(chunk_hash))
            await asyncio.gather(*share_chunk_coroutines)
            await aioconsole.aprint(f"\nShared file: {file}")

    async def share_chunk(self, chunk_hash):
        chunk_data = await self.kademlia_server.get(f"chunk:{chunk_hash}")
        if chunk_data:
            chunk = deserialize(chunk_data)
            peers = set(chunk['peers'])
            peers.add(f"{self.ip}:{self.port}")
            chunk['peers'] = list(peers)
        else:
            chunk = {"peers": [f"{self.ip}:{self.port}"]}
        print(chunk_hash, chunk)
        await self.kademlia_server.set(chunk_hash, serialize(chunk))

    async def find_file(self, file_hash):
        return await self.kademlia_server.get(file_hash)

    async def refresh_local_files(self):
        """Refreshes local files available for sharing."""
        while True:
            if self.file_store.load_files():
                await self.share_files()
            await asyncio.sleep(self.interval)

    async def process_user_input(self):
        await asyncio.sleep(1)
        while True:
            requested_file = await aioconsole.ainput("> ")
            if requested_file.lower() == 'exit':
                break  # Exit the loop to terminate the command prompt
            else:
                file = await self.find_file(requested_file)
                if file:
                    file_metadata = deserialize(file)
                    await aioconsole.aprint(f"Discovered file: {file_metadata}")

                else:
                    await aioconsole.aprint("File not found")

    async def run(self, bootstrap_addr):
        """Starts the peer network services."""
        await self.init_kademlia(bootstrap_addr)

        await asyncio.gather(self.refresh_local_files(), self.process_user_input())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a peer node and share files.")
    parser.add_argument("--port", type=int, help="The port to listen on.")
    parser.add_argument("--bootstrap", type=str, help="The address of the bootstrap node.")
    parser.add_argument("--dir", type=str, help="The directory to share files from.")
    base_directory = '../files/'
    args = parser.parse_args()
    if args.dir:
        base_directory = args.dir
    if args.port and args.bootstrap:
        bootstrap_ip, port = args.bootstrap.split(":")
        peer_network = PeerNetwork(
            base_directory=base_directory,
            port=args.port,
            bootstrap_addr=(bootstrap_ip, int(port))
        )
