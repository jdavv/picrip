from urllib.parse import urlparse
from imgur_client import *
import aiofiles
import aiohttp
import asyncio
import time
import pathlib
import praw


class PicRip:
    """
    Create an instance of of reddit using the PRAW library. This will allow us to get all reddit users submissions
    easily and go from there with ripping any images
    """
    def __init__(self, reddit_bot):

        # user praw.ini for client authentication.
        self.reddit_bot = None
        # instantiate an instance of the reddit object
        self.reddit = praw.Reddit(reddit_bot)
        # known imgur domains
        self.imgur_domains = ['i.imgur.com', 'm.imgur.com', 'imgur.com']
        # list to store any submissions that match the domains in imgur_domains
        self.imgur_urls = []
        # store the album hashes
        self.imgur_album_hashes = []
        # final urls of any images to download
        self.urls_ready_to_download = []
        # temp list of urls with a content type of 'text/html'
        self.urls_requires_further_processing = []
        # redditor's username that will be scrapped
        self.username = None
        # hold all the returned urls get_user_post method
        self.unprocessed_posts = []
        # mime types that will be downloaded
        self.content_type_ready_to_download = [
            'image/jpeg',
            'image/png',
            'video/mp4',
            'image/gif',
            'video/mpeg',
            'video/webm',
        ]

        # mime type for urls that are not images
        self.content_type_further_processing = ['text/html']

    def set_username(self, username):
        """
        Calling this method changes the username to scape submissions
        :param username: string : redditor's username
        :return:
        """
        self.username = username

    def get_user_posts(self):
        """
        Call various methods on the reddit instance to create a list of user's submissions URLs
        https://praw.readthedocs.io/en/latest/code_overview/models/redditor.html#praw.models.Redditor.submissions
        :return:
        """
        for submission in self.reddit.redditor(self.username).submissions.new(limit=None):
            self.unprocessed_posts.append(submission.url)

    def length_of_list(self, list):
        """
        Quick method to return length of list
        :param list: any list that is an attribute of instance
        :return: integer : length of the list
        """
        return len(list)

    async def imgur_get_hash(self, url):
        """
        This method removes leading "/" and "/a/" from a URL path.
        :param url: string : url that has an imgur domain
        :return: string : 5 or 7 characters long
        """

        path = urlparse(url).path

        if path.startswith('/a/') and len(path) is 8:
            self.imgur_album_hashes.append(path[3:])

        else:
            if len(path) is 8:
                self.imgur_album_hashes.append(path[1:])


    async def imgur_api_call(self, album_hash):
        """
        For each imgur album request JSON from imgur's api
        Set your client id in imgur_client.py
        :param album_hash: string : 5 or 7 character album hash
        :return: function call to process_imgur_album_json with imgur album json
        """
        # Send these headers with the get requests, this will authorize our client with imgur's api
        headers = {'Authorization': imgur_client_id}
        # Imgur's API url
        imgur_api_url = 'https://api.imgur.com/3/'
        # Full path for each album
        full_path = '{0}album/{1}/images'.format(imgur_api_url, album_hash)

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(full_path) as response:

                if response.status == 200:
                    return await self.process_imgur_album_json(await response.json())

    async def process_imgur_album_json(self, imgur_json):
        """
        Iterate through dictionary or list of dictionaries and call check_url_response with each image url
        :param imgur_json: dictionary or list of dictionaries. JSON response from imgur API
        :return: function call to the check_url_response method of PicRip instance
        """
        for item in imgur_json.get('data'):
            self.urls_ready_to_download.append(item['link'])

    async def check_url_response(self, url):
        """
        Check the response of url, if response is 200 we continue and check the content type.
        :param url: a string that is the submission link
        :return:
        """

        async with aiohttp.ClientSession() as session:

            try:
                async with session.get(url) as response:

                    if response.status == 200:

                        if response.content_type in self.content_type_ready_to_download:
                            print(response.content_type, url)
                            self.urls_ready_to_download.append(url)

                        if response.content_type in self.content_type_further_processing:
                            self.urls_requires_further_processing.append(url)
                            print(response.content_type, url)

            except aiohttp.ClientConnectionError as exception:
                return print(exception)

    async def split_url_by_domain(self, url):
        """
        Check if url domain is in the attribute imgur_domains
        :param url: string :
        :return:
        """

        domain = urlparse(url).netloc

        if domain in self.imgur_domains:
            self.imgur_urls.append(url)
      

async def main():
    test = PicRip(reddit_bot='bot1')

    username = input("what username")

    test.set_username(username)
    test.get_user_posts()
    tasks = [test.check_url_response(url) for url in test.unprocessed_posts]
    print(test.length_of_list(test.urls_ready_to_download), 'are ready to download')
    print(test.length_of_list(test.urls_requires_further_processing), 'requires further operations')
    await asyncio.gather(*tasks, return_exceptions=False)
    domain_check = [test.split_url_by_domain(url) for url in test.urls_requires_further_processing]
    await asyncio.gather(*domain_check, return_exceptions=False)
    print(test.length_of_list(test.imgur_urls))
    get_hashes = [test.imgur_get_hash(url) for url in test.imgur_urls]
    await asyncio.gather(*get_hashes, return_exceptions=False)
    imgur_api_calls = [test.imgur_api_call(album_hash) for album_hash in test.imgur_album_hashes]
    await asyncio.gather(*imgur_api_calls, return_exceptions=False)

asyncio.run(main())
