# -*- coding: utf-8 -*

#Inspired by https://tools.ietf.org/html/rfc439
#https://github.com/exponential-decay/rfc-du-jour

#multi-author:  https://tools.ietf.org/html/rfc6998
#non-existant:  https://tools.ietf.org/html/rfc7000
#standard-test: https://tools.ietf.org/html/rfc6998
#no title:      https://tools.ietf.org/html/rfc1849
#email:         https://tools.ietf.org/html/rfc4263
#curious        https://tools.ietf.org/html/rfc6471
#coffee         https://tools.ietf.org/html/rfc2324

import sys
import random
import urllib2
from HTMLParser import HTMLParser

# create a subclass and override the handler methods
# info on overriding: https://docs.python.org/2/library/htmlparser.html
class HTMLMetadataParser(HTMLParser):

   dcTitle = 'DC.Title'
   dcCreator = 'DC.Creator'
   dcIssued = 'DC.Date.Issued'

   #struct to build tweet
   tweetdata = {}
   author = []

   bAuth = False
   bTitle = False
   bIssued = False

   def handle_starttag(self, tag, attrs):

      #placeholder variables
      name = ''
      content = ''

      #read from the metadata tags
      if tag == 'meta':
         for x in attrs:         
            if x[0] == 'name':
               name = x[1]
            if x[0] == 'content':
               content = x[1].strip()

            if name == self.dcTitle:
               self.tweetdata['title'] = content
               self.bTitle = True 

            if name == self.dcCreator:
               if content != '':
                  self.author.append(content)
                  self.bAuth = True
      
            if name == self.dcIssued:
               self.tweetdata['issued'] = content
               self.bIssued = True

         if self.bAuth is True:
            self.tweetdata['author'] = self.author
         else: 
            self.tweetdata['author'] = None
         if self.bTitle is False:
            self.tweetdata['title'] = None   
         if self.bIssued is False:
            self.tweetdata['issued'] = None

class LatestRFCParser(HTMLParser):
   ietf = 'http://tools.ietf.org/html/'
   maxRFC = 0
   def handle_starttag(self, tag, attrs):
      if tag == 'a':
         for x in attrs:
            if x[0] == 'href':
               if self.ietf in x[1]:
                  val = int(x[1].replace(self.ietf, ''))
                  self.maxRFC = max(self.maxRFC, val)

#Create requests for IETF server
def createRFCRequest(no):
   url = 'https://tools.ietf.org/html/rfc' + str(no)
   req = urllib2.Request(url)
   req.add_header('User-Agent', '@rfcdujour')
   req.add_header('Range', 'bytes=0-6200') #we don't need the whole page
   return req

def createFindLatestRFCRequest():
   #index url lists all RFC requests for us...
   indexurl = 'https://tools.ietf.org/rfc/index'
   req = urllib2.Request(indexurl)
   req.add_header('User-Agent', '@rfcdujour')
   return returnURL(req)

#request web page for parsing later
def returnURL(req, RFCNO=False, RFC=0):
   code = ''
   try:
      response = urllib2.urlopen(req)
   except urllib2.HTTPError as e:
      if RFCNO == False:
         sys.stderr.write(str(e.code) + " response code from index request." + "\n")
         sys.exit(1) 
      if RFCNO == True:
         if e.code == 404:
            #page not found (potentially RFC wasn't issued)
            #reseed and return a new page...
            sys.stderr.write("RFC: " + str(RFC) + " does not exist.\n")
            returnRFCHTML(rfcToTweet(minRFC, maxRFC))
   return response

def compareLatest(current):
   f = open('latest.txt', 'rb')
   if current > int(f.read().strip()):
      f.close()
      return True
   return False

def writeLatest(current):
   f = open('latest.txt', 'wb')
   f.write(str(current))
   f.close()   

