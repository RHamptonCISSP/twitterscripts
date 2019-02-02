# script will search for liked/favorited tweets, select a 
# random subset of them and, if not already retweeted, 
# will retweet to increase engagement
import json
import logging
import random
import tweepy
import time
import datetime
from datetime import datetime, timedelta
import sys
from requests.exceptions import Timeout, ConnectionError
from requests.packages.urllib3.exceptions import ReadTimeoutError
from tweepy.error import TweepError

#from logging tutorial 
#https://docs.python.org/3/howto/logging.html#logging-basic-tutorial
# create logger
logger = logging.getLogger('retweet.py')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

interestingList=[] #interesting tweet IDs

def get_api(cfg):
  auth = tweepy.OAuthHandler(cfg['consumer_key'], cfg['consumer_secret'])
  auth.set_access_token(cfg['access_token'], cfg['access_token_secret'])
  return tweepy.API(auth)

#credits to https://martin-thoma.com/configuration-files-in-python/
#and https://stackoverflow.com/questions/2835559/parsing-values-from-a-json-file
with open('twitterbot.config') as json_data_file:
	data=json.load(json_data_file)
	cfg=data["cfg"]	

api = get_api(cfg)

if(api.verify_credentials):
    logger.info('We sucessfully logged in')

tup=()
counter=0

'''
Credits 

Paul Scott
http://paulscott.co.za/blog/imported-title-93/

Taeho Kang
http://tkang.blogspot.com/2011/01/tweepy-twitter-api-status-object.html

http://stackoverflow.com/questions/192109/is-there-a-function-in-python-to-print-all-the-current-properties-and-values-of
http://stackoverflow.com/questions/5449091/sending-out-twitter-retweets-with-python
'''

#print out each favorited tweet
#I've gotten as large as 897 tweets.  Maybe it goes as high as 3200
#See https://stackoverflow.com/questions/39840571/tweepy-get-list-of-favorites-for-a-specific-user
#And see https://twittercommunity.com/t/tweet-index-limits/49653
#you can do pages(9*4) for example
for page in tweepy.Cursor(api.favorites,id="RHamptonCISSP",wait_on_rate_limit=True,count=25).pages(4*4):
  for status in page:
    logger.info("\n-=-=-=-=-=-=-")

    Tdate = status.created_at
    Ttext = status.text
    TID=status.id
    Tretweeted=status.retweeted
    Tretweet_count=status.retweet_count
    #Tretweeted_status=status.retweeted_status
    if hasattr(status.user, 'screen_name'):
        user = status.user.screen_name
    else :
        user = "Unknown"
    line = [Tdate.isoformat(), Ttext.encode('utf8'), user.encode('utf8')]
    logger.info(line)
    logger.info("ID: " + str(TID))
    logger.info("Retweeted? . . . " + str(Tretweeted))
    logger.info("Retweet Count: " + str(Tretweet_count))
    
    if (Tretweeted == False and Tretweet_count>1):
        interestingList.append(status.id)
        logger.info("Added this tweet to interesting list")
    else:
        logger.info("Skipping this tweet")

logger.debug("BEFORE shuffle")
logger.debug("\n".join(map(str, interestingList)))
random.shuffle(interestingList)
logger.debug("AFTER shuffle")
logger.debug("\n".join(map(str, interestingList)))

logger.info("Count of interesting tweets is " + str(len(interestingList)))
maximum=10 #only retweet 10 tweets at a time.  Could be I don't need the -1 below
if len(interestingList) < maximum:
     maximum=len(interestingList)-1
logger.info("Retweeting " + str(maximum) + " of them.")
minimum=0
for x in xrange(minimum, maximum):
         try:
             logger.info("Retweeting tweet ID " + str(interestingList[x]))
             api.retweet(interestingList[x])
             time.sleep(5)
         except (Timeout, ReadTimeoutError, ConnectionError):
             logger.warn('We got a timeout ... Sleeping for 15 minutes')
             logger.warn("Current date & time = %s" % i)
             time.sleep(15*60)
             continue	
         except TweepError as e:
             if 'Failed to send request:' in e.reason:
                 logger.warn("TweepError was a timeout ... Sleeping for 15 minutes")
                 logger.warn("Current date & time = %s" % i)
                 time.sleep(15*60)
                 continue	
             elif 'Rate limit exceeded' in e.reason:
	         logger.warn("Rate limit exceeded ... Sleeping for 15 minutes")
                 logger.warn("Current date & time = %s" % i)
	         time.sleep(15*60)
	         continue
	     elif 'Over capacity' in e.reason:
    	        logger.warn("Twitter is over capacity ... Sleeping for 15 minutes")
	        logger.warn("Current date & time = %s" % i)
    	        time.sleep(15*60)
    	        continue
             elif 'already retweeted' in e.reason:
                 logger.warn("Tweet already retweeted.  Continuing")
		 continue
             elif 'You have been blocked' in e.reason:
		 logger.warn("User " + user + " blocks us.  Will unfollow LATER.  Continuing")
		 #unfollow here?
	         #unfollowList.append(user)
		 continue
             elif 'Not authorized' in e.reason:
		 logger.warn("Twitter says we are Not authorized. Pausing 1 minute")
                 logger.warn("Current date & time = %s" % i)
                 time.sleep(1*60)
		 continue
	     elif 'Invalid or expired token' in e.reason:
		 logger.error("Token is invalid or expired")
		 #do not raise - just exit loop here and end
		 break
             else:
	         logger.error("TweepError is not a timeout")
	         raise
         except:
	    logger.critical("Unexpected error while retweeting favorites:", sys.exc_info()[0])
            raise
