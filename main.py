import requests
from datetime import datetime
from datetime import date
import json
import time
import sys
import os
from supabase import create_client, Client
import contextlib
import io
from dotenv import load_dotenv


def main():
    userid = 555
    apiurl = "http://left/blank/on/purpose/for/public"
    load_dotenv()
    supa_url = os.environ.get("supa_url")
    supa_key = os.environ.get("supa_key")
    
    brevo_api_key = os.environ.get("brevo_api_key")
  
    print("Hello ptsl script")
    while True:
        thisday=date.today()
        posts = check_pts(userid, apiurl)
        supa = init_supabase_client(supa_url, supa_key)
        if posts:
            y= get_daily_count(supa, thisday)
            if y.data:
                postsInDb=y.data[0]['posts']
            else: 
                postsInDb=0
            #if we have any posts at all, and its not same as in db
            if (posts) and (len(posts) != postsInDb):
                    # if we have posts but no entry at all
                    if postsInDb == 0:
                        newPostCount = len(posts) 
                        print("New Posts (including first of the day):")
                        for post in posts:
                            print_post(post)
                        #email all posts
                        body=construct_email_body(posts)
                        send_mail(body, newPostCount, brevo_api_key)
                        upsert_date_count(supa, str(thisday), len(posts))
                    # we have posts and entry but simply different numbers
                    elif (len(posts) !=0 ) and (postsInDb !=0 ):
                        newPostCount = len(posts)-postsInDb                        
                        #email only new posts
                        newPosts = posts[:newPostCount]
                        print("New posts:")
                        for post in newPosts:
                            print_post(post)
                        body=construct_email_body(newPosts)
                        send_mail(body, newPostCount, brevo_api_key)
                        update_date_count(supa, str(thisday), newCount=len(posts))
        time.sleep(60)


def init_supabase_client(url, key):
    supa: Client = create_client(url, key)
    return supa


def get_all_counts(supa):
    response = supa.table('posts_by_date2').select("*").execute()
    return response


def supress_stdout(func):
    def wrapper(*a, **ka):
        with open(os.devnull, 'w') as devnull:
            with contextlib.redirect_stdout(devnull):
                return func(*a, **ka)
    return wrapper


@supress_stdout
def get_daily_count(supa, day):
    response = supa.table('posts_by_date2').select('*').eq('date', day).execute()
    return response


def create_date_entry(supa, day):
    print("Create new db row")
    data, count = supa.table('posts_by_date2').insert({"date": day, "posts": 1}).execute()


def update_date_count(supa, day, newCount):
    print(f"Update db row: {newCount}")
    data, count = supa.table('posts_by_date2').update({'posts': newCount}).eq('date', day).execute()


def upsert_date_count(supa, day, count):
    print(f"Upsert db row with {count}")
    data, count = supa.table('posts_by_date2').upsert({"date": day, "posts": count}).execute()


def check_pts(user, apiurl):
    startTime = get_start_time()
    endTime = get_end_time()
    url=apiurl
    params={
        "authorId": user,
        "startDate": startTime,
        "endDate": endTime,
        "pageSize": 100
    }
    res = requests.get(url, params)
    posts = res.json()
    current_dateTime = datetime.now()
    nowString = f"{current_dateTime.month}/{current_dateTime.day} @ {current_dateTime.hour}:{current_dateTime.minute} "
    print (f"Checked for posts from userid {user} on {nowString}. Response: {res.status_code}. Posts: {len(posts)}")
    return posts


def send_mail(htmlbody, numPosts, brevo_api_key):
    print(f"Mailing {numPosts} new posts.")
    url="https://api.brevo.com/v3/smtp/email"
    headers={
        'accept': 'application/json',
        'api-key': brevo_api_key,
        'content-type': 'application/json'
    }
    data={  
        "sender":{  
            "name":"authorize sender",
            "email":"authorized@email.com"
        },
        "to":[  
            {  
                "email":"autothorized@recipient.com",
                "name":"authorized recipient"
            }
        ],
        "subject":f"ptsl brevo alert. New Posts: {numPosts} ",
        "htmlContent": htmlbody
        }
    brevo_response = requests.post(url, data=json.dumps(data), headers=headers)
    print(brevo_response)


def construct_email_body(posts):
    body=f"""
        <html><head></head><body>"
        <p>{len(posts)} New Posts</p>
        """
    for raw in posts:
        postbody=f"""
            <p>Thread: {raw['threadSubject']}</p>
            <p>Posted: {raw['dateCreated']} "</p>
            <p>Body: <br>{raw['body']}</p>
        """
        body+=postbody
    body+="</body></html>"
    return body
    

def print_post(post):
    print(f"Thread: {post['threadSubject']}")
    print(f"Date: {post['dateCreated']}")
    print(f"Body:\n {post['body']}")


def get_start_time():
    now = datetime.now()
    current_date = date.today()
    # current_time = now.strftime("%H:%M:%S")
    return str(current_date)+"T00:00:00"


def get_end_time():
    now = datetime.now()
    current_date = date.today()
    # current_time = now.strftime("%H:%M:%S")
    return str(current_date)+"T23:59:59-0400"


if __name__ == "__main__":
    main()
