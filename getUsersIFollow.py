import sqlite3
import json
import logging
import tweepy
import time
import datetime
import datetime
import sys
from requests.exceptions import Timeout, ConnectionError
from requests.packages.urllib3.exceptions import ReadTimeoutError
from tweepy.error import TweepError

#from logging tutorial 
#https://docs.python.org/3/howto/logging.html#logging-basic-tutorial
# create logger
logger = logging.getLogger('getUsersIFollow.py')
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

DEBUG=0

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
conn = sqlite3.connect('twitterbot.db')
cur = conn.cursor()

#list= open('UsersIFollowList2.txt','w',0)

if(api.verify_credentials):
    logger.info('We sucessfully logged in')

user_id = tweepy.Cursor(api.friends_ids, screen_name="RHamptonCISSP").items()
counter=0
while True:
    try:
	i = datetime.datetime.now()
        u = next(user_id)
	fulluser=api.get_user(u,include_entities=1)
	#reminder full object structure http://tkang.blogspot.com/2011/01/tweepytwitter-api-user-object-structure.html

        # users Table structure from create 
        #(id integer primary key, ScreenName varchar(255), whitelisted boolean, followsMe boolean, lastUpdate datetime)''')

        timestamp = int(time.time())
        #DOES NOT WORK cur.execute("insert into users (id, ScreenName, whitelisted, followsMe, lastUpdate) values ('fulluser.id','fulluser.screen_name',0,0,'timestamp')")
        #WORKS cur.execute("insert into users (id, ScreenName) values ("+str(fulluser.id)+",'"+fulluser.screen_name+"')")
        cur.execute("insert into users (id, ScreenName, whitelisted, followsMe, lastUpdate) values ("+str(fulluser.id)+",'"+fulluser.screen_name+"',0,3,"+str(timestamp)+")")
	#Ugly code above.  Must convert integer into a string to drop into an integer field.  The SQL statement is a string even if data will ultimately not be in the db

        # Save (commit) the changes
        conn.commit()

	#list.write('Screen Name: ' + fulluser.screen_name +' \n')

	counter=counter+1
	if (DEBUG>0 and counter > 10):
		logger.info("Halting!")
		break
	if counter > 12:
		logger.info("Pausing")
	        logger.info("Current date & time = %s" % i)
                time.sleep(60)
		counter=0
		continue

    #Trap this sometime 
    #sqlite3.OperationalError: table users has 5 columns but 1 values were supplied

    except StopIteration:
	logger.info("Exiting loop")
	break

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

#list.close()

# We can also close the connection if we are done with it.
# Just be sure any changes have been committed or they will be lost.
conn.close()
