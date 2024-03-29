import socket
import threading
import time
import json
import filestore
import fileshare
from filechunking import combine_chunks, get_file_chunk
import math
import sys
import signal


class PeerNetwork:

    def __init__(self, base_directory, mode="normal", host='0.0.0.0', server_port=12345, broadcast_port=12346, interval=5):
        self.base_directory = base_directory
        self.chunk_size = 100
        self.host = host
        self.server_port = server_port
        self.broadcast_port = broadcast_port
        self.interval = interval
        self.file_store = filestore.FileStore(base_directory)  # handle local directory  
        self.shared_files = fileshare.FileShare()              # IP Address: List of Files; each file is a tuple (file_name, hash)
        self.mode = mode
        self.stop_event = threading.Event()

    def debug_print(self, message):
        """Helper function to print debug messages if debug mode is enabled."""
        if self.mode == "debug":
            print(message)


    def broadcast_presence(self):
        """Broadcasts this server's presence to the network every 'interval' seconds."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while not self.stop_event.is_set():
                s.sendto(self.serialize(
                    {
                        'type': 'DISCOVER',
                        'server_port': self.server_port
                    }
                ), ('<broadcast>', self.broadcast_port))
                s.sendto(self.serialize(
                    {
                        'type': 'FILES',
                        'server_port': self.server_port,
                        'files': self.file_store.get_files()
                    }
                ), ('<broadcast>', self.broadcast_port))
                self.debug_print(f"Broadcasted presence on port {self.broadcast_port}")
                time.sleep(self.interval)
            self.debug_print("close broadcast presence")


    def listen_for_peers(self):
        """Listens for broadcast messages from other peers to discover them."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            recv_buffer_size = s.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF) # Get the system's default receive buffer size for the socket
            s.bind(('', self.broadcast_port))
            s.setblocking(False)  # Set socket to non-blocking mode
            self.debug_print(f"Listening for peers on broadcast port {self.broadcast_port}")
            while not self.stop_event.is_set():
                try:
                    data, addr = s.recvfrom(recv_buffer_size)
                    if data:
                        message = self.deserialize(data)
                        if message['type'] == "DISCOVER":
                            server_port = message['server_port']
                            self.debug_print(f"Discovered peer at {addr[0]}:{server_port}")
                        elif message['type'] == "FILES":
                            self.shared_files.receive_data(addr[0], message['files'])
                except BlockingIOError:
                    pass
            self.debug_print("close listen for peers")



    def handle_client(self, conn, addr):
        """Handles incoming client connections and serves files from the base directory."""
        self.debug_print(f"Connection from {addr}")
        try:
            message_parts = conn.recv(1024).decode('utf-8').split()
            if message_parts[0] == "GET_CHUNK":
                fhash = message_parts[1]
                chunk_index = int(message_parts[2])
                fileobj = self.file_store.find_file_by_hash(fhash)
                chunk = get_file_chunk(fileobj.filepath, self.chunk_size, chunk_index)
                # Prepare the header: hash (64 bytes), chunk index (4 bytes), chunk_len (4 bytes)
                header = fhash.encode() + chunk_index.to_bytes(4, byteorder='big')  + len(chunk).to_bytes(4, byteorder='big')
                conn.sendall(header + chunk)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            conn.close()


    def start_server(self):
        """Starts a TCP server to serve files to peers."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.server_port))
            s.listen()
            s.settimeout(5)  # Timeout of 5 seconds so socket doesn't block forever
            self.debug_print(f"Listening on {self.host}:{self.server_port}")
            while not self.stop_event.is_set():
                try:
                    conn, addr = s.accept()
                    if conn:
                        client_thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                        client_thread.start()
                except TimeoutError:
                    pass
            self.debug_print("close start server")


    def serialize(self, data):
        """Serializes the given data to a JSON string."""
        return json.dumps(data).encode('utf-8')

    def deserialize(self, data):
        """Decodes the given JSON string to reconstruct the original data."""
        return json.loads(data.decode('utf-8'))

    def command_prompt(self):
        """Prompts user for file hash to request. If request successful, writes the data into the user's folder and returns True."""
        if self.shared_files.is_empty():
            return False
    
        time.sleep(2)
        files = self.shared_files.get_hash_to_info()
        print(files)
        
        if self.mode == "test":
            requested_file = "b9eb5104658f4d6ef8ff9b457f28f188b6aa1b201443719c501e462072eacf57"
        else:
            requested_file = input("Enter the file hash to request (or type 'exit' to quit): ").strip()
        
        if requested_file.lower() == 'exit':
            return None
            
        if requested_file not in files:
            print("The file you've requested is not available. Please try again.")
            return False

        success, data = self.request_file(requested_file)

        if not success:
            print("Request unsuccessful. Please try again.")
            return False
        
        chunks = [fdata for fidx, fdata in sorted(data.items())]
        if self.mode == "test":
            file_name = "test_output"
        else:
            file_name = input("Request successful! What would you like to name your file? (Do not include the extension): ").strip()
        try:
            filepath = combine_chunks(self.base_directory, file_name, files[requested_file]['ext'], chunks)
            print(f"File saved successfully at {filepath}.")
            return True
        except:
            print("Error when saving the file.")
            return False
                


    def request_chunk(self, ip, fhash, chunk_index):
        """Send the request to the node with the ip including the hash and the chunk index.
            Wait until get the chunk back and return the chunk.
        
            Note: curerntly using TCP protocol to communicate with other nodes.
        """
        data = None
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, self.server_port))
            request_message = f"GET_CHUNK {fhash} {chunk_index}"
            s.sendall(request_message.encode())

            # Receive response (Assume the only type of response we receive is chunk data)
            fhash_rcv, chunk_index_rcv, data = self.receive_with_header(s)
            self.debug_print(f"RECEIVED: {fhash}, {chunk_index}, {data}")
            if fhash_rcv != fhash or chunk_index_rcv != chunk_index:
                raise Exception(f"Hash index mismatch: Expected ({fhash}, {chunk_index}), but received ({fhash_rcv}, {chunk_index_rcv})")
            
        return data


    def receive_with_header(self, client_socket):
        # Read the header: hash (64 bytes), chunk index (4 bytes), chunk_len (4 bytes)
        header = client_socket.recv(64 + 4 + 4)
        fhash = header[:64].decode()
        chunk_index = int.from_bytes(header[64:68], byteorder='big')
        data_length = int.from_bytes(header[68:], byteorder='big')
        
        # Read the data based on the length from the header
        data = client_socket.recv(data_length)
        return fhash, chunk_index, data
    
        
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
        num_chunks = math.ceil(size/self.chunk_size)

        all_data_retrieved = False
        remaining_chunks = list(range(num_chunks))
        global_results = {"data": {}, "remaining": []}
        ips_to_chunk_indices = self.round_robin(peers, remaining_chunks)

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
        while not self.stop_event.is_set():
            self.file_store.load_files()
            time.sleep(self.interval)
        self.debug_print("close refresh local files")


    def run(self):
        """Starts the peer network services."""
        threads = [
            threading.Thread(target=self.start_server), 
            threading.Thread(target=self.broadcast_presence),
            threading.Thread(target=self.listen_for_peers),
            threading.Thread(target=self.refresh_local_files),
        ]

        signal.signal(signal.SIGINT, self.signal_handler) # Register signal handler for Ctrl+C

        for thread in threads: 
            thread.start()
        
        while True:
            result = self.command_prompt()
            if  result == None:
                break
            elif result == True and self.mode == "test":
                break
            

        self.stop_event.set()
        for thread in threads:
            thread.join()
        return
    

    def signal_handler(self, sig, frame): 
        print("Ctrl+C detected, closing program")       
        self.stop_event.set()
        sys.exit(0)
            


if __name__ == "__main__":
    base_directory = './files/'  # Adjust as per your directory structure
    mode = "test" 
    if len(sys.argv) > 1:
        if sys.argv[1] == 'debug': 
            mode = "debug"
        elif sys.argv[1] == 'test': 
            mode = "test"
    peer_network = PeerNetwork(base_directory, mode)
    peer_network.run()
