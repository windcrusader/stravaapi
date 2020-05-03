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

api = responder.API()

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

#get user activities from date
# 
@api.route("/getactivities")
def getactivities(req, resp):
    "Get user activities"

    #get token
    with open(SAVEFILELOCATION / "authsuccess.txt","r") as wfile:
        auth_resp = wfile.read()

    auth_resp = json.loads(auth_resp)
    #todo check auth is valid and has not expired

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
        r = requests.get("https://www.strava.com/api/v3/athlete/activities",
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
    api.run(address="0.0.0.0")
