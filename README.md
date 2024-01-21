# mydonuts-csv-generator
Generates the csv file with post and comment scores from a given sub.

# How to use

1. Set up a daily task with `csv_miner.py`. This will give you csv files with post and comment data, including the daily thread;
2. Set up a daily task with `pay2post.py`. This will give you csv files with all the posts submitted in the last 24h, regardless of the post being deleted or not. For this to work you need to set up AutoMod to mention the account whose API will be used in every new submission.
3. After the round has ended, run `csv_generator.py` to get your final csv.


