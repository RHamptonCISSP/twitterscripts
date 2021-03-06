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

#https://docs.python.org/3/library/argparse.html was easier to grok than getopt
#and this helped too http://techs.studyhorror.com/python-parsing-command-line-arguments-i-142
targetUser = ''
parser = argparse.ArgumentParser(description='Finds and writes to a file all the followers of a specific twitter user')
parser.add_argument('-u', '--user', help='the twitter user whose followers will be scraped', action='store', type=str)
parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.2')
args = parser.parse_args()
targetUser=args.user
print "Target user is '"+targetUser+"'"

#from logging tutorial 
#https://docs.python.org/3/howto/logging.html#logging-basic-tutorial
# create logger
logger = logging.getLogger('usetwitter.py')
logger.setLevel(logging.INFO)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

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

list= open('list.txt','w')

if(api.verify_credentials):
    logger.info('We sucessfully logged in')

#user = tweepy.Cursor(api.followers, screen_name="gdbassett").items()
user = tweepy.Cursor(api.followers, screen_name=targetUser).items()
counter=0
while True:
    try:
        i = datetime.datetime.now()
        u = next(user)
	list.write('Screen Name: ' + u.screen_name +' \n')
	fulluser=api.get_user(u.screen_name,include_entities=1)
	#unicodedescription = ((fulluser).description.__getstate__())
	unicodedescription = fulluser.description
	userdescription = unicodedescription.encode("ascii")
	list.write('Description: ' + userdescription +' \n')
	counter=counter+1
	if DEBUG == 1 and counter > 10:
		logger.debug("Halting!")
		break
    
    except UnicodeEncodeError:
	logger.warn("cannot decipher description")
	userdescription=""
	list.write('Description: ' + userdescription +' \n')
	counter=counter+1
        continue

    except StopIteration:
	logger.warn("Exiting loop")
	break

    except (Timeout, ReadTimeoutError, ConnectionError):
        logger.warn('We got a timeout ... Sleeping for 15 minutes')
        logger.warn("Current date & time = %s" % i)
        time.sleep(15*60)
        continue	

    except TweepError as e:
        if 'User not found.' in e.reason:
	   logger.warn("User " + u.screen_name + " not found.  Skipping.")
	   continue
        elif 'User has been suspended.' in e.reason:
	   logger.warn("User " + u.screen_name + " has been suspended.  Skipping.")
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
	elif 'page does not exist' in e.reason:
	    logger.error("Invalid user")
	    #do not raise - just exit loop here and end
	    #do not break
	    #print ""
	    list.close()
	    sys.exit(1)
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

list.close()

#Error Handling https://docs.python.org/3/tutorial/errors.html
# https://github.com/tweepy/tweepy/issues/617
# https://community.activestate.com/forum/using-python-how-do-i-terminate-stop-execution-my-script
#
#Clues necessary for the JSON part 
# https://groups.google.com/forum/#!topic/tweepy/WFrInVcowTM
# https://gist.github.com/TheSuggmeister/1941230
#
# Remember to pickle if you ever want to serialize
# https://docs.python.org/3/library/pickle.html
#
#These poor guys left their tokens on the net for anyone to copy
# http://alpha.ookook.net/sga-tweets/SGAcollect.py
#
# What twitter error codes mean
# https://dev.twitter.com/overview/api/response-codes
