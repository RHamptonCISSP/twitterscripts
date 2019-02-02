#!/usr/bin/env python
# very little borrowed from Glen Baker - iepathos@gmail.com
# Modified by RHampton on 6/29/2016
#script tries to find users to engage via favoriting tweets 
#also unfollows people who don't regularly tweet on national sec or infosec
#whitelists some users so they cannot be unfollowed
import sqlite3
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
from sets import Set

#from logging tutorial 
#https://docs.python.org/3/howto/logging.html#logging-basic-tutorial
# create logger
logger = logging.getLogger('unfriend.py')
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
interestingList=[] #interesting tweet IDs
unfollowList=[] #users to unfollow
engagedList=[] #users engaged

def get_api(cfg):
  auth = tweepy.OAuthHandler(cfg['consumer_key'], cfg['consumer_secret'])
  auth.set_access_token(cfg['access_token'], cfg['access_token_secret'])
  return tweepy.API(auth)

#credits to https://martin-thoma.com/configuration-files-in-python/
#and https://stackoverflow.com/questions/2835559/parsing-values-from-a-json-file
with open('twitterbot.config') as json_data_file:
	data=json.load(json_data_file)
	cfg=data["cfg"]	
	safeList=data["safeList"]
	wordsToMatch=data["wordsToMatchInTweets"]

logger.debug(str(wordsToMatch))
logger.debug(str(safeList))

api = get_api(cfg)
conn = sqlite3.connect('twitterbot.db')
cur = conn.cursor()

if(api.verify_credentials):
    logger.info('We sucessfully logged in')

#populate array of users from the database 
users=[]
#cur.execute("SELECT ScreenName FROM users WHERE followsMe=3") #3 is unknown
#cur.execute("SELECT ScreenName FROM users WHERE followsMe in (0, 3) AND lastUpdate > 1507766400") #3 is unknown
cur.execute("SELECT ScreenName FROM users WHERE followsMe in (0, 3)") #3 is unknown
for row in cur.fetchall():
    twitterLine = str(row[0])
    twitterLine = twitterLine.replace("\r","")
    twitterLine = twitterLine.replace("\n","")
    logger.debug("Screen name is " + twitterLine)
    users.append(twitterLine)

'''
looks like even though docs for tweepy 3.5.0 say exists_friendship works
the method is deprecated in favor of show_friendship
python
import tweepy
tweepy.__version__    will output version number

API.exists_friendship(user_a, user_b)
Checks if a friendship exists between two users. 
Will return True if user_a follows user_b, otherwise False.

instead you use show_friendship which returns a Friend object
turns out that is a tupple and inside are attributes followed_by and following
if followed_by = True then we keep them as a friend
if followed_by = False we dump them or drum up attention
'''

counter=0
logger.debug(users)

