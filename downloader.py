from urllib.parse import urlparse
import aiofiles
import aiohttp
import asyncio
import os


class Downloader:
    def __init__(self, urls, username):
        self.object = object

        self.urls = urls

        self.username = username

        asyncio.run(self.downloader(self.urls, self.username))

    async def downloader(self, urls, username):

        if not os.path.exists(username):
            os.mkdir(username)
            print('creating {} directory'.format(username))

            for url in urls:

                parsed_url = urlparse(url)
                path = parsed_url.path
                split_path = path.split('/')

                if len(split_path) <= 2:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as response:

                            f = await aiofiles.open(username + '/' + split_path[1], mode='wb')
                            await f.write(await response.read())
                            return await f.close()
