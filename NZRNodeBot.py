import discord
from discord.ext import tasks, commands
import logging
from NodeBotUser import NodeBotUser
from NodeBotCoin import NodeBotCoin
from DAL import DAL
from utilFuncs import secondsToDaysHoursMinutesSecondsString
from datetime import datetime
import time
import asyncio
import sqlite3
import sys
import os.path


## version 1.0 #######################################################################################################
#####################################            Version history           ###########################################
######################################################################################################################
# 1/30/20 - version 1.0 - initial version
#		INSTALL NOTES
#			requires
#               wheel (for other packages below)     (pip install wheel)
#				discord.py (built on version 1.2.5)  (pip install discord.py)
# 				requests (built on version 2.22.0)   (pip install requests)
#				bitcoinrpc (built on version 1.0)    (pip install python-bitcoinrpc)
#
#			additional user modules (coded by me) required in same directory
#				DAL.py (version 1.0)
#				NodeBotUser.py (version 1.0)
#				NodeBotCoin.py (version 1.0)
#				createNZRNodeBotDatabase.py (database creation script.  version 1.0)
#				utilFuncs.py (version 1.0)
#
#           utility scripts that run as cron jobs
#
######################################################################################################################

###################################################
##############    SET DEV MODE    #################
DEVMODE = False
#check devmode parameter
if len(sys.argv) > 1:
	if sys.argv[1] == "devmode=true":
		DEVMODE = True
###################################################

###################################################
############         SETTINGS       ###############
###################################################
g_sBotToken = 'XXXXXXXXXXXXXX'   #bot's secret token. Remove the value if ever showing someone the code
g_sCommandPrefix = "="

#Constants
g_sValidSignedMessage = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789=+/" #base64 encoding
g_sValidAlphaNumeric = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
g_sValidAlpha = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
g_sValidNumeric = "0123456789"
g_sNZRNodeBotDatabase = "XXXXXXXXX.db"

########### System Constants - these will be populated in the populateSystemConstants function from the databse (these can be modified on the fly by changing database and calling the repopulateConstancts command)
g_aSupportedCoins = []
g_aDiscordAdmins = []
g_nSystemMaintenance = 0
g_nUserResponseWaitTimeout = 0
g_nAliasNameMaxLength = 0
g_nOverSlotCountGraceDays = 0
g_nNZRNodeSlotMultiplier = 0
g_bPresaleIsActive = False
g_nNewNodeNotifierLoopSeconds = 0
g_nPollNodeStatusLoopSeconds = 0
g_sLoggingLevel = "VERBOSE" #default to verbose logging until we query database for the value.
######### End System Constants

g_sStatusCommand = g_sCommandPrefix + "status"
g_sRegisterUserCommand = g_sCommandPrefix + "registerUser"
g_sUnRegisterUserCommand = g_sCommandPrefix + "unregisterUser"
g_sRegisterNodeCommand = g_sCommandPrefix + "registerNode"
g_sUnRegisterNodeCommand = g_sCommandPrefix + "unregisterNode"
g_sListRegisteredNodesCommand = g_sCommandPrefix + "listRegisteredNodes"
g_sAddNodeCommand = g_sCommandPrefix + "addNode"
g_sRemoveNodeCommand = g_sCommandPrefix + "removeNode"
g_sShutdownBotCommand = g_sCommandPrefix + "shutdownBot"
g_sRepopulateConstantsCommand = g_sCommandPrefix + "repopulateConstants"
g_sListAddedNodesCommand = g_sCommandPrefix + "listAddedNodes"
g_sListConfigsCommand = g_sCommandPrefix + "listConfigs"
g_sListCoinsCommand = g_sCommandPrefix + "listCoins"
g_sStopNewNodeNotifierCommand = g_sCommandPrefix + "stopNewNodeNotifier"
g_sStopNewNodeNotifierCommand = g_sCommandPrefix + "startNewNodeNotifier"

#Response constants
#Responses for all commands
g_sResponse_UnknownMaintenanceState = "The database is currently in an unknown state. No functionality accessing the database can be performed. Please alert a team member."
g_sResponse_InMaintenanceMode = "The system is currently undergoing database maintenance. Any functionality accessing the database is disabled until maintenance is complete. While we cannot guarantee when it will be complete, we anticipate the system will be back online {} minutes from now."
g_sResponse_DatabaseConnectionFail = "The bot is unable to connect to the database at this time, please inform a team member."
g_sResponse_UsingXofYSlots = "You are currently using {} of your {} slots of free node hosting."
g_sResponse_TimeoutWaitingForResponse = "I'm sorry, you have taken over {} seconds to respond.  This interaction is being reset. Please start over by re-running the `{}` command."
g_sResponse_InputNotValidCharacters = "I'm sorry, you have entered a character that is not valid for this system.  Please ensure all characters you use are one of the following {}"
g_sResponse_ParametersNotValidCharacters = "I'm sorry, one or more of the entries you supplied contains invalid characters. Below is a listing of the invalid entries and the valid characters for that entry type."
g_sResponse_UnknownError = "I'm sorry, an unknown error occured. This interaction is being reset. If this issue continues, please inform a team member."
g_sResponse_DMOnlyAdminCommand = "This is a DM only command."
g_sResponse_DMOnlyCommand = ("For privacy reasons, the `{}` command is only to be used in DM (direct messages) with me. Please click my name and choose to send me a message directly to run that command.\n\n"
							 "NOTE: I will **NEVER** DM you first, you must DM me before i will ever interact with you in a DM.  After our first DM, you will always see our chat history and you can confirm you were the first to send me a message. If it ever looks like i DM'd you and there is no"
							 " chat history, then it is not me and it is a scammer.  You can also verify my discord ID to confirm it is me. See the help section to learn how to do that. Also, i will *never* ask you for private keys or log files or anything of that nature.")
g_sResponse_NoPermissionsCommand = "I'm sorry, you don't have permissions to run the `{}` command."
g_sResponse_FailedGeneric = "I was unable to {} for the following reason. {} This interaction is being reset. Please check your information and re-run the `{}` command if needed. If this issue continues and you believe this is an error, please contact a team member."
g_sResponse_AbortGeneric = "You have either chosen to abort {}, or i did not understand your response. This interaction is being reset. If you did not mean to do this, please run the `{}` command again."
g_sResponse_AddRegisterNodeUserNotRegistered = "I was unable to find you in the system. You do not appear to be registered yet. This interaction is being reset. Please run the `{}` command first. Then you can try to run the `{}` command again. If you believe you should already be registered, please contact a team member."
g_sResponse_ListUnRegRemoveNodeUserNotRegistered = "You do not appear to be registered in the system.  If this is accurate, then you have no nodes to {}. This interaction is being reset. To register in the system, please run the `{}` command. If you believe you should already be registered, please contact a team member."
#listCoins command responses
g_sResponse_ListCoinsSuccess = "The following is a listing of all supported coins."
#registerUser command responses
g_sResponse_UserAlreadyRegistered = "You are already registered in the system. This interaction is being reset."
g_sResponse_SuccessfullyRegisteredUser = "I have successfully registered you in the system. Your registration is linked to your discord ID, so if you leave the server and come back, you will still be registered."
g_sResponse_PresaleActiveFreeNode = ("Since it is currently presale of NZR coin, all users get 1 free node hosting slot. You have been given 1 free slot to use. Please remember that this is a promotional slot and could be revoked if abuse is detected, or expire if the need arises after presale (we don't anticipate this though). If the free node needs to expire"
										" (for non abuse reasons), you will be given ample notice before it is removed. Our plan is to always be give you at least {} days notice before a node is ever removed from the NodeZero system.")
#unregisterUser command responses
g_sResponse_UnRegisterUserNotRegistered = "I was unable to find you in the system. There is no need to unregister. If you believe this is an error, pleast contact a team member."
g_sResponse_SuccessfullyUnRegisteredUser = "I have sucessfully unregistered you from the system. If you decide to come back, you will need to register again."
#registerNode command responses
g_sResponse_SignatureValidationFailed = "I was unable to validate the signature you entered for the following reason. {} This interaction is being reset. Please check your information and re-run the `{}` command if needed. If this issue continues and you believe this is an error, please contact a team member."
g_sResponse_CheckMasternodeActiveFailed = "I was unable to validate the masternode is running for the following reason. {} This interaction is being reset. Please check your information and re-run the `{}` command if needed. If this issue continues and you believe this is an error, please contact a team member."
g_sResponse_SuccessfullyRegisteredNode = "I have successfully registered the node in the system and you are now receiving {} additional slots of free node hosting."
#unregisterNode command responses
g_sResponse_SuccessfullyUnRegisteredNode = "I have successfully unregistered the node."
#addNode command responses
g_sResponse_TickerNotSupported = "I'm sorry, the coin with ticker {} is not supported at this time.  This interaction is being reset. If you mistyped the ticker, please start over by re-running the `{}` command."
g_sResponse_AliasNameOverLimit = "The alias name you specified was more than {} characters.  Please specify an alias name that is {} characters or less.  Or enter `default` to have one generated for you."
g_sResponse_AliasNameOverLimitFail = "The alias name you entered was still over the limit of {} characters. I cannot continue. This interaction is being reset."
g_sResponse_NotCollateralTransaction = "The transaction ID specified cannot be confirmed as a valid collateral transaction for the following reason: {} : This interaction is being reset. Please check your information and re-run the `{}` command if needed. If this issue continues and you believe this is an error, please contact a team member."
g_sResponse_ImmatureCollateralTransaction = ("The collateral transaction ID supplied is valid, but the transaction is not yet mature. The transaction must have 16 or more confirmation to be mature. It currently has {} confirmations."
											" This interaction is being reset. Please try the `{}` command again after the transaction has at least 16 confirmations (which should be in about {} minutes).  To see how many confirmations the transaction has, go to the \"transactions\" tab"
											" in the wallet and hover over the transaction in question.")
g_sResponse_CollateralAddressUTXOMismatch = "The collateral address specified does not match the address found for the specified transaction ID and output index.  Please check your information and re-run the `{}` command if needed. If this continues and you believe this is an error, please contact a team member."
g_sResponse_SuccessfullyAddedNode = ("I have successfully added your node to the system. Now do the following.\n\n"
									 "1) Go to the \"Tools\" menu in your wallet and choose \"Open masternode configuration file\".\n"
									 "2) Copy/paste the following line of code into that file and save and close it.\n\n"
									 "`{}`\n\n"
									 "3) Close and restart the wallet.\n"
									 "4) Once it has started back up, unlock your wallet.\n"
									 "5) Go to the \"masternodes\" tab but *DO NOT* start the masternode yet. I need to configure the node in the system and it may take up to 5 minutes to do that.  Once i am done, i will notify you.  Once I notify you, then you can click"
									 " the \"Start Missing\" (or \"Start Alias\") button to start the masternode.")
g_sResponse_AddedNZRNode = "You have added a NZR node. This does not automatically register it in the system. If you want to register this node in the system (so you can claim more free hosting of nodes) then you still need to run the `{}` command to register it.  Please do that after you have started the node according to the instructions above"
#removeNode command responses
g_sResponse_SuccessfullyRemovedNode = "I have successfully removed the node. Please ensure to remove the appropriate line from your masternode.conf file. It will be the line with TXID of {} and TXIndex of {} (those values will be the last 2 items of the line you need to remove from your masternode.conf file.)"
#listAddedNodes command responses
g_sResponse_ListAddedNodesSuccess = "The following is a listing of {} nodes i have for you in the system."
#listConfigs command responses
g_sResponse_ListConfigsSuccess = "The following is a listing of {} nodes i have for you in the system. These can be copy/pasted into your masternode.conf file for each coin"
#listAddedNodes command responses
g_sResponse_ListRegisteredNodesSuccess = "The following is a listing of all registered nodes i have for you in the system."
#newNodeNotifier responses
g_sResponse_NewNodeReadyForStart = ("```css\n!!!!!Masternode ready notification!!!!!\n\n"
									"Your {} masternode is ready to start. Please go to your wallet and start the node with alias name of {}\n"
									"Do not reply to this message, i will not respond```")


#Prompt constants
#all commands
g_sPrompt_RemoveUnRegNZRNodeWillBeOverLimit = ("You are {} a NZR node. If you do this, your limit of free node hosting will drop to {} free nodes.  You are currently running {} nodes of other coins (not including NZR nodes, which are always free).  After {} this node, if you do not recreate and register another NZR node (either on your own host, or hosted here),"
											" then you will have a grace period of {} days to remove nodes of other coins to bring you to your limit. If you do not bring your node count under or to your limit within the grace period, the system will randomly remove nodes for you to bring you to your limit."
											" Are you sure you want to {} a NZR node? Please type `yes` to {} it, or `no` to cancel and abort this interaction.")
