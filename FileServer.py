import socket
import threading
import time
import os
import json

class PeerNetwork:
    def __init__(self, base_directory, host='0.0.0.0', server_port=12348, broadcast_port=12346, interval=5):
        self.base_directory = base_directory
        self.host = host
        self.server_port = server_port
        self.broadcast_port = broadcast_port
        self.interval = interval
        self.peers = set()
        self.shared_files = {}

    def broadcast_presence(self):
        """Broadcasts this server's presence to the network every 'interval' seconds."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while True:
                message = f"DISCOVER:{self.server_port}".encode('utf-8')
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
                        'files': my_files
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

    def run(self):
        """Starts the peer network services."""
        # threading.Thread(target=self.start_server).start()
        threading.Thread(target=self.broadcast_presence).start()
        threading.Thread(target=self.listen_for_peers).start()

if __name__ == "__main__":
    base_directory = './files/'  # Adjust as per your directory structure
    peer_network = PeerNetwork(base_directory)
    peer_network.run()
