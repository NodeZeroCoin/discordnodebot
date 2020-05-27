import sqlite3
from sqlite3 import Error
import sys
import os.path
from collections import OrderedDict


## version 1.0 #######################################################################################################
#####################################            Version history           ###########################################
######################################################################################################################
# 1/30/20 - version 1.0 - initial version
######################################################################################################################


sDatabaseFile = "XXXXXX.db"

dCreateTables = OrderedDict([
    ("SysSettings", """ CREATE TABLE IF NOT EXISTS SysSettings (
                            settingName TEXT PRIMARY KEY NOT NULL,
                            settingValue TEXT,
                            settingExtraData1 TEXT,
                            settingExtraData2 TEXT,
                            settingExtraData3 TEXT,
                            updateDateTime datetime NOT NULL DEFAULT current_timestamp,
                            updateEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now')),
                            entryDateTime datetime NOT NULL DEFAULT current_timestamp,
                            entryEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now'))
                    ); """),
    ("SysLogs", """ CREATE TABLE IF NOT EXISTS SysLogs (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                        logType TEXT,
                        source TEXT,
                        message TEXT,
                        entryDateTime datetime NOT NULL DEFAULT current_timestamp,
                        entryEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now'))
                ); """),
    ("Users", """ CREATE TABLE IF NOT EXISTS Users (
                    ID INTEGER PRIMARY KEY NOT NULL,
                    totalSlots INTEGER NOT NULL,
                    usedSlots INTEGER NOT NULL,
                    bonusSlots INTEGER NOT NULL DEFAULT 0,
                    updateDateTime datetime NOT NULL DEFAULT current_timestamp,
                    updateEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now')),
                    entryDateTime datetime NOT NULL DEFAULT current_timestamp,
                    entryEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now'))
                ); """),
    ("RegisteredNZRNodes", """ CREATE TABLE IF NOT EXISTS RegisteredNZRNodes (
                                    address TEXT PRIMARY KEY NOT NULL,
                                    userID INTEGER NOT NULL,
                                    isActive INTEGER NOT NULL DEFAULT 1,
                                    nodesAllowed INTEGER NOT NULL,
                                    lastSeenEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now')),
                                    lastNotifyEpDateTime INTEGER(4),
                                    updateDateTime datetime NOT NULL DEFAULT current_timestamp,
                                    updateEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now')),
                                    entryDateTime datetime NOT NULL DEFAULT current_timestamp,
                                    entryEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now')),
                                    FOREIGN KEY(userID) REFERENCES Users(ID)
                            ); """),
    ("Coins", """ CREATE TABLE IF NOT EXISTS Coins (
                        ticker TEXT PRIMARY KEY NOT NULL,
                        coinName TEXT NOT NULL,
                        port INTEGER NOT NULL,
                        collateralAmount INTEGER NOT NULL,
                        blockTimeSeconds INTEGER NOT NULL,
                        transactionCheckType TEXT NOT NULL,
                        transactionCheckURL TEXT NOT NULL,
                        masternodeCheckType TEXT NOT NULL,
                        masternodeCheckURL TEXT NOT NULL,
                        explorerCheckURL TEXT NOT NULL,
                        masternodeCheckType TEXT NOT NULL,
                        rpcAuthURL TEXT NOT NULL,
                        configFileLocation TEXT NOT NULL,
                        updateDateTime datetime NOT NULL DEFAULT current_timestamp,
                        updateEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now')),
                        entryDateTime datetime NOT NULL DEFAULT current_timestamp,
                        entryEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now')),
                        UNIQUE(coinName)
                ); """),
    ("UserNodes", """ CREATE TABLE IF NOT EXISTS UserNodes (
                            ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                            userID INTEGER NOT NULL,
                            coinTicker TEXT NOT NULL,
                            aliasName TEXT NOT NULL,
                            genKey TEXT NOT NULL,
                            IP TEXT NOT NULL,
                            coinPort INTEGER NOT NULL,
                            collateralAddress TEXT NOT NULL,
                            txID TEXT NOT NULL,
                            txIndex INTEGER NOT NULL,
                            isActive INTEGER NOT NULL DEFAULT 1,
                            systemStatus TEXT NOT NULL DEFAULT 'NEW',
                            networkStatus TEXT NOT NULL DEFAULT 'UNKNOWN',
                            daemonType TEXT NOT NULL,
                            phantomEpDateTime INTEGER(4) NOT NULL,
                            lastSeenEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now')),
                            lastNotifyEpDateTime INTEGER(4),
                            updateDateTime datetime NOT NULL DEFAULT current_timestamp,
                            updateEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now')),
                            entryDateTime datetime NOT NULL DEFAULT current_timestamp,
                            entryEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now')),
                            FOREIGN KEY(userID) REFERENCES Users(ID),
                            FOREIGN KEY(coinTicker) REFERENCES Coins(ticker),
                            UNIQUE(userID, coinTicker, aliasName)
                            UNIQUE(coinTicker, collateralAddress)
                    ); """),
    ("CoinIPs", """ CREATE TABLE IF NOT EXISTS CoinIPs (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                        coinTicker TEXT NOT NULL,
                        IP TEXT NOT NULL,
                        defaultAlias TEXT NOT NULL,
                        masternodeKey TEXT NOT NULL,
                        phantomEpDateTime INTEGER(4) NOT NULL,
                        isUsed INTEGER NOT NULL DEFAULT 0,
                        updateDateTime datetime NOT NULL DEFAULT current_timestamp,
                        updateEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now')),
                        entryDateTime datetime NOT NULL DEFAULT current_timestamp,
                        entryEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now')),
                        FOREIGN KEY(coinTicker) REFERENCES Coins(ticker),
                        UNIQUE(coinTicker, IP)
                ); """),
    ("DiscordAdmins", """ CREATE TABLE IF NOT EXISTS DiscordAdmins (
                            ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                            discordID INTEGER NOT NULL,
                            discordName TEXT NOT NULL,
                            role TEXT NOT NULL,
                            entryDateTime datetime NOT NULL DEFAULT current_timestamp,
                            entryEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now'))
                        ); """),
    ("Lookups", """ CREATE TABLE IF NOT EXISTS Lookups (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                        sourceTable TEXT NOT NULL,
                        sourceColumn TEXT NOT NULL,
                        keyValue TEXT NOT NULL,
                        description TEXT NOT NULL,
                        entryDateTime datetime NOT NULL DEFAULT current_timestamp,
                        entryEpDateTime INTEGER(4) NOT NULL DEFAULT(strftime('%s','now'))
                    ); """)
])

