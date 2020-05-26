import responder
import requests
import os
import urllib
from loguru import logger
import pathlib
import json
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import datetime as dt
from bisect import bisect_left, bisect_right
import math
from stravaapi import constants, db_handler

api = responder.API()

#Some assertions to check for environment variables
assert os.getenv("STRAVA_CLIENT_ID"), "No STRAVA_CLIENT_ID env variable set"
assert os.getenv("STRAVA_CLIENT_SECRET"),\
                "No STRAVA_CLIENT_SECRET env variable set"

try:
    # Create target Directory
    os.mkdir(constants.SAVEFILELOCATION)
    print("Directory " , constants.SAVEFILELOCATION,  " Created ") 
except FileExistsError:
    print("Directory " , constants.SAVEFILELOCATION,  " already exists")

#get the athlete DB
db = db_handler.Ath_DB()

def adf_factor(x):
    """return an adjustment factor based on an fitted curve to the 
    strava gradient adjusted pace curve"""
    coeff = [0.0017002, 0.02949656] 
    return coeff[0]*x**2 + coeff[1]*x + 1.0

def authorize_url(redirect_to):
    """Generate authorization uri"""
    app_url = os.getenv('APP_URL', 'http://localhost')
    logger.debug(f"APP_URL={app_url}")
    params = {
        "client_id": os.getenv('STRAVA_CLIENT_ID'),
        "response_type": "code",
        "redirect_uri": f"{app_url}:{constants.PORT}/{redirect_to}",
        "scope": "read,profile:read_all,activity:read",
        "state": 'https://github.com/windcrusader/stravaapi',
        "approval_prompt": "force"
    }
    values_url = urllib.parse.urlencode(params)
    base_url = 'https://www.strava.com/oauth/authorize'
    rv = base_url + '?' + values_url
    logger.debug(rv)
    return rv

@api.route("/")
def home(req, resp):
    resp.text = "Welcome to strava-oauth"

@api.route("/client")
def client(req, resp):
    resp.text = os.getenv('STRAVA_CLIENT_ID')

@api.route("/authorize")
def authorize(req, resp):
    """Redirect user to the Strava Authorization page"""
    api.redirect(resp, location=authorize_url("authorization_successful"))

@api.route("/authorization_successful")
def authorization_successful(req, resp):
    """Exchange code for a user token"""
    params = {
        "client_id": os.getenv('STRAVA_CLIENT_ID'),
        "client_secret": os.getenv('STRAVA_CLIENT_SECRET'),
        "code": req.params.get('code'),
        "grant_type": "authorization_code"
    }
    logger.debug(params)
    r = requests.post("https://www.strava.com/oauth/token", params)
    logger.debug(r.text)
    with open(constants.SAVEFILELOCATION / "authsuccess.txt","w+") as wfile:
         print(json.dumps(r.json()),file=wfile)
    resp.text = r.text

def refresh_token(ref_token):
    """Exchange refresh token for a new token"""
    params = {
        "client_id": os.getenv('STRAVA_CLIENT_ID'),
        "client_secret": os.getenv('STRAVA_CLIENT_SECRET'),
        "grant_type": "refresh_token",
        "refresh_token": ref_token
    }
    logger.debug(params)
    r = requests.post("https://www.strava.com/api/v3/oauth/token", params)
    logger.debug(r.text)
    with open(constants.SAVEFILELOCATION / "authsuccess.txt","w+") as wfile:
         print(json.dumps(r.json()),file=wfile)
    #resp.text = r.text
    return r.json()

#get altitude stream
# http get "https://www.strava.com/api/v3/activities/{id}/streams?keys=&key_by_type=
def getaltitude(id):
    #get token
    auth_resp, valid_token = gettoken()

    act_url = f"https://www.strava.com/api/v3/activities/{id}/streams"
    headers={'Authorization': f"Bearer {auth_resp['access_token']}"}
    params = {"keys":"altitude",
              "key_by_type":True} 

    r = requests.get(act_url,
                     params,
                     headers=headers)   

    return r

def calc_altdiff(resp, st_ind, end_ind):
    """calcs altitude difference"""
    assert resp['altitude'] is not None, "altitude data not in json response"
    return resp['altitude']['data'][end_ind] - resp['altitude']['data'][st_ind] 

def calctrimp(lap, altr):
    """calculates the training impulse for a lap
    TSS = (t * NGS * IF) / (FTS * 36)
        = t * IF**2 / 36
    
    IF = intensity factor NGS / FTS
    NGS = normalised grade adjusted speed (km/hr)
    t = activity time in seconds
    FTS = functional threshold pace (km/hr)

    input is a lap dictionary
    altr = altitude stream for the activity

    returns a tuple of the form
    (TRIMP, alt_diff, calc_grad, pace, NGP, NGS, IF)
    """

    #calculate altitude difference and gradient
    alt_diff = calc_altdiff(altr,lap['start_index'],lap['end_index'])
    logger.debug(f"alt_diff = {alt_diff}")
    calc_grad = alt_diff / lap['distance'] * 100
    logger.debug(f"calc_grad = {calc_grad}")
    
    #calculate speed
    speed = lap['distance'] / lap['moving_time'] * 3.6
    logger.debug(f"speed = {speed}")

    #calculate pace
    pace = speed_2_pace(speed)
    logger.debug(f"pace = {format_pace(pace)}")

    #calculate adjustment factor to normalise speed and pace
    adjustment = adf_factor(calc_grad)

    NGS = speed * adjustment
    logger.debug(f"NGS = {NGS}")
    NGP = speed_2_pace(NGS)
    logger.debug(f"NGP = {format_pace(NGP)}")

    #calculate IF
    IF = NGS / constants.FTS
    logger.debug(f"IF={IF}")

    #calulate TRIMP
    TRIMP = lap['moving_time'] * IF**2 / 36

    return (TRIMP, alt_diff, calc_grad, pace, NGP, NGS, IF)

