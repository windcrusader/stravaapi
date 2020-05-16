import pytest
from stravaapi import api

def test_trimp():

    #setup the input lap dict and the altitude stream
    lap = {'start_index':0,
           'end_index':1,
           'moving_time':60*60, #1hr
            'distance':15.254237288135592*1000}
    alt = {"altitude":{"data":[0,0]}}
    TRIMP, alt_diff, calc_grad, pace, NGP, NGS, IF = api.calctrimp(lap,alt)

    assert alt_diff == 0.0
    assert calc_grad == 0.0
    assert pytest.approx(pace) == 236.0
    assert pytest.approx(NGP) == 236.0
    assert pytest.approx(NGS) == 15.254237288135592
    assert IF == 1.0
    assert TRIMP == 100.0

def test_trimp_1():
    # t * IF**2 / 36
    #setup the input lap dict and the altitude stream
    lap = {'start_index':0,
            'end_index':1,
            'moving_time':40*60, #40 min run with 300m alt gain @12km/hr
            'distance':12*2/3*1000}
    alt = {"altitude":{"data":[0,300]}}
    TRIMP, alt_diff, calc_grad, pace, NGP, NGS, IF = api.calctrimp(lap,alt)    
    assert alt_diff == 300.0
    assert pytest.approx(calc_grad) == 300.0/8000.0 * 100
    assert pytest.approx(pace) == 300.0
    assert pytest.approx(NGP) == 264.4287
    assert pytest.approx(NGS) == 13.6142532
    assert pytest.approx(IF) == 0.8924899
    assert TRIMP == pytest.approx(53.102557)

def test_adf_factor():
    assert api.adf_factor(20) == pytest.approx(2.2700112)  
