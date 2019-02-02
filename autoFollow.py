#Looks like 338 may be max to follow in a day.  Probably less
import sqlite3
import json
import logging
import tweepy
import time
import datetime
import signal
import sys
from requests.exceptions import Timeout, ConnectionError
from requests.packages.urllib3.exceptions import ReadTimeoutError
from tweepy.error import TweepError
from sqlite3 import IntegrityError

def sigint_handler(signal, frame):
    print 'Interrupted'
    sys.exit(0)
signal.signal(signal.SIGINT, sigint_handler)

#from logging tutorial 
#https://docs.python.org/3/howto/logging.html#logging-basic-tutorial
# create logger
logger = logging.getLogger('autoFollow.py')
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


def get_api(cfg):
  auth = tweepy.OAuthHandler(cfg['consumer_key'], cfg['consumer_secret'])
  auth.set_access_token(cfg['access_token'], cfg['access_token_secret'])
  return tweepy.API(auth)

#credits to https://martin-thoma.com/configuration-files-in-python/
#and https://stackoverflow.com/questions/2835559/parsing-values-from-a-json-file
with open('twitterbot.config') as json_data_file:
	data=json.load(json_data_file)
	cfg=data["cfg"]	
	wordsToMatch=data["wordsToMatchInProfiles"]	

logger.debug(str(wordsToMatch))
time.sleep(3)

api = get_api(cfg)
if(api.verify_credentials):
    logger.info('We sucessfully logged in')


file = open('list.txt', 'r')
strikecounter=0
#wordsToMatch=["infosec", "cyber" , "security" , "army" , "force" , "navy" , "naval" , "space" , "hack" , "pen" , "hat" , "black" , "white" , "grey" , "gray" , "privacy" , "intelligence" , "threat" , "research" , "malware" , "defense" , "terrorism" , "warfare" , "vet" , "tactic" , "operation" , "strategy" , "risk" , "vuln" , "awareness" , "discovery" , "crim" , "analys" , "cipher" , "encrypt" , "infragard" , "federal" , "issa" , "isc2" , "martial" , "ciso" , "cio" , "cso" , "cto" , "cro" , "sides" , "conf" , "geek" , "nerd" , "dork" , "techie" , "maker" , "president" , "cissp" , "cism" , "cisa" , "ceh" , "linux" , "0day" , "ctf" , "editor" , "lawyer" , "attorney" , "jd" , "esq" , "founder" , "officer" , "ceo" , "pilot" , "commander" , "journalist" , "network" , "engineer" , "assurance" , "buckeye" , "executive" , "ninja" , "osint" , "owasp" , "cia" , "fbi" , "nsa" , "enthusias" , "incident" , "respon" , "gamer" , "maker" , "pgp" , "key" , "breach" , "opsec" , "fraud" , "abuse" , "sysadmin" , "freebsd" , "linux" , "kernel" , "crypto" , "cloud" , "coo", "esquire" , "professor" , "lecturer" , "python" , "policy" , "compliance" , "pci" , "hipaa" , "hitrust" , "phish" , "virus" , "trojan" , "worm" , "ware" , "exploit" , "pwn" , "phd" , "coffee" , "beer" , "ohio" , "giac" , "ics" , "scada" , "sans" , "nist" , "sox" , "oxley" , "ham" , "unix" , "brew" , "sirt" , "sides" , "defcon" , "crisc" , "ccsk" , "itil" , "csslp" , "isaca" , "vintage" , "venture" , "entreprenuer" , "trek" , "junkie" , "passion" , "usmc" , "marine" , "science" , "troop" , "nashville" , "tennessee" , "student" , "2600" , "sploit" , "remediat" , "red" , "dive" , "borg" , "developer" , "programmer" , "columbus" , "wars" , "forensic" , "revers" , "evangel" , "secret"]