#get a single activity by id
@api.route("/getactivity")
def getactivity(req, resp):
    """Get a user activity by ID"""
    #get token
    auth_resp, valid_token = gettoken()
    logger.debug(valid_token)
    if not valid_token:
        auth_resp = refresh_token(auth_resp['refresh_token'])

    id = 3431573159

    act_url = f"https://www.strava.com/api/v3/activities/{id}"
    headers={'Authorization': f"Bearer {auth_resp['access_token']}"}
    params = {"include_all_efforts": True} 

    r = requests.get(act_url,
                     params,
                     headers=headers)  


    if r.raise_for_status() is None: 
        resp.text = "success"
        json_act = r.json()

    #get the altitude stream
    altr = getaltitude(id)
    #convert to json
    altr = altr.json()
    activity_sum = [calctrimp(lap,altr) for lap in json_act['laps']]
    sumtrimp = 0.0
    for item in activity_sum:
        logger.debug(item)
        sumtrimp += item[0]
    logger.debug(sumtrimp)

def speed_2_pace(speed):
    """Convert speed in km/hr to pace in s/km"""
    return 60*60/speed

def format_pace(pace):
    """formats a pace in s/km as a nice mm:ss/km"""
    rem, inte = math.modf(pace/60)
    return f"{int(inte)}:{int(rem*100):02d}/km"

def pace_2_speed(pace):
    """converts a pace in s/km to km/hr"""
    return 1/(pace / 60**2)

def read_gap_table():
    df = pd.read_csv("GAP.csv")
    #print(df.head())
    return df

def gettoken():
    #get token
    with open(constants.SAVEFILELOCATION / "authsuccess.txt","r") as wfile:
        auth_resp = wfile.read()

    auth_resp = json.loads(auth_resp)
    #todo check auth is valid and has not expired
    if auth_resp['expires_at'] < dt.datetime.now().timestamp():
        print("Token expired")
        valid_token = False
        #redirect to auth page
        #print(authorize_url())
        #api.redirect(resp, location=authorize_url())
    else:
        valid_token = True

    return (auth_resp, valid_token)

#get user activities from date
@api.route("/getactivities")
def getactivities(req, resp):
    "Get user activities"

    auth_resp, valid_token = gettoken()
    #todo make this an input parameter
    dateafter = 1577782931

    act_url = "https://www.strava.com/api/v3/athlete/activities"
    headers={'Authorization': f"Bearer {auth_resp['access_token']}"}
    params = {"after": dateafter,
              "per_page": 50,
              "page":1
    } 

    col_names = ['start_date_local',
                'id',
                'distance',
                'elapsed_time',
                'total_elevation_gain',
                'moving_time']  
    activities = pd.DataFrame(columns=col_names)   
    #keep calling strave whilst response is not empty.      
    while True:
        r = requests.get(act_url,
                     params,
                     headers=headers)   
        
        new_list = []
        #iterate through returned data and just pick out the data I want
        if not r.json():
            break

        for item in r.json():
            if item['type'] == 'Run':
                newdict = {k: item[k] for k in col_names}
                new_list.append(newdict)    
        df = pd.DataFrame(new_list)
        frames = [activities, df]
        activities = pd.concat(frames)

        params['page'] += 1
        if params['page'] > 10:
            #failsafe in case something went bad
            resp.text('More than ten requests for data pages, problem?')
            break
  
    #add column with cumulative distance
    activities['dist_cum'] = (activities['distance'] / 1000) .cumsum()
    #calculate dist per day
    km_per_day = 2020 / 366
    
    #today
    today = dt.datetime.now()
    dates = pd.date_range("2020-01-01",
                         f"{today.year}-{today.month}-{today.day+1}"
                        ).tolist()

    list_2020 = list(np.arange(km_per_day,len(dates)*km_per_day,km_per_day))
    
    fig = go.Figure(data=[
                    go.Scatter(name="Distance Ran",
                                 x=activities['start_date_local'],
                                 y=activities['dist_cum']),
                    go.Scatter(name="Target", x=dates,y=list_2020)
                    ],
                    layout= {
                'title': "Brad's Running km 2020",
                "xaxis_title":"Date",
                "yaxis_title":"Distance (km)"
            })
    fig.write_html('first_figure.html', auto_open=True)
    #fig.write_image("fig1.svg")
    fig.write_image("fig1.png")

    #add retrieved activities to sqlite database
    save_act_to_db(activities)

def save_act_to_db(activities):
    #preprocess the table into a list of tuples for committing the DB
    db_data = []
    for index, row in activities.iterrows():

        db_data.append((row['id'],
                        row['start_date_local'],
                        row['distance'],
                        row['elapsed_time'],
                        row['moving_time']
                        ))
                    
    
    logger.debug(db_data)
    #commit to DB
    db.conn.executemany('INSERT OR IGNORE INTO activities VALUES (?,?,?,?,?)', db_data)
    db.conn.commit()
