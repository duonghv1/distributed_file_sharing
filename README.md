# Distributed File Sharing

## Naive Implementation
A naive node can be launched using the following command:
```
python naive_node.py --port 8000 --server_port 9000 --broadcast_port 33333 --dir ./files/
```
Nodes will communicate with nodes sharing the same `broadcast_port`

## Kademlia Implementation
The Kademlia network requires two nodes to start. A boostrap node can be started with the command:
```
python kademlia_bootstrap.py
```
This starts a Kademlia node with IP and port `192.168.1.1:9000`<br>
A Kademlia node can join an existing network via a bootstrap address with the command:
```
python kademlia_node.py --port 8001 --server_port 9001 --bootstrap 192.168.1.1:9000 --dir ./files/
```
#### Args
- `port` specifies the port to node is running on
- `server_port` specifies the port the file server is using for serving downloads
- `dir` specifies the folder that will be used to share files

## Usage
To get a list of commands run enter `help`
```
> help
Commands:
  ls               display local files being shared
  ls remote        display remote files being shared
  f <hash>         lookup file or chunk in the network
  dl <file_hash>   download file to directory
  exit             exit the program
```
