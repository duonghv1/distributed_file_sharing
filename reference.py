import socket

def request_file(server_host, server_port, filename):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_host, server_port))
        s.sendall(filename.encode('utf-8'))
        response = s.recv(1024)
        if response:
            with open(filename, 'wb') as f:
                f.write(response)
            print(f"Received {filename}")
        else:
            print("File not found or error occurred")

# Example usage
server_host = '128.195.27.46'
server_port = 12345
filename = 'example.txt'
request_file(server_host, server_port, filename)
