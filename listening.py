import socket
import struct

multicast_group = '224.3.29.71'  # An arbitrarily chosen multicast group address
multicast_port = 10000

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind to the server address
sock.bind(('', multicast_port))

# Tell the operating system to add the socket to the multicast group
# on all interfaces.
group = socket.inet_aton(multicast_group)
mreq = struct.pack('4sL', group, socket.INADDR_ANY)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

try:
    while True:
        print('\nWaiting to receive message')
        data, address = sock.recvfrom(1024)
        
        print(f'Received {len(data)} bytes from {address}')
        print(data.decode())
finally:
    print('Closing socket')
    sock.close()