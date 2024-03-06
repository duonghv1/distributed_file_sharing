import asyncio
import logging
import socket
from kademlia.network import Server
from utils import get_internal_ip

handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
log = logging.getLogger('kademlia')
log.addHandler(handler)
log.setLevel(logging.DEBUG)


async def start_node(port=9000):
    server = Server()
    await server.listen(port)
    print(f"Boostrap Node listening on {get_internal_ip()}:{port}")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(start_node())
