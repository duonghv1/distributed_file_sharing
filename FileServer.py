import socket
import threading
import time
import os
import json
import filestore
import fileshare
from filechunking import combine_chunks, get_file_chunk
import math

class PeerNetwork:

    CHUNK_SIZE = 32

    def __init__(self, base_directory, host='0.0.0.0', server_port=12348, broadcast_port=12346, interval=5):
        self.base_directory = base_directory
        self.__chunksize = 32
        self.host = host
        self.server_port = server_port
        self.broadcast_port = broadcast_port
        self.interval = interval
        self.peers = set()
        self.file_store = filestore.FileStore(base_directory)  # handle local directory  
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
            message_parts = conn.recv(1024).decode('utf-8').split()
            print("MESSAGE is", message_parts)
            if message_parts[0] == "GET_CHUNK":
                fhash = message_parts[1]
                chunk_index = int(message_parts[2])
                fileobj = self.file_store.find_file_by_hash(fhash)
                chunk = get_file_chunk(fileobj.filepath, self.__chunksize, chunk_index)
                print("CHUNK is", chunk)
                message = f"CHUNK RECEIVED {fhash} {idx} {chunk}"
                conn.sendall(message.encode())
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
        """Prompts user for file hash to request. If request successful, writes the data into the user's folder and returns True."""
        if self.shared_files.is_empty():
            print("No files are currently available for share.")
            return False
        
        time.sleep(2)
        files = self.shared_files.get_hash_to_info()
        print(files)
        
        requested_file = input("Enter the file hash to request (or type 'exit' to quit): ").strip()
        if requested_file.lower() == 'exit':
            return None  # Exit the loop to terminate the command prompt thread

        if requested_file not in files:
            print("The file you've requested is not available. Please try again.")
            return False

        success, data = self.request_file(requested_file)

        if not success:
            print("Request unsuccessful. Please try again.")
            return False
        
        chunks = [fdata for fidx, fdata in sorted(data.items())]

        file_name = input("Request successful! What would you like to name your file? (Do not include the extension): ").strip()
        try:
            filepath = combine_chunks(base_directory, file_name, files[requested_file]['ext'], chunks)
            print(f"File saved successfully at {filepath}.")
            return True
        except:
            print("Error when saving the file.")
            return False
        
        # print("TEST request chunk")
        # ip = input("Enter ip: ").strip()

        # self.request_chunk(ip, requested_file, 0)
        

    def request_chunk(self, ip, fhash, chunk_index):
        """Send the request to the node with the ip including the hash and the chunk index.
            Wait until get the chunk back and return the chunk.
        
            Note: curerntly using TCP protocol to communicate with other nodes.
        """
        print(f"Requested chunk {chunk_index} of {fhash} from {ip}")
        # Set up socket
        data = None
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Connect to the server
            s.connect((ip, self.server_port))
            # Send request
            request_message = f"GET_CHUNK {fhash} {chunk_index}"
            s.sendall(request_message.encode())

            # Receive response
            response = s.recv(1024)  # Adjust buffer size as needed
            data = response.decode()
            print(f"Received message: {data}")
        
        return data
    
        
    def request_chunks(self, ip, fhash, chunk_queue):
        """
        Returns: a dictionary that maps the chunk index to the data, as well as the remaining chunk index queue that hasn't been processed, if any.
        """
        cidx_to_data = {}

        while chunk_queue:
            try:
                data = self.request_chunk(ip, fhash, chunk_queue[0])
                cidx_to_data[chunk_queue.pop(0)] = data # if successful, pop from queue
            except Exception as e:
                print(f"Error requesting chunk from {ip}: {e}")
                break

        return cidx_to_data, chunk_queue

    def round_robin(self, peers, chunks):
        """Distribute chunks among peers in a round-robin fashion"""
        # the end result is ips_to_chunk_indices: each ip is mapped to a queue of chunk indices.
        idx_to_ip = {idx : peer for idx, peer in enumerate(peers)}
        ips_to_chunk_indices = {peer : [] for peer in peers}
        for cidx in chunks:
            pidx = cidx % len(peers)
            ips_to_chunk_indices[idx_to_ip[pidx]].append(cidx)

        return ips_to_chunk_indices

    def request_chunks_wrapper(self, ip, fhash, chunk_queue, result_lock, global_results):
        data, remaining_queue = self.request_chunks(ip, fhash, chunk_queue)
        with result_lock:
            global_results["data"].update(data)
            global_results["remaining"].extend(remaining_queue)

    def request_file(self, fhash):
        """return true if file request succeeded, else returns false"""
        peers = self.shared_files.get_peers_with_file(fhash)
        size = self.shared_files.get_size_of_file(fhash)
        num_chunks = math.ceil(size/CHUNK_SIZE)

        all_data_retrieved = False
        remaining_chunks = list(range(num_chunks))
        global_results = {"data": {}, "remaining": {}}

        while not all_data_retrieved and peers:
            ips_to_chunk_indices = self.round_robin(peers, remaining_chunks)
            threads = []
            result_lock = threading.Lock()

            for ip, chunk_queue in ips_to_chunk_indices.items():
                t = threading.Thread(target=self.request_chunks_wrapper, args=(ip, fhash, chunk_queue, result_lock, global_results))
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            if not global_results["remaining"]:
                all_data_retrieved = True

            else:
                # Reset everything for the next iteration
                remaining_chunks = global_results["remaining"]
                global_results["remaining"] = []

                # Updates peers
                peers = [peer for peer in peers if peer in ips_to_chunk_indices and ips_to_chunk_indices[peer]]
                if not peers:
                    peers = self.shared_files.get_peers_with_file(fhash)

        return all_data_retrieved, global_results["data"]


    def refresh_local_files(self):
        """Refreshes local files available for sharing."""
        while not self.stop_threads:
            self.file_store.load_files()
            time.sleep(self.interval)


    def run(self):
        """Starts the peer network services."""
        threads = [
            threading.Thread(target=self.start_server), 
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
