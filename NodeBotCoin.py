import sqlite3
from datetime import datetime
import sys
import os.path
import logging
from DAL import DAL
import json
import requests
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

## version 1.0 #######################################################################################################
#####################################            Version history           ###########################################
######################################################################################################################
# 1/30/20 - version 1.0 - initial version
######################################################################################################################


class NodeBotCoin:
    """Represents a NZR nodebot coin.
    Used to hold info (data) about a coin for easier access to the data.

    Attributes:
        ticker: (string) The ticker of this coin
        coinName: (string) The name of this coin
        collateral: (integer) Collateral amount for a masternode
        port: (integer) Coin P2P port
    """

    def __init__(self, sTicker, sDB, oLogger, sLoggingLevel, sErrRefID):
        """Initialize user values."""
        self.logger = oLogger
        self.loggingLevel = sLoggingLevel
        self.ticker = sTicker
        self.databaseFile = sDB
        self.errRefID = sErrRefID
        self.coinName = ""
        self.collateralAmount = 0
        self.port = 0
        self.blockTimeSeconds = 0
        self.transactionCheckType = ""
        self.transactionCheckURL = ""
        self.masternodeCheckType = ""
        self.masternodeCheckURL = ""
        self.explorerCheckURL = ""
        self.explorerType = ""
        self.rpcAuthURL = ""
        self._getCoinAttributes()

    def checkCollateralTX(self, sTXID):
        sFuncName = "NodeBotCoin.checkCollateralTX"

        #get transaction info
        try:

            if (self.transactionCheckType == 'EXPLORER'):
                #check the explorer
                if (not self.isExplorerAPIResponding()):
                    return False, 0, 0, "Coin explorer is not responding. This wizard cannot continue without the explorer. You can manually add this node (check `=help` command) or contact the team."

                nConfirmations = 0
                nCollateralOutputCount = 0
                nCollateralOutputIndex = None

                request = requests.get(self.transactionCheckURL.format(sTXID))
                response = request.text
                jsondata = json.loads(response)
                nConfirmations = jsondata["confirmations"]
                vouts = jsondata["vout"] #vouts is a list of dictionaries

                #Check each output for the collateral amount and store the output index (and count the outputs in case there are multiple)
                for vout in vouts:
                    if vout["value"] == self.collateralAmount:
                        nCollateralOutputIndex = vout["n"]
                        nCollateralOutputCount += 1

                #if no outputs found, the return with information
                if (nCollateralOutputCount == 0):
                    return False, 0, 0, "Transaction ID is not a collateral transaction (double check it is the transaction where you sent yourself {} coins).".format(self.collateralAmount)

                #if multiple outputs found, the return with information
                if (nCollateralOutputCount > 1):
                    return False, 0, 0, "Transaction ID contains multiple collateral outputs (meaning, multiple outputs of {} coins). This is currently not supported in this wizard. You can manually add this node (check `=help` command) or contact the team.".format(self.collateralAmount)

            if (self.transactionCheckType == 'WALLET'):
                #TODO Write this logic. Until it is written, return false
                return False, 0, 0, "Code for this type of coin not yet written. This wizard cannot continue without this portion of code. Until it is written, you can manually add this node (check `=help` command) or contact the team for an ETA when the wizard will be updated."

            if (self.transactionCheckType == 'NONE'):
                #We cannot confirm the transaction, return false
                return False, 0, 0, "This type of coin has no method to check the transaction. This wizard cannot continue without this.  You can manually add this node (check `=help` command) or contact the team for assistance."

        except Exception as e:
            self.logger.error("{} - Error occured. Error: {}. ErrRefID: {}".format(sFuncName, str(e), self.errRefID))
            return False, 0, 0, "Unknown error. Please contact team."
        else:
            return True, nConfirmations, nCollateralOutputIndex, "[return value not used]"

    def getCollateralAddress(self, sTXID, nTXIndex):
        sFuncName = "NodeBotCoin.getCollateralAddress"

        #get collateral address from transaction info
        try:
            if (self.transactionCheckType == 'EXPLORER'):
                #check the explorer
                if (not self.isExplorerAPIResponding()):
                    return False, "Coin explorer is not responding. This wizard cannot continue without the explorer. You can manually add this node (check `=help` command) or contact the team."

                request = requests.get(self.transactionCheckURL.format(sTXID))
                response = request.text
                jsondata = json.loads(response)
                vouts = jsondata["vout"] #vouts is a list of dictionaries

                #Check each output for the specified TXindex and get the address for that UTXO
                for vout in vouts:
                    if vout["n"] == nTXIndex:
                        scriptPubKey = vout["scriptPubKey"]
                        if (len(scriptPubKey["addresses"]) == 1):
                            return True, scriptPubKey["addresses"][0]
                        else:
                            self.logger.error("{} - Failed to get collateral address associated with TXID {} and TXIndex {}. There was zero or multiple addresses in the scriptpubkey address array. ErrRefID: {}".format(sFuncName, sTXID, str(nTXIndex), self.errRefID))
                            return False, "Failed to identify the address associated with the transaction and index. Please contact the team."

            if (self.transactionCheckType == 'WALLET'):
                #TODO Write this logic. Until it is written, return false
                return False, "Code for this type of coin not yet written. This wizard cannot continue without this portion of code. Until it is written, you can manually add this node (check `=help` command) or contact the team for an ETA when the wizard will be updated."

            if (self.transactionCheckType == 'NONE'):
                #We cannot confirm the transaction, return false
                return False, "This type of coin has no method to check the transaction. This wizard cannot continue without this.  You can manually add this node (check `=help` command) or contact the team for assistance."

        except Exception as e:
            self.logger.error("{} - Error occured. Error: {}. ErrRefID: {}".format(sFuncName, str(e), self.errRefID))
            return False, "Unknown error. Please contact team."
        else:
            #If we got here, we never found the address, return unknown issue error
            self.logger.error("{} - Never found a collateral address for TXID of {} and TXIndex of {}. ErrRefID: {}".format(sFuncName, sTXID, str(nTXIndex), self.errRefID))
            return False, "Failed to identify the address associated with the transaction and index. Please contact the team."

    def isMasternodeActive(self, sCollateralAddress):
        sFuncName = "NodeBotCoin.isMasternodeActive"
        bFound = False  #identifies if we found this collateral address in the list of active masternodes

        try:
            # check the apis to see if they are responding
            if(self.masternodeCheckType == 'EXPLORER'):
                if (not self.isExplorerAPIResponding()):
                    return False, "Coin explorer is not responding. Please wait a while and try again once explorer is working."
            if (self.masternodeCheckType == 'WALLET'):
                #TODO Write this logic. Until it is written, return assume success
                pass
            if (self.masternodeCheckType == 'NONE'):
                #We cannot confirm the masternode, return false
                return False, "NONE api type masternode listing is impossible."

            #get the data and search for the node
            jsondata = self._getMasternodeList()  #jsondata is a array of objects
            # Check each output for the collateral amount and store the output index (and count the outputs in case there are multiple)
            for item in jsondata:
                if item["addr"] == sCollateralAddress:
                    bFound = True

        except Exception as e:
            self.logger.error("{} - Error occured. Error: {}. ErrRefID: {}".format(sFuncName, str(e), self.errRefID))
            return False, "Unknown error. Please contact team."
        else:
            if (bFound):
                return True, "[return value not used]"
            else:
                return False, "The collateral address was not found in the list of active masternodes. Please ensure the node is active and/or wait a few minutes and try again."

    def isValidSignature(self, sAddress, sSignature, sMessage):
        sFuncName = "NodeBotCoin.isValidSignature"
        bValid = False  # identifies if signature is valid

        # check if signature is valid
        try:
            # hit the RPC server to see if signature is valid for the address and message
            oRPCConnection = AuthServiceProxy(self.rpcAuthURL)
            bValid = oRPCConnection.verifymessage(sAddress, sSignature, sMessage)
        except Exception as e:
            self.logger.warning("{} - Unknown error occured.  Error: {}. ErrRefID: {}".format(sFuncName, str(e), self.errRefID))
            return False, "Unknown error occured validating signature. Please wait a while and try again."
        else:
            if (bValid):
                return True, "[return value not used]"
            else:
                return False, "Signature did not validate."

    def isExplorerAPIResponding(self):
        sFuncName = "NodeBotCoin.isExplorerAPIResponding"

        #check the explorer
        try:
            request = requests.get(self.explorerCheckURL)
        except Exception as e:
            self.logger.error("{} - Unknown exception checking explorer. Ticker: {}. ExplorerCheckURL: {} ErrRefID: {}".format(sFuncName, self.ticker, self.explorerCheckURL, self.errRefID))
            return False #no need to re-raise the exception as it simply means the explorer is not responding
        else:
            return True

    def _getMasternodeList(self):
        sFuncName = "NodeBotCoin._getMasternodeList"

        try:
            if(self.masternodeCheckType == "EXPLORER"):
                request = requests.get(self.masternodeCheckURL)
                response = request.text

                if(self.explorerType == "IQUIDUS"):
                    jsondata = json.loads(response)
                elif(self.explorerType == "BULWARK"): #Bulwark embeds the data in a sub-element called mns
                    jsondata = json.loads(response)
                    jsondata = jsondata["mns"]
                else:
                    raise Exception("{} - Coin ticker {} has masternodeCheckType of EXPLORER but non-supported explorerType of {}".format(sFuncName, self.ticker, self.explorerType))

            if(self.masternodeCheckType == "WALLET"):
                oRPCConnection = AuthServiceProxy(self.rpcAuthURL)
                jsondata = oRPCConnection.listmasternodes()

            if(self.masternodeCheckType == "NONE"):
                raise Exception("{} - masternodeCheckType of NONE masternode listing is impossible".format(sFuncName))
        except Exception as e:
            self.logger.error("{} - Error occured. Error: {}. ErrRefID: {}".format(sFuncName, str(e), self.errRefID))
            raise
        else:
            return jsondata

    def _getCoinAttributes(self):
        sFuncName = "NodeBotCoin._getCoinAttributes"

        try:
            myDAL = DAL(self.databaseFile, self.logger, self.loggingLevel, self.errRefID)
            myDAL.connect()
            row = myDAL.selectData("single","SELECT coinName, collateralAmount, port, blockTimeSeconds, transactionCheckType, transactionCheckURL, masternodeCheckType, masternodeCheckURL, explorerCheckURL, explorerType, rpcAuthURL FROM Coins WHERE ticker=?",[self.ticker])
            myDAL.disconnect()
            if row:
                self.coinName = row["coinName"]
                self.collateralAmount = row["collateralAmount"]
                self.port = row["port"]
                self.blockTimeSeconds = row["blockTimeSeconds"]
                self.transactionCheckType = row["transactionCheckType"]
                self.transactionCheckURL = row["transactionCheckURL"]
                self.masternodeCheckType = row["masternodeCheckType"]
                self.masternodeCheckURL = row["masternodeCheckURL"]
                self.explorerCheckURL = row["explorerCheckURL"]
                self.explorerType = row["explorerType"]
                self.rpcAuthURL = row["rpcAuthURL"]
            else:
                self.logger.error("{} - Coin not found in database. Ticker: {}. ErrRefID: {}".format(sFuncName, self.ticker, self.errRefID))
                raise Exception("Coin not found")
        except Exception as e:
            self.logger.error("{} - Error occured. Ticker: {} Error: {}. ErrRefID: {}".format(sFuncName, self.ticker, str(e), self.errRefID))
            raise







