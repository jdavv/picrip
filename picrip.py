from urllib.parse import urlparse
from imgur_client import *
import aiofiles
import aiohttp
import asyncio
import time
import pathlib
import praw


class PicRip:

    def __init__(self, reddit_bot, username):
        """
        :param reddit_bot: string : name of credentials for reddit's API located in the praw.ini file
        :param username: string : name of reddit user
        """
        # user praw.ini for client authentication.
        self.reddit_bot = reddit_bot
        # instantiate an instance of the reddit object
        self.reddit = praw.Reddit(reddit_bot)
        # known gfycat domain
        self.gfycat_domain = ['gfycat.com']
        # gfycat urls that need an api call
        self.gfycat_urls = []
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
        self.username = username
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

        # spin it up on init
        asyncio.run(self.run())

    async def run(self):
        """
        This function is called upon initialization of the PicRip class.
        Sorts URLs and handles API calls asynchronously to create the class attribute
        of urls_ready_to_download.
        :return:
        """
        print('Getting posts for {}'.format(self.username))
        self.get_user_posts()

        tasks = [self.check_url_response(url) for url in self.unprocessed_posts]
        await asyncio.gather(*tasks, return_exceptions=False)

        domain_check = [self.sort_url_by_domain(url) for url in self.urls_requires_further_processing]
        await asyncio.gather(*domain_check, return_exceptions=False)

        get_hashes = [self.imgur_get_hash(url) for url in self.imgur_urls]
        await asyncio.gather(*get_hashes, return_exceptions=False)

        imgur_api_calls = [self.imgur_api_call(album_hash) for album_hash in self.imgur_album_hashes]
        await asyncio.gather(*imgur_api_calls, return_exceptions=False)

        gfycat_api_calls = [self.gfycat_get_json(url) for url in self.gfycat_urls]
        await asyncio.gather(*gfycat_api_calls, return_exceptions=False)

    def get_user_posts(self):
        """
        Call various methods on the reddit instance to create a list of user's submissions URLs
        https://praw.readthedocs.io/en/latest/code_overview/models/redditor.html#praw.models.Redditor.submissions
        :return:
        """
        for submission in self.reddit.redditor(self.username).submissions.new(limit=None):
            self.unprocessed_posts.append(submission.url)

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
        # Combine API URL and the album hash into a URL for Imgur's API
        full_path = '{0}album/{1}/images'.format(imgur_api_url, album_hash)

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(full_path) as response:

                if response.status == 200:
                    await self.process_imgur_album_json(await response.json())

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
                            self.urls_ready_to_download.append(url)

                        if response.content_type in self.content_type_further_processing:
                            self.urls_requires_further_processing.append(url)

            except aiohttp.ClientConnectionError as exception:
                return print(exception)

    async def gfycat_get_json(self, url):
        """
        Make request to the gfycat api for json
        :param url: string : url to gfycat
        :return: call to gfycat_json_url_to list to process json
        """
        api_url = 'https://api.gfycat.com/v1/gfycats{}'.format(urlparse(url).path)

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:

                if response.status == 200:
                    await self.gfycat_json_url_to_list(await response.json())

    async def gfycat_json_url_to_list(self, json):
        """
        Get the value for the mp4Url and append to urls_ready_to_download list.
        :param json:
        :return: gfycat_mp4 : string : is appended to urls_ready_to_download list
        """
        gfycat_mp4 = (json.get('gfyItem').get('mp4Url'))

        return self.urls_ready_to_download.append(gfycat_mp4)

    async def sort_url_by_domain(self, url):
        """
        Check if url domain is in the attribute imgur_domains or attribute gfycat_domain
        :param url: string :
        :return:
        """
        domain = urlparse(url).netloc

        if domain in self.imgur_domains:
            self.imgur_urls.append(url)

        if domain in self.gfycat_domain:
            self.gfycat_urls.append(url)


def main():
    """
    Create objects from the username list
    :return: call print_all_urls with a list of objects
    """
    usernames = []
    user_objects = []

    for username in usernames:
        username = PicRip(reddit_bot='bot1', username=username)
        user_objects.append(username)

    return print_all_urls(user_objects)


def print_all_urls(user_objects):
    """
    Iterate through the list attribute urls_ready_to_download from each object
    :param user_objects: a list of PicRip instances
    :return: prints url to stdout
    """
    for user_object in user_objects:
        for url in user_object.urls_ready_to_download:
            print(url)


if __name__ == "__main__":
    main()
