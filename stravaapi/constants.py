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
