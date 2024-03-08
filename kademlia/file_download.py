import aiohttp
import asyncio
import aiofiles
import os
from aioconsole import aprint
from file_store import File, Chunk


class FileDownloader:
    def __init__(self, base_directory, file_data, chunks):
        self.base_directory = base_directory
        self.file_data = file_data
        self.chunks = chunks
        self.file_path = self.base_directory + self.file_data['file_name']
        self.temp_file_path = self.file_path + '.download'
        self.init_file()

    def init_file(self):
        file_size = self.file_data['file_size']
        with open(self.temp_file_path, 'wb') as file:
            file.truncate(file_size)

    async def download_piece(self, session, chunk, start, end, peers):
        failed_peers = set()
        while not peers.empty():
            await aprint(peers.qsize())
            peer = await peers.get()
            url = f"http://{peer}/chunks/{chunk.chunk_hash}"
            headers = {"Range": f"bytes={start}-{end}"}
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 206:
                        return await response.read(), failed_peers
                    else:
                        raise Exception
            except Exception as e:
                failed_peers.add(peer)
        return None, failed_peers

    async def download_chunk(self, session, chunk):
        num_peers = len(chunk.peers)
        piece_size = chunk.size // num_peers
        download_coroutines = []
        for i, peer in enumerate(chunk.peers):
            start = chunk.offset + i * piece_size
            end = start + piece_size - 1 if i < num_peers - 1 else chunk.offset + chunk.size - 1
            peers = asyncio.Queue()
            [await peers.put(chunk.peers[(i + j) % num_peers]) for j in range(num_peers)]
            download_coroutines.append(self.download_piece(session, chunk, start, end, peers))
        result = await asyncio.gather(*download_coroutines, return_exceptions=True)
        all_failed_peers = set()
        for _, failed_peers in result:
            all_failed_peers.update(failed_peers)
        chunk_data = b''.join([piece for piece, _ in result if piece is not None])
        for piece, _ in result:
            if piece is None:
                await aprint(f"Failed to download chunk {chunk.chunk_hash}")
                return chunk.chunk_hash, all_failed_peers
        await self.write_chunk_to_file(chunk, chunk_data)
        return chunk.chunk_hash, all_failed_peers

    async def write_chunk_to_file(self, chunk, data):
        async with aiofiles.open(self.temp_file_path, 'rb+') as file:
            await file.seek(chunk.offset)
            await file.write(data)

    async def download_file(self):
        failed_peers = []
        try:
            async with aiohttp.ClientSession(trust_env=True) as session:
                download_coroutines = []
                for chunk_data in self.chunks:
                    chunk = Chunk(**chunk_data)
                    download_coroutines.append(self.download_chunk(session, chunk))
                results = await asyncio.gather(*download_coroutines)
                for item in results:
                    failed_peers.append(item)
                file = File(self.temp_file_path, self.file_data['file_name'], self.file_data['chunk_size'])
                if file.hash() == self.file_data['file_hash']:
                    os.rename(self.temp_file_path, self.file_path)
                    await aprint(f"Downloaded file: {self.file_data['file_name']}")
                else:
                    raise Exception("File hash mismatch. Missing chunks.")
        except Exception as e:
            await aprint(f"Failed to download file: {self.file_data['file_name']}")
            await aprint(f"Error: {e}")
            await aprint("Cleaning up...")
            os.remove(self.temp_file_path)
        return failed_peers
