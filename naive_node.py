import asyncio
import argparse
import aioconsole
import socket
from src import file_store, file_server, file_download
from src.utils import serialize, deserialize, get_internal_ip

MAX_PEERS = 30

class UserExit(Exception):
    pass

class PeerNetwork:
    def __init__(self, base_directory, port=9000, server_port=8000, broadcast_port=12346, timeout=1, cmd_line=True):
        self.base_directory = base_directory
        self.ip = get_internal_ip()
        self.port = port
        self.timeout = timeout
        self.cmd_line = cmd_line
        self.file_store = file_store.FileStore(base_directory)
        self.debug = False
        self.file_server = file_server.FileServer(self.file_store, self.ip, server_port)
        self.broadcast_port = broadcast_port
        self.file_responses = {} # temporary storage for file responses

    def broadcast(self, message):
        # Send a broadcast message to the network
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(message, ('<broadcast>', self.broadcast_port))
        sock.close()

    def send_message(self, message, addr):
        # Send a message to a specific address
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message, addr)
        sock.close()

    async def request_file(self, file_hash):
        self.file_responses[file_hash] = None
        msg = serialize({"type": "request", "file_hash": file_hash, "addr": f"{self.ip}:{self.port}"})
        self.broadcast(msg)
        await asyncio.sleep(self.timeout)
        if file_hash == 'index:0':
            index = {}
            for file_hash, file in self.file_responses.items():
                if file:
                    index[file_hash] = file['file_name']
            return index
        return self.file_responses.pop(file_hash, None)

    async def listen(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.bind(('', port))

        sock.setblocking(False)
        while True:
            try:
                data, addr = await asyncio.get_event_loop().run_in_executor(None, sock.recvfrom, 1024 * 8)
                message = deserialize(data)
                if message['addr'] == f"{self.ip}:{self.port}":
                    continue
                if message['type'] == 'request':
                    await self.handle_file_request(message, addr)
                if message['type'] == 'response':
                    self.handle_file_response(message)
            except BlockingIOError:
                await asyncio.sleep(0.1)

    async def handle_file_request(self, message, addr):
        file_hash = message['file_hash']
        message_addr_parts = message['addr'].split(':')
        message_addr = (message_addr_parts[0], int(message_addr_parts[1]))
        if file_hash == 'index:0':
            for file_hash, file in self.file_store.files.items():
                response = {"type": "response", "file_hash": file.hash(), "file": file.metadata(), "addr": f"{self.ip}:{self.file_server.port}"}
                self.send_message(serialize(response), message_addr)
        else:
            file = self.file_store.get_file(file_hash)
            if file:
                response = {"type": "response", "file_hash": file.hash(), "file": file.metadata(), "addr": f"{self.ip}:{self.file_server.port}"}
                self.send_message(serialize(response), message_addr)

    def handle_file_response(self, message):
        file = message['file']
        addr = message['addr']
        file_hash = message['file_hash']
        file['peers'] = [addr]
        if not self.file_responses.get(file_hash):
            self.file_responses[file_hash] = file
        else:
            self.file_responses[file_hash]['peers'].append(addr)

    async def find_hash(self, file_hash):
        return await self.request_file(file_hash)

    async def refresh_local_files(self):
        """Refreshes local files available for sharing."""
        while True:
            self.file_store.load_files()
            await asyncio.sleep(self.timeout)

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
            file_metadata = file
            file_metadata['file_hash'] = file_hash
            for chunk in file_metadata['chunks']:
                chunk_hash = chunk['chunk_hash']
                chunk['peers'] = file_metadata['peers']
                if len(chunk['peers']) == 0:
                    await aioconsole.aprint(f"No peers found for chunk {chunk_hash}. Aborting download...")
                    return
                chunks.append(chunk)
            downloader = file_download.FileDownloader(self.base_directory, file_metadata, chunks)
            status, failed_peers = await downloader.download_file()
            return status
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
        if not data:
            await aioconsole.aprint("No remote files found.")
            return
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
                data = await self.find_hash(requested_hash)
                if data:
                    if requested_hash.startswith('file:'):
                        await aioconsole.aprint(f"Discovered file: {data}")
                    elif requested_hash == 'index:0':
                        await self.display_remote_files(data)
                else:
                    await aioconsole.aprint("Hash not found")
            elif command == "ls":
                await aioconsole.aprint("Local files:")
                for file in self.file_store.files.values():
                    await aioconsole.aprint(f"  {file}")
            elif command == "ls remote":
                await self.display_remote_files(await self.find_hash("index:0"))
            else:
                await aioconsole.aprint("Command not found. Type 'help' for a list of commands.")
            await aioconsole.aprint("")
        raise UserExit("User exited program.")

    async def run(self):
        """Starts the peer network services."""
        await self.file_server.run()
        async_tasks = [self.refresh_local_files(), self.listen(self.broadcast_port), self.listen(self.port)]
        if self.cmd_line:
            async_tasks.append(self.process_user_input())
        await asyncio.gather(*async_tasks)

    async def terminate(self):
        await self.file_server.terminate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a peer node and share files.")
    parser.add_argument("--n", type=int, help="Node number; will create node with kademlia port 900x and server port "
                                              "800x using dir ../files/x.")
    parser.add_argument("--port", type=int, help="The port for node to listen on.")
    parser.add_argument("--server_port", type=int, help="The port for file server to listen on.")
    parser.add_argument("--broadcast_port", type=int, help="The port to broadcast on.")
    parser.add_argument("--dir", type=str, help="The directory to share files from.")
    base_directory = './files/'
    bootstrap_node = "0.0.0.0:9000"
    port = 9001
    server_port = 8001
    broadcast_port = 12346
    args = parser.parse_args()
    if args.n and args.n > 0:
        base_directory = f'./files/{args.n}/'
        port = 9000 + args.n
        server_port = 8000 + args.n
    if args.dir:
        base_directory = args.dir
    if args.port:
        port = args.kademlia_port
    if args.server_port:
        server_port = args.server_port
    if args.broadcast_port:
        broadcast_port = args.broadcast_port
    peer_network = PeerNetwork(
        base_directory=base_directory,
        port=port,
        server_port=server_port,
        broadcast_port=broadcast_port
    )
    try:
        asyncio.run(peer_network.run())
    except (KeyboardInterrupt, UserExit) as e:
        print("Shutdown requested...exiting")
    finally:
        asyncio.run(peer_network.terminate())