interestingList=[]
screenName=""
descripton=""
for twitterLine in file.readlines():
    values = twitterLine.split(': ',1) #use 1 in case colon space in output
    try:
        remainder = values[1].replace("\r","")
        remainder = remainder.replace("\n","")
        if values[0] == "Description":
    	    #print "Description is " + values[1]
    	    logger.debug("Description is " + remainder)
	    description=remainder
            description=description.lower() #convert to lower case

            #assumes description comes after screen name is set on previous
	    #loop iteration
	    #check to see if description of user is interesting
	    #if so keep the screen name to see if can be followed later
	    counter=0
            for theWord in wordsToMatch:
	        theWord=theWord.lower()
	        if theWord in description:
		    screenName = screenName.replace(" ","")
	            interestingList.append(screenName)
		    logger.debug("Matched " + theWord)
	            logger.info("Adding " + screenName + " to list of interesting accounts")
		    screenName="" #re-initialize for next loop iteration
		    counter=counter+1
		    break
	    if counter==0:
                logger.debug("Screen Name " + screenName + "'s decription did not match.  Description: " + description)
		
        elif values[0] == "Screen Name":
    	    #print "Screen Name is " + values[1]
    	    logger.debug("Screen Name is " + remainder)
	    screenName=remainder
        else:
            #print "Unrecognized line %r" % values #print raw string
	    rawstring="Unrecognized line %r" % values
	    logger.error(rawstring.decode('string-escape'))
	    break
    except IndexError:
	#print "IndexError: Unrecognized line %r" % values #print raw string
	rawstring2="IndexError: Unrecognized line %r" % values
	logger.error(rawstring2.decode('string-escape'))
        continue
    except KeyboardInterrupt:
        print 'Interrupted'
        sys.exit(0)

file.close()

interestingList.sort()
logger.info("interesting list: ", interestingList)
logger.info("seeded . . . continuing until stopped")

for interestingUser in interestingList:
	interestingUser = interestingUser.rstrip()
	logger.info("interestingUser " + interestingUser)

#check if RHamptonCISSP is already friends with the user
#first load RHamptonCISSP's friends found by program  getUsersIFollow.py 
#and output to a database
# http://openbookproject.net/thinkcs/python/english3e/files.html
logger.debug("I AM HERE")
friendsList=[]
conn = sqlite3.connect('twitterbot.db')
cur = conn.cursor()

#file2 = open('UsersIFollowList.txt','r')
#for aline in file2.readlines():

cur.execute("select ScreenName from users")
for row in cur.fetchall():
    aline = str(row[0])
    aline = aline.replace("\r","")
    aline = aline.replace("\n","")
    aline = aline.replace(" ","")
    friendsList.append(aline)

#file2.close()
friendsList.sort()

#print [c for c in interestingList if c not in friendsList]
logger.debug(str([c for c in interestingList if c not in friendsList]))
targetList = [c for c in interestingList if c not in friendsList]

#print "Index for RHamptonCISSP in interestingList",interestingList.index('RHamptonCISSP')
logger.info(friendsList[0])
logger.info(friendsList[1])
logger.info(friendsList[2])
#print friendsList[0]
#print friendsList[1]
#print friendsList[2]

#print "Index for RHamptonCISSP in friendsList",friendsList.index('RHamptonCISSP')
logger.info("targetList element 0 is " + targetList[0])

#and now we follow the targets
for targetUser in targetList:
        try:
            i = datetime.datetime.now()
	    timestamp = int(time.time())

	    if targetUser == 'RHamptonCISSP':
                continue

	    else:
		fulluser = api.get_user(targetUser,include_entities=1)
		targetUserID=str(fulluser.id)
	        cur.execute("INSERT INTO users (id, ScreenName, whitelisted, followsMe, lastUpdate) VALUES ("+targetUserID+",'"+targetUser+"',0,3,"+str(timestamp)+")")
	        conn.commit()
                api.create_friendship(targetUser)
                logger.info("followed " + targetUser)

	except IntegrityError as ie:
	    logger.error("SQLite error: "+ie.message)
	    continue

        except KeyboardInterrupt:
            print 'Interrupted'
            sys.exit(0)

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
            elif 'User not found' in e.reason:
	       logger.warn("User not found. Skipping " + targetUser + ".") 
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
		raise
            else:
    	        logger.error("TweepError is not a timeout")
    	        raise
        except:
    	    logger.critical("Unexpected error:", sys.exc_info()[0])
            raise

conn.close()
