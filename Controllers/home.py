import os
import datetime
import webapp2
import jinja2
import cgi
from google.appengine.ext import ndb
from google.appengine.api import users
from google.appengine.api import mail
import urllib
from google.appengine.api import urlfetch

import pprint
import json
from poster.encode import multipart_encode, MultipartParam
import urllib2
import base64
import re
from collections import OrderedDict
import csv
from Controllers import BingAPI
from Controllers import Diffbot
from Controllers import Alchemy
from Controllers import Tweets


class Articles(ndb.Model):
	articles = ndb.JsonProperty()
	tweets = ndb.JsonProperty()
	created = ndb.DateTimeProperty(auto_now_add=True)
	stockInfo = ndb.JsonProperty()

class Home1(webapp2.RequestHandler):

	def get(self):

		path = self.request.path
		
		#Get the Latest Queries
		query = Articles().query().order(-Articles.created)
		query = query.fetch_page(100)

		tmp = "home22.html"

		views = os.path.abspath(os.path.join(__file__, os.path.pardir, "../Views"))
		jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(views))
		
		template_values = {
				"path": path,
				"query":query
			}
		template = jinja_environment.get_template(tmp)
		
		#Render Page along with Values
		self.response.out.write(template.render(template_values))
		
		
	def post(self):
		#Twitter App Credentials		
		consumerKey = "6hl3xqvrwc5ElShe55hxQ"
		consumerSecret = "v0JYb5XHk2HIVNisHWUjuhmOOWgLWrLlP2FXGtuy4"
		
		key = consumerKey + ":" + consumerSecret
		
		api_key = base64.b64encode(key)
		
		#Get Authorization Token
		url = "https://api.twitter.com/oauth2/token"
		rpc = urlfetch.create_rpc(deadline=60)
		urlfetch.make_fetch_call(rpc,url,method=urlfetch.POST,headers={"Authorization": "Basic %s" %api_key},payload="grant_type=client_credentials")
		result = rpc.get_result()
		result = json.loads(result.content)
		accessToken = result["access_token"]
		
		#Get Stock Symbols
		searchQ = self.request.get("searchQ")
		
		#turn it into a list
		query = searchQ.split(",")
		
		#getting articles from bing
		bingInfo = []
		for q in query:
			bing = BingAPI(q,5)
			urls = bing.getArticles()
			bingInfo.append(urls)
		
			
		#using diffbot to extract article texts' for analysis
		aTexts=[]
		for a in bingInfo:
			diffbot = Diffbot(a)
			articleTexts = diffbot.getText()
			aTexts.append(articleTexts)
		
		#alchemy Bing
		aScores  = []
		for a in aTexts:
			alchemy = Alchemy(a)
			request = alchemy.getSentiment()
			bingData = alchemy.extractResults(request,query)
			aScores.append(bingData)
	
		print bingData
		
		#Use Token To Get Tweets
		lTweets = []
		for t in query:
			twitter = Tweets(t,accessToken)
			tweets = twitter.getTweets()
			lTweets.append(tweets)
		
		tScores = []
		for s in lTweets:
			#alchemy Twitter
			talchemy = Alchemy(tweets)
			trequest = talchemy.getSentiment()
			twitterData = talchemy.extractResults(trequest,query)
			tScores.append(twitterData)
		
		print tScores
		print aScores

		#Get Fundmentals from Yahoo Finance
		
		fData={
		"sSymbol":"s",
		"priceToSales":"p5",
		"peRatio":"r",
		"pegRatio":"r5",
		"priceEpsCurrentYear":"r6",
		"priceBook":"p6"
		}
		
		stockList = searchQ
		
		stockList = stockList.replace(",","+")
		
		url="http://finance.yahoo.com/d/quotes.csv?s="+stockList+"&f="+fData['sSymbol']+fData['priceToSales']+fData['peRatio']+fData['pegRatio']+fData['priceEpsCurrentYear']+fData['priceBook']
		result = urlfetch.fetch(url=url,method=urlfetch.GET)
		
		#breakdown results into a list of lists
		info = result.content
		info = re.split("\r|\n",info)
		info = [s for s in info if s != '']
		infoList = []
		for i in info:
			infoList.append(i.split(','))
		
		#Turn info into a well structured Dictionary		
		dInfo = {}
		tData = fData.keys()
		for i in infoList:
				i[0] = str(i[0])
				i[0] = i[0].replace('"','')
				dInfo.update({i[0]:{tData[2]:i[1],tData[3]:i[2],tData[0]:i[3],tData[1]:i[4],tData[5]:i[5]}})
		print dInfo
		
		
		#upload info to the database
		articles = Articles()
		articles.tweets = tScores
		articles.articles = aScores
		articles.stockInfo = dInfo
		articles.put()
		
		#Redirect Home Where the Results Are displayed
		self.redirect("/home")
		

		
		
		
		
		
		
		
