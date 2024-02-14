import socket
import threading
import time
import os
import json
import filestore
import fileshare


class PeerNetwork:

    CHUNK_SIZE = 32

    def __init__(self, base_directory, host='0.0.0.0', server_port=12348, broadcast_port=12346, interval=5):
        self.base_directory = base_directory
        self.host = host
        self.server_port = server_port
        self.broadcast_port = broadcast_port
        self.interval = interval
        self.peers = set()
        self.file_store = filestore.FileStore(base_directory)
        self.shared_files = fileshare.FileShare() # IP Address: List of Files; each file is a tuple containing (file_name, hash)
        self.stop_threads = False

    def broadcast_presence(self):
        """Broadcasts this server's presence to the network every 'interval' seconds."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while not self.stop_threads:
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
            while not self.stop_threads:
                data, addr = s.recvfrom(1024)
                message = self.deserialize(data)
                if message['type'] == "DISCOVER":
                    server_port = message['server_port']
                    print(f"Discovered peer at {addr[0]}:{server_port}")
                elif message['type'] == "FILES":
                    self.shared_files.receive_data(addr[0], message['files'])

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
            while not self.stop_threads:
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
        if self.shared_files.is_empty():
            return ()
        
        peers_with_file = []
        print(self.shared_files.get_hash_to_info())
        
        requested_file = input("Enter the file hash to request (or type 'exit' to quit): ").strip()
        if requested_file.lower() == 'exit':
            return None  # Exit the loop to terminate the command prompt thread

        self.request_file(requested_file)
        # peers_with_file = self.shared_files.get_peers_with_file(requested_file)
          
        # print((requested_file, peers_with_file))
        # return (requested_file, peers_with_file)
        # # TODO: algorithm for requesting file from peers with this information

    def request_chunk(self, ip, fhash, chunk_index):
        """Return the data requsted"""
        print(f"Requested chunk {chunk_index} of {fhash} from {ip}")
        return f"Requested chunk {chunk_index} of {fhash} from {ip}"
        pass # Merge with Linda's code

    def request_chunks(self, ip, fhash, chunk_queue):
        """
        Returns: a dictionary that maps the chunk index to the data, as well as the remaining chunk index queue that hasn't been processed, if any.
        """
        cidx_to_data = {}

        while chunk_queue:
            try:
                data = self.request_chunk(ip, fhash, chunk_queue[0])
                cidx_to_data[chunk_queue.pop(0)] = data # if successful, pop from queue
            except:
                return cidx_to_data, chunk_queue

        return cidx_to_data, chunk_queue

    def request_file(self, fhash):
        """return true if file request succeeded, else returns false"""
        peers = self.shared_files.get_peers_with_file(fhash)
        size = self.shared_files.get_size_of_file(fhash)
        num_chunks = math.ceil(size/CHUNK_SIZE)

        idx_to_ip = {idx : peer for idx, peer in enumerate(peers)}
        ips_to_chunk_indices = {peer: [] for peer in peers}
        for cidx in num_chunks:
            pidx = cidx % num_chunks
            ips_to_chunk_indices[idx_to_ip[pidx]].append(cidx)
        
        # threads = []
        # for ip, cqueue in ips_to_chunk_indices.items():
        #     threads.append(threading.Thread(target=self.request_chunks, args=(ip, fhash, cqueue)))
        
        # TODO: call request_chunks, use threading to try to do it concurrently for each thread.
        # take the result of request_chunks and if there are still items yet to be processed in the chunk_queue,
        # remove that peer, and redistribute it, round robin style, to the rest of the peers

    def refresh_local_files(self):
        """Refreshes local files available for sharing."""
        while not self.stop_threads:
            self.file_store.load_files()
            time.sleep(self.interval)


    # def process_user_input(self):
         
            
        
    def run(self):
        """Starts the peer network services."""
        threads = [
            # threading.Thread(target=self.start_server), -- TODO: debug this, was raising an OSError
            threading.Thread(target=self.broadcast_presence),
            threading.Thread(target=self.listen_for_peers),
            threading.Thread(target=self.refresh_local_files),
        ]
        for thread in threads:
            thread.start()
        
        while True:
            if self.command_prompt() == None:
                self.stop_threads = True
                for thread in threads:
                    thread.join()
                return
        
        
        

       


if __name__ == "__main__":
    base_directory = './files/'  # Adjust as per your directory structure
    peer_network = PeerNetwork(base_directory)
    peer_network.run()
