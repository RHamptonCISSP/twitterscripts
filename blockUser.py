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
#the try catch failed to stop the warnings from argparse
try:
    parser = argparse.ArgumentParser(description='follows specified twitter user and adds to the twitterbot sqlite database')
    parser.add_argument('-u', '--user', help='the twitter user to follow', action='store', type=str)
    args = parser.parse_args()
except TypeError as f:
    if 'not all arguments converted during string formatting' in f.reason:
        logger.warn("Incorrect number of arguments")

targetUser=str(args.user)

interestingList=[]

interestingList.append(targetUser)

interestingList.sort()
logger.info("interesting list: ", interestingList)
logger.info("seeded . . . continuing until stopped")

for interestingUser in interestingList:
	interestingUser = interestingUser.rstrip()
	logger.info("interestingUser " + interestingUser)

friendsList=[]
#removed code for appending to friendsList because friendship doesn't matter when I'm blocking

logger.debug(str([c for c in interestingList if c not in friendsList]))
targetList = [c for c in interestingList if c not in friendsList]

logger.info("Length of targetList is "+str(len(targetList))+"")
#interesting the list is None and has len of 1 if empty.  Tried not list instead and it did not work. Tried targetList==None and also did not work. 
#if len(targetList)==0:
if interestingUser=="None":
    logger.info("Nobody to block.  -u argument is  "+targetUser)
    sys.exit(0)
        
#and now we block the targets
def get_api(cfg):
  auth = tweepy.OAuthHandler(cfg['consumer_key'], cfg['consumer_secret'])
  auth.set_access_token(cfg['access_token'], cfg['access_token_secret'])
  return tweepy.API(auth)

#credits to https://martin-thoma.com/configuration-files-in-python/
#and https://stackoverflow.com/questions/2835559/parsing-values-from-a-json-file
with open('twitterbot.config') as json_data_file:
	data=json.load(json_data_file)
	cfg=data["cfg"]	

conn = sqlite3.connect('twitterbot.db')
cur = conn.cursor()

api = get_api(cfg)
if(api.verify_credentials):
    logger.info('We sucessfully logged in')


for targetUser in targetList:
        try:
            i = datetime.datetime.now()
	    timestamp = int(time.time())

	    if targetUser == 'RHamptonCISSP':
		logger.debug("Cannot block yourself.  Skipping targetUser "+targetUser)
                continue

	    else:
		fulluser = api.get_user(targetUser,include_entities=1)
		targetUserID=str(fulluser.id)
	        #cur.execute("INSERT INTO users (id, ScreenName, whitelisted, followsMe, lastUpdate) VALUES ("+targetUserID+",'"+targetUser+"',0,3,"+str(timestamp)+")")
                cur.execute("DELETE from users WHERE ScreenName='"+targetUser+"'")
                rowsdeleted=cur.rowcount
                if (rowsdeleted <> 1):
                    conn.rollback()
                    logger.debug("rolled back because rowcount was "+str(cur.rowcount)+".")
        
                if (rowsdeleted == 1):
                    logger.debug("rows 1")
                    conn.commit()
        #the commit in the middle may change the rowcount to 0 so this block has to go second.
        #I had another bug so not 100% sure it is true but it works this way so why switch it?
        
                #create_block will also unfriend the user
                api.create_block(targetUser)
                time.sleep(5)
                logger.info("Blocked (and unfollowed) " + targetUser)

                #if counter % 5 == 0:
                    #logger.info('Waiting 60 seconds between next unfollow every 5 unfollows \nbecause Twitter doesn\'t like spammers. Clients are only allowed \n350 requests every hour. So, about 5.83 unfollows a minute.')
                    #time.sleep(60)

        except StopIteration:
    	    logger.info("Exiting loop")
    	    break
    
        except (Timeout, ReadTimeoutError, ConnectionError):
            logger.warn('We got a timeout ... Sleeping for 15 minutes')
	    logger.warn("Current date & time = %s" % i)
            time.sleep(15*60)
            continue	
    
        except TweepError as e:
            if 'Sorry, that page does not exist' in e.reason:
               logger.warn("TweepError says page does not exist.  Could be username contains special characters.  Continuing")
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

        except ValueError:
            logger.error('ValueError. Twitter is unhappy with us.')
            continue

        except:
    	    logger.critical("Unexpected error while blocking user:", sys.exc_info()[0])
            raise

#reminder SQLite is ACID compliant.  Doesn't matter if you error out.
conn.close()