g_sPrompt_CollateralAddress = "Please enter the masternode collateral address you wish to {}. The masternode collateral address is the address you sent the masternode collateral to. It is also the address that receives masternode rewards."
g_sPrompt_DoubleCheckRemoveUnReg = "Are you sure you want to {} the {} node with collateral address of {}? Please type `yes` to {} it, or `no` to cancel and abort this interaction."
#unregisterUser command prompts
g_sPrompt_UnregisterUserConfirm = "Unregistering will remove your data and cannot be undone. Are you sure you want to unregister? Please type `yes` or `no`."
g_sPrompt_UnregisterUserHasNodes = "You have nodes registered and/or added to the system. Below is a listing. Unregistering yourself will cause these nodes to also become unregistered and/or removed from the system. If the nodes are still running, they will go missing and stop collecting rewards."
#addNode command prompts
g_sPrompt_Ticker = "Please enter the ticker of the coin you want to create a node for.  (Example:  BTC )"
g_sPrompt_AliasName = "Please enter the alias name for your node. (Example: MN1 ) Or enter `default` to have me generate one for you."
g_sPrompt_TXID = ("Please enter the transaction ID for your collateral transaction (the transaction where you sent yourself {} coins). You can find this transaction ID by going to the \"transactions\" tab"
				 " in your wallet and right-clicking the transaction and choosing \"Copy Transaction ID\". If you are unable to find it that way, go to your debug console and type `getmasternodeoutputs`"
				 " and the transaction ID will be the long string of numbers that are printed.")




#Set up logging
_logger = logging.getLogger('discord')
_logger.setLevel(logging.INFO)
_handler = logging.FileHandler(filename='XXXXXX.log', encoding='utf-8', mode='a')
_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
_logger.addHandler(_handler)
g_dtBotBootupDateTime = int(time.time())
_logger.warning("################################################################################")
_logger.warning("-----  Starting bot. Start time: '{0}' -----".format(datetime.utcfromtimestamp(g_dtBotBootupDateTime)))
_logger.warning("################################################################################")

###################################################
##############   Utility functions ################
#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
def _populateSystemConstants():
	"""Populate global variables from database"""

	global g_aSupportedCoins
	global g_aDiscordAdmins

	global g_nSystemMaintenance
	global g_nUserResponseWaitTimeout
	global g_nAliasNameMaxLength
	global g_nOverSlotCountGraceDays
	global g_nNZRNodeSlotMultiplier
	global g_bPresaleIsActive
	global g_nNewNodeNotifierLoopSeconds
	global g_nPollNodeStatusLoopSeconds
	global g_sLoggingLevel



	try:
		myDAL = DAL(g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, "")
		myDAL.connect()

		#populate suppported coins array (****!! REMEMBER TO ADD GLOBAL IDENTIFIER ABOVE !!****)
		rows = None
		rows = myDAL.selectData("multi", """SELECT ticker, coinName FROM Coins ORDER BY ticker""")
		for row in rows:
			g_aSupportedCoins.append([row["ticker"],row["coinName"]])
		_logger.info("Successfully populated supported coins constant.")

		#populate discord admins (***!! REMEMBER TO ADD GLOBAL IDENTIFIER ABOVE !!*****)
		rows = None
		rows = myDAL.selectData("multi", """SELECT discordID, role FROM DiscordAdmins""")
		for row in rows:
			g_aDiscordAdmins.append([row["discordID"], row["role"]])
		_logger.info("Successfully populated discord admins constant.")

		#populate other single value constants (****!! REMEMBER TO ADD GLOBAL IDENTIFIER ABOVE !!****)
		rows = None
		rows = myDAL.selectData("multi", """SELECT settingName, settingValue FROM SysSettings""")
		for row in rows:
			if row["settingName"] == 'InMaintenance':
				g_nSystemMaintenance = int(row["settingValue"])
			elif row["settingName"] == 'UserResponseTimeoutSeconds':
				g_nUserResponseWaitTimeout = int(row["settingValue"])
			elif row["settingName"] == 'AliasNameMaxLength':
				g_nAliasNameMaxLength = int(row["settingValue"])
			elif row["settingName"] == 'OverSlotCountGraceDays':
				g_nOverSlotCountGraceDays = int(row["settingValue"])
			elif row["settingName"] == 'NZRNodeSlotMultiplier':
				g_nNZRNodeSlotMultiplier = int(row["settingValue"])
			elif row["settingName"] == 'PresaleIsActive':
				if(row["settingValue"] == 'true'):
					g_bPresaleIsActive = True  #it defaults to false, so only need to set if it is true true
			elif row["settingName"] == 'NewNodeNotifierLoopSeconds':
				g_nNewNodeNotifierLoopSeconds = int(row["settingValue"])
			elif row["settingName"] == "PollNodeStatusLoopSeconds":
				g_nPollNodeStatusLoopSeconds = int(row["settingValue"])
			elif row["settingName"] == "LoggingLevel":
				g_sLoggingLevel = row["settingValue"]
		_logger.info("Successfully populated single value global constants.")

	except Exception as e:
			_logger.error("Error occured populating system constants. Error: {}".format(str(e)))
			print("Error occured populating system constants.")
			sys.exit()
	else:
		myDAL.disconnect()
		_logger.info("Finished populating system constants")

def _isMaintenanceMode(sErrRefID):
	"""Check if system is set to maintenance mode and inform user expected completion time"""

	if(g_nSystemMaintenance == 0):  #not in maintenance
		return False, "[return value not used]"
	else: #in maintenance. The value is the epoch time we expect to be finished. convert that to minutes
		if (int(time.time()) > g_nSystemMaintenance):
			return True, g_sResponse_InMaintenanceMode.format("[unknown ETA]")
		else:
			return True, g_sResponse_InMaintenanceMode.format(round((int(g_nSystemMaintenance)-int(time.time()))/60))

def _isValidInput(sValidInput, sInput):
	"""Verify input string contains only the set of valid characters"""
	for c in sInput:
		if (not c in sValidInput):
			return False
	return True

async def _getUserResponse(ctx, bot, sErrRefID, sCommand, sValidCharacters, nUserID, guild, sPrompt, nTimeout=None, sTimeoutMessage=g_sResponse_TimeoutWaitingForResponse):
	"""Prompt user for a response"""

	#if nTimeout was not specified, use the global setting
	if (nTimeout is None):
		nTimeout = g_nUserResponseWaitTimeout

	#if default timeout message was used, populate it with the command details (this is sort of a hack, but its simpler to do it this way)
	if (sTimeoutMessage == g_sResponse_TimeoutWaitingForResponse):
		sTimeoutMessage = sTimeoutMessage.format(nTimeout, sCommand)

	sInputReceived = ""
	
	try:
		await ctx.send(sPrompt)
		while True:
			msg = await bot.wait_for("message", timeout=nTimeout)
			if (msg.author.id == nUserID) and (msg.guild == guild):
				break
	except asyncio.TimeoutError:
		return False, sTimeoutMessage
	except Exception as e:
		_logger.error("Unknown error occured in the {} command: Error was {} ErrRefID: {}".format(sCommand, str(e), sErrRefID))
		return False, g_sResponse_UnknownError
	else:
		sInputReceived = msg.content.replace(" ", "")
		if (not _isValidInput(sValidCharacters, sInputReceived)):
			return False, g_sResponse_InputNotValidCharacters.format(sValidCharacters)
		else:
			return True, sInputReceived

async def _getUserResponseWithImages(ctx, bot, sErrRefID, sCommand, sValidCharacters, nUserID, guild, oPromptSeries, nTimeout=None, sTimeoutMessage=g_sResponse_TimeoutWaitingForResponse):
	"""Prompt user for a response using text prompts and images"""

	#if nTimeout was not specified, use the global setting
	if (nTimeout is None):
		nTimeout = g_nUserResponseWaitTimeout

	#if default timeout message was used, populate it with the command details (this is sort of a hack, but its simpler to do it this way)
	if sTimeoutMessage == g_sResponse_TimeoutWaitingForResponse:
		sTimeoutMessage = sTimeoutMessage.format(nTimeout, sCommand)

	sInputReceived = ""

	try:
		for oPrompt in oPromptSeries:
			await ctx.send(oPrompt[0])
			if (oPrompt[1] != ""):
				await ctx.send(file=discord.File(oPrompt[1]))

		while True:
			msg = await bot.wait_for("message", timeout=nTimeout)
			if (msg.author.id == nUserID) and (msg.guild == guild):
				break
	except asyncio.TimeoutError:
		return False, sTimeoutMessage
	except Exception as e:
		_logger.error("Unknown error occured in the {} command: Error was {}. ErrRefID: {}".format(sCommand, str(e), sErrRefID))
		return False, g_sResponse_UnknownError
	else:
		sInputReceived = msg.content.replace(" ", "")
		if (not _isValidInput(sValidCharacters, sInputReceived)):
			return False, g_sResponse_InputNotValidCharacters.format(sValidCharacters)
		else:
			return True, sInputReceived

def _formatDiscordTable(allRows, alignments = "left", separator = "|", lPad = 1, rPad = 1, addHeaderSeperator = True, padLastColumn = True):
	"""Format an input string into an array of (identically formmatted) table like structures to post in discord. If the input string with the formatting characters added is longer than 1950 characters, the return value will be an array of similarly formatted table strings to post in discord."""

	aFinalReturnTables = []
	aTmpTables = []
	sCurrentTable = ""
	sRowToAdd = ""
	allRowsTransposed = []
	lengths = []
	aligns = []
	nTableMaxLength = 1950 #Discord has a max length of 2000 characters. But we allow a buffer. We will create table strings almost as large as the max. The calling funciton must handle this (ie. send each table without extra text when long tables are expected)
	nEndPad = 0 #variable to hold number of spaces padding the end of the last column in the row, so we can remove the end of line padding if needed

	# If a single alignment value (for all columns) was specified, then build a list with appropriate number of items with that value
	if (isinstance(alignments,str)):
		for item in allRows[0]:
			aligns.append(alignments)

	#Transpose rows (put each ordinal column into a new list and create list of those lists) so we can get maximum length of data in each individual column
	allRowsTransposed = list(zip(*allRows))
	for row in allRowsTransposed:
		lengths.append(len(max(row, key=len)) + lPad + rPad)

	#Build our return tables with all the columns aligned properly (all return tables will be the same width so it looks good)
	bHeaderSeparatorRow = True
	sHeaderSeparatorRow = separator
	for row in allRows:
		#Build the text for this row
		sRowToAdd = separator
		for colVal, colLength, colAlign in zip(row, lengths, aligns):
			if (colAlign == "left"):
				sRowToAdd += (" " * lPad) + colVal + (" " * (colLength - len(colVal) - lPad - rPad)) + (" " * rPad) + separator
				nEndPad = len((" " * (colLength - lPad - len(colVal))) + (" " * rPad) + separator)
				if bHeaderSeparatorRow: #also build a header separator row if we are building the first row in the table - make sure this matches the same building logic as the data line above
					sHeaderSeparatorRow += ("-" * lPad) + ("-" * len(colVal)) + ("-" * (colLength - len(colVal) - lPad - rPad)) + ("-" * rPad) + separator
		#remove end of line padding if user did not want it (bypass this check when the padding was zero anyways)
		if((not padLastColumn) and (nEndPad > 0)):
			sRowToAdd = sRowToAdd[:-nEndPad]
		sRowToAdd += "\n"
		if((bHeaderSeparatorRow) and (addHeaderSeperator)): #if we just built the separator and user wants it, add it now. We don't account for over the limit of characters yet because we should never get to the limit when creating the header row
			sRowToAdd += sHeaderSeparatorRow + "\n"
			bHeaderSeparatorRow = False #mark header separator as finished
		#if this row will not put us over our max, then add the row to the current table
		if ((len(sCurrentTable) + len(sRowToAdd)) <= nTableMaxLength):
			sCurrentTable += sRowToAdd
		else: #will be over max, add current table to array and start new table with this row
			aTmpTables.append(sCurrentTable)
			sCurrentTable = sRowToAdd

	#add our final table to the array
	aTmpTables.append(sCurrentTable)

	#for each table object, add characters to have it print in discord code block
	for table in aTmpTables:
		aFinalReturnTables.append("```" + table + "```")


	return aFinalReturnTables

