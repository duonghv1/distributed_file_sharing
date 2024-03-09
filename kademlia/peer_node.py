import asyncio
import argparse
import aioconsole
import file_store
import file_server
import file_download
from kademlia.network import Server
from utils import serialize, deserialize, get_internal_ip


PUBLIC_IP_GETTER = "https://checkip.amazonaws.com"
MAX_PEERS = 30

class UserExit(Exception):
    pass

class PeerNetwork:
    def __init__(self, base_directory, kademlia_port=9001, server_port=8000, bootstrap_addr=("0.0.0.0", 9000), interval=5):
        self.base_directory = base_directory
        self.ip = get_internal_ip()
        self.port = kademlia_port
        self.interval = interval
        self.file_store = file_store.FileStore(base_directory)
        self.debug = False
        self.kademlia_server = Server()
        self.file_server = file_server.FileServer(self.file_store, self.ip, server_port)

    async def init_kademlia(self, boostrap_addr):
        await self.kademlia_server.listen(self.port)
        await self.kademlia_server.bootstrap([boostrap_addr])

    async def share_files(self):
        file_index = await self.find_hash("index:0")
        if not file_index:
            file_index = {}
        else:
            file_index = deserialize(file_index)
        for file_hash, file in self.file_store.files.items():
            if file_hash not in file_index:
                file_index[file_hash] = file.file_name
            if not self.find_hash(file_hash):
                await self.kademlia_server.set(file_hash, file.metadata(serialized=True))
            share_chunk_coroutines = []
            for chunk in file.chunks.values():
                share_chunk_coroutines.append(self.share_chunk(chunk.chunk_hash))
            await asyncio.gather(*share_chunk_coroutines)
        await self.kademlia_server.set("index:0", serialize(file_index))

    async def share_chunk(self, chunk_hash):
        chunk_data = await self.kademlia_server.get(chunk_hash)
        if chunk_data:
            chunk = deserialize(chunk_data)
            peers = set(chunk['peers'])
            peers.add(f"{self.ip}:{self.file_server.port}")
            chunk['peers'] = list(peers)
        else:
            chunk = {"peers": [f"{self.ip}:{self.file_server.port}"]}
        await self.kademlia_server.set(chunk_hash, serialize(chunk))

    async def find_hash(self, file_hash):
        return await self.kademlia_server.get(file_hash)

    async def refresh_local_files(self):
        """Refreshes local files available for sharing."""
        while True:
            if self.file_store.load_files():
                await self.file_server.update_file_store(self.file_store)
                await self.share_files()
            await asyncio.sleep(self.interval)

    async def download_file(self, file_hash):
        if not file_hash.startswith('file:'):
            await aioconsole.aprint("Invalid file hash.")
            return
        if self.file_store.files.get(file_hash):
            await aioconsole.aprint("File already exists locally.")
            return
        file = await self.find_hash(file_hash)
        if file:
            chunks = []
            file_metadata = deserialize(file)
            file_metadata['file_hash'] = file_hash
            for chunk in file_metadata['chunks']:
                chunk_hash = chunk['chunk_hash']
                chunk_data = await self.kademlia_server.get(chunk_hash)
                if chunk_data:
                    chunk_metadata = deserialize(chunk_data)
                    chunk_peers = [x for x in chunk_metadata['peers'][0:MAX_PEERS] if x != f"{self.ip}:{self.file_server.port}"]
                    if len(chunk_peers) == 0:
                        await aioconsole.aprint(f"No peers found for chunk {chunk_hash}. Aborting download...")
                        return
                    chunk['peers'] = chunk_peers
                    chunks.append(chunk)
            downloader = file_download.FileDownloader(self.base_directory, file_metadata, chunks)
            status, failed_peers = await downloader.download_file()
            # Remove failed peers from chunk metadata
            # for chunk_hash, peers in failed_peers:
            #     chunk_data = await self.kademlia_server.get(chunk_hash)
            #     if chunk_data:
            #         chunk_metadata = deserialize(chunk_data)
            #         chunk_peers = chunk_metadata['peers']
            #         chunk_peers = list(set(chunk_peers) - set(peers))
            #         chunk_metadata['peers'] = chunk_peers
            #         await self.kademlia_server.set(chunk_hash, serialize(chunk_metadata))
            # return status
        return False

    async def display_help(self):
        commands = {
            "ls": "display local files being shared",
            "ls remote": "display remote files being shared",
            "f <hash>": "lookup file or chunk in the network",
            "dl <file_hash>": "download file to directory",
            "exit": "exit the program"
        }
        await aioconsole.aprint("Commands:")
        for command, description in commands.items():
            await aioconsole.aprint(f"  {command:16} {description}")

    async def display_remote_files(self, data):
        await aioconsole.aprint("Remote files:")
        for file_hash, file_name in sorted(data.items(), key=lambda x: x[1]):
            await aioconsole.aprint(f"  {file_name:16} {file_hash}")

    async def process_user_input(self):

        await asyncio.sleep(1)
        while True:
            command = await aioconsole.ainput("> ")
            if command == 'help':
                await self.display_help()
            elif command == 'exit':
                await self.terminate()
                break # Exit the loop to terminate the command prompt
            elif command.startswith("download ") or command.startswith("dl "):
                requested_file = command.split(" ")[1]
                await self.download_file(requested_file)
            elif command.startswith("find ") or command.startswith("f "):
                requested_hash = command.split(" ")[1]
                result = await self.find_hash(requested_hash)
                if result:
                    data = deserialize(result)
                    if requested_hash.startswith('file:'):
                        await aioconsole.aprint(f"Discovered file: {data}")
                    elif requested_hash.startswith('chunk:'):
                        await aioconsole.aprint(f"Discovered chunk: {data}")
                    elif requested_hash == 'index:0':
                        await self.display_remote_files(data)
                else:
                    await aioconsole.aprint("Hash not found")
            elif command == "ls":
                await aioconsole.aprint("Local files:")
                for file in self.file_store.files.values():
                    await aioconsole.aprint(f"  {file}")
            elif command == "ls remote":
                await self.display_remote_files(deserialize(await self.find_hash("index:0")))
            else:
                await aioconsole.aprint("Command not found. Type 'help' for a list of commands.")
            await aioconsole.aprint("")
        raise UserExit("User exited program.")

    async def run(self, bootstrap_addr):
        """Starts the peer network services."""
        await self.init_kademlia(bootstrap_addr)
        await self.file_server.run()
        await asyncio.gather(self.refresh_local_files(), self.process_user_input())

    async def terminate(self):
        await self.file_server.terminate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a peer node and share files.")
    parser.add_argument("--n", type=int, help="Node number; will create node with kademlia port 900x and server port "
                                              "800x using dir ../files/x.")
    parser.add_argument("--kademlia_port", type=int, help="The port for node to listen on.")
    parser.add_argument("--server_port", type=int, help="The port for file server to listen on.")
    parser.add_argument("--bootstrap", type=str, help="The address of the bootstrap node.")
    parser.add_argument("--dir", type=str, help="The directory to share files from.")
    base_directory = '../files/'
    bootstrap_node = "0.0.0.0:9000"
    kademlia_port = 9001
    server_port = 8001
    args = parser.parse_args()
    if args.n and args.n > 0:
        base_directory = f'../files/{args.n}/'
        kademlia_port = 9000 + args.n
        server_port = 8000 + args.n
    if args.dir:
        base_directory = args.dir
    if args.kademlia_port:
        kademlia_port = args.kademlia_port
    if args.server_port:
        server_port = args.server_port
    if args.bootstrap:
        bootstrap_node = args.bootstrap
    bootstrap_ip, port = bootstrap_node.split(":")
    bootstrap_addr = (bootstrap_ip, int(port))
    peer_network = PeerNetwork(
        base_directory=base_directory,
        kademlia_port=kademlia_port,
        server_port=server_port,
        bootstrap_addr=bootstrap_addr
    )
    try:
        asyncio.run(peer_network.run(bootstrap_addr))
    except (KeyboardInterrupt, UserExit) as e:
        print("Shutdown requested...exiting")
    finally:
        asyncio.run(peer_network.terminate())
