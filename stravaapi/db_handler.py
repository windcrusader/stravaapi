"""
Handles the interface to sqlite3 where athelete activity data is stored
offline
"""
import sqlite3
from stravaapi import constants
from loguru import logger

class Ath_DB:

    def __init__(self):
        #get the db
        self.conn = sqlite3.connect(constants.SAVEFILELOCATION  / 'athlete.db',
                    check_same_thread=False)

        #do some self-checks on the DB
        #check for the activities table  
        query = ("SELECT name from sqlite_master"
                " WHERE type='table' AND name='activities';")
        if self.conn.execute(query).fetchone() is None:
            logger.debug("Activities table not found in DB, creating it.")
            self.create_act_table()

        #check for the act_elevation table  
        query = ("SELECT name from sqlite_master"
                " WHERE type='table' AND name='act_elevation';")
        if self.conn.execute(query).fetchone() is None:
            logger.debug("Activity elevation table not found in DB, creating it.")
            self.create_act_elev_table()

        #check for the act_lap table  
        query = ("SELECT name from sqlite_master"
                " WHERE type='table' AND name='act_lap';")
        if self.conn.execute(query).fetchone() is None:
            logger.debug("Activity lap table not found in DB, creating it.")
            self.create_act_lap_table()
    
    def create_act_table(self):
        query = ('''CREATE TABLE activities'''+
                " (id integer primary key, start_date_local text, distance real,"+
                " elapsed_time integer, moving_time integer);")
        logger.debug(query)
        self.conn.execute(query)
        self.conn.commit()

    def create_act_elev_table(self):
        query = ('''CREATE TABLE act_elevation'''+
                " (id integer primary key, elev_stream text);")
        logger.debug(query)
        self.conn.execute(query)
        self.conn.commit()

    def create_act_lap_table(self):
        query = ('''CREATE TABLE act_lap'''+
                " (id integer primary key, lap_stream text);")
        logger.debug(query)
        self.conn.execute(query)
        self.conn.commit()

