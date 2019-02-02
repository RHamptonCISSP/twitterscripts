import sqlite3
import json
import logging
import tweepy
import time
import datetime
import sys
import argparse
from requests.exceptions import Timeout, ConnectionError
from requests.packages.urllib3.exceptions import ReadTimeoutError
from tweepy.error import TweepError

#from logging tutorial 
#https://docs.python.org/3/howto/logging.html#logging-basic-tutorial
# create logger
logger = logging.getLogger('unfollowUser.py')
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


targetUser = ""
parser = argparse.ArgumentParser(description='unfollows specified twitter user and deletes from the twitterbot sqlite database')
parser.add_argument('-u', '--user', help='the twitter user to unfollow', action='store', type=str)
args = parser.parse_args()
targetUser=str(args.user)

interestingList=[]

interestingList.append(targetUser)

interestingList.sort()
logger.info("interesting list: ", interestingList)
logger.info("seeded . . . continuing until stopped")

for interestingUser in interestingList:
	interestingUser = interestingUser.rstrip()
	logger.info("interestingUser " + interestingUser)

#check if RHamptonCISSP is already friends with the user
friendsList=[]
conn = sqlite3.connect('twitterbot.db')
cur = conn.cursor()

cur.execute("select ScreenName from users")
for row in cur.fetchall():
    aline = str(row[0])
    aline = aline.replace("\r","")
    aline = aline.replace("\n","")
    aline = aline.replace(" ","")
    friendsList.append(aline)

friendsList.sort()

#changed to 'in' instead of 'not in'
logger.debug(str([c for c in interestingList if c in friendsList]))
targetList = [c for c in interestingList if c in friendsList]

#and now we unfollow the targets

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

if len(targetList)==0:
	logger.info("Already unfollowed "+targetUser)

for targetUser in targetList:
        try:
            i = datetime.datetime.now()
	    timestamp = int(time.time())

	    if targetUser == 'RHamptonCISSP':
		logger.debug("Skipping targetUser "+targetUser)
                continue

	    else:
		fulluser = api.get_user(targetUser,include_entities=1)
		targetUserID=str(fulluser.id)
		#because we looked up the id, reduces chance of sql injection
	        cur.execute("DELETE FROM users WHERE id="+targetUserID+" AND ScreenName='"+targetUser+"'")
	        conn.commit()
                api.destroy_friendship(targetUser)
                logger.info("unfollowed " + targetUser)

        except StopIteration:
    	    logger.info("Exiting loop")
    	    break
    
        except (Timeout, ReadTimeoutError, ConnectionError):
            logger.warn('We got a timeout ... Sleeping for 15 minutes')
	    logger.warn("Current date & time = %s" % i)
            time.sleep(15*60)
            continue	
    
        except TweepError as e:
            if 'spam or malicious activity' in e.reason:
               logger.warn("Followed too many people.  Stopping at " + targetUser + ".") 
	       break
            elif 'Cannot find specified user' in e.reason:
               logger.warn("Cannot find specified user " + targetUser + ". Skipping.")
	       continue
            elif 'Failed to send request:' in e.reason:
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
	    elif 'Invalid or expired token' in e.reason:
		logger.error("Token is invalid or expired")
		#do not raise - just exit loop here and end
		break
            else:
    	        logger.error("TweepError is not a timeout")
    	        raise
        except:
    	    logger.critical("Unexpected error:", sys.exc_info()[0])
            raise

conn.close()
