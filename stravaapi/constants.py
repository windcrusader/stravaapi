"""
Constants used throughout the module
"""
import sys
import pathlib

#home location
HOME = pathlib.Path.home()
#folder to store tidepredict files
SAVEFILELOCATION = HOME / ".stravaapi" 

#port for server
PORT = 5039

#Below define the base functional threshold pace and speed.
#using calculator at https://www.8020endurance.com/8020-zone-calculator/
FTP = 3 * 60 + 56 #3:56/km based on parkrun on 18/01/20
FTS = 15.254237288135592

#Constants for TRIMP training load calculation
ALPHA_CTL = 45
ALPHA_ATL = 15
#
K1 = 1 #training load weight used for form calculation
K2 = 2 #fatigue weight used for form calculation
FUT_DAYS = 30 #number of days to predict into the future