random.shuffle(users)
tup=()
for user in users:
     logger.info("-=-=-=-=-=-=-")
     engagedList.append(user)
     if "defcon" in user:
          safeList.append(user)
     if "BSides" in user:
          safeList.append(user)
     if "Bsides" in user:
          safeList.append(user)
     if "ISSA" in user:
          safeList.append(user)
     if "CISSP" in user:
          safeList.append(user)
     if "cissp" in user:
          safeList.append(user)
     if "ISACA" in user:
          safeList.append(user)
     if user == "RHamptonCISSP":
          safeList.append(user)
	  logger.info("Adding " + user + "to the list of safe users")
          continue
     else:
         tup=()
	 i = datetime.now()
         #DEPRECAATED boolean=api.exists_friendship(user,"RHamptonCISSP")
	 #
	 #RETURNS two Friendship objects
         #tup=api.show_friendship(source_screen_name="RHamptonCISSP",target_screen_name=user)
	 #also returns two Friendship objects.  First one is RHamptonCISSP and second is user we care about.  followed_by field is not correct.  Use following
         try:
             tup=api.show_friendship(target_screen_name=user)
             logger.debug("Screen name "+user+" object dump",tup[1])
             #getattr(object, name[, default])
	     boolean=getattr(tup[1],"following")
	     #is truly a boolean.  you can test this by trying to concat with + below instead of comma
             logger.info("Does "+user+" follow RHamptonCISSP? . . . " + str(boolean))
	     #reinitialize for next loop
	     del tup
             timestamp = int(time.time())
	     if boolean == True:
                 safeList.append(user)
		 cur.execute("UPDATE users SET followsMe=1, lastUpdate="+str(timestamp)+" WHERE ScreenName='"+user+"'")
                 conn.commit()
	         logger.info("Adding " + user + "to the list of safe users")
		 
	     if boolean == False:
		 cur.execute("UPDATE users SET followsMe=0, lastUpdate="+str(timestamp)+" WHERE ScreenName='"+user+"'")
                 conn.commit()

                 counter=counter+1 #only increment if not following
	         #Engage!
	         inner_counter=1

                 status_list = api.user_timeline(screen_name=user,include_rts=1,count=5)
	         for status in status_list:
                     try:
		         printing_text = status.text.encode("utf-8")
		         printing_text = printing_text.lower()
		         printing_text = printing_text.replace("\r","")
		         printing_text = printing_text.replace("\n","")
                         logger.info("User "+user+" tweet number " + str(inner_counter) + ":" + printing_text)
		         logger.info("status id is " + str(status.id))
		         logger.info("status date is " + str(status.created_at)) #a datetime.datetime object
		         d=datetime.today()-timedelta(days=7)
		         inner_counter=inner_counter+1
		         if status.created_at>=d:
                             logger.info("this status was within the LAST WEEK")
                             for theWord in wordsToMatch:
	                         theWord=theWord.lower()
			         theWord=theWord.encode("utf-8")
	                         if theWord in printing_text and "http" in printing_text:
	                             interestingList.append(status.id)
			             safeList.append(user)
		                     logger.debug("Matched " + theWord)
	                             logger.info("Adding " + str(status.id) + " to list of interesting tweets")
			             logger.info("Adding " + user + " to the list of safe users")
				     break #added to make more efficient
		                 continue
                     except TypeError:
	                 logger.warn("problem with message format")
                         continue
                     except UnicodeEncodeError:
	                 logger.warn("cannot convert tweet to ascii")
                         continue
		     except:
    	                 logger.critical("Unexpected error:", sys.exc_info()[0])
                         raise
             boolean=False #reinitialize
	     if counter==50:
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
             elif 'User not found' in e.reason:
		 logger.warn("User " + user + " not found.  Continuing")
		 continue
             elif 'You have been blocked' in e.reason:
		 logger.warn("User " + user + " blocks us.  Will unfollow.  Continuing")
	         unfollowList.append(user)
		 continue
             elif 'Not authorized' in e.reason:
		 logger.warn("Twitter says we are Not authorized. Pausing 1 minute")
                 logger.warn("Current date & time = %s" % i)
                 time.sleep(1*60)
		 continue
	     elif 'Invalid or expired token' in e.reason:
	  	 logger.error("Token is invalid or expired")
		 #do not raise - just exit loop here and end
		 #do not break - if you exit here program continues
                 conn.close()
		 sys.exit(1)
             else:
	         logger.error("TweepError is not known or understood")
	         raise
         except:
	    logger.critical("Unexpected error:", sys.exc_info()[0])
            raise


logger.info("Count of interesting tweets is " + str(len(interestingList)))
maximum=5 #favorite 5 tweets at a time
if len(interestingList) < maximum:
     maximum=len(interestingList)-1
minimum=0
logger.info("Favoriting " + str(maximum) + " of them")
for x in xrange(minimum, maximum):
    try:
        api.create_favorite(interestingList[x])
        time.sleep(5)
        logger.info("Created favorite for tweet ID " + str(interestingList[x]))
    except TweepError as e:
         if 'already favorited' in e.reason:
             logger.warn("tweet already a favorite")
	 continue
    except:
         logger.critical("Unexpected error while favoriting tweets:", sys.exc_info()[0])
         raise


logger.info("Comparing users and safeusers")
for person in engagedList:
     if person not in safeList:
          logger.info("Going to unfollow " + person)
	  unfollowList.append(person)
     else:
          logger.info("Going to leave alone " + person)


for safeUser in Set(safeList):
    logger.info("Safe user " + safeUser)

for friend in unfollowList:
    try:
        cur.execute("DELETE from users WHERE ScreenName='"+friend+"'")
	rowsdeleted=cur.rowcount
	if (rowsdeleted <> 1):
	    conn.rollback()
	    logger.debug("rolled back because rowcount was "+str(cur.rowcount)+".")

	if (rowsdeleted == 1):
	    logger.debug("rows 1")
	    conn.commit()
#the commit in the middle may change the rowcount to 0 so this block has to go second.  
#I had another bug so not 100% sure it is true but it works this way so why switch it?

        api.destroy_friendship(friend)
        time.sleep(5)
        logger.info("Unfollowed " + friend)
        counter += 1

        if counter % 5 == 0:
            logger.info('Waiting 60 seconds between next unfollow every 5 unfollows \nbecause Twitter doesn\'t like spammers. Clients are only allowed \n350 requests every hour. So, about 5.83 unfollows a minute.')
            time.sleep(60)

    except ValueError:
        logger.error('ValueError. Twitter is unhappy with us.')
	continue

    except TweepError as e:
        if 'Sorry, that page does not exist' in e.reason:
            logger.warn("TweepError says page does not exist.  Could be username contains special characters.  Continuing")
	    continue

    except:
        logger.critical("Unexpected error while unfriending users:", sys.exc_info()[0])
        raise

#reminder SQLite is ACID compliant.  Doesn't matter if you error out.
conn.close()
