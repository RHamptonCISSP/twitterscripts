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
logger = logging.getLogger('followUser.py')
logger.setLevel(logging.INFO)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)


targetUser = ""
parser = argparse.ArgumentParser(description='follows specified twitter user and adds to the twitterbot sqlite database')
parser.add_argument('-u', '--user', help='the twitter user to follow', action='store', type=str)
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

logger.debug(str([c for c in interestingList if c not in friendsList]))
targetList = [c for c in interestingList if c not in friendsList]

#and now we follow the targets

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
	logger.info("Already following "+targetUser)

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
	        cur.execute("INSERT INTO users (id, ScreenName, whitelisted, followsMe, lastUpdate) VALUES ("+targetUserID+",'"+targetUser+"',0,3,"+str(timestamp)+")")
	        conn.commit()
                api.create_friendship(targetUser)
                logger.info("followed " + targetUser)

        except StopIteration:
    	    logger.info("Exiting loop")
    	    break
    
        except (Timeout, ReadTimeoutError, ConnectionError):
            logger.warn('We got a timeout ... Sleeping for 15 minutes')
	    logger.warn("Current date & time = %s" % i)
            time.sleep(15*60)
            continue	
    
        except TweepError as e:
            if 'follow yourself' in e.reason:
               logger.warn("You cannot follow yourself. Skipping " + targetUser + ".")
	       continue 
            elif 'blocked from following' in e.reason:
               logger.warn("You have been blocked from following this account at the request of the user. Skipping " + targetUser + ".") 
	       continue 
            elif 'spam or malicious activity' in e.reason:
               logger.warn("Followed too many people.  Stopping at " + targetUser + ".") 
	       break
            elif 'You are unable to follow more people at this time' in e.reason:
               logger.warn("Cannot follow more right now. Sleeping for 15 minutes at " + targetUser + ".")
	       logger.warn("Current date & time = %s" % i)
               time.sleep(15*60)
	       if strikecounter == 1:
	           logger.warn("Two strikes against us.  Stopping at "+targetUser)
                   break
	       else:
	   	   strikecounter = strikecounter+1
		   continue
            elif 'Cannot find specified user' in e.reason:
               logger.warn("Cannot find specified user " + targetUser + ". Skipping.")
	       continue
            elif 'User not found' in e.reason:
               logger.warn("User " + targetUser + " not found. Skipping.")
	       continue
            elif 'already requested to follow' in e.reason:
               logger.warn("Already a pending request to follow " + targetUser + ". Skipping.") 
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
