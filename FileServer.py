import socket
import threading
import time
import os
import json
import filestore


class PeerNetwork:
    def __init__(self, base_directory, host='0.0.0.0', server_port=12348, broadcast_port=12346, interval=5):
        self.base_directory = base_directory
        self.host = host
        self.server_port = server_port
        self.broadcast_port = broadcast_port
        self.interval = interval
        self.peers = set()
        self.file_store = filestore.FileStore(base_directory)
        self.shared_files = {} # IP Address: List of Files; each file is a tuple containing (file_name, hash)

    def broadcast_presence(self):
        """Broadcasts this server's presence to the network every 'interval' seconds."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while True:
                s.sendto(self.serialize(
                    {
                        'type': 'DISCOVER',
                        'server_port': self.server_port
                    }
                ), ('<broadcast>', self.broadcast_port))
                my_files = [f for f in os.listdir(self.base_directory) if os.path.isfile(os.path.join(self.base_directory, f)) and not f.startswith('.')]
                s.sendto(self.serialize(
                    {
                        'type': 'FILES',
                        'server_port': self.server_port,
                        'files': self.file_store.get_files()
                    }
                ), ('<broadcast>', self.broadcast_port))
                print(f"Broadcasted presence on port {self.broadcast_port}")
                time.sleep(self.interval)

    def listen_for_peers(self):
        """Listens for broadcast messages from other peers to discover them."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('', self.broadcast_port))
            print(f"Listening for peers on broadcast port {self.broadcast_port}")
            while True:
                data, addr = s.recvfrom(1024)
                message = self.deserialize(data)
                if message['type'] == "DISCOVER":
                    server_port = message['server_port']
                    print(f"Discovered peer at {addr[0]}:{server_port}")
                elif message['type'] == "FILES":
                    files = message['files']
                    self.shared_files[addr[0]] = files
                    print(self.shared_files)

    def handle_client(self, conn, addr):
        """Handles incoming client connections and serves files from the base directory."""
        print(f"Connection from {addr}")
        try:
            filename = conn.recv(1024).decode('utf-8')
            filepath = os.path.join(self.base_directory, filename)
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    data = f.read()
                    conn.sendall(data)
                print(f"Sent {filename} to {addr}")
            else:
                conn.sendall(b'File not found')
        except Exception as e:
            print(f"Error: {e}")
        finally:
            conn.close()

    def start_server(self):
        """Starts a TCP server to serve files to peers."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.server_port))
            s.listen()
            print(f"Listening on {self.host}:{self.server_port}")
            while True:
                conn, addr = s.accept()
                client_thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                client_thread.start()

    def serialize(self, data):
        """Serializes the given data to a JSON string."""
        return json.dumps(data).encode('utf-8')

    def deserialize(self, data):
        """Decodes the given JSON string to reconstruct the original data."""
        return json.loads(data.decode('utf-8'))

    def command_prompt(self):
        """Prompts user for file hash to request. Returns the file that the user requests, and the list of peers with that file."""
        peers_with_file = []
        print("Lists of files available for requesting: ")
        print(self.shared_files)
        
        requested_file = input("Enter the file hash to request (or type 'exit' to quit): ").strip()
        if requested_file.lower() == 'exit':
            return None  # Exit the loop to terminate the command prompt thread

        if not self.shared_files:
            print("No files available for share yet. Try again later.")
        
        for peer_ip, files in self.shared_files.items():
            # file_name, file_hash = file
            if requested_file in files: # file_hash:
                peers_with_file.append(peer_ip)
                
        print((requested_file, peers_with_file))
        return (requested_file, peers_with_file)
        # TODO: algorithm for requesting file from peers with this information

    def refresh_local_files(self):
        """Refreshes local files available for sharing."""
        while True:
            self.file_store.load_files()
            time.sleep(self.interval)

    def process_user_input(self):
        while(True):
            if not self.command_prompt():
                break

    def run(self):
        """Starts the peer network services."""
        # threading.Thread(target=self.start_server).start()
        threading.Thread(target=self.broadcast_presence).start()
        threading.Thread(target=self.listen_for_peers).start()
        threading.Thread(target=self.refresh_local_files()).start()
        # TODO: add start up prompt
        threading.Thread(target=self.process_user_input).start() 

if __name__ == "__main__":
    base_directory = './files/'  # Adjust as per your directory structure
    peer_network = PeerNetwork(base_directory)
    peer_network.run()
