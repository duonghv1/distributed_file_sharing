import aiohttp.web
import aioconsole
import asyncio
from .file_store import FileStore, File

DOWNLOAD_RATE = 1024 * 1024 * 10  # 10MB/s

class FileServer:
    def __init__(self, file_store: FileStore, host, port, download_rate=DOWNLOAD_RATE):
        self.file_store = file_store
        self.host = host
        self.port = port
        self.server = aiohttp.web.Application()
        self.create_routes()
        self.download_rate = download_rate
        self.runner = None

    def create_routes(self):
        self.server.router.add_get('', self.handle_root_request)
        self.server.router.add_get('/chunks/{chunk_hash}', self.handle_chunk_request)

    async def update_file_store(self, file_store):
        self.file_store = file_store

    async def handle_root_request(self, request):
        return aiohttp.web.Response(text="Online")

    async def handle_chunk_request(self, request):
        chunk_hash = request.match_info['chunk_hash']
        range_header = request.headers.get('Range')

        file = self.file_store.get_file(chunk_hash)
        if not file:
            return aiohttp.web.Response(status=404, text="Chunk not found")
        chunk = file.chunks[chunk_hash]
        if range_header:
            start, end = map(int, range_header.split('=')[1].split('-'))
            return await self.serve_content(request, file, start, end)
        else:
            return await self.serve_content(request, file, chunk.offset, chunk.offset + chunk.size - 1)

    async def serve_content(self, request, file: File, start, end):
        end = min(end, file.file_size)
        length = end - start + 1
        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-Range': f'bytes {start}-{end}/{file.file_size}',
            'Content-Length': str(length)
        }
        try:
            response = aiohttp.web.StreamResponse(status=206, headers=headers)
            await response.prepare(request)
            with open(file.file_path, 'rb') as f:
                f.seek(start)
                while start <= end:
                    chunk_size = min(1024 * 1024, end - start + 1)
                    data = f.read(chunk_size)  # Read in small chunks
                    await response.write(data)
                    start += len(data)
                    await asyncio.sleep(self.rate_limit(len(data)))
            await response.write_eof()
            return response
        except (ConnectionError, ConnectionResetError) as e:
            return aiohttp.web.Response(status=500, text="Connection error")


    def rate_limit(self, chunk_size):
        return max(chunk_size/self.download_rate, 0)

    async def run(self):
        self.runner = aiohttp.web.AppRunner(self.server)
        await self.runner.setup()
        site = aiohttp.web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        await aioconsole.aprint(f'File Server running on {self.host}:{self.port}')

    async def terminate(self):
        await self.server.shutdown()
        await self.server.cleanup()
        await self.runner.cleanup()





