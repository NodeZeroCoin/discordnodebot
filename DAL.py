import logging
import sqlite3
from datetime import datetime
import sys
import os.path

## version 1.0 #######################################################################################################
#####################################            Version history           ###########################################
######################################################################################################################
# 1/30/20 - version 1.0 - initial version
######################################################################################################################


class DAL:

    def __init__(self, sDB, oLogger, sLoggingLevel, sErrRefID):
        self.logger = oLogger
        self.loggingLevel = sLoggingLevel
        self.databaseFile = sDB
        self.errRefID = sErrRefID
        self.conn = None


    def selectData(self, singleMultiNumRows, sQuery, lParams=[], bLogZeroRecords=True):

        if ((singleMultiNumRows != "single") and (singleMultiNumRows != "multi") and (not singleMultiNumRows.isnumeric())):
            self.logger.error("DAL - selectData - Invalid parameter for 'singleMultiNumRows'. Value specified: {}. ErrRefID: {}".format(str(singleMultiNumRows), self.errRefID))
            raise Exception("Invalid parameter.")

        try:
            self.conn.row_factory = sqlite3.Row
            curr = self.conn.cursor()
            curr.execute(sQuery, lParams)
            if singleMultiNumRows == "single":
                rows = curr.fetchone()
            elif singleMultiNumRows == "multi":
                rows = curr.fetchall()
            elif singleMultiNumRows.isnumeric():
                rows = curr.fetchmany(int(singleMultiNumRows))
            if ((not rows) and (bLogZeroRecords)):
                self.logger.warning("DAL - selectData - No data returned from query. Query: {} Params: {}. ErrRefID: {}".format(sQuery, lParams, self.errRefID))
        except Exception as e:
            self.logger.error("DAL - selectData - Error occured. Query: {} Error: {}. ErrRefID: {}".format(sQuery, str(e), self.errRefID))
            raise
        else:
            return rows

    def insertUpdateDelete(self, sQuery, lParams=[], bLogZeroRecords=True):
        try:
            curr = self.conn.cursor()
            curr.execute(sQuery, lParams)
            if ((curr.rowcount) == 0 and (bLogZeroRecords)):
                self.logger.warning("DAL - insertUpdateData - No data modified. Query: {} Params: {}. ErrRefID: {}".format(sQuery, lParams, self.errRefID))
        except Exception as e:
            self.logger.error("DAL - insertUpdateData - Error occured. Query: {} Error: {}. ErrRefID: {}".format(sQuery, str(e), self.errRefID))
            raise
        else:
            return curr.rowcount

    def connect(self):
        sDB = self.databaseFile
        conn = None

        # if database does not exist, then raise exception
        if not os.path.exists(sDB):
            self.logger.error("DAL - connect - Failed connecting to database {}. It does not exist. ErrRefID: {}".format(sDB, self.errRefID))
            raise Exception("Database does not exist.")

        try:
            conn = sqlite3.connect(sDB)
        except Exception as e:
            self.logger.error("DAL - connect - Error connecting to database {}. Error: {}. ErrRefID: {}".format(sDB, str(e), self.errRefID))
            raise

        self.conn = conn

    def disconnect(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception as e:
                self.logger.warning("DAL - disconnect - Failed to close connection to {}. Ignoring error. Likely it was already closed. Error: {}. ErrRefID: {}".format(self.databaseFile, str(e), self.errRefID))

    def commit(self):
        try:
            self.conn.commit()
        except Exception as e:
            self.logger.warning("DAL - commit - Error occured but ignoring error. Likely transaction not open. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))

    def rollback(self):
        try:
            self.conn.rollback()
        except Exception as e:
            self.logger.warning("DAL - rollback - Error occured but ignoring error. Likely transaction not open. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))

    #!!!!!!   NOTE:  This function has table and column names hard coded for the SysLogs table. Ensure this matches your database setup.  !!!!!
    # To ensure validity of your transactions, this function should be called after you commit your original queries (but before you disconnect the connection) in your function.
    # This function will throw away all errors and will never raise an error to the calling function (but it will log them in the log file)
    def addSysLogEntry(self, sLogType, sLogSource, sLogMessage):
        try:
            curr = self.conn.cursor()
            curr.execute("""INSERT INTO SysLogs (logtype, source, message) VALUES(?,?,?)""",[sLogType, sLogSource, sLogMessage])
        except Exception as e:
            self.logger.error("DAL - addSysLogEntry - Error occured. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
        else:
            self.commit()