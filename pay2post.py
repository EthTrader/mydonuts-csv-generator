def pay2post(wdir,current_round):
'''This function returns csv with all the posts and their authors in the previous day, i.e. if you run it today, it will fetch data
from yesterday.

   Inputs:
   wdir [str]: working directory
   current_round [int]: current round #
   
   Output:
   pay2post_DATE.csv
   
   NOTES: 
   Insert your API key data on lines 25-30. Set the function to run on a specific hour every day.
   For use in your own sub, make AutoModerator mention the account whose API will be used in every new post.
   
   author: reddito321
   
'''
  
  import praw
  from datetime import datetime, timedelta
  import numpy as np
  import pandas as pd
  
  r = praw.Reddit(client_id=,
        client_secret=,
        user_agent=,
        password=,
        username=,
        check_for_async=False) # This is related to ethtrader-pay2post bot.
  
  # current_round=int(np.loadtxt(wdir+"current_round.txt"))
  begin_date = datetime(datetime.today().year, datetime.today().month, datetime.today().day, 0, 0)+timedelta(days=-1)
  end_date = begin_date+timedelta(hours=23,minutes=59,seconds=59)

  pay2post = []
  
  try:
      for mention in r.inbox.mentions(limit=300):
          pay2post.append(
                      {
                          'id': mention.submission.id,
                          'username': mention.body.split()[0][0:-1],# mention.submission.author,
                          'date':  datetime.fromtimestamp(mention.submission.created_utc),
                      })
  except:
      for mention in r.inbox.mentions(limit=300):
          pay2post.append(
                      {
                          'id': mention.submission.id,
                          'username': mention.body.split()[0][0:-1],# mention.submission.author,
                          'date':  datetime.fromtimestamp(mention.submission.created_utc),
                      })
  
  pay2post = pd.DataFrame(pay2post)
  pay2post = pay2post.loc[(pay2post['date'] >= begin_date) & (pay2post['date'] < end_date)]
  
  pay2post.to_csv(wdir+str(current_round)+'/pay2post_'+str(begin_date.year)+str(begin_date.month)+str(begin_date.day)+'.csv',index=False)
