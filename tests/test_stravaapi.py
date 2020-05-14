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
    assert TRIMP == 100.0
    assert alt_diff == 0.0
    assert calc_grad == 0.0
    assert pytest.approx(pace) == 236.0
    assert pytest.approx(NGP) == 236.0
    assert pytest.approx(NGS) == 15.254237288135592
    assert IF == 1.0