def returnRFCHTML(rfcnumber):
   req = createRFCRequest(rfcnumber)

   response = returnURL(req, True, rfcnumber)
   html = response.read()

   # This shows you the actual bytes that have been downloaded.
   content_range=response.headers.get('Content-Range')
   sys.stderr.write("Received: " + content_range + "\n")

   # instantiate the parser and feed it HTML
   parser = HTMLMetadataParser()
   parser.feed(html)

   return parser

def rfc_title(rfcnumber):
   rfcpart = "RFC" + str(rfcnumber)
   return rfcpart

def rfc_url(rfcnumber):
   urlpart = 'https://tools.ietf.org/html/rfc' + str(rfcnumber)
   return urlpart

def create_author_string(parser):
   if parser.tweetdata['author'] is not None:
      author = parser.tweetdata['author'][0]
      if len(parser.tweetdata['author']) > 1:
         author = author + " et al."
      else:
         author = author + "."
   else:
      sys.stderr.write("DC.Creator metadata tag not specified." + "\n")
      author = None   
   return author

def processauthor(author):
   if '@' in author:
      sys.stderr.write("Redacting author email." + "\n")
      author = author[0:author.find('<')].strip() + "."
   
   #additional exceptions if spotted
   #not sure if a good idea...   
   author = author.replace("<>, ","") #exception in #6471
   return author

def create_tweet(parser, rfctitle, rfcurl, author):
   
   HASHTAGS = " #ietf #computing" #17 Characters
   LABEL = rfctitle + " " 

   if parser.tweetdata['title'] is not None:   
      TITLE = parser.tweetdata['title'] + ". "
   else:
      TITLE = ""

   if author is not None:
      AUTHOR = processauthor(author) + " "
   else: 
      AUTHOR = ""
  
   if parser.tweetdata['issued'] is not None:
      ISSUED = parser.tweetdata['issued'] + " "
   else:
      ISSUED = ""

   tweetpart1 = LABEL + TITLE + AUTHOR + ISSUED
   
   currwidth = len(tweetpart1)
   ELIPSES = 4              
   ALLOWED = 101 
   TRUNCATE = ALLOWED - ELIPSES  #remaining space including spaces and hashtags and links
   if len(tweetpart1) > ALLOWED:
      sys.stderr.write("Tweet too long at: " + str(currwidth) + " characters. Truncating." + "\n")
      diff = currwidth - TRUNCATE
      titlelen = len(TITLE) - diff - ELIPSES
      tweetpart1 = LABEL + TITLE[0:titlelen].strip() + "... " + AUTHOR + ISSUED
   
   tweet = tweetpart1 + rfcurl + HASHTAGS   
   return tweet

def getLatestRFCNumber():
   html = createFindLatestRFCRequest().read()
   indexparser = LatestRFCParser()
   indexparser.feed(html)

   if compareLatest(indexparser.maxRFC):
      writeLatest(indexparser.maxRFC)
      sys.stderr.write("[NEW] RFC" + str(indexparser.maxRFC) + "." + "\n")
      print makeTweet(indexparser.maxRFC, True)

   return indexparser.maxRFC

def rfcToTweet(minRFC, maxRFC):
   #use the latest RFC number and RFC1 to find an RFC to tweet
   random.seed()
   rfcnumber = random.randrange(minRFC, maxRFC)   
   return rfcnumber

def makeTweet(rfcnumber, new=False):
   #read the RFC page
   parser = returnRFCHTML(rfcnumber)

   #We've an RFC and we can tweet it
   author = create_author_string(parser)
   rfctitle = rfc_title(rfcnumber)   
   if new == True:
      rfctitle = "[NEW] " + rfc_title(rfcnumber)
   rfcurl = rfc_url(rfcnumber)

   return create_tweet(parser, rfctitle, rfcurl, author)

#rfc numbers
minRFC = 1
maxRFC = getLatestRFCNumber()

rfcnumber = rfcToTweet(minRFC, maxRFC)

tweet = makeTweet(rfcnumber)
print tweet
