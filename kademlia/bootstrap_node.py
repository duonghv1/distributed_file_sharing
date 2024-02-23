import asyncio
import logging
import socket
from kademlia.network import Server

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log = logging.getLogger('kademlia')
log.addHandler(handler)
log.setLevel(logging.DEBUG)


async def start_node(port=9000):
    server = Server()
    await server.listen(port)
    host = socket.gethostbyname(socket.gethostname()+'.')
    print(f"Boostrap Node listening on {host}:{port}")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(start_node())