dInsertTables = OrderedDict([
    ("SysSettings", """ INSERT INTO SysSettings (settingName, settingValue)
                        VALUES
                            ('InMaintenance', 'X'),
                            ('AliasNameMaxLength', 'X'),
                            ('OverSlotCountGraceDays', 'X'),
                            ('NZRNodeSlotMultiplier', 'X'),
                            ('PresaleIsActive', 'X'),
                            ('NewNodeNotifierLoopSeconds', 'X'),
                            ('UserResponseTimeoutSeconds','X'),
                            ('PollNodeStatusLoopSeconds', 'X'); """),
    ("Lookups", """ INSERT INTO Lookups (sourceTable, sourceColumn, keyValue, description)
                    VALUES
                        ('DiscordAdmins', 'role', 'SUPERUSER', 'Super user has all access.'),
                        ('DiscordAdmins', 'role', 'ADMIN', 'One level below superuser. Has almost all access.'),
                        ('DiscordAdmins', 'role', 'MODERATOR', 'General moderator access.'),
                        ('UserNodes', 'systemStatus', 'NEW', 'Status 1: New node that needs to be added to config files.'),
                        ('UserNodes', 'systemStatus', 'INPROCESS', 'Status 2: New node that is process of being added to config files. This status is only active during the config file creation process.'),
                        ('UserNodes', 'systemStatus', 'NOTIFY', 'Status 3: Newly added node. It is in the config files and the user needs to be notified. This identifies the notification system needs to alert the user.'),
                        ('UserNodes', 'systemStatus', 'COMPLETE', 'Status 4: User has been alerted and we assume they have started the node. This is the last status.'),
                        ('UserNodes', 'systemStatus', 'REMOVE', 'Record marked for removal. Will be removed in next coin config creation process.'),
                        ('UserNodes', 'networkStatus', 'NEW', 'Initial status. Stays in this status until the first time the node is seen on the coins masternode network.'),
                        ('UserNodes', 'networkStatus', 'UNKNOWN', 'No way to poll the network for masternode status.'),
                        ('UserNodes', 'daemonType', 'phantom', 'Masternode backend uses a phantom daemon.'),
                        ('UserNodes', 'daemonType', 'IPV6_ver1', 'Masternode backend uses a IPV6 version1 setup (to allow different setups in future).'),
                        ('Coins', 'masternodeCheckType', 'EXPLORER', 'Standard explorer API to get masternode listing.'),
                        ('Coins', 'masternodeCheckType', 'WALLET', 'Use RPC to a remote wallet daemon access masternode listing. This requiers the rpcAuthURL column to be populated with the credentials to access the remote wallet.'),
                        ('Coins', 'masternodeCheckType', 'NONE', 'No way to check the masternode status.'),
                        ('Coins', 'transactionCheckType', 'EXPLORER', 'Standard explorer API to get transaction info.'),
                        ('Coins', 'transactionCheckType', 'WALLET', 'Use RPC to a remote wallet daemon access transaction info. This requiers the rpcAuthURL column to be populated with the credentials to access the remote wallet.'),
                        ('Coins', 'transactionCheckType', 'NONE', 'No way to check the transaction info.'),
                        ('Coins', 'explorerType', 'IQUIDUS', 'Standard iquidus clone.'),
                        ('Coins', 'explorerType', 'BULWARK', 'Bulwark clone.'),
                        ('SysLogs', 'logType', 'info', 'Informational log entry. Usually for a job run that did no action (so no success or fail, just a plain run with no action needed).'),
                        ('SysLogs', 'logType', 'error', 'Error log entry. Usually for a job run that failed.'),
                        ('SysLogs', 'logType', 'success', 'Success log entry. Usually for a job run that succeeded.'),
                        ('SysLogs', 'logType', 'log', 'Log entry for archiving purposes. Usually to record data we delete in case it is needed in the future for troubleshooting or other purposes.'); """)
])

