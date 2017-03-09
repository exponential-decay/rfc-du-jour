﻿#!/usr/bin/python
# -*- coding: utf-8 -*

import os
from twitter import *

#Twitter pieces
def twitter_authentication():
	CONSUMER_KEYS = os.path.expanduser('.twitter-consumer-keys')
	CONSUMER_KEY, CONSUMER_SECRET = read_token_file(CONSUMER_KEYS)

	MY_TWITTER_CREDS = os.path.expanduser('.twitter-rfc-du-jour-credentials')
	if not os.path.exists(MY_TWITTER_CREDS):
		oauth_dance("rfc-du-jour", CONSUMER_KEY, CONSUMER_SECRET, MY_TWITTER_CREDS)

	oauth_token, oauth_secret = read_token_file(MY_TWITTER_CREDS)
	twitter = Twitter(auth=OAuth(oauth_token, oauth_secret, CONSUMER_KEY, CONSUMER_SECRET))
	
	return twitter

