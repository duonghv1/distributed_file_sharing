import argparse
import asyncio
from kademlia.network import Server

async def start_node(host="0.0.0.0", port=8468):
    server = Server()
    await server.listen(port)
    print(f"Node listening on {host}:{port}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start_node())
