
## version 1.0 #######################################################################################################
#####################################            Version history           ###########################################
######################################################################################################################
# 4/08/20 - version 1.0 - initial version
######################################################################################################################

def secondsToDaysHoursMinutesSecondsString(seconds):
	sReturn = ""
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	days, hours = divmod(hours, 24)
	sReturn = str(days) + " days " + str(hours) + " hours " + str(minutes) + " minutes " + str(seconds) + " seconds"
	return (sReturn)