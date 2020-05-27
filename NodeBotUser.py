import sqlite3
from datetime import datetime
import sys
import os.path
from DAL import DAL
from utilFuncs import secondsToDaysHoursMinutesSecondsString


## version 1.0 #######################################################################################################
#####################################            Version history           ###########################################
######################################################################################################################
# 1/30/20 - version 1.0 - initial version
######################################################################################################################

class NodeBotUser:
    """Represents a NZR nodebot user.
    Used to hold info (data) about a user for easier access to the data.

    Attributes:
        discordID: (integer) The discord ID of this user
        totalSlots: (integer) Number of total masternode slots this user can use.
        usedSlots: (integer) Number of masternode slots used by this user.
        conn: (object) A connection to the database
    """

    def __init__(self, sDiscordID, sDB, oLogger, sLoggingLevel, sErrRefID):
        """Initialize user values."""
        self.logger = oLogger
        self.loggingLevel = sLoggingLevel
        self.discordID = sDiscordID
        self.databaseFile = sDB
        self.errRefID = sErrRefID
        self.isRegistered = False
        self.totalSlots = None
        self.usedSlots = None
        self._populateUserObject()

    def _populateUserObject(self):
        try:
            myDAL = DAL(self.databaseFile, self.logger, self.loggingLevel, self.errRefID)
            myDAL.connect()
            row = myDAL.selectData("single",
                                   """SELECT 1 as 'isRegistered', totalSlots, bonusSlots, usedSlots FROM Users WHERE ID = ?""",
                                   [self.discordID])
            myDAL.disconnect()
            if row:
                self.isRegistered = row["isRegistered"]
                self.totalSlots = row["totalSlots"] + row["bonusSlots"]
                self.usedSlots = row["usedSlots"]
            else:
                self.logger.warning("NodeBotUser - _populateUser - User not found in database. UserID: {}. ErrRefID: {}".format(self.discordID, self.errRefID))
        except Exception as e:
            self.logger.error("NodeBotUser - _populateUser - Error occured. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            raise

    def registerUser(self, nBonusSlots=0):
        try:
            myDAL = DAL(self.databaseFile, self.logger, self.loggingLevel, self.errRefID)
            myDAL.connect()

            #add the user to the Users table
            count = 0
            count = myDAL.insertUpdateDelete("""INSERT INTO Users (ID, totalSlots, usedSlots, bonusSlots)
                                                VALUES(?,?,?,?)""",[self.discordID, 0, 0, nBonusSlots])
            if (count != 1):
                self.logger.error("NodeBotUser - registerUser - Failed to insert user to Users table. BonusSlots: {}. ErrRefID: {}".format(str(nBonusSlots), self.errRefID))
                myDAL.rollback()
                myDAL.disconnect()
                return False, "Failed to insert required data. Please contact team."

            #update user object info
            self.isRegistered = True
            self.totalSlots = nBonusSlots
            self.usedSlots = 0

        except Exception as e:
            self.logger.error("NodeBotUser - registerUser - Error occured. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            myDAL.rollback()
            myDAL.disconnect()
            return False, "Failed to get required data. Please contact team."
        else:
            myDAL.commit()
            myDAL.addSysLogEntry("log","registerUser", "Success registerUser. User: {} BonusSlots: {}.".format(str(self.discordID), str(nBonusSlots)))
            myDAL.disconnect()
            return True, "[return value not used]"

    def unregisterUser(self):
        nBonusSlots = 0
        oAddedNodes = []
        oRegisteredNodes = []

        #Get a listing of all nodes the user has added to the system
        #the listNodes() function is self contained so keep it in its own try block
        try:
            bTmp, sTmp = self.listAddedNodes()
            if (bTmp):
                oAddedNodes = sTmp
            else:
                # this could mean an error, but we'll ignore any error and assume it means the user has no nodes
                pass
        except Exception as e:
            self.logger.error("NodeBotUser - unregisterUser - Unknown error occured getting listing of added nodes. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            return False, "Failed to obtain required data. Please contact team."

        #Get a listing of all registered nodes
        #the listRegisteredNodes() function is self contained so keep it in its own try block
        try:
            bTmp, sTmp = self.listRegisteredNodes()
            if (bTmp):
                oRegisteredNodes = sTmp
            else:
                # this could mean an error, but we'll ignore any error and assume it means the user has no nodes
                pass
        except Exception as e:
            self.logger.error("NodeBotUser - unregisterUser - Unknown error occured getting listing of registered nodes. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            return False, "Failed to obtain required data. Please contact team."

        #Remove all the added nodes
        #the removeNode() function is self contained so keep it in its own try block
        try:
            for node in oAddedNodes[1:]: #skip first entry because it is a header entry
                self.removeNode(node[0], node[2]) #the ticker is first item in the list, the collateral address is the 3rd item
        except Exception as e:
            self.logger.error("NodeBotUser - unregisterUser - Error occured removing added nodes. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            return False, "Failed to remove required data. Please contact team."

        #Unregister all nodes
        #the unregisterNode() function is self contained so keep it in its own try block
        try:
            for node in oRegisteredNodes[1:]: #skip first entry because it is a header entry
                self.unregisterNode(node[0]) #the collateral address is the 1st item
        except Exception as e:
            self.logger.error("NodeBotUser - unregisterUser - Error occured unregistering nodes. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            return False, "Failed to remove required data. Please contact team."

        #Now remove the user
        try:
            myDAL = DAL(self.databaseFile, self.logger, self.loggingLevel, self.errRefID)
            myDAL.connect()

            #get existing data for this user to add to system log when we delete (for recovery purposes)
            row = None
            row = myDAL.selectData("single", """SELECT bonusSlots FROM Users WHERE ID = ?""", [self.discordID])
            if row:
                nBonusSlots = row["bonusSlots"]
            else:
                self.logger.error("NodeBotUser - unregisterUser - No record found for user id {}. ErrRefID: {}".format(str(self.discordID), self.errRefID))
                myDAL.disconnect()
                return False, "Failed to select required data. Please contact team."

            #remove the user from the Users table
            count = 0
            count = myDAL.insertUpdateDelete("""DELETE FROM Users WHERE ID = ?""",[self.discordID])
            if (count != 1):
                self.logger.error("NodeBotUser - unregisterUser - Failed to delete user from Users table. User: {}. ErrRefID: {}".format(str(self.discordID), self.errRefID))
                myDAL.rollback()
                myDAL.disconnect()
                return False, "Failed to delete required data. Please contact team."

            #update user object info
            self.isRegistered = False
            self.totalSlots = 0
            self.usedSlots = 0

        except Exception as e:
            self.logger.error("NodeBotUser - unregisterUser - Error occured. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            myDAL.rollback()
            myDAL.disconnect()
            return False, "Failed to delete required data. Please contact team."
        else:
            myDAL.commit()
            myDAL.addSysLogEntry("log","unregisterUser", "Success unregisterUser. User: {} BonusSlots: {}.".format(str(self.discordID), str(nBonusSlots)))
            myDAL.disconnect()
            return True, "[return value not used]"

    def registerNode(self, sCollateralAddress, nFreeNodes):
        try:
            myDAL = DAL(self.databaseFile, self.logger, self.loggingLevel, self.errRefID)
            myDAL.connect()

            #verify this address is not already registered in the system
            row = None
            row = myDAL.selectData("single", """SELECT userID FROM RegisteredNZRNodes WHERE address = ?""", [sCollateralAddress])
            if row:
                myDAL.disconnect()
                if(row["userID"] == self.discordID):
                    self.logger.error("NodeBotUser - registerNode - Node already registered by this user. User: {} Address: {}. ErrRefID: {}".format(str(self.discordID), sCollateralAddress, self.errRefID))
                    return False, "You have already registered this node. Please contact team if you believe this is an error."
                else:
                    self.logger.error("NodeBotUser - registerNode - Node already registered by another user. UserTryingToAdd: {} Address: {}. ErrRefID: {}".format(str(self.discordID), sCollateralAddress, self.errRefID))
                    return False, "This node is already registered by another user in the system. Please contact team if you believe this is an error."

            #add the record to the RegisteredNZRNodes table
            count = 0
            count = myDAL.insertUpdateDelete("""INSERT INTO RegisteredNZRNodes (address, userID, nodesAllowed)
                                                VALUES(?,?,?)""",[sCollateralAddress, self.discordID, nFreeNodes])
            if (count != 1):
                self.logger.error("NodeBotUser - registerNode - Failed to insert node to RegisteredNZRNodes table. User: {} CollateralAddress: {} NodesAllowed: {}. ErrRefID: {}".format(str(self.discordID), sCollateralAddress, str(nFreeNodes), self.errRefID))
                myDAL.rollback()
                myDAL.disconnect()
                return False, "Failed to insert required data. Please contact team."

            #update user node count in database and in object
            self.totalSlots = self.totalSlots + nFreeNodes
            count = 0
            count = myDAL.insertUpdateDelete("""UPDATE Users SET totalSlots = totalSlots + ? WHERE ID = ?""",[nFreeNodes, self.discordID])
            if (count != 1):
                self.logger.error("NodeBotUser - registerNode - Failed to increment total slots for the user. User: {} Address: {} FreeSlots: {}. ErrRefID: {}".format(str(self.discordID), sCollateralAddress, str(nFreeNodes), self.errRefID))
                myDAL.rollback()
                myDAL.disconnect()
                return False, "Failed to update required data. Please contact team."

        except Exception as e:
            self.logger.error("NodeBotUser - registerNode - Error occured. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            myDAL.rollback()
            myDAL.disconnect()
            return False, "Failed to get required data. Please contact team."
        else:
            myDAL.commit()
            myDAL.addSysLogEntry("log","registerNode", "Success registernode. User: {} Address: {} FreeSlots: {}.".format(str(self.discordID), sCollateralAddress, str(nFreeNodes)))
            myDAL.disconnect()
            return True, "[return value not used]"

    def unregisterNode(self, sCollateralAddress):
        nFreeSlots = 0
        try:
            myDAL = DAL(self.databaseFile, self.logger, self.loggingLevel, self.errRefID)
            myDAL.connect()

            # verify this collateral address is registered to the user
            row = None
            row = myDAL.selectData("single", """SELECT nodesAllowed FROM RegisteredNZRNodes WHERE userID = ? and address = ?""",[self.discordID, sCollateralAddress])
            if row:
                nFreeSlots = row["nodesAllowed"]
            else:
                myDAL.disconnect()
                self.logger.warning("NodeBotUser - unregisterNode - User attempted to unregister a node that was not found for them. User: {} CollateralAddress: {}. ErrRefID: {}".format(str(self.discordID), sCollateralAddress, self.errRefID))
                return False, "No NZR node with collateral address of {} found to be registered for you in the system.".format(sCollateralAddress)

            # remove the record from the RegisteredNZRNodes table
            count = 0
            count = myDAL.insertUpdateDelete("""DELETE FROM RegisteredNZRNodes WHERE userID = ? and address = ?""", [self.discordID, sCollateralAddress])
            if (count != 1):
                self.logger.error("NodeBotUser - unregisterNode - Failed to remove node from RegisteredNZRNodes table. User: {} CollateralAddress: {}. ErrRefID: {}".format(str(self.discordID), sCollateralAddress, self.errRefID))
                myDAL.rollback()
                myDAL.disconnect()
                return False, "Failed to delete required data. Please contact team."

            # update user free node count in database and in object
            self.totalSlots = self.totalSlots - nFreeSlots
            count = 0
            count = myDAL.insertUpdateDelete("""UPDATE Users SET totalSlots = totalSlots - ? WHERE ID = ?""", [nFreeSlots, self.discordID])
            if (count != 1):
                self.logger.error("NodeBotUser - unregisterNode - Failed to decrement total slot count for the user. UserID: {} CollateralAddress: {} FreeSlotDecrement: {}. ErrRefID: {}".format(str(self.discordID), sCollateralAddress, str(nFreeSlots), self.errRefID))
                myDAL.rollback()
                myDAL.disconnect()
                return False, "Failed to update required data. Please contact team."

        except Exception as e:
            self.logger.error("NodeBotUser - unregisterNode - Error occured. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            myDAL.rollback()
            myDAL.disconnect()
            return False, "Failed to get required data. Please contact team."
        else:
            myDAL.commit()
            myDAL.addSysLogEntry("log", "unregisterNode", "Success unregister node. UserID: {} CollateralAddress: {} FreeSlotDecrement: {}".format(str(self.discordID), sCollateralAddress, str(nFreeSlots)))
            myDAL.disconnect()
            return True, "[return value not used]"

    def listRegisteredNodes(self):
        sFuncName = "NodeBotUser.listRegisteredNodes"
        returnList = []
        try:
            myDAL = DAL(self.databaseFile, self.logger, self.loggingLevel, self.errRefID)
            myDAL.connect()

            # query the data
            rows = None
            rows = myDAL.selectData("multi", """SELECT  address, 
                                                        CASE isActive WHEN 1 THEN 'Enabled' ELSE 'Missing' END isActive, 
                                                        nodesAllowed, 
                                                        DATETIME(lastSeenEpDateTime, 'unixepoch') as lastSeenDateTime 
                                                FROM RegisteredNZRNodes WHERE userID = ? ORDER BY address""",[self.discordID], False)
            if rows:
                #add header row
                returnList.append(["Node Address", "Status", "Granting Free Nodes", "Last Seen On Network (GMT)"])
                for row in rows:
                    returnList.append([str(x) for x in row])  #need all values as strings for our discord table creation function
            else:
                myDAL.disconnect()
                if(self.loggingLevel in ["INFO","VERBOSE"]):
                    self.logger.info("{} - No results from query. User: {} ErrRefID: {}".format(sFuncName, str(self.discordID), self.errRefID))
                return False, "No registered nodes were found for you in the system."
        except Exception as e:
            self.logger.error("{} - Error occured. Error: {}. ErrRefID: {}".format(sFuncName, str(e), self.errRefID))
            myDAL.disconnect()
            return False, "Failed to get required data. Please contact team."
        else:
            myDAL.disconnect()
            return True, returnList

    def addNode(self, sTicker, sAliasName, nPort, sCollateralAddress, sTXID, nTXIndex):
        sDefaultAliasName = ""
        sIPAddress = ""
        sMasternodeKey = ""
        sDaemonType = ""
        nPhantomEpDateTime = 0
        try:
            myDAL = DAL(self.databaseFile, self.logger, self.loggingLevel, self.errRefID)
            myDAL.connect()

            #verify this UTXO is not already registered in the system
            row = None
            row = myDAL.selectData("single", """SELECT userID FROM UserNodes WHERE coinTicker = ? and txID = ? and txIndex=?""", [sTicker, sTXID, nTXIndex], False)
            if row:
                myDAL.disconnect()
                if(row["userID"] == self.discordID):
                    self.logger.error("NodeBotUser - addNode - UTXO already used by this user. Ticker: {} TXID: {} TXIndex: {}. ErrRefID: {}".format(sTicker, sTXID, str(nTXIndex), self.errRefID))
                    return False, "You have already added a node with this transaction ID and transaction index. If needed, please delete it before adding it again, or contact team if you believe this is an error."
                else:
                    self.logger.error("NodeBotUser - addNode - UTXO already used by another user. UserTryingToAdd: {} Ticker: {} TXID: {} TXIndex: {}. ErrRefID: {}".format(str(self.discordID), sTicker, sTXID, str(nTXIndex), self.errRefID))
                    return False, "Transaction ID and transaction index are already added by another user in the system. Please try again, or contact team if you believe this is an error."

            #get an unused IP address and default alias name for this coin
            row = None
            row = myDAL.selectData("single", """SELECT IP, defaultAlias, masternodeKey, daemonType, phantomEpDateTime FROM CoinIPs WHERE coinTicker = ? and isUsed=0 ORDER BY ID LIMIT 1""", [sTicker])
            if row:
                sDefaultAliasName = row["defaultAlias"]
                sIPAddress = row["IP"]
                sMasternodeKey = row["masternodeKey"]
                sDaemonType = row["daemonType"]
                nPhantomEpDateTime = row["phantomEpDateTime"]

            else:
                self.logger.error("NodeBotUser - addNode - No unused coin IP address found for coin {}. ErrRefID: {}".format(sTicker, self.errRefID))
                myDAL.disconnect()
                return False, "System capacity for {} coin reached. Please contact team to inform them.".format(sTicker)

            #if alias name is default, then use the default one
            if (sAliasName.lower() == 'default'):
                sAliasName = sDefaultAliasName

            #verify aliasname is unique for this user/ticker combination (an alias name must be unique in a user's wallet)
            row = None
            row = myDAL.selectData("single", """SELECT 1 FROM UserNodes WHERE userID = ? and coinTicker = ? and aliasName=?""", [str(self.discordID), sTicker, sAliasName.lower()],False)
            if row:
                myDAL.disconnect()
                self.logger.error("NodeBotUser - addNode - Aliasname already in use by this user. User: {} Ticker: {} AliasName: {}. ErrRefID: {}".format(str(self.discordID), sTicker, sAliasName, self.errRefID))
                return False, "You are already using alias name of {} for coin {}. The alias name is case-insensitive (meaning MN1 = Mn1 = mN1 = mn1). This is not allowed. Please remove the other node if it is not in use or choose a different alias name. Please contact a team member if you belive this is in error.".format(sAliasName, sTicker)

            #verify this collateral address is not already registered in the system for this coin
            row = None
            row = myDAL.selectData("single", """SELECT userID FROM UserNodes WHERE coinTicker = ? and collateralAddress = ?""", [sTicker, sCollateralAddress], False)
            if row:
                myDAL.disconnect()
                if(row["userID"] == self.discordID):
                    self.logger.error("NodeBotUser - addNode - Collateral address for UTXO already used by this user. Ticker: {} TXID: {} TXIndex: {} CollateralAddress {}. ErrRefID: {}".format(sTicker, sTXID, str(nTXIndex), sCollateralAddress, self.errRefID))
                    return False, "You have already registered a {} node with collateral address of {}. If needed, please delete it before adding it again, or contact team if you believe this is an error.".format(sTicker, sCollateralAddress)
                else:
                    self.logger.error("NodeBotUser - addNode - Collateral address for UTXO already used by another user. UserTryingToAdd: {} Ticker: {} TXID: {} TXIndex: {} CollateralAddress {}. ErrRefID: {}".format(str(self.discordID), sTicker, sTXID, str(nTXIndex), sCollateralAddress, self.errRefID))
                    return False, "A {} node with collateral address of {} is already registered by another user in the system. Please try again, or contact team if you believe this is an error.".format(sTicker, sCollateralAddress)


            #mark this IP as used
            count = 0
            count = myDAL.insertUpdateDelete("""UPDATE CoinIPs SET isUsed=1 WHERE coinTicker = ? AND IP = ?""",[sTicker, sIPAddress])
            if (count != 1):
                self.logger.error("NodeBotUser - addNode - IP address failed to be marked as used. Ticker: {} IP: {}. ErrRefID: {}".format(sTicker, sIPAddress, self.errRefID))
                myDAL.rollback()
                myDAL.disconnect()
                return False, "Failed to update required data. Please contact team."


            #add the record to the UserNodes table
            count = 0
            count = myDAL.insertUpdateDelete("""INSERT INTO UserNodes (userID, coinTicker, aliasName, genKey, IP, coinPort, collateralAddress, txID, txIndex, isActive, systemStatus, daemonType, phantomEpDateTime)
                                                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",[self.discordID, sTicker, sAliasName, sMasternodeKey, sIPAddress, nPort, sCollateralAddress, sTXID, nTXIndex, 1, 'NEW', sDaemonType, nPhantomEpDateTime])
            if (count != 1):
                self.logger.error("NodeBotUser - addNode - Failed to insert node to UserNodes table. User: {} Ticker: {} AliasName: {} GenKey: {} IP: {} Port: {} CollateralAddress: {} TXID: {} TXIndex: {} DaemonType: {} PhantomEpDateTime: {}. ErrRefID: {}".format(str(self.discordID), sTicker, sAliasName, sMasternodeKey, sIPAddress, str(nPort), sCollateralAddress, sTXID, str(nTXIndex), sDaemonType, str(nPhantomEpDateTime), self.errRefID))
                myDAL.rollback()
                myDAL.disconnect()
                return False, "Failed to insert required data. Please contact team."

            #update user node count in database and in object if not NZR
            if(sTicker != 'NZR'):
                self.usedSlots = self.usedSlots + 1
                count = 0
                count = myDAL.insertUpdateDelete("""UPDATE Users SET usedSlots = usedSlots + 1 WHERE ID = ?""",[self.discordID])
                if (count != 1):
                    self.logger.error("NodeBotUser - addNode - Failed to increment used count for the user. User: {} Ticker: {} AliasName: {} GenKey: {} IP: {} Port: {} CollateralAddress: {} TXID: {} TXIndex: {} DaemonType: {} PhantomEpDateTime: {}. ErrRefID: {}".format(str(self.discordID), sTicker, sAliasName, sMasternodeKey, sIPAddress, str(nPort), sCollateralAddress, sTXID, str(nTXIndex), sDaemonType, str(nPhantomEpDateTime), self.errRefID))
                    myDAL.rollback()
                    myDAL.disconnect()
                    return False, "Failed to update required data. Please contact team."

        except Exception as e:
            self.logger.error("NodeBotUser - addNode - Error occured. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            myDAL.rollback()
            myDAL.disconnect()
            return False, "Failed to get required data. Please contact team."
        else:
            myDAL.commit()
            myDAL.addSysLogEntry("log","addNode", "Success addnode. User: {} Ticker: {} AliasName: {} GenKey: {} IP: {} Port: {} CollateralAddress: {} TXID: {} TXIndex: {} DaemonType: {} PhantomEpDateTime: {}.".format(str(self.discordID), sTicker, sAliasName, sMasternodeKey, sIPAddress, str(nPort), sCollateralAddress, sTXID, str(nTXIndex), sDaemonType, str(nPhantomEpDateTime)))
            myDAL.disconnect()
            return True, (sAliasName + " " + sIPAddress + ":" + str(nPort) + " " + sMasternodeKey + " " + sTXID + " " + str(nTXIndex))

    def removeNode(self, sTicker, sCollateralAddress):
        sTXID = ""
        nTXIndex = ""
        sIP = ""
        try:
            myDAL = DAL(self.databaseFile, self.logger, self.loggingLevel, self.errRefID)
            myDAL.connect()

            # verify this collateral address is registered to the user
            row = None
            row = myDAL.selectData("single", """SELECT txID, txIndex, IP FROM UserNodes WHERE coinTicker = ? and collateralAddress = ? and userID = ?""",[sTicker, sCollateralAddress, self.discordID])
            if row:
                sTXID = row["txID"]
                nTXIndex = int(row["txIndex"])
                sIP = row["IP"]
            else:
                myDAL.disconnect()
                self.logger.warning("NodeBotUser - removeNode - User attempted to remove a node that was not found for them. User: {} Ticker: {} CollateralAddress: {}. ErrRefID: {}".format(str(self.discordID), sTicker, sCollateralAddress, self.errRefID))
                return False, "A {} node with collateral address of {} was not found for you in the system.".format(sTicker, sCollateralAddress), "[return value not used]"

            # mark the record to REMOVE from the UserNodes table
            count = 0
            count = myDAL.insertUpdateDelete("""Update UserNodes set systemStatus = ? WHERE userID = ? and coinTicker = ? and collateralAddress = ?""", ['REMOVE', self.discordID, sTicker, sCollateralAddress])
            if (count != 1):
                self.logger.error("NodeBotUser - removeNode - Failed to mark node as systemStatus of REMOVE in UserNodes table. User: {} Ticker: {} CollateralAddress: {}. ErrRefID: {}".format(str(self.discordID), sTicker, sCollateralAddress, self.errRefID))
                myDAL.rollback()
                myDAL.disconnect()
                return False, "Failed to delete required data. Please contact team.", "[return value not used]"

            #mark this IP as unused
            count = 0
            count = myDAL.insertUpdateDelete("""UPDATE CoinIPs SET isUsed=0 WHERE coinTicker = ? AND IP = ?""",[sTicker, sIP])
            if (count != 1):
                self.logger.error("NodeBotUser - removeNode - IP address failed to be marked as unused. Ticker: {} IP: {}. ErrRefID: {}".format(sTicker, sIP, self.errRefID))
                myDAL.rollback()
                myDAL.disconnect()
                return False, "Failed to update required data. Please contact team."

            # update user node count in database and in object if not NZR node
            if (sTicker != 'NZR'):
                self.usedSlots = self.usedSlots - 1
                count = 0
                count = myDAL.insertUpdateDelete("""UPDATE Users SET usedSlots = usedSlots - 1 WHERE ID = ?""", [self.discordID])
                if (count != 1):
                    self.logger.error("NodeBotUser - removeNode - Failed to decrement used slot count for the user. UserID: {} Ticker: {} CollateralAddress: {} IPAddress: {} TXID: {} TXindex: {}. ErrRefID: {}".format(str(self.discordID), sTicker, sCollateralAddress, sIP, sTXID, str(nTXIndex), self.errRefID))
                    myDAL.rollback()
                    myDAL.disconnect()
                    return False, "Failed to update required data. Please contact team.", "[return value not used]"

        except Exception as e:
            self.logger.error("NodeBotUser - removeNode - Error occured. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            myDAL.rollback()
            myDAL.disconnect()
            return False, "Failed to get required data. Please contact team.", "[return value not used]"
        else:
            myDAL.commit()
            myDAL.addSysLogEntry("log", "removeNode", "Success mark node for removal. UserID: {} Ticker: {} CollateralAddress: {} IPAddress: {} TXID: {} TXindex: {}".format(str(self.discordID), sTicker, sCollateralAddress, sIP, sTXID, str(nTXIndex)))
            myDAL.disconnect()
            return True, sTXID, nTXIndex

    def listAddedNodes(self, sTicker=''):
        returnList = []
        try:
            myDAL = DAL(self.databaseFile, self.logger, self.loggingLevel, self.errRefID)
            myDAL.connect()

            # query the data
            rows = None
            if (sTicker != ""):
                rows = myDAL.selectData("multi", """SELECT coinTicker,
                                                            aliasName,
                                                            collateralAddress,
                                                            networkStatus,
                                                            (strftime('%s','now') - lastSeenEpDateTime) as lastSeenSeconds
                                                            FROM UserNodes WHERE coinTicker = ? and userID = ? ORDER BY aliasName""",[sTicker, self.discordID],False)
            else:
                rows = myDAL.selectData("multi", """SELECT coinTicker, 
                                                            aliasName, 
                                                            collateralAddress,
                                                            networkStatus,
                                                            (strftime('%s','now') - lastSeenEpDateTime) as lastSeenSeconds
                                                            FROM UserNodes WHERE userID = ? ORDER BY coinTicker, aliasName""", [self.discordID], False)
            if rows:
                #add header row
                returnList.append(["Ticker", "Alias Name", "Collateral Address", "Status", "Last Seen"])
                for row in rows:
                    returnList.append([row["coinTicker"], row["aliasName"], row["collateralAddress"], row["networkStatus"], secondsToDaysHoursMinutesSecondsString(row["lastSeenSeconds"])]) #need all values as strings for our discord table creation function
            else:
                myDAL.disconnect()
                if (sTicker != ""):
                    return False, "No {} nodes were found for you in the system.".format(sTicker)
                else:
                    return False, "No nodes were found for you in the system."
        except Exception as e:
            self.logger.error("NodeBotUser - listAddedNodes - Error occured. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            myDAL.disconnect()
            return False, "Failed to get required data. Please contact team."
        else:
            myDAL.disconnect()
            return True, returnList

    def listConfigs(self, sTicker=''):
        returnList = []
        sCurrTicker = ""  #used to identify current ticker when building our listing of all nodes (so we an add headers when group the tickers in output)
        try:
            myDAL = DAL(self.databaseFile, self.logger, self.loggingLevel, self.errRefID)
            myDAL.connect()

            # query the data
            rows = None
            if (sTicker != ""):
                rows = myDAL.selectData("multi", """SELECT coinTicker,
                                                            aliasName,
                                                            collateralAddress,
                                                            IP,
                                                            coinPort,
                                                            genKey,
                                                            txID,
                                                            txIndex
                                                            FROM UserNodes WHERE coinTicker = ? and userID = ? ORDER BY aliasName""",[sTicker, self.discordID])
            else:
                rows = myDAL.selectData("multi", """SELECT coinTicker, 
                                                            aliasName,
                                                            collateralAddress,
                                                            IP,
                                                            coinPort,
                                                            genKey,
                                                            txID,
                                                            txIndex
                                                            FROM UserNodes WHERE userID = ? ORDER BY coinTicker, aliasName""", [self.discordID])
            if rows:
                for row in rows:
                    #if ticker changed (or first time through), set the current ticker and add a header row
                    if ((sCurrTicker != row["coinTicker"]) or (sCurrTicker == "")):
                        sCurrTicker = row["coinTicker"]
                        returnList.append(["##### " + row["coinTicker"] + " #####"])

                    #add the data
                    returnList.append([(row["aliasName"] + " " + row["IP"] + ":" + str(row["coinPort"]) + " " + row["genKey"] + " " + row["txID"] + " " + str(row["txIndex"]))])   #need all values as strings for our discord table creation function
            else:
                myDAL.disconnect()
                if (sTicker != ""):
                    self.logger.warning("NodeBotUser - listConfigs - No results from query. User: {} Ticker: {}. ErrRefID: {}".format(str(self.discordID), sTicker, self.errRefID))
                    return False, "No {} nodes were found for you in the system.".format(sTicker)
                else:
                    self.logger.warning("NodeBotUser - listConfigs - No results from query. User: {} Ticker: [all tickers]. ErrRefID: {}".format(str(self.discordID), self.errRefID))
                    return False, "No nodes were found for you in the system."
        except Exception as e:
            self.logger.error("NodeBotUser - listConfigs - Error occured. Error: {}. ErrRefID: {}".format(str(e), self.errRefID))
            myDAL.disconnect()
            return False, "Failed to get required data. Please contact team."
        else:
            myDAL.disconnect()
            return True, returnList
