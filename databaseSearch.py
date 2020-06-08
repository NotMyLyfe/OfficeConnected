# databaseSearch.py
# Gordon Lin and Evan Lu
# Goes through each value in the database and checks for updates on Microsoft 365
import os, requests, app_config, datetime, sql, time
from twilioSend import send
from app import _build_msal_app

# Functions getTeamMeetings, getTeamMessages and getEmailsOverSMS have the exact same parameters
# token is the user's access token
# phoneNumber is the user's phoneNumber
# lastCheckTime is the last time the server has began checking for Teams notifications
# startCheckTime is the time the server began checking for the most recent Teams notifications

# A delay has been set up so the server can fully catchup to the influx of notifications, rather than skipping or repeating notifications

# Retrieves Microsoft Teams meetings of the user
def getTeamMeetings(token, phoneNumber, lastCheckTime, startCheckTime):
    # Reminder time prior to meetings
    timeIncrements = [5, 10, 15, 30]

    # Makes a GET request to retrieve all the teams that the user is joined
    teamsData = requests.get(
        app_config.ENDPOINT + '/me/joinedTeams',
        headers={'Authorization': 'Bearer ' + token},
        ).json()
    
    # Goes through all the information regarding the joined teams of the user
    for joinedTeams in teamsData['value']:
        # Gets the name of the team being referenced
        teamName = joinedTeams['displayName']

        # Gets all the currently saved events of team that's being referenced
        teamsEvents = requests.get(
            app_config.ENDPOINT + '/groups/' + joinedTeams['id'] + '/events',
            headers={'Authorization': 'Bearer ' + token},
            ).json()
        
        # Goes through all the events (which are usually meetings on Teams) of the referenced team
        for teamsMeetings in teamsEvents['value']:

            # Finds the start time of the event and takes the JSON date and converts into a format recognizable in Python
            eventStartTime = datetime.datetime.strptime(teamsMeetings['start']['dateTime'], '%Y-%m-%dT%H:%M:%S.%f0')

            # Checks if the currently team meeting has yet to start from the time the server last checked for new updates
            if eventStartTime > lastCheckTime:
                # Finds the time of last checked and when the server begins to start checking for new updates
                timeDifferenceFromLastChecked = int((eventStartTime - lastCheckTime).total_seconds())
                timeDifferenceFromStartChecked = int((eventStartTime - startCheckTime).total_seconds())

                # Checks if the the team meeting has started since the server started checking for new updates and notifys the user
                if eventStartTime <= startCheckTime:
                    send("OfficeConnected: You currently have a meeting with %s starting now" % teamName, phoneNumber)
                else:
                    # Checks if the team meeting is less than 30 minutes ahead of the server starting to check for new updates
                    if timeDifferenceFromStartChecked <= 1800:
                        # Goes through all the in time increments that were specified prior to the meeting for notifications
                        for times in timeIncrements:
                            # Checks if the last checked time was prior to the time increment, but the current check has commenced on or after the time prior to the meeting
                            if timeDifferenceFromLastChecked > times * 60 and timeDifferenceFromStartChecked <= times*60:
                                # Sends a message notifying for upcoming meeting
                                send("OfficeConnected: You currently have a meeting with %s in %d minutes" % (teamName, times), phoneNumber)
                                break
                    
                    # Checks if the server last check prior to 24 hours before the meeting and has now reaches 24 hours til the meeting and notifys the user that a meeting is tomorrow
                    elif timeDifferenceFromStartChecked <= 86400 and timeDifferenceFromLastChecked > 86400:
                        send("OfficeConnected: Reminder you have a meeting with %s tomorrow" % teamName, phoneNumber)

