import json
import logging
import sqlite3
import tweepy
import time
import datetime
from datetime import datetime, timedelta
import sys
import argparse
from requests.exceptions import Timeout, ConnectionError
from requests.packages.urllib3.exceptions import ReadTimeoutError
from tweepy.error import TweepError
import re

#from logging tutorial 
#https://docs.python.org/3/howto/logging.html#logging-basic-tutorial
# create logger
logger = logging.getLogger('findUsersToBlock.py')
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

DEBUG=1 #set to 1 to add debug logging; set to 2 to halt after 6 iterations
if DEBUG>0:
    logger.setLevel(logging.DEBUG)

#https://docs.python.org/3/library/argparse.html was easier to grok than getopt
#and this helped too http://techs.studyhorror.com/python-parsing-command-line-arguments-i-142
targetUser = ''
parser = argparse.ArgumentParser(description='Finds and writes to a file all the followers of a specific twitter user who should be blocked')
parser.add_argument('-u', '--user', help='the twitter user whose followers will be scraped', action='store', type=str)
parser.add_argument('-v', '--version', action='version', version='%(prog)s 1.2')
args = parser.parse_args()
targetUser=args.user
if targetUser==None:
     targetUser="RHamptonCISSP"

logger.info("Target user is '"+str(targetUser)+"'")

def get_api(cfg):
  auth = tweepy.OAuthHandler(cfg['consumer_key'], cfg['consumer_secret'])
  auth.set_access_token(cfg['access_token'], cfg['access_token_secret'])
  return tweepy.API(auth)

#credits to https://martin-thoma.com/configuration-files-in-python/
#and https://stackoverflow.com/questions/2835559/parsing-values-from-a-json-file
with open('twitterbot.config') as json_data_file:
	data=json.load(json_data_file)
	cfg=data["cfg"]
        #safeList=data["safeList"]
        wordsToMatch=data["wordsToMatchInTweets"]
	wordsToMatchP=data["wordsToMatchInProfiles"]	

api = get_api(cfg)
conn = sqlite3.connect('twitterbot.db')
cur = conn.cursor()

list= open('potentialblocklist.txt','w')

if(api.verify_credentials):
    logger.info('We sucessfully logged in')

