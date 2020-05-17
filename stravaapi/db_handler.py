"""
Handles the interface to sqlite3 where athelete activity data is stored
offline
"""
import sqlite3

class Ath_DB:

    def __init__(self):
        #get the db
        