# Gets all the messages in Teams (without replies)
def getTeamMessages(token, phoneNumber, lastCheckTime, startCheckTime):
    # Makes a GET request to get only the name of the user
    nameOfUser = requests.get(
        app_config.ENDPOINT + '/me',
        headers={'Authorization' : 'Bearer ' + token},
    ).json()['displayName']

    # Gets all the information regarding all the joined teams of the user
    teamsData = requests.get( 
        app_config.ENDPOINT + '/me/joinedTeams',
        headers={'Authorization': 'Bearer ' + token},
        ).json()
    
    # Goes through each individual team
    for joinedTeams in teamsData['value']:
        # Gets the name of the team
        teamName = joinedTeams['displayName']

        # Gets all the information regarding the channels of the specified team
        channelsData = requests.get(
            app_config.ENDPOINT + '/teams/' + joinedTeams['id'] + '/channels',
            headers={'Authorization': 'Bearer ' + token},
            ).json()
        
        # Goes through each individual channel of the team
        for channels in channelsData['value']:
            # Gets all the data regarding each message on the channel
            messagesData = requests.get(
                app_config.ENDPOINT + '/teams/' + joinedTeams['id'] + '/channels/' + channels['id'] + '/messages',
                headers={'Authorization': 'Bearer ' + token},
                ).json()
            
            # Goes through each individual message in the channel
            for messages in messagesData['value']:
                # Detecting for cancelled meeting
                # Checks if the message in question is regarding a scheduled meeting
                if "Scheduled a meeting" in messages['body']['content']:
                    # Gets all the replies of the specified message
                    repliesData = requests.get(
                    app_config.ENDPOINT + '/teams/' + joinedTeams['id'] + '/channels/' + channels['id'] + '/messages/' + messages['id'] + '/replies',
                    headers={'Authorization': 'Bearer ' + token},
                    ).json()

                    # Goes through each individual reply of the message regarding the scheduled meeting
                    for replies in repliesData['value']:
                        # Checks if the reply is text rather than HTML or another type
                        if replies["body"]["contentType"] == "text":
                            # Gets the reply
                            reply = replies["body"]["content"]

                            # Checks if the message hasn't been checked over by the servers yet
                            if startCheckTime >= datetime.datetime.strptime(replies['createdDateTime'], '%Y-%m-%dT%H:%M:%S.%fZ') >= lastCheckTime:
                                # Finds if the quotes are contained inside the reply (which the notification for a cancelled meeting contians quotes with the meeting name)
                                if '"' in reply and reply.find('"') != reply.rfind('"'):
                                    # Gets the meeting name and removes the meeting name from the reply
                                    meetingName = reply[reply.find('"')+1 : reply.rfind('"')]
                                    reply = reply[:reply.find('"')-1] + reply[reply.rfind('"')+1:]
                                    
                                    # Checks if the reply is regarding a cancelled meeting and notifys the user about the cancelled meeting
                                    if reply == "The meeting has been cancelled":
                                        send("OfficeConnected: Your meeting regarding %s with %s has been cancelled" % (meetingName, teamName), phoneNumber)
                
                # Detecting normal messages on the channel
                # Checks if the message doesn't originate from the user and is a message from a user
                elif messages.get("from").get("user") and messages["from"]["user"]["displayName"] != nameOfUser:
                    speaker = messages["from"]["user"]["displayName"]
                    # Checks if the message contains text
                    if messages["body"]["contentType"] == "text":
                        # Checks if the message has been modified and that the text was modified recently between the time the server started checking and the time the server last checked
                        if messages["lastModifiedDateTime"] and startCheckTime >= datetime.datetime.strptime(messages["lastModifiedDateTime"], '%Y-%m-%dT%H:%M:%S.%fZ') >= lastCheckTime:
                            # Gets the message and sends the message to the user
                            message = messages["body"]["content"]
                            send("OfficeConnected: (%s) %s modified: %s" % (teamName, speaker, message), phoneNumber)
                        
                        # Checks if the message hasn't been modified and that the text was created recently between the time the server started checking and the time the server last checked
                        elif startCheckTime >= datetime.datetime.strptime(messages["createdDateTime"], '%Y-%m-%dT%H:%M:%S.%fZ') >= lastCheckTime:
                            # Gets the message and sends the message to the user
                            message = messages["body"]["content"]
                            send("OfficeConnected: (%s) %s: %s" % (teamName, speaker, message), phoneNumber)
                    # Else if the message isn't text, but the message was created recently between the time the server started checking the and the time the server last checked
                    elif startCheckTime >= datetime.datetime.strptime(messages["createdDateTime"], '%Y-%m-%dT%H:%M:%S.%fZ') >= lastCheckTime:
                        # Sends a notification regarding the incompatible message to the user
                        send("OfficeConnected: %s has said something on %s" % (speaker, teamName), phoneNumber)

