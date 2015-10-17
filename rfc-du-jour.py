# -*- coding: utf-8 -*

#Inspired by https://tools.ietf.org/html/rfc439
#https://github.com/exponential-decay/rfc-du-jour

#multi-author:  https://tools.ietf.org/html/rfc6998
#non-existant:  https://tools.ietf.org/html/rfc7000
#standard-test: https://tools.ietf.org/html/rfc6998
#no title:      https://tools.ietf.org/html/rfc1849
#email:         https://tools.ietf.org/html/rfc4263

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
            
            if name == self.dcCreator:
               if content != '':
                  self.author.append(content)

            if name == self.dcIssued:
               self.tweetdata['issued'] = content

         self.tweetdata['author'] = self.author
   
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
def returnURL(req, RFCNO=False):
   code = ''

   try:
      response = urllib2.urlopen(req)
   except urllib2.HTTPError as e:
      if RFCNO == False:
         sys.stderr.write(str(e.code) + " response code from index request." + "\n")
      if RFCNO == True:
         if e.code == 404:
            sys.stderr.write("RFC: " + str(1234) + " does not exist.\n")
      sys.exit(0) 

      #return not found
      #reseed the url, send a new request
      #else read the data we want

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

def returnRFCHTML(indexparser, rfcnumber):
   req = createRFCRequest(rfcnumber)

   response = returnURL(req, True)
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
   author = parser.tweetdata['author'][0]
   if len(parser.tweetdata['author']) > 1:
      author = author + " et al."
   else:
      author = author
   return author

def create_tweet(parser, rfctitle, rfcurl, author):
   tweet = rfctitle + " " + parser.tweetdata['title'] + ". " + author + " " + parser.tweetdata['issued'] + " "  + rfcurl 
   return tweet


html = createFindLatestRFCRequest().read()

indexparser = LatestRFCParser()
indexparser.feed(html)

if compareLatest(indexparser.maxRFC):
   writeLatest(parser.maxRFC)
   #something here about writing a new tweet about a new RFC

random.seed()
rfcnumber = random.randrange(1, indexparser.maxRFC)

parser = returnRFCHTML(indexparser, rfcnumber)

author = create_author_string(parser)
rfctitle = rfc_title(rfcnumber)
rfcurl = rfc_url(rfcnumber)

print create_tweet(parser, rfctitle, rfcurl, author)

