def csv_generator(wdir,crypto_sub,current_round,daily_hour,days_ago):
'''This function returns csv files with post, comment and daily thread 24-hour data from crypto_sub.

   Inputs:
   wdir [str]: working directory
   crypto_sub [str]: name of the sub, e.g. ethtrader
   current_round [int]: current round #
   daily_hour [int]: starting hour for the scrapper. Default for ethtrader is 23, i.e. it starts at 23h (or 11 p.m.) of days_ago
   days_ago [int]: starting day. Default for ethtrader is 2, i.e. it fetches data starting 48h ago and ending 24h ago, with a starting time set by daily_hour.

   Output:
   posts_DATE.csv
   comments_DATE.csv
   daily_DATE.csv
   
   NOTES: 
   Insert your API key data on lines 36-41 and 90-95.
   For optimal use, set this function as a task to be run every day at a fixed time whose hour > daily_hour.
   
   author: reddito321
   
'''
  
  import praw
  from datetime import datetime, timedelta
  import numpy as np
  import pandas as pd
  import time
  import os
  
  begin_date = datetime(datetime.today().year, datetime.today().month, datetime.today().day, daily_hour, 0)  +timedelta(days=-days_ago)
  end_date = begin_date+timedelta(hours=23,minutes=59,seconds=59)
  
  # current_round=int(np.loadtxt("/home/mydonuts/current_round.txt"))
  
  r = praw.Reddit(client_id=,
              client_secret=,
              user_agent=,
              password=,
              username=,
              check_for_async=False)
  
  # Posts
  sub_pscore = 0
  posts = []
  for submission in r.subreddit("ethtrader").new(limit=None):
      if (((datetime.fromtimestamp(submission.created_utc) >= begin_date) and (datetime.fromtimestamp(submission.created_utc) <= end_date))):
          sub_pscore += (submission.score)
          posts.append(
              {
                  'id': submission.id,
                  'score':submission.score,
                  'author': submission.author.name,
                  'date':  datetime.fromtimestamp(submission.created_utc),
                  'comments': submission.num_comments,
                  'flair': submission.link_flair_text
              }
          )
  print('Post score: '+str(sub_pscore))
  
  posts = pd.DataFrame(posts)
  posts.to_csv(wdir+str(current_round)+'/posts_'+str(begin_date.year)+str(begin_date.month)+str(begin_date.day)+'.csv')

  
  # Comments
  
  comments=[]
  sub_cscore = 0
  
  for i in range (0,len(posts)):
      submission = r.submission(posts['id'][i])
      if submission.author != "AutoModerator":
          submission.comments.replace_more(limit=None)
          for comment in submission.comments.list():
              sub_cscore+=comment.score
              comments.append(
                  {
                      'id': comment.id,
                      'score':comment.score,
                      'author': comment.author,
                      'date':  datetime.fromtimestamp(comment.created_utc),
                      'submission': comment.submission
                  })
  print('Comment score: '+str(sub_cscore))
  
  comments = pd.DataFrame(comments)
  comments.to_csv(wdir+str(current_round)+'/comments_'+str(begin_date.year)+str(begin_date.month)+str(begin_date.day)+'.csv')

  
  r = praw.Reddit(client_id=,
              client_secret=,
              user_agent=,
              password=,
              username=,
              check_for_async=False)
  
  daily=[]
  daily_id = posts['id'][posts['author']=='AutoModerator']
  daily_ = r.submission(daily_id.iloc[0])
  daily_cscore = 0
  
  # As the daily has more than 1k comments, we'll load the comment tree before looping over it, otherwise we'll get Error 429.
  
  try:
      daily_.comments.replace_more(limit=None)
  except:
      try:
          daily_.comments.replace_more(limit=None)
      except:
          try:
              daily_.comments.replace_more(limit=None)
          except: daily_.comments.replace_more(limit=None)
  
  # Giving a break to the API
  time.sleep(3)
  
  for comment in daily_.comments.list():
      daily_cscore+=comment.score
      daily.append(
          {
              'id': comment.id,
              'score':comment.score,
              'author': comment.author,
              'date':  datetime.fromtimestamp(comment.created_utc),
              'submission': comment.submission
              })
  print('Daily score: '+str(daily_cscore))
  
  daily=pd.DataFrame(daily)
  daily.to_csv(wdir+str(current_round)+'/daily_'+str(begin_date.year)+str(begin_date.month)+str(begin_date.day)+'.csv')
