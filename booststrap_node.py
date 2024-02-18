import asyncio
import socket
from kademlia.network import Server


async def start_node(port=9000):
    server = Server()
    await server.listen(port)
    host = socket.gethostbyname(socket.gethostname())
    print(f"Boostrap Node listening on {host}:{port}")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(start_node())
