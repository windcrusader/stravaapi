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

api = responder.API()

class Globals():
      #create a path for storing the tokens
    #home location
    HOME = pathlib.Path.home()
    #folder to store token
    SAVEFILELOCATION = HOME / ".stravaapi" 

    #Some assertions to check for environment variables
    assert os.getenv("STRAVA_CLIENT_ID"), "No STRAVA_CLIENT_ID env variable set"
    assert os.getenv("STRAVA_CLIENT_SECRET"),\
                    "No STRAVA_CLIENT_SECRET env variable set"

    try:
        # Create target Directory
        os.mkdir(SAVEFILELOCATION)
        print("Directory " , SAVEFILELOCATION,  " Created ") 
    except FileExistsError:
        print("Directory " , SAVEFILELOCATION,  " already exists")

    #coefficients for GAP function
    #when given a gradient calculate the adjustment factor
    #factor = ax**2 + bx + c
    coeff = [0.0017002, 0.02949656]  

def adf_factor(x):
    """return an adjustment factor based on an fitted curve to the 
    strava gradient adjusted pace curve"""
    return Globals.coeff[0]*x**2 + Globals.coeff[1]*x + 1.0

def authorize_url():
    """Generate authorization uri"""
    app_url = os.getenv('APP_URL', 'http://localhost')
    logger.debug(f"APP_URL={app_url}")
    params = {
        "client_id": os.getenv('STRAVA_CLIENT_ID'),
        "response_type": "code",
        "redirect_uri": f"{app_url}:5042/authorization_successful",
        "scope": "read,profile:read_all,activity:read",
        "state": 'https://github.com/sladkovm/strava-oauth',
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
    api.redirect(resp, location=authorize_url())


@api.route("/authorization_successful")
def authorization_successful(req, resp):
    """Exchange code for a user token"""
    params = {
        "client_id": os.getenv('STRAVA_CLIENT_ID'),
        "client_secret": os.getenv('STRAVA_CLIENT_SECRET'),
        "code": req.params.get('code'),
        "grant_type": "authorization_code"
    }
    print(params)
    r = requests.post("https://www.strava.com/oauth/token", params)
    logger.debug(r.text)
    with open(SAVEFILELOCATION / "authsuccess.txt","w+") as wfile:
         print(json.dumps(r.json()),file=wfile)
    resp.text = r.text

#get altitude stream
# http get "https://www.strava.com/api/v3/activities/{id}/streams?keys=&key_by_type=
def getaltitude(id):
    #get token
    auth_resp = gettoken()

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

#get a single activity by id
@api.route("/getactivity")
def getactivity(req, resp):
    """Get a user activity by ID"""
    #get token
    auth_resp = gettoken()

    id = 3431573159

    act_url = f"https://www.strava.com/api/v3/activities/{id}"
    headers={'Authorization': f"Bearer {auth_resp['access_token']}"}
    params = {"include_all_efforts": True} 

    r = requests.get(act_url,
                     params,
                     headers=headers)   
    resp.text = r.text

    #get the altitude stream
    altr = getaltitude(id)
    altr = altr.json()
    #print(altr.json())

    json_act = r.json()
    for lap in json_act['laps']:
        #print(lap.keys())
        print("*"*10)
        print(lap['name'])
        print("*"*10)
        #calculate gradient
        alt_diff = calc_altdiff(altr,lap['start_index'],lap['end_index'])
        print(f"alt_diff = {alt_diff}")
        grad = lap['total_elevation_gain'] / lap['distance'] * 100
        calc_grad = alt_diff / lap['distance'] * 100
        print(f"grad = {grad}")
        print(f"calc_grad = {calc_grad}")
        speed = lap['distance'] / lap['moving_time'] * 3.6
        print(f"speed = {speed}")
        pace = speed_2_pace(speed)
        print(f"pace = {pace[0]}:{pace[1]:02d}/km")
        adjustment = adf_factor(calc_grad)
        gas = speed * adjustment
        print(f"gas = {gas}")
        gap = speed_2_pace(gas)
        print(f"gap = {gap[0]}:{gap[1]:02d}/km")

def speed_2_pace(speed):
    """Convert speed in km/hr to pace in min/km"""
    rem, inte = math.modf(60/speed)
    return (int(inte),int(rem*60))

def get_nearest_gap(gradient):
    assert Globals.GAP is not None, "Gradient CSV file non existent"
    index = bisect_left(Globals.GAP['gradient'].values, gradient)
    return Globals.GAP['adjustment'].iloc[index]

def read_gap_table():
    df = pd.read_csv("GAP.csv")
    #print(df.head())
    return df


def gettoken():
    #get token
    with open(SAVEFILELOCATION / "authsuccess.txt","r") as wfile:
        auth_resp = wfile.read()

    auth_resp = json.loads(auth_resp)
    #todo check auth is valid and has not expired
    return auth_resp

#get user activities from date
@api.route("/getactivities")
def getactivities(req, resp):
    "Get user activities"

    auth_resp = gettoken()

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

if __name__ == "__main__":
    #create a path for storing the tokens
    #home location
    HOME = pathlib.Path.home()
    #folder to store token
    SAVEFILELOCATION = HOME / ".stravaapi" 

    #Some assertions to check for environment variables
    assert os.getenv("STRAVA_CLIENT_ID"), "No STRAVA_CLIENT_ID env variable set"
    assert os.getenv("STRAVA_CLIENT_SECRET"),\
                    "No STRAVA_CLIENT_SECRET env variable set"

    try:
        # Create target Directory
        os.mkdir(SAVEFILELOCATION)
        print("Directory " , SAVEFILELOCATION,  " Created ") 
    except FileExistsError:
        print("Directory " , SAVEFILELOCATION,  " already exists")

    
    Globals.GAP = read_gap_table()
    api.run(address="0.0.0.0")
