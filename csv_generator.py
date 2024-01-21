def csv_generator(wdir):
''' This function generates the final csv for posts and comments.

Inputs:
wdir [str]: working directory, must be the one where csv files generated with csv_miner.py and pay2post.py are stored.
current_round [int]: current round #

Outputs:
round_CURRENT_ROUND.csv

author: reddito321
'''
    
  import numpy as np
  import pandas as pd
  import glob
  
  datadir = wdir
  
  comments = glob.glob(datadir+"/comment*")
  posts = glob.glob(datadir+"/post*")
  daily = glob.glob(datadir+"/daily*")
  p2p = glob.glob(datadir+"/pay2post*")
  
  #%% Unique users
  users = []
  
  for i in range(0,len(comments)):
      c = pd.read_csv(comments[i])['author'].unique()
      p = pd.read_csv(posts[i])['author'].unique()
      d = pd.read_csv(daily[i])['author'].unique()
      for j in range(0,len(c)):
          users.append(c[j])
      for j in range(0,len(p)):
          users.append(p[j])
      for j in range(0,len(d)):
          users.append(d[j])
          
  all_users = np.unique(np.array(users))
  
  #%% Fetching only registered users
  
  wallets = pd.read_json("https://ethtrader.github.io/donut.distribution/users.json") 
  df_wallets = pd.DataFrame({'username': wallets['username'], 'blockchain_address': wallets['address']})
  
  registered_users = pd.merge(pd.DataFrame({'username':all_users}),df_wallets,how='inner',on=['username'])
  users = np.array(registered_users['username'])
  
  #%% Comments
  cscores=np.zeros(len(users))
  clen=np.zeros(len(users))
  
  for i in range(0,len(users)):
      cscore=0
      for j in range(0,len(comments)):
          c = pd.read_csv(comments[j])
          idx = np.where(c['author']==users[i])[0]
          cscore+=np.sum(c['score'][idx]-1)
          clen[i]+=len(idx)
      cscores[i]+=cscore    
      
  #%% Posts
  pscores=np.zeros(len(users))
  plen=np.zeros(len(users))
  
  for i in range(0,len(users)):
      # plen=0
      pscore=0
      for j in range(0,len(posts)):
          p = pd.read_csv(posts[j])
          for k in range(0,len(p)):
              if p['author'][k] == users[i]:
                  plen[i]+=1
                  if p['flair'][k] == "Media" or p['flair'][k] == "Comedy" or p['flair'][k] == "Self Story":
                      pscore+=0.1*(p['score'][k]-1)
                  else:
                      pscore+=p['score'][k]-1
  
      pscores[i]+=pscore
  
  #%% Daily
  
  for i in range(0,len(users)):
      dscore=0
      for j in range(0,len(daily)):
          d = pd.read_csv(daily[j])
          idxd=np.where(d['author']==users[i])[0]
          dscore+=np.sum(d['score'][idxd]-1)
          clen[i]+=len(idxd)
      cscores[i]+=dscore  
  # 
  
  #%% pay2post
  
  p2p_list = []
  
  for i in range(0,len(p2p)):
      p2 = pd.read_csv(p2p[i])
      p2p_list.append(p2)
  
  p2p_ = pd.DataFrame({'username':(pd.concat(p2p_list))['author'].value_counts().index,'total_posts':(pd.concat(p2p_list)['author'].value_counts().values)})
  
  #%% Computing the ratios
  
  pratio = (510000)/np.sum(pscores.clip(min=0))
  cratio = 340000/np.sum(cscores.clip(min=0))
  
  #%%
  
  userscores = pratio*pscores.clip(min=0) + cratio*cscores.clip(min=0)
  
  df = pd.DataFrame({'username': users, 'comments': clen.astype(int), 'comment_score':cscores*cratio, 'posts': plen.astype(int),'post_score': pscores*pratio})
  df = pd.merge(df,p2p_, how='left', on=['username']).fillna(0)
  df['pay2post'] = -df['total_posts']*250
  df['base'] = userscores+df['pay2post'] 
  #%%
  final_csv = pd.merge(df[df['base']!=0],df_wallets, how='inner', on=['username']).sort_values(by=['base'],ascending=False).reset_index(drop=True)
  final_csv.to_csv(datadir+'/round_'+str(current_round)+'.csv',index=False)
  
  print(np.sum((userscores-plen*250))+250*np.sum(plen))