#user = tweepy.Cursor(api.followers, screen_name="gdbassett").items()
user = tweepy.Cursor(api.followers, screen_name=targetUser).items()
counter=0
while True:
    try:
        strikes=0
        i = datetime.now()
        u = next(user)

	logger.info('Parsing Screen Name: ' + u.screen_name)
	fulluser=api.get_user(u.screen_name,include_entities=1)
	#unicodedescription = ((fulluser).description.__getstate__())
	unicodedescription = fulluser.description
	userdescription = unicodedescription.encode("ascii")
        logger.info('Description: '+str(userdescription))

        #may as well update follower timestamp
        timestamp = int(time.time())
        cur.execute("UPDATE users SET followsMe=1, lastUpdate="+str(timestamp)+" WHERE ScreenName='"+str(u.screen_name)+"'")
        logger.debug("rowcount: "+str(cur.rowcount))
        #nice hack here, if the rowcount is zero the user is not in the database and therefore not followed by me
        #note this logic must change if we ever make the script generic for another user to check their followers
        #if they are in the database then I follow them and they get strike - 1
        if cur.rowcount>0:
            logger.debug("I follow this user.  Strike -1")
            strikes=strikes-1
        else:
            logger.debug("I do not follow this user. Strikes unchanged.")
        conn.commit()

        #CODE GOES HERE
        #props to http://tkang.blogspot.com/2011/01/tweepytwitter-api-user-object-structure.html
        #are they verified?
        #'verified': False
        logger.info('Verified: '+str(u.verified))
        if u.verified==True:
            strikes=strikes-1
            logger.debug("Strikes -1 because user is verified.")
        else:
            logger.debug("Strikes unchanged because user is not verified.")


        #do they still use the egg as their profile pic?
        #'profile_use_background_image': True
        #'profile_background_image_url': 'ht
        #'profile_image_url': 'http://a1.t
        #https://developer.twitter.com/en/docs/accounts-and-users/user-profile-images-and-banners.html
        #https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png
        logger.info('Profile Image URL: '+str(u.profile_image_url))
        #FOR TESTING ONLY if re.search("RL7LPdNN_normal.jpg",str(u.profile_image_url)):
        if re.search("default_profile_normal.png",str(u.profile_image_url)):
            strikes=strikes+1
            logger.debug("Strikes +1 because user has default profile image aka the egg.")
        else:
            logger.debug("Strikes unchanged because the user has changed the profile image.")
                         

        #when did they join twitter?
        #'created_at': datetime.datetime(2010, 4, 14, 1, 20, 45)
        logger.info('Created at: '+str(u.created_at))
        d=datetime.today()-timedelta(days=365)
        if u.created_at>=d:
             logger.debug("Strikes+1 because the profile was created within the last year.")
             strikes=strikes+1
        else:
             logger.debug("Strikes unchanged because the profile is more than one year old.")

        #YEARS CODE GOES HERE
        current_year = int(datetime.now().year)
        logger.debug("Current year is "+str(current_year))
        dt = datetime.strptime(str(u.created_at), '%Y-%m-%d %H:%M:%S')
        years_on_twitter=current_year-dt.year
        logger.info("Years on twitter "+str(years_on_twitter))

        #how active are they on here over all time?
        #'statuses_count': 742
        #'favourites_count': 2
        logger.info('Number of tweets: '+str(u.statuses_count))
        logger.info('Number of likes: '+str(u.favourites_count))
        #only check for strikes if more than a year on twitter
        if (years_on_twitter>0):
            if (int(u.statuses_count/years_on_twitter)>9375):
                 logger.debug("More tweeting activity than expected.  Strikes+1")
                 strikes=strikes+1
            else:
                 logger.debug("Tweeting activity normal.  Strikes unchanged.")

            
            if (int(u.favourites_count/years_on_twitter)>5225):
                 logger.debug("More liking/favoriting than expected.  Strikes+1")
                 strikes=strikes+1
            else:
                 logger.debug("Liking/favoriting activity normal.  Strikes unchanged.")

        else:
            logger.debug("Less than a year on twitter.  Skipped checks for number of tweets and number of likes")

        #'followers_count': 80,
        #'friends_count': 133,
        logger.info('Followed by: '+str(u.followers_count))
        if (u.followers_count>10000):
             logger.debug("Number of followers greater than 10K.  Strikes+1.")
             strikes=strikes+1
        else:
             logger.debug("Number of followers less than 10K.  Strikes unchanged.")


        logger.info('Following: '+str(u.friends_count))
        #Note twitter puts a cap on people you can follow at 5000 so getting above this is difficult organically
        if (u.friends_count>6000):
             logger.debug("Number of people followed greater than 6K.  Strikes+1.")
             strikes=strikes+1
        else:
             logger.debug("Number of people followed less than 6K.  Strikes unchanged.")

        #'lang': 'en'
        logger.info('Language: '+str(u.lang))
        if (str(u.lang)=="en"):
             logger.debug("Language setting is English. Strikes unchanged.")
        else:
             logger.debug("Language setting is not English.  Strikes+1. ")
             strikes=strikes+1

        #do they have a sequence of 7+ digits in their name?  If so strike+1
        sn=str(u.screen_name)
        name=str(u.name)
        logger.debug("screen name is "+sn)
        logger.debug("name is "+sn)
        tempstrike=0
        match = re.search(r'\d\d\d\d\d\d\d', sn)
        if match:
            logger.debug("match group "+match.group()+" in screen name.  Strikes+1")
            strikes=strikes+1
            tempstrike=1
        else:
            logger.debug("match not found")

        if (name!=sn):
            match = re.search(r'\d\d\d\d\d\d\d', name)
            if match:
                logger.debug("match group "+match.group()+" in name.  Strikes+"+str(1-tempstrike))
                strikes=strikes+1-tempstrike #do not double up on strikes for this test
            else:
                logger.debug("match not found")

        #Is the user tweeting about stuff I like? And how active are they in a 72 hour period
        inner_counter=1
        day_counter=0
        #status_list = api.user_timeline(screen_name=sn,include_rts=1,count=100)
        status_list=[] #FOR DEBUGGING
        goodUser=False
        for status in status_list:
            try:
                printing_text = status.text.encode("utf-8")
                printing_text = printing_text.lower()
                printing_text = printing_text.replace("\r","")
                printing_text = printing_text.replace("\n","")
                logger.debug("User "+sn+" tweet number " + str(inner_counter) + ":" + printing_text)
                logger.debug("status id is " + str(status.id))
                logger.debug("status date is " + str(status.created_at)) #a datetime.datetime object
                #logger.debug("printing text is " + printing_text) #a datetime.datetime object
                d=datetime.today()-timedelta(days=1)
                if status.created_at>=d:
                    day_counter=day_counter+1
                    logger.debug("this status was within 24 HOURS")
                    for theWord in wordsToMatch:
                        theWord=theWord.lower()
                        theWord=theWord.encode("utf-8")
                        if theWord in printing_text and "http" in printing_text:
                            #interestingList.append(status.id)
                            goodUser=True
                            logger.debug("Matched " + str(theWord))
                            logger.debug("Adding " + str(status.id) + " to list of interesting tweets")
                            logger.debug("Adding " + sn + " to the list of safe users")
                            break #added to make more efficient
                        continue
                    #end for looop
                #end if
                inner_counter=inner_counter+1
            except TypeError:
                logger.warn("problem with message format")
                continue
            except UnicodeEncodeError:
                logger.warn("cannot convert tweet to ascii")
                continue
            except:
                logger.critical("Unexpected error:", sys.exc_info()[0])
                raise
            #end try
        #end for loop
        logger.debug("Day counter is "+str(day_counter))
        if (day_counter>99):
            logger.debug("Strike for being too active within 24 hours.") 
            strikes=strikes+1
        else:
            logger.debug("Strikes unchanged.  Activity normal in the last 24 hours.") 

        if goodUser==True:
             logger.debug("User does tweet about things I like. Strikes unchanged.")
             #break #stop after 1 iteration
        else:
             strikes=strikes+1
             logger.debug("User does NOT tweet about things I like. Strikes +1.")

        #if I do not see if they match profile (are they in infosec? if not strike+1)
	description=userdescription
        description=description.lower() #convert to lower case
	wordcounter=0
        for theWordP in wordsToMatchP:
	    theWordP=theWordP.lower()
	    if theWordP in description:
                logger.debug("Matched " + theWordP+" in description. Strikes unchanged.")
		wordcounter=wordcounter+1
		break
	if wordcounter==0:
            logger.debug("Decription did not match any words in our list.  Strike+1. Description: " + description)
            strikes=strikes+1


        #do they say marketing, CMO, actress, model, SEO or some other word like that?  if so strike+1
        wordsNotToMatch=('marketing','cmo','actress','actor','model','seo','influencer')
	wordcounter=0
        for theWordN in wordsNotToMatch:
	    theWordN=theWordN.lower()
	    if theWordN in description:
                logger.debug("Matched " + theWordN+" in description. Strikes+1. Description: "+description)
		wordcounter=wordcounter+1
                strikes=strikes+1
		break
	if wordcounter==0:
            logger.debug("Decription did not match any words in our bad list. Strikes unchanged.")
        

        #are they in TN,AL,MS,AR,KS,IA,OK? Nashville, Knoxville, Memphis, Chat?  if so remove strike-1
        #'location': 'Seoul Korea'
        # use same type of code as wordsToMatch
        logger.info('Location: '+str(u.location))
        location=str(u.location)
        #location=location.lower()
        wordsToMatchL=('York','Tennessee','TN','Alabama','AL','Mississippi','MS','Arkansas','AR','Kansas','KS','Georgia','GA','Florida','FL','Ohio','OH','Michigan','MI','Iowa','IA','Missouri','MO','Nashville','Memphis','Knoxville','Chattanooga','Columbus','Cincinnati','Akron','Lima','Dayton','Cleveland','Detroit','Lansing','Atlanta','Jackson','Birmingham','Huntsville','Decatur','Mobile','Rock','Little','Lawrence','City','Orlando','Lauderdale','Fort','Moines','Louis')
	wordcounter=0
        for theWordL in wordsToMatchL:
	    #theWordL=theWordL.lower()
	    if theWordL in location:
                logger.debug("Matched " + theWordL+" in location. Strikes-1.")
		wordcounter=wordcounter+1
                strikes=strikes-1
		break
	if wordcounter==0:
            logger.debug("Location did not match any words in our list. Strikes unchanged.")


        logger.debug("Strikes are "+str(strikes))
        if strikes>2:
            logger.info("Adding "+u.screen_name+" to the list of people to block.")
	    list.write('Screen Name: ' + u.screen_name +' \n')
	    list.write('Description: ' + userdescription +' \n')
        logger.debug("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")

	counter=counter+1
	if DEBUG == 2 and counter > 6:
		logger.debug("Halting!")
		break

    except UnicodeEncodeError:
	logger.warn("cannot decipher description")
	userdescription=""
	list.write('Description: ' + userdescription +' \n')
	counter=counter+1
        logger.debug("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
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
conn.close()

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
