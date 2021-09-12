#!/usr/bin/python
# -*- coding: utf-8 -*

from __future__ import print_function

import os
import sys
import time
import random
import urllib2
import rfclist as rf
import pylisttopy as pl
import twitterpieces as tw

from HTMLParser import HTMLParser


# create a subclass and override the handler methods
# info on overriding: https://docs.python.org/2/library/htmlparser.html
class HTMLMetadataParser(HTMLParser):

    dcTitle = "DC.Title"
    dcCreator = "DC.Creator"
    dcIssued = "DC.Date.Issued"

    desc = "description"

    # struct to build tweet
    tweetdata = {}
    author = []

    bAuth = False
    bTitle = False
    bIssued = False

    def handle_starttag(self, tag, attrs):

        # Setup defaults but only once. We can remove this once other
        # dict handling is brought up to scratch.
        if not self.tweetdata.get("author"):
            self.tweetdata["author"] = None
        if not self.tweetdata.get("title"):
            self.tweetdata["title"] = None
        if not self.tweetdata.get("issued"):
            self.tweetdata["issued"] = None

        # placeholder variables
        name = ""
        content = ""

        # read from the metadata tags
        if tag == "meta":
            for x in attrs:
                if x[0].strip() == "name":
                    name = x[1].strip()
                if x[0].strip() == "content":
                    content = x[1].strip()

                if name == self.dcTitle:
                    if content:
                        self.tweetdata["title"] = content
                        self.bTitle = True

                # Version 2: This is temporary code to make up for changes
                # made by the IETF to the template which makes it harder
                # to access tweet data.
                if name == self.desc:
                    content = ""
                    for attr in attrs:
                        if attr[0].strip() == "content":
                            rfc_template = " (RFC )"
                            content = attr[1].strip()
                            if content.endswith(rfc_template):
                                content = content.replace(rfc_template, "")
                    if content and self.bTitle == False:
                        self.tweetdata["title"] = content
                        self.bTitle = True

                if name == self.dcCreator:
                    if content != "":
                        self.author.append(content)
                        self.bAuth = True

                if name == self.dcIssued:
                    self.tweetdata["issued"] = content
                    self.bIssued = True

            if self.bAuth is True:
                self.tweetdata["author"] = self.author


class LatestRFCParser(HTMLParser):

    rfclist_all = []

    def handle_data(self, data):
        """Read the contents of the HTML and look for specific data
        that contains an RFC number.
        """
        # Look for: doMainDocLink('RFC0001');
        #
        # Replace all the main elements and then take the RFC number.
        if "doMainDocLink" in data.strip():
            rfc_number = (
                data.strip()
                .replace("'", "")
                .replace("(", "")
                .replace(");", "")
                .replace("doMainDocLink", "")
                .replace("RFC", "")
            )
            rfc_number = rfc_number.lstrip("0")
            if rfc_number not in self.rfclist_all:
                self.rfclist_all.append(int(rfc_number))


# Read the RFC master index to return all the numbers
# of RFCs that have been submitted...
def createFindLatestRFCRequest():
    """Index url lists all RFC requests for us..."""
    indexurl = "https://www.rfc-editor.org/rfc-index.html"
    req = urllib2.Request(indexurl)
    req.add_header("User-Agent", "@rfcdujour")
    return return_url(req)


# We need to extract some metadata from the RFC HTML
# form. Authors, title, etc. Do that with this request
def createRFCRequest(no):
    url = "https://tools.ietf.org/html/rfc" + str(no)
    req = urllib2.Request(url)
    req.add_header("User-Agent", "@rfcdujour")
    req.add_header("Range", "bytes=0-6200")  # we don't need the whole page
    return req


# request web page for parsing later
def return_url(req, RFCNO=False, RFC=0):
    try:
        response = urllib2.urlopen(req)
    except urllib2.HTTPError as err:
        if RFCNO is False:
            print("{} response from index request".format(err), file=sys.stderr)
            sys.exit(1)
        if RFCNO is True:
            if err.code == 404:
                # page not found (potentially RFC wasn't issued)
                # reseed and return a new page...
                print("RFC: {} does not exist".format(RFC), file=sys.stderr)
            # could be something else but return false non-the-less...
            return False
    # we're looking good!
    return response


def test_and_return_html_response(rfcnumber):
    req = createRFCRequest(rfcnumber)
    response = return_url(req, True, rfcnumber)
    if response is False:
        return False
    return response


def read_rfc_html(response):
    html = response.read()

    # This shows you the actual bytes that have been downloaded.
    content_range = response.headers.get("Content-Range")
    print("Received: {}".format(content_range), file=sys.stderr)

    # instantiate the parser and feed it HTML
    parser = HTMLMetadataParser()
    parser.feed(html)

    return parser


def rfc_title(rfcnumber):
    rfcpart = "RFC{}".format(rfcnumber)
    return rfcpart


def rfc_url(rfcnumber):
    urlpart = "https://tools.ietf.org/html/rfc{}".format(rfcnumber)
    return urlpart


def create_author_string(parser):
    if parser.tweetdata["author"] is not None:
        author = parser.tweetdata["author"][0]
        if len(parser.tweetdata["author"]) > 1:
            author = "{} et al.".format(author)
        else:
            author = author + "."
        # Author list in parser is added to, so needs emptying after we have author
        del parser.tweetdata["author"][:]
    else:
        print("DC.Creator metadata tag not specified", file=sys.stderr)
        author = None
    return author