# Sends email notifications over SMS
def getEmailOverSMS(token, phoneNumber, email, lastCheckTime, startCheckTime):
    # Makes an GET request to get all the emails from the user
    emails = requests.get(
        app_config.ENDPOINT + "/me/messages",
        headers={'Authorization' : 'Bearer ' + token},
    ).json()

    # Goes through every email
    for emailInfo in emails["value"]:
        # Gets time stamp of when the email was sent
        received = datetime.datetime.strptime(emailInfo["sentDateTime"], '%Y-%m-%dT%H:%M:%SZ')
        # Checks if the email was sent between the time the server last checked for updates and when the server starting checking for updates
        if startCheckTime >= received >= lastCheckTime:
            # Checks if the email doesn't match the user's email and sends an SMS notification about the email
            if emailInfo["sender"]["emailAddress"]["address"] != email:
                send("OfficeConnected: %s has emailed you about %s" % (emailInfo["sender"]["emailAddress"]["name"], emailInfo["subject"]), phoneNumber)
        # Checks if the email is older than the last checked time by the server
        elif received <= lastCheckTime:
            break

# Variable for the last known time the server has been checked
lastCheckTime = datetime.datetime.utcnow()
while True:
    try:
        # Gets all the queries on the database
        database = sql.getAll()
        # Variable for the time the server started checking for updates
        startCheckTime = datetime.datetime.utcnow()
        # Goes through all the queries on the database
        for userData in database:
            # Gets the user's refresh token
            refreshToken = userData[0]
            
            # Gets the user's email
            email = userData[3]
            # Checks if the user has a verified has a verified phone number and creates variable storing phone number if verified
            verifiedPhone = userData[5]
            if verifiedPhone:
                phoneNumber = userData[1]
            else:
                phoneNumber = None
            # Checks if refresh token hasn't been flagged as invalid
            if refreshToken:
                # Checks if the user has opted in to SMS notifications and email over SMS
                getSMSTeamsNotifications = userData[2]
                emailOverSMS = userData[4]
                # Attempts to get an access token
                try:
                    token = _build_msal_app().acquire_token_by_refresh_token(refresh_token=refreshToken, scopes=app_config.SCOPE)
                except:
                    # Creates token with error telling that it failed to get an access token
                    token = {
                        "error" : "failed to get token"
                    }
                
                # Checks if the token doesn't contain an error
                if "error" not in token:
                    # Goes through and tries to get data requested by the user (such as getting Teams notifications or email info), if a phone number is also specified
                    if phoneNumber:
                        if getSMSTeamsNotifications:
                            getTeamMessages(token['access_token'], phoneNumber, lastCheckTime, startCheckTime)
                            getTeamMeetings(token['access_token'], phoneNumber, lastCheckTime, startCheckTime)
                        if emailOverSMS:
                            getEmailOverSMS(token['access_token'], phoneNumber, email, lastCheckTime, startCheckTime)
                else:
                    # If code does contain an error, tells user about the error (if phone number is specified and verified) and updates refresh token to be invalid
                    if phoneNumber:
                        send("OfficeConnected: Your login credentials have expired, please relogin to refresh credentials at https://officeconnected.azurewebsites.net", phoneNumber)
                    sql.updateVal(userData[3], 'Token', None)
                    break
        # Updates last check time to become last checked time
        lastCheckTime = startCheckTime
        # Setting up 1/4 sec delay to allow small gaps for SQL input
        time.sleep(0.25)
    except:
        pass