def main(sDB):

    #if database exists then quit
    if os.path.exists(sDB):
        print('Database already exists, aborting script.')
        sys.exit(0)

    # create connection (will also create the database)
    conn = createConnection(sDB)

    #create tables
    if conn:
        for sTable, sQuery in dCreateTables.items():
            createTable(conn, sTable, sQuery)

        print("Finished create tables.")
    else:
        print("Unknown error occured. I don't think we created the tables")

    #insert data
    if conn:
        for sTable, sQuery in dInsertTables.items():
            insertToTable(conn, sTable, sQuery)

        print("Finished populate tables.")
    else:
        print("Unknown error occured. I don't think we populated the tables")

    #close connection
    if conn:
        conn.close()

    #report completion
    print("Finished process. Exiting script.")


def createConnection(sDB):
    conn = None
    try:
        conn = sqlite3.connect(sDB)
        print("Connected to SQLLite version {}".format(sqlite3.version))
    except Error as e:
        print(e)

    return conn


def createTable(conn, sTable, sQuery):
    try:
        c = conn.cursor()
        c.execute(sQuery)
    except Error as e:
        print(e)
    else:
        print("Created {}".format(sTable))

def insertToTable(conn, sTable, sQuery):
    nRowCount = None
    try:
        c = conn.cursor()
        c.execute(sQuery)
        conn.commit()
        nRowCount = c.rowcount
        c.close()
    except Error as e:
        print(e)
    else:
        print("Inserted {} rows into {} table.".format(nRowCount, sTable))

if __name__ == '__main__':
    main(sDatabaseFile)