def processauthor(author):
    if "@" in author:
        print("Redacting author email", file=sys.stderr)
        author = author[0 : author.find("<")].strip() + "."

    # additional exceptions if spotted
    # not sure if a good idea...
    author = author.replace("<>, ", "")  # exception in #6471
    return author


def create_tweet(parser, rfctitle, rfcurl, author):

    HASHTAGS = " #ietf #computing"  # 17 Characters
    LABEL = "#" + rfctitle + " "

    if parser.tweetdata["title"] is not None:
        TITLE = parser.tweetdata["title"] + ". "
    else:
        TITLE = ""

    if author is not None:
        AUTHOR = processauthor(author) + " "
    else:
        AUTHOR = ""

    if parser.tweetdata["issued"] is not None:
        ISSUED = parser.tweetdata["issued"] + " "
    else:
        ISSUED = ""

    tweetpart1 = LABEL + TITLE + AUTHOR + ISSUED

    # N.B. Tweet with one link leaves 118 alphanumeric
    currwidth = len(tweetpart1)
    ELIPSES = 4
    # Allowed tweet length is 280 minus hashtags minus link length which is a constant 22.
    ALLOWED = 200
    TRUNCATE = (
        ALLOWED - ELIPSES
    )  # remaining space including spaces and hashtags and links
    if len(tweetpart1) > ALLOWED:
        print(
            "Tweet too long at: {} characters. Truncating".format(currwidth),
            file=sys.stderr,
        )
        diff = currwidth - TRUNCATE
        titlelen = len(TITLE) - diff - ELIPSES
        tweetpart1 = "{}{}... {}{}".format(
            LABEL, TITLE[0:titlelen].strip(), AUTHOR, ISSUED
        )

    tweet = tweetpart1 + rfcurl + HASHTAGS
    print("Tweet length: {}".format(len(tweet)), file=sys.stderr)
    return tweet


def getLatestRFC():
    html = createFindLatestRFCRequest().read()

    indexparser = LatestRFCParser()
    indexparser.feed(html)

    # create sets of our two lists to find new RFCs
    new_list = set(indexparser.rfclist_all)
    old_list = set(rf.rfclist)

    # Write a new list to our rfc list file.
    if len(new_list) > len(old_list):
        print("Writing new legacy RFC list", file=sys.stderr)
        script_dir = os.path.dirname(os.path.realpath(__file__))
        rfc_list_file = "rfclist"
        rfc_list = os.path.join(script_dir, rfc_list_file)
        lto = pl.ListToPy(
            set(indexparser.rfclist_all),
            rfc_list_file,
            rfc_list,
        )
        lto.list_to_py()

    return new_list - old_list


def rfcToTweet():
    # use the latest RFC number and RFC1 to find an RFC to tweet
    random.seed()
    rfcnumber = random.randrange(min(rf.rfclist), max(rf.rfclist))
    if rfcnumber not in rf.rfclist:
        print(
            "RFC Number not published, finding again. RFC: {}".format(rfcnumber),
            file=sys.stderr,
        )
        return rfcToTweet()
    return rfcnumber


# Go through the process of constructing our Tweet...
def makeTweet(rfcnumber, new=False):
    # read the RFC page
    response = test_and_return_html_response(rfcnumber)

    if response is False and new is False:
        return historical_rfc()

    if response is False and new is True:
        print(
            "Error retrieving [NEW] RFC{} returning and continuing".format(rfcnumber),
            file=sys.stderr,
        )
        return False

    parser = read_rfc_html(response)

    # We've an RFC and we can tweet it
    author = create_author_string(parser)
    rfctitle = rfc_title(rfcnumber)

    if new is True:
        rfctitle = rfc_title(rfcnumber) + " [NEW]"
    rfcurl = rfc_url(rfcnumber)

    return create_tweet(parser, rfctitle, rfcurl, author)


# Send the update to Twitter...
def tweet_update(twitter, tweet):
    twitter.statuses.update(status=tweet)


# Control the generation of historical RFC tweets
def historical_rfc():
    rfcnumber = rfcToTweet()
    print("RFC{}".format(rfcnumber), file=sys.stderr)
    tweet = makeTweet(rfcnumber)
    return tweet


def newRFC():
    """Generate a new RFC to post."""

    # List to store each of our Tweets in...
    tweets = []

    # Tweet historical RFC.
    tweets.append(historical_rfc())

    # Tweet new RFCs.
    newrfcs = getLatestRFC()
    if len(newrfcs) > 0:
        newrfcs = list(newrfcs)
        newrfcs.sort()
        for rfc in newrfcs:
            tweet = makeTweet(rfc, True)
            if tweet is not False:
                tweets.append(tweet)
                print("Tweet: {}".format(tweet), file=sys.stderr)

    return tweets


def main():
    """Primary entry point:

    ...do twitter things, make tweet...
    """
    twitter = tw.twitter_authentication()
    newtweets = newRFC()
    # Generate two tweets and post to timeline...
    for rfc in newtweets:
        if rfc is not False:
            """Tweet our RFCs."""
            tweet_update(twitter, rfc)
            time.sleep(10)


if __name__ == "__main__":
    main()
