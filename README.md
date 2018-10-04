PICRIP for reddit

PICRIP is a multi-threaded image ripper written in Python 3.7. (big changes to the asyncio library) PICRIP utilizes the PRAW 
library to gather all of a reddit user's submissions than search for JPG, PNG, GIF, MP4
files and download them into a directory named after that users reddit username.

PICRIP is capable of extracting all images out of any given imgur gallery as well as 
mp4 or gif files from gfycat links.

Please see the requirements.txt for prerequisite libraries.

You will need reddit API access : https://www.reddit.com/wiki/api

Also imgur API access : https://apidocs.imgur.com/#authorization-and-oauth

Currently this software will run as many threads as possible to max out network usage.

I don't plan on updating this project much, as it was coded as a personal exercise in 
utilizing concurrency in python.