def _popCoinConfigs(sTicker, sErrRefID):
	"""If there are any newly added or removed nodes of the specified coin, re-create the phantom configuration file (masternode.txt) for that coin with all completed nodes in system for that coin"""

	sFuncName = "_popCoinConfigs"
	aAllCoins = []
	nCoinAttemptCount = 0
	nCoinSuccessCount = 0
	nCoinErrorCount = 0
	nNewRecordCount = 0
	nRemoveRecordCount = 0
	nLineCount = 0

	#Enum to hold coin

	#Get array of all coins to process
	#do this in a seperate try/except block to keep it contained away from the processing where we may want to rollback in case of issues
	try:
		myDAL = DAL(g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
		myDAL.connect()

		if (sTicker.lower() == "[all]"):
			rows = myDAL.selectData("multi", """SELECT DISTINCT Coins.ticker, Coins.configFileLocation FROM Coins JOIN UserNodes on Coins.ticker = UserNodes.coinTicker WHERE UserNodes.daemonType = 'phantom' and UserNodes.systemStatus in (?,?);""",['NEW', 'REMOVE'], False)
			for row in rows:
				aAllCoins.append(dict([
										("ticker", row["ticker"]),
										("configFileLocation", row["configFileLocation"])
									])
								 )
		else:
			row = myDAL.selectData("single", """SELECT Coins.ticker, Coins.configFileLocation FROM Coins JOIN UserNodes on Coins.ticker = UserNodes.coinTicker WHERE UserNodes.daemonType = 'phantom' and Coins.ticker = ? and UserNodes.systemStatus in (?,?);""",[sTicker, 'NEW', 'REMOVE'], False)
			aAllCoins.append(dict([
									("ticker", row["ticker"]),
									("configFileLocation", row["configFileLocation"])
								])
							)
	except Exception as e:
		_logger.error("{} - Error occured getting list of coins to process. Ticker: {} Error: {}. ErrRefID: {}".format(sFuncName, sTicker, str(e), sErrRefID))
		myDAL.disconnect()
	else:
		myDAL.disconnect()

	#Loop through our coins and process each one. If errors on one coin, move to next to allow at least some coins to be updated.
	myDAL = DAL(g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	myDAL.connect()
	for coin in aAllCoins:
		nCoinAttemptCount += 1
		nNewRecordCount = 0
		nRemoveCount = 0
		nLineCount = 0
		try:
			#mark new records as in-process (the rest of steps will only process non NEW records. This helps us remember which records have never been added to the config file before)
			count = 0
			count = myDAL.insertUpdateDelete("""UPDATE UserNodes SET systemStatus = ? WHERE daemonType = 'phantom' AND systemStatus = ? AND coinTicker = ?""",["INPROCESS", "NEW", coin["ticker"]], False)
			nNewRecordCount = count

			#remove records marked for removal
			count = 0
			count = myDAL.insertUpdateDelete("""DELETE FROM UserNodes WHERE daemonType = 'phantom' AND systemStatus = ? AND coinTicker = ?""",["REMOVE", coin["ticker"]], False)
			nRemoveRecordCount = count

			#if no records were marked to add or remove, there was an issue. Log it, rollback, and move on to next coin
			if ((nNewRecordCount == 0) and (nRemoveRecordCount == 0)):
				_logger.error("{} - Error occured - no records to add or delete when we expected some. Ticker: {} ErrRefID: {}".format(sFuncName, sTicker, sErrRefID))
				myDAL.rollback()
				nCoinErrorCount += 1
				continue

			#Get data for the file (don't get data for NEW records as they may not have been ready yet for processing)
			lines = None
			lines = myDAL.selectData("multi", """SELECT coinTicker, IP, coinPort, genKey, txID, txIndex, entryEpDateTime, phantomEpDateTime FROM UserNodes WHERE daemonType = 'phantom' AND coinTicker = ? AND systemStatus != ?;""",[coin["ticker"], "NEW"], False)
			nLineCount = len(lines)

			#Mark the INPROCESS records as NOTIFY so users can be alerted they are ready to start
			count = 0
			count = myDAL.insertUpdateDelete("""UPDATE UserNodes SET systemStatus = ? WHERE daemonType = 'phantom' AND systemStatus = ? AND coinTicker = ?""",["NOTIFY", "INPROCESS", coin["ticker"]], False)
			if (count != nNewRecordCount):
				#we updated a different amount of records than we expected to NOTIFY
				_logger.error("{} - Error occured. We updated different count of records to NOTIFY than we had marked as INPROCESS. Aborting update process for ticker {}. Records marked as NOTIFY: {}  Records marked as INPROCESS: {}. ErrRefID: {}".format(sFuncName, coin["ticker"], str(count), str(nNewRecordCount), sErrRefID))
				myDAL.rollback()
				nCoinErrorCount += 1
				continue

			#Write the config file (overwrite existing)
			sContents = ""
			for line in lines:
				sContents += line["coinTicker"] + str(line["phantomEpDateTime"]) + " " + line["IP"] + ":" + str(line["coinPort"]) + " " + line["genKey"] + " " + line["txID"] + " " + str(line["txIndex"]) + " " + str(line["phantomEpDateTime"]) + "\n"
			with open(coin["configFileLocation"], "w") as f:
				f.write(sContents)
		except Exception as e:
			nCoinErrorCount += 1
			_logger.error("{} - Unknown error processing coin {}. Error: {}. ErrRefID: {}".format(sFuncName, coin["ticker"], str(e), sErrRefID))
			myDAL.rollback()
			continue
		else:
			nCoinSuccessCount += 1
			_logger.info("{} - Success - Ticker: {} New Records: {} Removed Records: {} Total Records in file now: {}. ErrRefID: {}".format(sFuncName, coin["ticker"], str(nNewRecordCount), str(nRemoveRecordCount), str(nLineCount), sErrRefID))
			myDAL.commit()

	#log results
	if(nCoinAttemptCount > 0):
		if (nCoinErrorCount > 0):
			myDAL.addSysLogEntry("error", sFuncName, "Error populate configs. Coin Attempt Count: {} Coin Success Count: {} Coin Error Count: {} ErrRefID: {}.".format(str(nCoinAttemptCount), str(nCoinSuccessCount), str(nCoinErrorCount), sErrRefID))
		else:
			myDAL.addSysLogEntry("success", sFuncName, "Success populate configs. Coin Attempt Count: {} Coin Success Count: {} Coin Error Count: {} ErrRefID: {}.".format(str(nCoinAttemptCount), str(nCoinSuccessCount), str(nCoinErrorCount), sErrRefID))
	else:
		myDAL.addSysLogEntry("info", sFuncName, "Job run. No config file changes needed. ErrRefID: {}.".format(sErrRefID))

	myDAL.disconnect()

def _pollNodeStatus(sTicker, sErrRefID):
	"""Poll the network for masternodenode status."""

	sFuncName = "_pollNodeStatus"
	aAllCoins = []
	nbcCoin = None
	nCoinAttemptCount = 0
	nCoinSuccessCount = 0
	nCoinErrorCount = 0
	nMasternodeCheckTypeExplorerCount = 0
	nMasternodeCheckTypeWalletCount = 0
	nMasternodeCheckTypeNoneCount = 0
	sAllEnabledNodesSQLInClause = ""
	sAllActiveNodesSQLInClause = ""
	sAllExpiredNodesSQLInClause = ""
	nPreExistingMissingCount = 0
	nMarkedExpiredCount = 0
	nMarkedMissingCount = 0
	nMarkedEnabledCount = 0
	nMarkedActiveCount = 0


	#Get array of all coins to process - We will only poll coins that have at least one running node (systemStatus of COMPLETE)
	#do this in a seperate try/except block to keep it contained away from the processing where we may want to rollback in case of issues
	try:
		myDAL = DAL(g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
		myDAL.connect()

		if (sTicker.lower() == "[all]"):
			rows = myDAL.selectData("multi", """SELECT DISTINCT Coins.ticker FROM Coins JOIN UserNodes ON Coins.ticker = UserNodes.coinTicker WHERE UserNodes.systemStatus = ?;""",['COMPLETE'], False)
			for row in rows:
				aAllCoins.append(dict([
										("ticker", row["ticker"])
									])
								)
		else:
			row = myDAL.selectData("single", """SELECT DISTINCT Coins.ticker FROM Coins JOIN UserNodes ON Coins.ticker = UserNodes.coinTicker WHERE Coins.ticker = ? AND UserNodes.systemStatus = ?;""",[sTicker, 'COMPLETE'], False)
			aAllCoins.append(dict([
									("ticker", row["ticker"])
								])
							)
	except Exception as e:
		_logger.error("{} - Error occured getting list of coins to process. CoinsToPoll: {} Error: {}. ErrRefID: {}".format(sFuncName, sTicker, str(e), sErrRefID))
		myDAL.disconnect()
	else:
		myDAL.disconnect()

	#Loop through our coins and process each one. If errors on one coin, move to next to allow at least some coins to be updated.
	myDAL = DAL(g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	myDAL.connect()
	for coin in aAllCoins:

		try:
			nCoinAttemptCount += 1

			#create coin object
			try:
				nbcCoin = NodeBotCoin(coin["ticker"], g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
			except Exception as e:
				raise Exception("{} - Failed to instantiate a coin object. Ticker: {} Error: {}".format(sFuncName, coin["ticker"], str(e)))

			#check APIs to ensure they are responding
			if (nbcCoin.masternodeCheckType == "EXPLORER"):
				nMasternodeCheckTypeExplorerCount += 1
				if (not nbcCoin.isExplorerAPIResponding()):
					raise Exception("{} - Explorer not responding. Ticker: {} ExplorerURL: {}".format(sFuncName, nbcCoin.ticker, nbcCoin.explorerCheckURL))
			#if remote RPC wallet, get data
			if (nbcCoin.masternodeCheckType == "WALLET"):
				#TODO - write logic to check the API if needed, until we write that logic just pretend success
				nMasternodeCheckTypeWalletCount += 1
			#if no way to poll masternodes, just increment the counter and move to next coin
			if (nbcCoin.masternodeCheckType == "NONE"):
				nMasternodeCheckTypeNoneCount += 1
				nCoinSuccessCount += 1
				continue

			#get all masternode statuses into a list for our query to update the data
			sAllEnabledNodesSQLInClause = ""
			sAllActiveNodesSQLInClause = ""
			sAllExpiredNodesSQLInClause = ""
			jsondata = nbcCoin._getMasternodeList()
			for item in jsondata:
				if (item["status"] == "ACTIVE"):
					sAllActiveNodesSQLInClause += "'" + item["addr"] + "',"
				elif (item["status"] == "ENABLED"):
					sAllEnabledNodesSQLInClause += "'" + item["addr"] + "',"
				elif (item["status"] == "EXPIRED"):
					sAllExpiredNodesSQLInClause += "'" + item["addr"] + "',"
			if (len(sAllActiveNodesSQLInClause) > 0): #remove trailing comma
				sAllActiveNodesSQLInClause = sAllActiveNodesSQLInClause[:-1]
			if (len(sAllEnabledNodesSQLInClause) > 0): #remove trailing comma
				sAllEnabledNodesSQLInClause = sAllEnabledNodesSQLInClause[:-1]
			if (len(sAllExpiredNodesSQLInClause) > 0): #remove trailing comma
				sAllExpiredNodesSQLInClause = sAllExpiredNodesSQLInClause[:-1]

			#get count of MISSING nodes just for logging purposes
			nPreExistingMissingCount = 0
			rows = None
			rows = myDAL.selectData("multi", """SELECT ID 
												FROM UserNodes 
												WHERE systemStatus = 'COMPLETE'
												AND networkStatus = 'MISSING'
												AND coinTicker = ?""",[nbcCoin.ticker], False)
			nPreExistingMissingCount = len(rows)


			#update all ACTIVE and ENABLED nodes of this coin to MISSING so we can re-poll their status
			nMarkedMissingCount = 0
			nMarkedMissingCount = myDAL.insertUpdateDelete("""UPDATE UserNodes 
												SET networkStatus = 'MISSING',
													updateEpDateTime = strftime('%s', 'now')
												WHERE systemStatus = 'COMPLETE'
													AND networkStatus in ('ENABLED','ACTIVE')
													AND coinTicker = ?""",[nbcCoin.ticker], False)

			#update the enabled nodes
			nMarkedEnabledCount = 0
			nMarkedEnabledCount = myDAL.insertUpdateDelete("""UPDATE UserNodes 
												SET networkStatus = 'ENABLED',
													updateEpDateTime = strftime('%s', 'now'),
													lastSeenEpDateTime = strftime('%s', 'now')
												WHERE systemStatus = 'COMPLETE'
													AND coinTicker = ?
													AND collateralAddress IN (""" + sAllEnabledNodesSQLInClause + ")", [nbcCoin.ticker], False)

			#update the active nodes
			nMarkedActiveCount = 0
			nMarkedActiveCount = myDAL.insertUpdateDelete("""UPDATE UserNodes 
												SET networkStatus = 'ACTIVE',
													updateEpDateTime = strftime('%s', 'now'),
													lastSeenEpDateTime = strftime('%s', 'now')
												WHERE systemStatus = 'COMPLETE'
													AND coinTicker = ?
													AND collateralAddress IN (""" + sAllActiveNodesSQLInClause + ")", [nbcCoin.ticker], False)

			#update the expired nodes
			#Do not update last seen date so we can rememeber when it was last seen as not expired
			nMarkedExpiredCount = 0
			nMarkedExpiredCount = myDAL.insertUpdateDelete("""UPDATE UserNodes 
												SET networkStatus = 'EXPIRED',
													updateEpDateTime = strftime('%s', 'now')
												WHERE systemStatus = 'COMPLETE'
													AND coinTicker = ?
													AND collateralAddress IN (""" + sAllExpiredNodesSQLInClause + ")", [nbcCoin.ticker], False)


		except Exception as e:
			nCoinErrorCount += 1
			_logger.error("{} - Unknown error processing coin {}. Error: {}. ErrRefID: {}".format(sFuncName, nbcCoin.ticker, str(e), sErrRefID))
			myDAL.rollback()
			continue
		else:
			nCoinSuccessCount += 1
			if(g_sLoggingLevel in ["INFO","VERBOSE"]):
				_logger.info("{} - Success - Ticker: {} PreExisingMissingCount: {} MarkedMissingCount: {} MarkedEnabledCount: {} MarkedActiveCount: {} MarkedExpiredCount: {}. ErrRefID: {}".format(sFuncName, nbcCoin.ticker, str(nPreExistingMissingCount), str(nMarkedMissingCount), str(nMarkedEnabledCount), str(nMarkedActiveCount), str(nMarkedExpiredCount), sErrRefID))
			myDAL.commit()

	#log results
	if(nCoinAttemptCount > 0):
		if (nCoinErrorCount > 0):
			myDAL.addSysLogEntry("error", sFuncName, "Coin Attempt Count: {} Coin Success Count: {} Coin Error Count: {} EXPLORERCheckTypeCount: {} WALLETCheckTypeCount: {} NONECheckTypeCount: {} ErrRefID: {}.".format(str(nCoinAttemptCount), str(nCoinSuccessCount), str(nCoinErrorCount), str(nMasternodeCheckTypeExplorerCount), str(nMasternodeCheckTypeWalletCount), str(nMasternodeCheckTypeNoneCount), sErrRefID))
		else:
			myDAL.addSysLogEntry("success", sFuncName, "Coin Attempt Count: {} Coin Success Count: {} Coin Error Count: {} EXPLORERCheckTypeCount: {} WALLETCheckTypeCount: {} NONECheckTypeCount: {} ErrRefID: {}.".format(str(nCoinAttemptCount), str(nCoinSuccessCount), str(nCoinErrorCount), str(nMasternodeCheckTypeExplorerCount), str(nMasternodeCheckTypeWalletCount), str(nMasternodeCheckTypeNoneCount), sErrRefID))
	else:
		myDAL.addSysLogEntry("info", sFuncName, "Job run. No polling needed. ErrRefID: {}.".format(sErrRefID))

	myDAL.disconnect()

async def _notifyUsersNewNodes(sErrRefID):
	"""Notify the owners of any newly added nodes to the config file that they can start their node now"""

	nNotificationAttemptCount = 0
	nNotificationSuccessCount = 0
	nNotificationErrorCount = 0
	aAllNodesReady = []
	oMessage = None #variable to hold message we sent to user so we can get the jump_url to save in database

	# Get array of all records to process
	# do this in a seperate try/except block to keep it contained away from the processing where we may want to rollback in case of issues
	try:
		myDAL = DAL(g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
		myDAL.connect()

		rows = myDAL.selectData("multi", """SELECT userID, coinTicker, aliasName FROM UserNodes WHERE systemStatus = ?;""",["NOTIFY"], False)
		for row in rows:
			aAllNodesReady.append([row["userID"], row["coinTicker"], row["aliasName"]])
	except Exception as e:
		_logger.error("_notifyUsersNewNodes - Error occured getting list of users to notify. Error: {}. ErrRefID: {}".format(str(e), sErrRefID))
		myDAL.disconnect()
	else:
		myDAL.disconnect()

	# Loop through each user to notify. If errors on one user, move to next to allow at least some records to be updated.
	myDAL = DAL(g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	myDAL.connect()
	for node in aAllNodesReady:
		nNotificationAttemptCount += 1
		try:
			#Alert the user the node is ready
			oMessage = None
			oMessage = await _DMUser(node[0], g_sResponse_NewNodeReadyForStart.format(node[1], node[2]))


			#Update the record to COMPLETE to indicate the user has been notified
			count = 0
			count = myDAL.insertUpdateDelete("""UPDATE UserNodes SET systemStatus = ? WHERE userID = ? AND coinTicker = ? and aliasName = ? and systemStatus = ?""",["COMPLETE", node[0], node[1], node[2], "NOTIFY"])
			if (count == 0):
				# no records marked, log it, rollback, and move on to next coin
				_logger.info("_notifyUsersNewNodes - No record updated to notify user of node being ready. UserID: {} CoinTicker: {} AliasName: {}. ErrRefID: {}".format(str(node[0]), node[1], node[2], sErrRefID))
				myDAL.rollback()
				nNotificationErrorCount += 1
				continue
		except Exception as e:
			_logger.error("_notifyUsersNewNodes - Unknown error notifying user. Error: {}. ErrRefID: {}".format(str(e), sErrRefID))
			myDAL.rollback()
			nNotificationErrorCount += 1
			continue
		else:
			myDAL.commit()
			myDAL.addSysLogEntry("log", "_notifyUsersNewNodes", "Success notify user. User: {} CoinTicker: {} AliasName: {} DiscordMessageURL: {} ErrRefID: {}.".format(str(node[0]), node[1], node[2], oMessage.jump_url, sErrRefID))
			nNotificationSuccessCount += 1
	#log results
	if(nNotificationAttemptCount > 0):
		if (nNotificationErrorCount > 0):
			myDAL.addSysLogEntry("error", "_notifyUsersNewNodes", "Error notify user. Attempt Count: {} Success Count: {} Error Count: {} ErrRefID: {}.".format(str(nNotificationAttemptCount), str(nNotificationSuccessCount), str(nNotificationErrorCount), sErrRefID))
		else:
			myDAL.addSysLogEntry("success", "_notifyUsersNewNodes", "Success notify user. Attempt Count: {} Success Count: {} Error Count: {} ErrRefID: {}.".format(str(nNotificationAttemptCount), str(nNotificationSuccessCount), str(nNotificationErrorCount), sErrRefID))
	else:
		myDAL.addSysLogEntry("info", "_notifyUsersNewNodes", "Job run. No notifications needed. ErrRefID: {}.".format(sErrRefID))
	myDAL.disconnect()

async def _DMAdmins(sAdminTypeToNotify, sMessage):
	"""Send DM to the list of 'admins' with the specified role.  This is not a discord admin or role, it is a system specific role stored in the local database."""

	sFuncName = "_DMAdmins"
	try:
		#Loop through all the individuals with the role and send the message
		for admin in g_aDiscordAdmins:
			user = None
			if(admin[1] == sAdminTypeToNotify):
				await _DMUser(int(admin[0]), "`!#!#!#  SYSTEM ALERT  !#!#!#\n" + sMessage + "`")
	except Exception as e:
		_logger.error(sFuncName + " - Failed to notify {} admin types of message {}. Error {}".format(sAdminTypeToNotify, sMessage, str(e)))
		raise

async def _DMUser(nUserID, sMessage):
	"""DM a user"""

	sFuncName = "_DMUser"
	try:
		user = None
		user = bot.get_user(nUserID)
		return await user.send(sMessage)
	except Exception as e:
		_logger.error(sFuncName + " - Failed.  UserID: {}. Error {}".format(str(nUserID), str(e)))
		raise

def _getUserMention(nUserID):
	"""Get string to mention user in a response"""

	sFuncName = "_getUserMention"
	try:
		user = None
		user = bot.get_user(nUserD)
		return user.mention
	except Exception as e:
		_logger.error(sFuncName + " - Failed.  UserID: {}. Error {}".format(str(nUserID), str(e)))
		raise

def _getRoleMention(ctx, sRoleName):
	"""Get string to mention a discord role in a response"""

	sFuncName = "_getRoleMention"
	try:
		for role in ctx.message.guild.roles:
			if (role.name == sRoleName):
				return role.mention
	except Exception as e:
		_logger.error(_getUserMention + " - Failed.  UserID: {}. Error {}".format(str(nUserID), str(e)))
		raise
	


#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
############  End Utility functions ###############
###################################################


#initialize the system
_populateSystemConstants()

#set up the bot
bot = commands.Bot(command_prefix = g_sCommandPrefix, case_insensitive = True)

#Log Bot Ready
@bot.event
async def on_ready():
	_logger.warning("Bot initialized and ready.")
	print('Bot initialized and ready.')
	# aRows = []
	# aRows.append(["Start Block","End Block","Block Reward","Masternode Collateral","Masternode Reward","Staking Reward","Dev Fee"])
	# aRows.append(["1","5000","0.5","1000","0.365","0.125","0.01"])
	# aRows.append(["5001","20000","1.2","1000","0.876","0.3","0.024"])
	# aRows.append(["20001","80000","1.8","1000","1.314","0.45","0.036"])
	# aRows.append(["80001","140000","2.8","1000","2.044","0.7","0.056"])
	# aRows.append(["140001","200000","5.2","1000","3.786","1.3","0.104"])
	# aRows.append(["200001","260000","9.6","1000","7.008","2.4","0.192"])
	# aRows.append(["260001","300000","10","2000","7.3","2.5","0.2"])
	# aRows.append(["300001","340000","14","2000","10.22","3.5","0.28"])
	# aRows.append(["340001","400000","17","2000","12.41","4.25","0.34"])
	# aRows.append(["400001","435000","24","3000","17.52","6","0.48"])
	# aRows.append(["435001","495000","30","3000","21.9","7.5","0.6"])
	# aRows.append(["495001","∞","40","5000","29.2","10","0.8"])
	# print(_formatDiscordTable(aRows))

#############    BOT TASKS  #################
@tasks.loop(seconds=g_nNewNodeNotifierLoopSeconds)
async def newNodeNotifier():
	"""Background Task - Update config files for newly added/removed nodes and send alerts to users to inform them to start new nodes"""

	#Get a timestamp for this run for logging
	sErrRefID = str(int(time.time()))
	#Populate coin configs
	_popCoinConfigs('[all]', sErrRefID)
	#alert users of ready nodes
	await _notifyUsersNewNodes(sErrRefID)

@tasks.loop(seconds=g_nPollNodeStatusLoopSeconds)
async def pollNodeStatus():
	"""Background Task - Poll masternode status from coin network."""

	#Get a timestamp for this run for logging
	sErrRefID = str(int(time.time()))
	#Poll node status
	_pollNodeStatus('[all]', sErrRefID)


#########    BOT COMMAND CHECKS   ###########
class CheckRoleFail(commands.CheckFailure): pass   #exception class for the checkRole check
def checkRole(sRole):
	"""Custom 'check' for command permissions. This is not a discord role, it is a system specific role stored in the local database. """

	def predicate(ctx):
		#raise CheckRoleFail exception if userid/role combination doesn't exist in list of all userid/role entries
		if ([ctx.message.author.id, sRole] in g_aDiscordAdmins):
			return True
		else:
			raise CheckRoleFail("User failed role check.")
	return commands.check(predicate)

###################################################
############       BOT COMMANDS     ###############
#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

@bot.command()
async def listCoins(ctx):
	"""
	List all coins supported by the system.

	Parameters:
		None
	"""

	#local constants
	sCommandName = g_sListCoinsCommand     #Command name with prefix
	sErrRefID = str(ctx.message.author.id) + "-" + str(int(time.time()))
	sErrRefIDFooter = "\nInteraction Reference ID: " + sErrRefID
	sFinalResponse = ""    #Final response we will build for the user.
	aDiscordTableResponses = []

	#create a copy of our list and add a header item to to the beginnng (so it prints with a header row in our discord table)
	aSupportedCoinsCopy = g_aSupportedCoins.copy()
	aSupportedCoinsCopy.insert(0, ["Coin Ticker", "Coin Name"])

	#Build table listing all the coins
	aDiscordTableResponses = _formatDiscordTable(aSupportedCoinsCopy)

	#Send final response
	await ctx.send(g_sResponse_ListCoinsSuccess + "\n\n")
	for table in aDiscordTableResponses:
		await ctx.send(table)
	await ctx.send(sErrRefIDFooter)

@bot.command()
@commands.dm_only()
async def registerUser(ctx):
	"""
	Register youself in the system.
	This must be performed before adding any nodes to the system.

	Parameters:
		None
	"""

	# local constants
	sCommandName = g_sRegisterUserCommand  # Command name with prefix
	sFinalResponse = ""  # Final response we will build for the user.
	sErrRefID = str(ctx.message.author.id) + "-" + str(int(time.time()))
	sErrRefIDFooter = "\nInteraction Reference ID: " + sErrRefID
	nBonusSlots = 0  # bonus slots (if any) we will give users (during promotions)

	#check if system in maintenance
	bMaintenance, sMaintenance = _isMaintenanceMode(sErrRefID)
	if bMaintenance:
		await ctx.send(sMaintenance + sErrRefIDFooter)
		return

	# Try to create a user object for this user (if user is found in database, they will be created with a IsRegistered flag of true)
	try:
		nbuUser = NodeBotUser(ctx.message.author.id, g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	except Exception as e:
		_logger.error("Failed to create a user object in command {}. ErrRefID: {}".format(sCommandName, sErrRefID))
		sFinalResponse = g_sResponse_DatabaseConnectionFail + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	# Tell user they are already registered
	if (nbuUser.isRegistered):
		sFinalResponse = g_sResponse_UserAlreadyRegistered + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	# Bonus slot calculation
	if g_bPresaleIsActive:  # during presale users get 1 bonus
		nBonusSlots = 1

	# We have all data, register the user
	bTmpSuccess, sTmpResponse = nbuUser.registerUser(nBonusSlots)
	if bTmpSuccess:
		# Successfully registered the user. Build the success message
		sFinalResponse = g_sResponse_SuccessfullyRegisteredUser
		# Add an extra message during presale about the user getting free slots
		if g_bPresaleIsActive:
			sFinalResponse += "\n\n" + g_sResponse_PresaleActiveFreeNode.format(g_nOverSlotCountGraceDays)
		# Add message indicating the number of slots the user has
		sFinalResponse += "\n\n" + g_sResponse_UsingXofYSlots.format(nbuUser.usedSlots, nbuUser.totalSlots)
	else:
		# There was an issue, build the failure message
		sFinalResponse = g_sResponse_FailedGeneric.format("register you", sTmpResponse, sCommandName)

	# Send final response
	sFinalResponse += sErrRefIDFooter
	await ctx.send(sFinalResponse)

@bot.command()
@commands.dm_only()
async def unregisterUser(ctx):
	"""
	Un-register yourself from the system.
	This will remove all information for you. Including removing all registered NZR masternodes and destroying all other masternodes added by you.  This cannot be un-done.

	Parameters:
		None
	"""

	# local constants
	sCommandName = g_sUnRegisterUserCommand  # Command name with prefix
	sFinalResponse = ""  # Final response we will build for the user.
	sErrRefID = str(ctx.message.author.id) + "-" + str(int(time.time()))
	sErrRefIDFooter = "\nInteraction Reference ID: " + sErrRefID
	aUserAddedNodes = ""  # discord table(s) listing of all the nodes the user has added
	aUserRegisteredNodes = ""  # discord table(s) listing of all the nodes the user has registered
	sUserConfirmPrompt = ""  # a prompt message we will build to confirm user wants to unregister

	#check if system in maintenance
	bMaintenance, sMaintenance = _isMaintenanceMode(sErrRefID)
	if bMaintenance:
		await ctx.send(sMaintenance + sErrRefIDFooter)
		return

	# Create a user object for this user
	try:
		nbuUser = NodeBotUser(ctx.message.author.id, g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	except Exception as e:
		_logger.error("Failed to create a user object in command {}. ErrRefID: {}".format(sCommandName, sErrRefID))
		sFinalResponse = g_sResponse_DatabaseConnectionFail + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	# Tell user to register if they are not yet
	if (not nbuUser.isRegistered):
		sFinalResponse = g_sResponse_UnRegisterUserNotRegistered + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	# Get list of user's added nodes to display for confirmation
	bTmpSuccess, sTmpResponse = nbuUser.listAddedNodes()
	if bTmpSuccess:
		aUserAddedNodes = _formatDiscordTable(sTmpResponse)
	else:
		# this could mean an error, but we'll ignore any error and assume it means the user has no nodes
		pass

	# Get list of user's registered nodes to display for confirmation
	bTmpSuccess, sTmpResponse = nbuUser.listRegisteredNodes()
	if bTmpSuccess:
		aUserRegisteredNodes = _formatDiscordTable(sTmpResponse)
	else:
		# this could mean an error, but we'll ignore any error and assume it means the user has no nodes
		pass

	# aler user with all needed warnings
	if ((len(aUserAddedNodes) == 0) and (len(aUserRegisteredNodes) == 0)):
		pass #nothing to do here since user has no nodes to warn about, continue on
	else:
		#user has nodes, warn them with list of all nodes
		await ctx.send(g_sPrompt_UnregisterUserHasNodes)
		if (len(aUserAddedNodes) != 0):
			await ctx.send("\n\nAdded nodes (nodes being hosted by the NodeZero Network:")
			for table in aUserAddedNodes:
				await ctx.send(table)
		if (len(aUserRegisteredNodes) != 0):
			await ctx.send("\n\nRegistered NZR nodes:")
			for table in aUserRegisteredNodes:
				await ctx.send(table)

	# Confirm the user wants to unregister
	bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric,
													   nbuUser.discordID, None, g_sPrompt_UnregisterUserConfirm)
	if bTmpSuccess:
		if sTmpResponse.lower() != 'yes':
			sFinalResponse = g_sResponse_AbortGeneric.format("unregistering", sCommandName) + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return
	else:
		sFinalResponse = sTmpResponse + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	# We have all data, unregister the user
	bTmpSuccess, sTmpResponse = nbuUser.unregisterUser()
	if bTmpSuccess:
		# Successfully unregistered the user. Build the success message
		sFinalResponse = g_sResponse_SuccessfullyUnRegisteredUser
	else:
		# There was an issue, build the failure message
		sFinalResponse = g_sResponse_FailedGeneric.format("unregister you", sTmpResponse, sCommandName)

	# Send final response
	sFinalResponse += sErrRefIDFooter
	await ctx.send(sFinalResponse)

@bot.command()
@commands.dm_only()
async def registerNode(ctx, sCollateralAddress = '', sSignature = ''):
	"""
    Register a NZR masternode in the system.
    This is not adding a masternode to be run by the system. This registers an already running NZR masternode to prove ownership so you can be credited with extra slots to run other masternodes.

    Parameters:
        sCollateralAddress	- The collateral address of the masternode being registered.
        sSignature			- The 'signature' created by the wallet to prove ownership of the collateral address (sign the message with the collateral address and make the message just the colllateral address)

    NOTE: You do not need to specify the parameters when running this command. If you do not, the system will walk you through the process and prompt you for them one by one.  But, if any parameters are sent, they must all be sent, and they must be sent in the order specified.
    """

	# local constants
	sCommandName = g_sRegisterNodeCommand  # Command name with prefix
	sFinalResponse = ""  # Final response we will build for the user.
	sErrRefID = str(ctx.message.author.id) + "-" + str(int(time.time()))
	sErrRefIDFooter = "\nInteraction Reference ID: " + sErrRefID
	sTicker = 'NZR'

	#check if system in maintenance
	bMaintenance, sMaintenance = _isMaintenanceMode(sErrRefID)
	if bMaintenance:
		await ctx.send(sMaintenance + sErrRefIDFooter)
		return

	#Ensure valid characters for the parameters specified (if any)
	aInvalidInputs = []
	if (sCollateralAddress != ""):
		if (not _isValidInput(g_sValidAlphaNumeric, sCollateralAddress)):
			aInvalidInputs.append(["Collateral Address", g_sValidAlphaNumeric])
	if (sSignature != ""):
		if (not _isValidInput(g_sValidSignedMessage, sSignature)):
			aInvalidInputs.append(["Signed Message", g_sValidSignedMessage])

	#alert user if any parameters were specified and they are invalid
	if (len(aInvalidInputs) != 0):
		aInvalidInputs.insert(0, ["Entry Name", "Valid Characters"])
		sFinalResponse = g_sResponse_ParametersNotValidCharacters + "\n" + _formatDiscordTable(aInvalidInputs)[0] + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Create a user object for this user
	try:
		nbuUser = NodeBotUser(ctx.message.author.id, g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	except Exception as e:
		_logger.error("Failed to create a user object in command {}. ErrRefID: {}".format(sCommandName, sErrRefID))
		sFinalResponse = g_sResponse_DatabaseConnectionFail + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Tell user to register if they are not yet
	if (not nbuUser.isRegistered):
		sFinalResponse = g_sResponse_AddRegisterNodeUserNotRegistered.format(g_sRegisterUserCommand, sCommandName) + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#if no collateral address was specified, ask for it
	if (sCollateralAddress == ""):
		bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric, nbuUser.discordID, None, g_sPrompt_CollateralAddress.format("register"))
		if bTmpSuccess:
			sCollateralAddress = sTmpResponse
		else:
			sFinalResponse = sTmpResponse + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#We are far enough along, we can create a coin object to help obtain the remaining info we need
	try:
		nbcCoin = NodeBotCoin(sTicker, g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	except Exception as e:
		_logger.warning("Failed to instantiate a coin object for ticker {} in command {}. ErrRefID: {}".format(sTicker, sCommandName, sErrRefID))
		sFinalResponse = g_sResponse_UnknownError + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Validate masternode is running
	bTmpSuccess, sTmpResponse = nbcCoin.isMasternodeActive(sCollateralAddress)
	if not bTmpSuccess:
		sFinalResponse = g_sResponse_CheckMasternodeActiveFailed.format(sTmpResponse, sCommandName) + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#If no signed message was specified, ask for it
	#Build our series of prompts to help user create the signed message
	aPrompts = []
	aPrompts.append(["I will have you sign a message to prove ownership of that address. (A 'signature' in this context is just a long string of characters). This does not expose you to risk in any way. I will walk you through the process to sign a message.  Please follow the 5 steps below (Note: occasionally the 5 steps take a moment to display...please wait for all 5 steps to display before typing any responses).", ""])
	aPrompts.append(["1.)  In your wallet, go to 'File' -> 'Sign Message'", "images/signmessage_step1.png"])
	aPrompts.append(["2.)  Paste your masternode collateral address ({}) in the first and second boxes as shown in the screenshot below.".format(sCollateralAddress), "images/signmessage_step2.png"])
	aPrompts.append(["3.)  Click the 'Sign Message' box", "images/signmessage_step3.png"])
	aPrompts.append(["4.)  Click the 'copy' button to copy the signature to your clipboard", "images/signmessage_step4.png"])
	aPrompts.append(["5.)  Paste the text of the signature here in discord and send it to me.  (there is no screenshot for this step, so you can enter your response now)", ""])
	if (sSignature == ""):
		bTmpSuccess, sTmpResponse = await _getUserResponseWithImages(ctx, bot, sErrRefID, sCommandName, g_sValidSignedMessage, nbuUser.discordID, None, aPrompts)
		if bTmpSuccess:
			sTXID = sTmpResponse
		else:
			sFinalResponse = sTmpResponse + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#Validate signature
	bTmpSuccess, sTmpResponse = nbcCoin.isValidSignature(sCollateralAddress, sSignature, sCollateralAddress) #3rd parameter is the signed message...which is the same as the address in this case
	if not bTmpSuccess:
		sFinalResponse = g_sResponse_SignatureValidationFailed.format(sTmpResponse, sCommandName) + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#We have all data, add to database
	bTmpSuccess, sTmpResponse = nbuUser.registerNode(sCollateralAddress, g_nNZRNodeSlotMultiplier)
	if bTmpSuccess:
		#Successfully registered the node. Build the complete success message
		sFinalResponse = g_sResponse_SuccessfullyRegisteredNode.format(g_nNZRNodeSlotMultiplier)
		sFinalResponse += "\n\n" + g_sResponse_UsingXofYSlots.format(nbuUser.usedSlots, nbuUser.totalSlots)
	else:
		#There was an issue, build the failure message
		sFinalResponse = g_sResponse_FailedGeneric.format("register the node", sTmpResponse, sCommandName)

	# Send final response
	sFinalResponse += sErrRefIDFooter
	await ctx.send(sFinalResponse)

@bot.command()
@commands.dm_only()
async def unregisterNode(ctx, sCollateralAddress = ''):
	"""
    Un-register a NZR masternode from the system.
    This will reduce the number of masternodes you can run in the system. If un-registering a NZR masternode will cause you to be running more than your maximum number of masternodes, you will be given fair warning and a grace period of time (at least a few days) to register another NZR masternode or remove some running masternodes before any of your masternodes are destroyed in the system.

    Parameters:
        sCollateralAddress 	- The collateral address of the masternode being un-registered.

    NOTE: You do not need to specify the parameter when running this command. If you do not, the system will prompt you for it.
    """

	# local constants
	sCommandName = g_sUnRegisterNodeCommand  # Command name with prefix
	sFinalResponse = ""  # Final response we will build for the user.
	sErrRefID = str(ctx.message.author.id) + "-" + str(int(time.time()))
	sErrRefIDFooter = "\nInteraction Reference ID: " + sErrRefID
	sTicker = 'NZR'

	#check if system in maintenance
	bMaintenance, sMaintenance = _isMaintenanceMode(sErrRefID)
	if bMaintenance:
		await ctx.send(sMaintenance + sErrRefIDFooter)
		return

	#Ensure valid characters for the parameters specified (if any)
	aInvalidInputs = []
	if (sCollateralAddress != ""):
		if (not _isValidInput(g_sValidAlphaNumeric, sCollateralAddress)):
			aInvalidInputs.append(["Collateral Address", g_sValidAlphaNumeric])

	#alert user if any parameters were specified and they are invalid
	if (len(aInvalidInputs) != 0):
		aInvalidInputs.insert(0, ["Entry Name", "Valid Characters"])
		sFinalResponse = g_sResponse_ParametersNotValidCharacters + "\n" + _formatDiscordTable(aInvalidInputs)[0] + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Create a user object for this user
	try:
		nbuUser = NodeBotUser(ctx.message.author.id, g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	except Exception as e:
		_logger.error("Failed to create a user object in command {}. ErrRefID: {}".format(sCommandName, sErrRefID))
		sFinalResponse = g_sResponse_DatabaseConnectionFail + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Tell user to register if they are not yet
	if (not nbuUser.isRegistered):
		sFinalResponse =  g_sResponse_ListUnRegRemoveNodeUserNotRegistered.format("unregister", g_sRegisterUserCommand) + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#if no collateral address was specified, ask for it
	if (sCollateralAddress == ""):
		bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric, nbuUser.discordID, None, g_sPrompt_CollateralAddress.format("unregister"))
		if bTmpSuccess:
			sCollateralAddress = sTmpResponse
		else:
			sFinalResponse = sTmpResponse + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#Check if removal will make them over their limit of node hosting
	if (nbuUser.usedSlots > (nbuUser.totalSlots - g_nNZRNodeSlotMultiplier)):
		bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric, nbuUser.discordID, None, g_sPrompt_RemoveUnRegNZRNodeWillBeOverLimit.format("unregistering", (nbuUser.totalSlots - g_nNZRNodeSlotMultiplier), nbuUser.usedSlots, "unregistering", g_nOverSlotCountGraceDays, "unregister", "unregister"))
		if bTmpSuccess:
			if sTmpResponse.lower() != 'yes':
				sFinalResponse = g_sResponse_AbortGeneric.format("unregistering", sCommandName) + sErrRefIDFooter
				await ctx.send(sFinalResponse)
				return
		else:
			sFinalResponse = sTmpResponse + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#double check user wants to unregister this node
	bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric, nbuUser.discordID, None, g_sPrompt_DoubleCheckRemoveUnReg.format("unregister", sTicker, sCollateralAddress, "unregister"))
	if bTmpSuccess:
		if sTmpResponse.lower() != 'yes':
			sFinalResponse = g_sResponse_AbortGeneric.format("unregistering the node", sCommandName) + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return
	else:
		sFinalResponse = sTmpResponse + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#We have all data, unregister the node from the database
	bTmpSuccess, sTmpResponse = nbuUser.unregisterNode(sCollateralAddress)
	if bTmpSuccess:
		#Successfully unregistered the node. Build the complete success message
		sFinalResponse = g_sResponse_SuccessfullyUnRegisteredNode
		sFinalResponse += "\n\n" + g_sResponse_UsingXofYSlots.format(nbuUser.usedSlots, nbuUser.totalSlots)
	else:
		#There was an issue, build the failure message
		sFinalResponse = g_sResponse_FailedGeneric.format("unregister the node", sTmpResponse, sCommandName)

	# Send final response
	sFinalResponse += sErrRefIDFooter
	await ctx.send(sFinalResponse)

@bot.command()
@commands.dm_only()
async def listRegisteredNodes(ctx):
	"""
	List all your registered NZR masternodes.

	Args:
		None
	"""

	#local constants
	sCommandName = g_sListRegisteredNodesCommand     #Command name with prefix
	sFinalResponse = ""    #Final response we will build for the user.
	sErrRefID = str(ctx.message.author.id) + "-" + str(int(time.time()))
	sErrRefIDFooter = "\nInteraction Reference ID: " + sErrRefID
	aDiscordTableResponses = [] #table listing all the nodes associated with the user

	#check if system in maintenance
	bMaintenance, sMaintenance = _isMaintenanceMode(sErrRefID)
	if bMaintenance:
		await ctx.send(sMaintenance + sErrRefIDFooter)
		return

	#Create a user object for this user
	try:
		nbuUser = NodeBotUser(ctx.message.author.id, g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	except Exception as e:
		_logger.error("Failed to create a user object in command {}. ErrRefID : {}".format(sCommandName), sErrRefID)
		sFinalResponse = g_sResponse_DatabaseConnectionFail + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Tell user to register if they are not yet
	if (not nbuUser.isRegistered):
		sFinalResponse = g_sResponse_ListUnRegRemoveNodeUserNotRegistered.format("list", g_sRegisterUserCommand) + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#We have all data, list the nodes for this user
	bTmpSuccess, sTmpResponse = nbuUser.listRegisteredNodes()
	if bTmpSuccess:
		aDiscordTableResponses = _formatDiscordTable(sTmpResponse)
		#Send response
		await ctx.send(g_sResponse_ListRegisteredNodesSuccess + "\n\n")
		for table in aDiscordTableResponses:
			 await ctx.send(table)
		await ctx.send("\n\n" + g_sResponse_UsingXofYSlots.format(nbuUser.usedSlots, nbuUser.totalSlots))
	else:
		#There was an issue, build the failure message
		await ctx.send(g_sResponse_FailedGeneric.format("list your registered nodes", sTmpResponse, sCommandName))

	#Send final response
	await ctx.send(sErrRefIDFooter)

@bot.command()
@commands.dm_only()
async def addNode(ctx, sTicker = '', sAliasName = '', sCollateralAddress = '', sTXID = '', nTXIndex = None):
	"""
	Add a masternode to be run by the system.

	Parameters:
		sTicker		- The coin ticker of the masternode being added
		sAliasName	- The alias name for the masternode (for the user's masternode.conf file) Maximum length is 10 characters.
		sTXID		- The transaction ID of the collateral transaction

	NOTE: You do not need to specify the parameters when running this command. If you do not, the system will walk you through the process and prompt you for them one by one.  But, if any parameters are sent, they must all be sent, and they must be sent in the order specified.
	"""

	#local constants
	sCommandName = g_sAddNodeCommand     #Command name with prefix
	sFinalResponse = ""    #Final response we will build for the user.
	sErrRefID = str(ctx.message.author.id) + "-" + str(int(time.time()))
	sErrRefIDFooter = "\nInteraction Reference ID: " + sErrRefID

	#check if system in maintenance
	bMaintenance, sMaintenance = _isMaintenanceMode(sErrRefID)
	if bMaintenance:
		await ctx.send(sMaintenance + sErrRefIDFooter)
		return

	#Ensure valid characters for the parameters specified (if any)
	aInvalidInputs = []
	if (sTicker != ""):
		if (not _isValidInput(g_sValidAlphaNumeric, sTicker)):
			aInvalidInputs.append(["Ticker", g_sValidAlphaNumeric])
	if (sAliasName != ""):
		if (not _isValidInput(g_sValidAlphaNumeric, sAliasName)):
			aInvalidInputs.append(["Alias Name", g_sValidAlphaNumeric])
	if (sCollateralAddress != ""):
		if (not _isValidInput(g_sValidAlphaNumeric, sCollateralAddress)):
			aInvalidInputs.append(["Collateral Address", g_sValidAlphaNumeric])
	if (sTXID != ""):
		if (not _isValidInput(g_sValidAlphaNumeric, sTXID)):
			aInvalidInputs.append(["Transaction ID", g_sValidAlphaNumeric])
	#at this point nTXIndex will be a string if supplied, but None otherwise. So check validity as if a string for now
	if (not nTXIndex is None):
		if (not _isValidInput(g_sValidNumeric, nTXIndex)):
			aInvalidInputs.append(["Transaction Index", g_sValidNumeric])

	#alert user if any parameters were specified and they are invalid
	if (len(aInvalidInputs) != 0):
		aInvalidInputs.insert(0, ["Entry Name", "Valid Characters"])
		sFinalResponse = g_sResponse_ParametersNotValidCharacters + "\n" + _formatDiscordTable(aInvalidInputs)[0] + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#finally, convert transaction index to integer if it was entered (we know this should not fail because we validated it was integer above)
	if(not nTXIndex is None):
		nTXIndex = int(nTXIndex)

	#Create a user object for this user
	try:
		nbuUser = NodeBotUser(ctx.message.author.id, g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	except Exception as e:
		_logger.error("Failed to create a user object in command {} ErrRefID: {}.".format(sCommandName, sErrRefID))
		sFinalResponse = g_sResponse_DatabaseConnectionFail + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Tell user to register if they are not yet
	if (not nbuUser.isRegistered):
		sFinalResponse = g_sResponse_AddRegisterNodeUserNotRegistered.format(g_sRegisterUserCommand, sCommandName) + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Check if user has open slots to add (NZR nodes are always free, so only check if non-AZR node)
	if (sTicker != "NZR"):
		if nbuUser.usedSlots >= nbuUser.totalSlots:
			sFinalResponse = "You cannot add another node. " + g_sResponse_UsingXofYSlots.format(nbuUser.usedSlots,nbuUser.totalSlots) + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#if no ticker specified, ask for ticker
	if (sTicker == ""):
		bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric, nbuUser.discordID, None, g_sPrompt_Ticker)
		if bTmpSuccess:
			sTicker = sTmpResponse.upper()
		else:
			sFinalResponse = sTmpResponse + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return
	else: #ticker specified, force to upper
		sTicker = sTicker.upper()

	#verify ticker is valid
	if not sTicker in [coin[0] for coin in g_aSupportedCoins]:
		sFinalResponse = g_sResponse_TickerNotSupported.format(sTicker, sCommandName) + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#if no aliasname was specified, ask for it
	if (sAliasName == ""):
		bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric, nbuUser.discordID, None, g_sPrompt_AliasName)
		if bTmpSuccess:
			sAliasName = sTmpResponse
		else:
			sFinalResponse = sTmpResponse + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#If alias name was specified, ensure not over max characters
	if len(sAliasName) > g_nAliasNameMaxLength:
		bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric, nbuUser.discordID, None, g_sResponse_AliasNameOverLimit.format(g_nAliasNameMaxLength,g_nAliasNameMaxLength))
		if bTmpSuccess:
			sAliasName = sTmpResponse
		else:
			sFinalResponse = sTmpResponse + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#If alias name was still too long, exit and ask user to try again
	if len(sAliasName) > g_nAliasNameMaxLength:
		sFinalResponse = g_sResponse_AliasNameOverLimitFail.format(g_nAliasNameMaxLength) + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#We are far enough along, we can create a coin object to help obtain the remaining info we need
	try:
		nbcCoin = NodeBotCoin(sTicker, g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	except Exception as e:
		_logger.warning("Failed to instantiate a coin object for ticker {} in command {}. ErrRefID: {}".format(sTicker, sCommandName, sErrRefID))
		sFinalResponse = g_sResponse_UnknownError + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#If no TXID was specified, ask for it
	if (sTXID == ""):
		bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric, nbuUser.discordID, None, g_sPrompt_TXID.format(nbcCoin.collateralAmount))
		if bTmpSuccess:
			sTXID = sTmpResponse
		else:
			sFinalResponse = sTmpResponse + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#If no TXIndex was specified, we need to look it up
	if (nTXIndex is None):
		bTmpSuccess, nTmpConfirms, nTmpTXIndex, sTmpResponse = nbcCoin.checkCollateralTX(sTXID)
		if bTmpSuccess:
			nTXIndex = nTmpTXIndex
			if nTmpConfirms < 16:
				sFinalResponse = g_sResponse_ImmatureCollateralTransaction.format(nTmpConfirms, sCommandName, (round(((16 - nTmpConfirms)*nbcCoin.blockTimeSeconds)/60))) + sErrRefIDFooter
				await ctx.send(sFinalResponse)
				return
		else:
			sFinalResponse = g_sResponse_NotCollateralTransaction.format(sTmpResponse, sCommandName) + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#Lookup collateral address if not specified.
	if (sCollateralAddress == ""):
		bTmpSuccess, sTmpResponse = nbcCoin.getCollateralAddress(sTXID, nTXIndex)
		if bTmpSuccess:
			if (sCollateralAddress == ""):
				sCollateralAddress = sTmpResponse
			else:
				sFinalResponse = g_sResponse_CollateralAddressUTXOMismatch.format(sCommandName) + sErrRefIDFooter
				await ctx.send(sFinalResponse)
				return
		else:
			sFinalResponse = g_sResponse_FailedGeneric.format("validate the collateral address for this TXID", sTmpResponse, sCommandName) + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#We have all data, add to database and return the string for the users's masternode.conf file.
	bTmpSuccess, sTmpResponse = nbuUser.addNode(nbcCoin.ticker, sAliasName, nbcCoin.port, sCollateralAddress, sTXID, nTXIndex)
	if bTmpSuccess:
		#Successfully added the node. Build the complete success message
		sFinalResponse = g_sResponse_SuccessfullyAddedNode.format(sTmpResponse)
		#If it was a NZR node, remind user that is is not automatically registerd and it needs to be done manually
		if (sTicker == 'NZR'):
			sFinalResponse += "\n\n" + g_sResponse_AddedNZRNode.format(g_sRegisterNodeCommand)
		#Add info about how many nodes user is using/has left
		sFinalResponse += "\n\n" + g_sResponse_UsingXofYSlots.format(nbuUser.usedSlots, nbuUser.totalSlots)
	else:
		#There was an issue, build the failure message
		sFinalResponse = g_sResponse_FailedGeneric.format("add the node", sTmpResponse, sCommandName)

	#Send final response
	sFinalResponse += sErrRefIDFooter
	await ctx.send(sFinalResponse)

@bot.command()
@commands.dm_only()
async def removeNode(ctx, sTicker = '', sCollateralAddress = ''):
	"""
	Remove and destroy a masternode in the system.

	Parameters:
		sTicker				- The coin ticker of the masternode being removed
		sCollateralAddress	- The collateral address of the masternode being removed

	NOTE: You do not need to specify the parameters when running this command. If you do not, the system will walk you through the process and prompt you for them one by one.  But, if any parameters are sent, they must all be sent, and they must be sent in the order specified.
	"""

	#local constants
	sCommandName = g_sRemoveNodeCommand     #Command name with prefix
	sFinalResponse = ""    #Final response we will build for the user.
	sErrRefID = str(ctx.message.author.id) + "-" + str(int(time.time()))
	sErrRefIDFooter = "\nInteraction Reference ID: " + sErrRefID

	#check if system in maintenance
	bMaintenance, sMaintenance = _isMaintenanceMode(sErrRefID)
	if bMaintenance:
		await ctx.send(sMaintenance + sErrRefIDFooter)
		return

	#Ensure valid characters for the parameters specified (if any)
	aInvalidInputs = []
	if ((sTicker != "") and (not _isValidInput(g_sValidAlphaNumeric, sTicker))):
		aInvalidInputs.append(["Ticker", g_sValidAlphaNumeric])
	if ((sCollateralAddress != "") and (not _isValidInput(g_sValidAlphaNumeric, sCollateralAddress))):
		aInvalidInputs.append(["Collateral Address", g_sValidAlphaNumeric])

	#alert user if any parameters were specified and they are invalid
	if (len(aInvalidInputs) != 0):
		aInvalidInputs.insert(0, ["Entry Name", "Valid Characters"])
		sFinalResponse = g_sResponse_ParametersNotValidCharacters + "\n" + _formatDiscordTable(aInvalidInputs)[0] + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Create a user object for this user
	try:
		nbuUser = NodeBotUser(ctx.message.author.id, g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	except Exception as e:
		_logger.error("Failed to create a user object in command {}. ErrRefID: {}".format(sCommandName, sErrRefID))
		sFinalResponse = g_sResponse_DatabaseConnectionFail + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Tell user to register if they are not yet
	if (not nbuUser.isRegistered):
		sFinalResponse = g_sResponse_ListUnRegRemoveNodeUserNotRegistered.format("remove", g_sRegisterUserCommand) + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#if no ticker specified, ask for ticker
	if (sTicker == ""):
		bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric, nbuUser.discordID, None, g_sPrompt_Ticker)
		if bTmpSuccess:
			sTicker = sTmpResponse.upper()
		else:
			sFinalResponse = sTmpResponse + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return
	else: #ticker specified, force to upper
		sTicker = sTicker.upper()

	#verify ticker is valid
	if not sTicker in [coin[0] for coin in g_aSupportedCoins]:
		sFinalResponse = g_sResponse_TickerNotSupported.format(sTicker, sCommandName) + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Check if user is removing a NZR nodes and if that removal will make them over their limit of node hosting, warm them.
	if ((sTicker == "NZR") and (nbuUser.usedSlots > (nbuUser.totalSlots - g_nNZRNodeSlotMultiplier))):
		bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric, nbuUser.discordID, None, g_sPrompt_RemoveUnRegNZRNodeWillBeOverLimit.format("removing", (nbuUser.totalSlots - g_nNZRNodeSlotMultiplier), nbuUser.usedSlots, "removing", g_nOverSlotCountGraceDays, "remove", "remove"))
		if bTmpSuccess:
			if sTmpResponse.lower() != 'yes':
				sFinalResponse = g_sResponse_AbortGeneric.format("removing the node", sCommandName) + sErrRefIDFooter
				await ctx.send(sFinalResponse)
				return
		else:
			sFinalResponse = sTmpResponse + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#if no collateral address name was specified, ask for it
	if (sCollateralAddress == ""):
		bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric, nbuUser.discordID, None, g_sPrompt_CollateralAddress.format("remove"))
		if bTmpSuccess:
			sCollateralAddress = sTmpResponse
		else:
			sFinalResponse = sTmpResponse + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#double check user wants to remove this node
	bTmpSuccess, sTmpResponse = await _getUserResponse(ctx, bot, sErrRefID, sCommandName, g_sValidAlphaNumeric, nbuUser.discordID, None, g_sPrompt_DoubleCheckRemoveUnReg.format("remove", sTicker, sCollateralAddress, "remove"))
	if bTmpSuccess:
		if sTmpResponse.lower() != 'yes':
			sFinalResponse = g_sResponse_AbortGeneric.format("removing the node", sCommandName) + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return
	else:
		sFinalResponse = sTmpResponse + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return


	#We have all data, remove the node from the database and set user's used node count
	#(even if this is a NZR node, we will not recalculate the user's free node limit.  We only do that when unregistering in case they are just moving this node to another host)
	bTmpSuccess, sTmpResponse1, sTmpResponse2 = nbuUser.removeNode(sTicker, sCollateralAddress)
	if bTmpSuccess:
		#Successfully removed the node. Build the success message
		sFinalResponse = g_sResponse_SuccessfullyRemovedNode.format(sTmpResponse1, sTmpResponse2) + " " + g_sResponse_UsingXofYSlots.format(nbuUser.usedSlots, nbuUser.totalSlots)
	else:
		#There was an issue, build the failure message
		sFinalResponse = g_sResponse_FailedGeneric.format("remove the node", sTmpResponse1, sCommandName)

	#Send final response
	sFinalResponse += sErrRefIDFooter
	await ctx.send(sFinalResponse)

@bot.command()
@commands.dm_only()
async def listAddedNodes(ctx, sTicker = ''):
	"""
	List the masternodes being run for you in the system.
	If a coin ticker is supplied, it will list the masternodes for that ticker, otherwise will display all nodes.

	Parameters:
		sTicker	- The coin ticker of the masternodes to display. (leave blank to display all masternodes)

	NOTE: You do not need to specify the parameter when running this command. If you do not, the system will prompt you for it.
	"""

	#local constants
	sCommandName = g_sListAddedNodesCommand     #Command name with prefix
	sFinalResponse = ""    #Final response we will build for the user.
	sErrRefID = str(ctx.message.author.id) + "-" + str(int(time.time()))
	sErrRefIDFooter = "\nInteraction Reference ID: " + sErrRefID
	aDiscordTableResponses = [] #table listing all the nodes associated with the user

	#check if system in maintenance
	bMaintenance, sMaintenance = _isMaintenanceMode(sErrRefID)
	if bMaintenance:
		await ctx.send(sMaintenance + sErrRefIDFooter)
		return

	#Ensure valid characters for the parameters specified (if any)
	aInvalidInputs = []
	if ((sTicker != "") and (not _isValidInput(g_sValidAlphaNumeric, sTicker))):
		aInvalidInputs.append(["Ticker", g_sValidAlphaNumeric])

	#alert user if any parameters were specified and they are invalid
	if (len(aInvalidInputs) != 0):
		aInvalidInputs.insert(0, ["Entry Name", "Valid Characters"])
		sFinalResponse = g_sResponse_ParametersNotValidCharacters + "\n" + _formatDiscordTable(aInvalidInputs)[0] + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Create a user object for this user
	try:
		nbuUser = NodeBotUser(ctx.message.author.id, g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	except Exception as e:
		_logger.error("Failed to create a user object in command {}. ErrRefID : {}".format(sCommandName), sErrRefID)
		sFinalResponse = g_sResponse_DatabaseConnectionFail + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Tell user to register if they are not yet
	if (not nbuUser.isRegistered):
		sFinalResponse = g_sResponse_ListUnRegRemoveNodeUserNotRegistered.format("list", g_sRegisterUserCommand) + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#if ticker specified, force to upper and verify valid
	if (sTicker != ""):
		sTicker = sTicker.upper()
		if not sTicker in [coin[0] for coin in g_aSupportedCoins]:
			sFinalResponse = g_sResponse_TickerNotSupported.format(sTicker, sCommandName) + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#We have all data, list the nodes for this user
	bTmpSuccess, sTmpResponse = nbuUser.listAddedNodes(sTicker)
	if bTmpSuccess:
		aDiscordTableResponses = _formatDiscordTable(sTmpResponse)
		#Send response
		await ctx.send(g_sResponse_ListAddedNodesSuccess.format("all" if (sTicker == "") else sTicker) + "\n\n")
		for table in aDiscordTableResponses:
			await ctx.send(table)
		await ctx.send("\n\n" + g_sResponse_UsingXofYSlots.format(nbuUser.usedSlots, nbuUser.totalSlots))
	else:
		#There was an issue, build the failure message
		await ctx.send(g_sResponse_FailedGeneric.format("list your nodes", sTmpResponse, sCommandName))

	#Send final response
	await ctx.send(sErrRefIDFooter)

@bot.command()
@commands.dm_only()
async def listConfigs(ctx, sTicker = ''):
	"""
	List the masternode.conf file entries for your masternodes.
	If a coin ticker is supplied, it will list the masternode.conf file entries for that ticker, otherwise it will list entries for all coins.

	Parameters:
		sTicker	- The coin ticker of the masternode.conf file entries to display. (leave blank to display for all coins)

	NOTE: You do not need to specify the parameter when running this command. If you do not, the system will prompt you for it.
	"""

	#local constants
	sCommandName = g_sListConfigsCommand     #Command name with prefix
	sFinalResponse = ""    #Final response we will build for the user.
	sErrRefID = str(ctx.message.author.id) + "-" + str(int(time.time()))
	sErrRefIDFooter = "\nInteraction Reference ID: " + sErrRefID
	aDiscordTableResponses = [] #table listing all the nodes associated with the user

	#check if system in maintenance
	bMaintenance, sMaintenance = _isMaintenanceMode(sErrRefID)
	if bMaintenance:
		await ctx.send(sMaintenance + sErrRefIDFooter)
		return

	#Ensure valid characters for the parameters specified (if any)
	aInvalidInputs = []
	if ((sTicker != "") and (not _isValidInput(g_sValidAlphaNumeric, sTicker))):
		aInvalidInputs.append(["Ticker", g_sValidAlphaNumeric])

	#alert user if any parameters were specified and they are invalid
	if (len(aInvalidInputs) != 0):
		aInvalidInputs.insert(0, ["Entry Name", "Valid Characters"])
		sFinalResponse = g_sResponse_ParametersNotValidCharacters + "\n" + _formatDiscordTable(aInvalidInputs)[0] + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Create a user object for this user
	try:
		nbuUser = NodeBotUser(ctx.message.author.id, g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, sErrRefID)
	except Exception as e:
		_logger.error("Failed to create a user object in command {}. ErrRefID : {}".format(sCommandName), sErrRefID)
		sFinalResponse = g_sResponse_DatabaseConnectionFail + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#Tell user to register if they are not yet
	if (not nbuUser.isRegistered):
		sFinalResponse = g_sResponse_ListUnRegRemoveNodeUserNotRegistered.format("list", g_sRegisterUserCommand) + sErrRefIDFooter
		await ctx.send(sFinalResponse)
		return

	#if ticker specified, force to upper and verify valid
	if (sTicker != ""):
		sTicker = sTicker.upper()
		if not sTicker in [coin[0] for coin in g_aSupportedCoins]:
			sFinalResponse = g_sResponse_TickerNotSupported.format(sTicker, sCommandName) + sErrRefIDFooter
			await ctx.send(sFinalResponse)
			return

	#We have all data, list the nodes for this user
	bTmpSuccess, sTmpResponse = nbuUser.listConfigs(sTicker)
	if bTmpSuccess:
		aDiscordTableResponses = _formatDiscordTable(sTmpResponse,"left","",0,0,False,False) #format table with no seperators, no padding, no header seperartor, and no end of line padding so user can easily copy/paste into config file
		#Send response
		await ctx.send(g_sResponse_ListConfigsSuccess.format("all" if (sTicker == "") else sTicker) + "\n\n")
		for table in aDiscordTableResponses:
			await ctx.send(table)
		await ctx.send("\n\n" + g_sResponse_UsingXofYSlots.format(nbuUser.usedSlots, nbuUser.totalSlots))
	else:
		#There was an issue, build the failure message
		await ctx.send(g_sResponse_FailedGeneric.format("list your masternode config entries", sTmpResponse, sCommandName))

	#Send final response
	await ctx.send(sErrRefIDFooter)

@bot.command(hidden=True)
@checkRole("ADMIN")
@commands.dm_only()
async def status(ctx):
	"""Respond with a system status"""

	aStatusList = []
	sFinalSystemStatus = "unknown"
	sReturn = ""

	#Start a table of statuses
	aStatusList.append(["System", "Status", "Notes"])

	#Get background task statuses
	sTaskName = "newNodeNotifier"
	nTaskCurrentLoop = newNodeNotifier.current_loop
	dTaskNextIteration = newNodeNotifier.next_iteration
	bTaskIsBeingCancelled = newNodeNotifier.is_being_cancelled()
	nLoopTime = g_nNewNodeNotifierLoopSeconds
	sNextIteration = "unknown"
	if (not dTaskNextIteration is None):
		nDiff = dTaskNextIteration.timestamp() - int(time.time())
		sNextIteration = str(int(nDiff/60)) + " minutes " + str(int(nDiff % 60)) + " seconds"
	if (nTaskCurrentLoop == 0):
		aStatusList.append([sTaskName, "Off", ""])
	elif ((sNextIteration == "unknown") or (bTaskIsBeingCancelled)):
		aStatusList.append([sTaskName, "Shutting down", ""])
	else:
		aStatusList.append([sTaskName, "On", "Loop Time: {}. Current Iteration: {}. Next Iteration: {}.".format(str(nLoopTime), str(nTaskCurrentLoop), sNextIteration)])

	sTaskName = "pollNodeStatus"
	nTaskCurrentLoop = pollNodeStatus.current_loop
	dTaskNextIteration = pollNodeStatus.next_iteration
	bTaskIsBeingCancelled = pollNodeStatus.is_being_cancelled()
	nLoopTime = g_nPollNodeStatusLoopSeconds
	sNextIteration = "unknown"
	if (not dTaskNextIteration is None):
		nDiff = dTaskNextIteration.timestamp() - int(time.time())
		sNextIteration = str(int(nDiff/60)) + " minutes " + str(int(nDiff % 60)) + " seconds"
	if (nTaskCurrentLoop == 0):
		aStatusList.append([sTaskName, "Off", ""])
	elif ((sNextIteration == "unknown") or (bTaskIsBeingCancelled)):
		aStatusList.append([sTaskName, "Shutting down", ""])
	else:
		aStatusList.append([sTaskName, "On", "Loop Time: {}. Current Iteration: {}. Next Iteration: {}.".format(str(nLoopTime), str(nTaskCurrentLoop), sNextIteration)])


	#Calculate final system status

	#check if system in maintenance
	bMaintenance, sMaintenance = _isMaintenanceMode("")
	if bMaintenance:
		sFinalSystemStatus = "database in maintenance mode"
	else:
		sFinalSystemStatus = "nominal" #we have no other checks at this time

	aStatusList.append(["-----------------------------","-----------------------------","----------------------------------------------------------"])
	aStatusList.append(["FINAL SYSTEM STATUS", sFinalSystemStatus, ""])

	#Return result
	sReturn = "System status is below."
	sReturn += "\n\n" + _formatDiscordTable(aStatusList)[0]
	await ctx.send(sReturn)

@bot.command(hidden=True)
async def test(ctx):
	pass
	#await ctx.send("Hi, i'm the bot, please send me a DM to get started.")


@bot.command(hidden=True)
@checkRole("ADMIN")
@commands.dm_only()
async def repopulateConstants(ctx):
	"""Re-query and re-load system constants. Do this after updating system constants in the database and causing them to be used by the system."""

	try:
		_populateSystemConstants()
	except Exception as e:
		_logger.error("Re-populating system constants failed. Initiated by DiscordName {} : DiscordId {} Error {}".format(ctx.message.author.name, ctx.message.author.id, str(e)))
		await ctx.send("Repopulating system constants failed, check logs.")
	else:
		_logger.info("Re-populating system constants success. Initiated by DiscordName {} : DiscordId {}".format(ctx.message.author.name, ctx.message.author.id))
		await ctx.send("Repopulated system constants successfully. All is good.")

@bot.command(hidden=True)
@checkRole("ADMIN")
@commands.dm_only()
async def startNewNodeNotifier(ctx):
	"""Start the NewNodeNotifier background task"""

	sFuncName = "startNewNodeNotifier"
	sReturn = ""
	nLoopTime = g_nNewNodeNotifierLoopSeconds

	#our task decorator has the default loop time set, but because python reads and replaces that value the first time this script is parsed, it gets stuck at that value.
	#So we re-set the loop value here in case we change the value in the database and want to use the new value
	newNodeNotifier.change_interval(seconds=nLoopTime)

	try:
		myDAL = DAL(g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, "")
		myDAL.connect()
		newNodeNotifier.start()
		_logger.info("{} - Started successfully.  User: {}({}) Loop Time: {}.".format(sFuncName, ctx.message.author.name, ctx.message.author.id, str(nLoopTime)))
		myDAL.addSysLogEntry("log", sFuncName,"Success. User: {}({}) Loop Time: {}.".format(ctx.message.author.name, ctx.message.author.id, str(nLoopTime)))
		sReturn = "Task started. Loop time {} seconds.".format(str(nLoopTime))
	except Exception as e:
		if ("Task is already launched" in str(e)):
			sReturn = "Task is already running."
		else:
			sReturn = "Error occured. Unsure if task was started. Error: {}".format(str(e))
			_logger.error("{} - Unknown error occured. Loop Time: {} Error: {}.".format(sFuncName, str(nLoopTime), str(e)))
	myDAL.disconnect()
	await ctx.send(sReturn)

@bot.command(hidden=True)
@checkRole("ADMIN")
@commands.dm_only()
async def stopNewNodeNotifier(ctx, force = None):
	"""Stops the NewNodeNotifier background task
	Use the 'force' parameter to stop the task immediately. Otherwise it will be stopped after the next run of the task.
	"""

	sFuncName = "stopNewNodeNotifier"
	sReturn = ""
	nIterations = newNodeNotifier.current_loop

	try:
		myDAL = DAL(g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, "")
		myDAL.connect()

		if (nIterations == 0):
			sReturn = "Task not running."
		elif (newNodeNotifier.is_being_cancelled()):
			sReturn = "Task is in process of being cancelled"
		else:
			if(force):
				newNodeNotifier.cancel()
			else:
				newNodeNotifier.stop()
			_logger.info("{} - Stopped successfully.  Force: {} User: {}({}) Loop Iterations: {}.".format(sFuncName, bool(force), ctx.message.author.name, ctx.message.author.id, str(nIterations)))
			myDAL.addSysLogEntry("log", sFuncName,"Success. Force: {} User: {}({}) Loop Iterations: {}.".format(bool(force), ctx.message.author.name, ctx.message.author.id, str(nIterations)))
			sReturn = "Task stopped. Loop iterations: {}".format(str(nIterations))
	except Exception as e:
		sReturn = "Error occured. Unsure if task was stopped. Error: {}".format(str(e))
		_logger.error("{} - Error occured. Loop Iterations: {} Error: {}.".format(sFuncName, str(nIterations), str(e)))
	myDAL.disconnect()
	await ctx.send(sReturn)

@bot.command(hidden=True)
@checkRole("ADMIN")
@commands.dm_only()
async def startPollNodeStatus(ctx):
	"""Start the pollNodeStatus background task"""

	sFuncName = "startPollNodeStatus"
	sReturn = ""
	nLoopTime = g_nPollNodeStatusLoopSeconds

	#our task decorator has the default loop time set, but because python reads and replaces that value the first time this script is parsed, it gets stuck at that value.
	#So we re-set the loop value here in case we change the value in the database and want to use the new value
	pollNodeStatus.change_interval(seconds=nLoopTime)

	try:
		myDAL = DAL(g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, "")
		myDAL.connect()
		pollNodeStatus.start()
		_logger.info("{} - Started successfully.  User: {}({}) Loop Time: {}.".format(sFuncName, ctx.message.author.name, ctx.message.author.id, str(nLoopTime)))
		myDAL.addSysLogEntry("log", sFuncName,"Success. User: {}({}) Loop Time: {}.".format(ctx.message.author.name, ctx.message.author.id, str(nLoopTime)))
		sReturn = "Task started. Loop time {} seconds.".format(str(nLoopTime))
	except Exception as e:
		if ("Task is already launched" in str(e)):
			sReturn = "Task is already running."
		else:
			sReturn = "Error occured. Unsure if task was started. Error: {}".format(str(e))
			_logger.error("{} - Unknown error occured. Loop Time: {} Error: {}.".format(sFuncName, str(nLoopTime), str(e)))
	myDAL.disconnect()
	await ctx.send(sReturn)

@bot.command(hidden=True)
@checkRole("ADMIN")
@commands.dm_only()
async def stopPollNodeStatus(ctx, force = None):
	"""Stops the pollNodeStatus background task
	Use the 'force' parameter to stop the task immediately. Otherwise it will be stopped after the next run of the task.
	"""

	sFuncName = "stopPollNodeStatus"
	sReturn = ""
	nIterations = pollNodeStatus.current_loop

	try:
		myDAL = DAL(g_sNZRNodeBotDatabase, _logger, g_sLoggingLevel, "")
		myDAL.connect()

		if (nIterations == 0):
			sReturn = "Task not running."
		elif (pollNodeStatus.is_being_cancelled()):
			sReturn = "Task is in process of being cancelled"
		else:
			if(force):
				pollNodeStatus.cancel()
			else:
				pollNodeStatus.stop()
			_logger.info("{} - Stopped successfully.  Force: {} User: {}({}) Loop Iterations: {}.".format(sFuncName, bool(force), ctx.message.author.name, ctx.message.author.id, str(nIterations)))
			myDAL.addSysLogEntry("log", sFuncName,"Success. Force: {} User: {}({}) Loop Iterations: {}.".format(bool(force), ctx.message.author.name, ctx.message.author.id, str(nIterations)))
			sReturn = "Task stopped. Loop iterations: {}".format(str(nIterations))
	except Exception as e:
		sReturn = "Error occured. Unsure if task was stopped. Error: {}".format(str(e))
		_logger.error("{} - Error occured. Loop Iterations: {} Error: {}.".format(sFuncName, str(nIterations), str(e)))
	myDAL.disconnect()
	await ctx.send(sReturn)


@bot.command(hidden=True)
@checkRole("SUPERUSER")
@commands.dm_only()
async def shutdownBot(ctx):
	"""Shut down the bot and log info"""

	await ctx.send("Shutting down bot now.")
	print('Bot shutting down from shutdown command.')
	_logger.warning("################################################################################")
	_logger.warning("-----  Shutting down bot from shutdown command. Initiated by: {}({}) - Original bot start time: {}  -----".format(ctx.message.author.name, ctx.message.author.id, datetime.utcfromtimestamp(g_dtBotBootupDateTime)))
	_logger.warning("################################################################################")
	await bot.close()

#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
############    END BOT COMMANDS    ###############
###################################################




###################################################
#######    BOT COMMAND ERROR HANDLERS   ###########
#vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

@registerUser.error
async def registerUser_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@unregisterUser.error
async def unregisterUser_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@registerNode.error
async def registerNode_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@unregisterNode.error
async def unregisterNode_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@listRegisteredNodes.error
async def listRegisteredNodes_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@addNode.error
async def addNode_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@removeNode.error
async def removeNode_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@listAddedNodes.error
async def listAddedNodes_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@listAddedNodes.error
async def listConfigs_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@repopulateConstants.error
async def repopulateConstants_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@startNewNodeNotifier.error
async def startNewNodeNotifier_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@stopNewNodeNotifier.error
async def stopNewNodeNotifier_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@startPollNodeStatus.error
async def startPollNodeStatus_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@stopPollNodeStatus.error
async def stopPollNodeStatus_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@status.error
async def status_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise

@shutdownBot.error
async def shutdownBot_handler(ctx, error):
	#Handle Private Message required error
	if isinstance(error, commands.PrivateMessageOnly):
		await ctx.send(g_sResponse_DMOnlyCommand)
	# Handle missing permissions error
	if isinstance(error, CheckRoleFail):
		await ctx.send(g_sResponse_NoPermissionsCommand)
	raise


#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#####  END BOT COMMAND ERROR HANDLERS   ###########
###################################################

#Start the bot
bot.run(g_sBotToken)
