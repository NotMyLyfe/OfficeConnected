# app.py
# Gordon Lin and Evan Lu
# Web app that can interact with Microsoft 365 services directly from SMS
# Can receive Microsoft Teams notifications, send Teams messages, receive/send emails

import uuid, requests, msal, app_config, pyodbc, sql, multiprocessing, os, random, string, threading, datetime, time
from flask import Flask, render_template, session, request, redirect, url_for
from flask_session import Session
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

# Creates Flask app and session with config
app = Flask(__name__)
app.config.from_object(app_config)
Session(app)

# Protocol scheme for OAuth2
# If running locally, set to 'http', otherwise, set to 'https'
# OAuth can only be run on a secure connection, but secure connections can't be done to localhost
protocolScheme = 'https'

# SMS messaging service to a phone number from the server
def send(text, to):
    # Creates Twilio client process with TWILIOSID and TWILIOAUTH environment variables
    client = Client(os.getenv("TWILIOSID"), os.getenv("TWILIOAUTH"))
    
    # Sends message with body text, from phone number registered under account
    message = client.messages.create(
            body = text,
            from_='+18449612701',
            to='+1'+str(to)
        )

# POST request from Twilio to server
@app.route("/sms", methods=['POST'])
def sms_reply():
    # Gets phone number of messenger
    number = request.form['From'] 

    # Messenging service for Twilio
    resp = MessagingResponse()    
    
    # Checks if number doesn't corresponds to the US/Canada phone standard
    if len(number) != 12 or number[0:2] != "+1":
        # Currently on US/Canada is supported with this service
        resp.message("OfficeConnected: Sorry, the country where you're messaging from is currently unsupported")
    else:
        # Removes international code
        number = number[2:]

        # Gets data regarding user from database by searching their phone number
        userData = sql.fetchPhone(number).fetchone()

        # Checks if user doesn't exists in the database
        if not userData:
            resp.message("OfficeConnected: Your phone number is currently not saved on our database, please visit https://officeconnect.azurewebsites.net to connect your phone")
        else:
            # Retrieves email of the user to easily update information regarding the user
            email = userData[3]

            # Checks if refresh token hasn't been already flagged as invalid
            if userData[0]:
                # Tries to acquire access token of user and checks if token is still valid
                try:
                    token = _build_msal_app().acquire_token_by_refresh_token(refresh_token=userData[0], scopes=app_config.SCOPE)['access_token']
                except:
                    # Creates token with error
                    token = {
                        'error' : 'failed to get token'
                    }
                
                # Checks if there's an error in token and tells user that there's an error
                if "error" in token:
                    resp.message("OfficeConnected: Your login credentials have expired, please relogin to refresh credentials at https://officeconnected.azurewebsites.net")
                    sql.updateVal(email, 'Token', None)
                else:

                    # Gets message from the user
                    message = request.form['Body']

                    # Checks if the user hasn't verified their number
                    if not userData[5]:
                        # Checks if the user is wishing to verify their number with the command 'LINK'
                        if message.upper() == 'LINK':
                            # Creates verification code, replies verification code to user, and updates verification code on the database
                            verificationCode = str("".join(random.choice(string.ascii_letters + string.digits) for i in range(6)))
                            resp.message("OfficeConnected: Your verification code is %s" % verificationCode)
                            sql.updateVal(email, 'VerificationCode', verificationCode)

                        # Checks if the user wishes to unlink their phone number
                        elif message.upper() == 'UNLINK':
                            # Responds confirming that phone number has been removed from the database and removing the phone number from the database
                            resp.message("OfficeConnected: Alright, your phone has been removed from our database")
                            sql.updateVal(email, 'PhoneNumber', None)
                        else:
                            # Gives an error that their phone number is not verified
                            resp.message("OfficeConnected: You're phone number is currently unverified on our system. Please verify your phone number by responding with 'LINK' and entering your code at our website https://officeconnected.azurewebsites.net 1/2")
                            resp.message("If you wish to remove your phone number from our database, reply with 'UNLINK'")
                    else:
                        # Commands to the SMS service

                        # Variable for storing if the user wishes to allow email over SMS
                        emailOverSMS = userData[4]

                        # Command for cancelling a continuing command
                        if message.upper() == 'CANCELCMD':
                            # Checks if the user actually intialized a continuing command and cancels the command
                            if userData[7]:
                                resp.message("OfficeConmnected: Alright, your recent command has been cancelled")
                                sql.updateVal(email, 'ContinuedCommand', None)
                            else:
                                # Gives an error that the user didn't intialize a command
                                resp.message("OfficeConnected: You have no active continuing commands to cancel.")

                        # Continuing commands
                        # Checks if the user has intialized continuing commands
                        elif userData[7]:
                            # Checks if the user wishes to send a message to Teams and has already intialized the command
                            if userData[7] == 'MESSAGE':
                                # Makes a GET request via Microsoft Graphs API to get information regarding the teams that the user has joined 
                                teamsData = requests.get(
                                    app_config.ENDPOINT + '/me/joinedTeams',
                                    headers={'Authorization': 'Bearer ' + token},
                                    ).json()

                                # Stores the ID of the team, unless the selected team is invalid in which it remains None
                                teamID = None

                                # Searches through all the teams that the user has joined, and checks if the user selected one their teams they've joined
                                # and updates teamID to the ID of the selected team
                                for teams in teamsData['value']:
                                    if message == teams['displayName']:
                                        teamID = teams['id']
                                        break

                                # If the user has selected a valid team
                                if teamID:
                                    # Array for storing names of all the channels of the respective team
                                    channelNames = []

                                    # Makes a GET request via Microsoft Graphs API to get information regarding the channels in the team that was selected
                                    channelsData = requests.get(
                                        app_config.ENDPOINT + '/teams/' + teamID + '/channels',
                                        headers={'Authorization': 'Bearer ' + token},
                                        ).json()

                                    # Gets all the names of the channels and combines them into a joined string
                                    for channels in channelsData['value']:
                                        channelNames.append(channels['displayName'])
                                    stringOfNames = ", ".join(channelNames)

                                    # Replies with a list of channels to select from
                                    resp.message("OfficeConnected: Select one of the channels of %s: %s" % (message, stringOfNames))

                                    # Updates ContinuedCommand with the selected team ID
                                    sql.updateVal(email, 'ContinuedCommand', 'TEAM%s' % teamID)
                                else:
                                    # User has selected an invalid team and an error is sent to the user
                                    resp.message("OfficeConnected: That team name is invalid. Make sure it's correctly spelt (case sensetive). If you wish to cancel this command, reply with 'CANCELCMD'")

                            # User wishes to send a message to Teams and has already selected a team
                            elif userData[7][:4] == 'TEAM':
                                # Gets the team ID from the data stored about the continued command on the database
                                command = userData[7]
                                teamID = command[4:]

                                # Makes a GET request via Microsoft Graphs API to get information regarding the channels in the team that was selected
                                channelsData = requests.get(
                                    app_config.ENDPOINT + '/teams/' + teamID + '/channels',
                                    headers={'Authorization': 'Bearer ' + token},
                                    ).json()

                                # Stores the ID of the channel, unless the selected team is invalid in which it remains None
                                channelID = None

                                # Searches through all the channels in the team selected and makes sure that the channel is valid
                                # as well as update the channel ID value to the selected value
                                for channels in channelsData['value']:
                                    if message == channels['displayName']:
                                        channelID = channels['id']
                                        break
                                    
                                # If the channel selected is valid
                                if channelID:
                                    # Asks the user for the intended message and updates the continued command on the database with the channel ID
                                    resp.message("OfficeConnected: Type your message")
                                    sql.updateVal(email, 'ContinuedCommand', 'CHANNEL%s"%s' % (channelID, command))
                                else:
                                    # User has selected an invalid channel and an error is sent to the user
                                    resp.message("OfficeConnected: That channel name is invalid. Make sure it's correctly spelt (case sensetive). If you wish to cancel this command, reply with 'CANCELCMD'")

                            # User wishes to send a message to Teams and a channel and team has already been selected
                            elif userData[7][:7] == "CHANNEL":
                                # Gets the team ID and channel ID from the stored command information on the database
                                command = userData[7]
                                channelID = command[7 : command.find('"')]
                                teamID = command[command.find('"') + 5 :]

                                # Makes a POST request via Microsoft Graphs API with the message to the proper channel and team on Teams
                                messagePost = requests.post(
                                    app_config.ENDPOINT + '/teams/' + teamID + '/channels/' + channelID + '/messages',
                                    headers={'Authorization': 'Bearer ' + token},
                                    json={
                                        "body" : {
                                            "content" : message
                                        }
                                    }
                                ).json()

                                # Checks if the POST request failed
                                if 'error' in messagePost:
                                    # Tells the user that the POST request wasn't able to send the message
                                    resp.message("OfficeConnected: We're sorry, we weren't able to send the message.")
                                    resp.message("Please type your message, or if you'd like to cancel this command, reply with 'CANCELCMD'")
                                else:
                                    # Tells the user that the message has been sent and that the continuing command has been cleared from the database
                                    resp.message("OfficeConnected: Alright, message sent.")
                                    sql.updateVal(email, 'ContinuedCommand', None)
                            
                            # User wishes to send an email and has already intialized command
                            elif userData[7] == 'EMAIL':
                                # Responds confirming choice and asking for subject of the email
                                resp.message("OfficeConnected: Alright, what is the subject of the email?")
                                
                                # Updates continuing command to include email of receiver
                                sql.updateVal(email, 'ContinuedCommand', 'TO%s' % message)
                            
                            # User wishes to send an email and has already selected an email to send to and selecting a subject
                            elif userData[7][:2] == 'TO':
                                # Detect if unsupported character in subject name (using ~ to seperate subject with email)
                                if "~" in message:
                                    resp.message("OfficeConnected: Unfortunately, we're unable to support the character '~' over SMS, please retype your subject line and try again")
                                else:
                                    # Responds confirming subject and asking for the body of email
                                    resp.message("OfficeConnected: Alright, what would you like included in your email?")

                                    # Updates continuing command to include subject of email
                                    sql.updateVal(email, 'ContinuedCommand', 'SUBJECT%s~%s' % (message, userData[7]))
                            
                            # Users wishes to send an email and everything is already set to send email
                            elif userData[7][:7] == 'SUBJECT':
                                # Gets the subject of email and who the email is being sent to
                                subject = userData[7][7:userData[7].find("~")]
                                toEmail = userData[7][userData[7].find("~") + 3 :]

                                # Makes a POST request to the email with all the information
                                emailPost = requests.post(
                                    app_config.ENDPOINT + '/me/sendMail',
                                    headers={'Authorization': 'Bearer ' + token},
                                    json={
                                        "message": {
                                            "subject": subject,
                                            "body": {
                                                "contentType": "Text",
                                                "content": message
                                            },
                                            "toRecipients": [
                                                {
                                                    "emailAddress": {
                                                        "address": toEmail
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                )

                                # Checks if the HTTP request was successful, or else outputs an error
                                if emailPost.status_code == 202:
                                    resp.message("OfficeConnected: Alright, email sent.")
                                else:
                                    resp.message("OfficeConnected: We're sorry, we weren't able to send your email. Please try again")

                                # Tells database to erase ContinuedCommand
                                sql.updateVal(email, 'ContinuedCommand', None)

                        # Command to intialize continuing command regarding sending a message to Microsoft Teams
                        elif message.upper() == 'MESSAGE':
                            # Array for storing names of joined teams
                            teamNames = []

                            # Makes a GET request via Microsoft Graphs API getting the information regarding the joined teams of the user
                            teamsData = requests.get(
                                app_config.ENDPOINT + '/me/joinedTeams',
                                headers={'Authorization': 'Bearer ' + token},
                                ).json()

                            # Makes a string full of the names of the joined teams
                            for teams in teamsData['value']:
                                teamNames.append(teams['displayName'])
                            stringOfNames = ", ".join(teamNames)

                            # Replies to the user with the list of teams to select
                            resp.message("OfficeConnected: Select one of your teams to message: %s" % stringOfNames)

                            # Updates the database that the user intends to have a continuing command
                            sql.updateVal(email, 'ContinuedCommand', 'MESSAGE')

                        # Command to intialize continuing command regarding sending an email
                        elif message.upper() == 'EMAIL':
                            if emailOverSMS:
                                sql.updateVal(email, 'ContinuedCommand', 'EMAIL')
                                resp.message("OfficeConnected: Who would you like to email?")
                            else:
                                resp.message("OfficeConnected: You have disabled email over SMS. To enable this command, visit https://officeconnect.azurewebsites.net and enable email over SMS")

                        # Error message to the user trying to link phone despite having phone already linked to their account
                        elif message.upper() == 'LINK':
                            resp.message("OfficeConnected: You already have your phone number linked, no need to link it again. If you wish to unlink your phone, reply with 'UNLINK'.")

                        # Command to unlink their phone from their account, with message confirming the removal as well as removal of data from the database
                        elif message.upper() == 'UNLINK':
                            resp.message("OfficeConnected: Alright, your phone has been unlinked from your account. To delete your account, please login at https://officeconnected.azurewebsites.net and hit 'Delete Account'")
                            sql.updateVal(email, 'PhoneNumber', None)
                            sql.updateVal(email, 'VerifiedPhone', False)
                            sql.updateVal(email, 'VerificationCode', None)

                        # Tells the user a list of commands
                        elif message.upper() == 'CMD':
                            resp.message("OfficeConnected: 'UNLINK' to unlink your phone number from your account, 'EMAIL' to send emails, 'MESSAGE' to send a message to Teams")
                            resp.message("'CANCELCMD' to cancel a continuing command. For more help, visit https://officeconnected.azurewebsites.net")

                        # User inputted an invalid command and error is spit out
                        else:
                            resp.message("OfficeConnected: Your command is not recognized by our system. Make sure you've typed it correctly or to find a list of commands, reply with 'CMD'")
            else:
                # If refresh token has already been flagged as invalid, reminds user token is invalid
                resp.message("OfficeConnected: Your login credentials have expired, please relogin to refresh credentials at https://officeconnected.azurewebsites.net")

    # Returns server response to the user
    return str(resp)

# Actual website that the user will see at "/"
@app.route("/", methods=['POST', 'GET'])
def index():

    # Bootstrap alerts and errors that will popup on the top of the screen
    alerts = []
    errors = []

    # Arguments being passed through to the html page
    htmlArguments = {}

    # Checks if an error is detected in the HTML arguments (generally the text after '?' in the domain) and adds the information to the Bootstrap errors
    if 'error' in request.args:
        errors.append({
            'error' : request.args['error'],
            'error_description' : request.args['error_description']
        })

    # Checks if the user isn't logged in locally
    if not session.get("user"):
        # Creates a state for the session for the user
        session["state"] = str(uuid.uuid4())

        # Creates the OAuth2 redirect URL for the user to be logged into, which is passed through into the html arguments
        auth_url = _build_auth_url(scopes=app_config.SCOPE, state=session["state"])
        htmlArguments['auth_url'] = auth_url
    else:
        # Gets email of the user, and looks up user in the database
        emailOfUser = session["user"]["preferred_username"]
        databaseInfo = sql.fetch(emailOfUser).fetchone()

        # if user is not found in database or invalid refresh token
        if not databaseInfo or not databaseInfo[0]:
            # logs out user
            return redirect(url_for("logout"))

        # Checks if user requires SMS verification, by searching if user has phone number saved, but not verified
        requireSMSVerification = databaseInfo[1] and not databaseInfo[5]
        # Checks if the user wishes to receive Microsoft Teams notifications
        getTeamsNotifications = databaseInfo[2]
        # Checks if the user wishes to send and receive emails over SMS
        emailOverSMS = databaseInfo[4]

        # Prefills phone number on HTML form if phone number is already in the database
        if databaseInfo[1]:
            htmlArguments['prefilledPhoneNumber'] = databaseInfo[1]
        else:
            htmlArguments['prefilledPhoneNumber'] = ""

        # Checks if the user has made a POST request
        if request.method == 'POST':
            # Checks if the user pressed the update button
            if 'updateButton' in request.form:
                # Gets the phone number from the form
                phoneNumber = request.form['phoneNumber']

                # Gets the verification code from the form if required
                if requireSMSVerification:
                    verificationCodeFromUser = request.form['smsVerificationCode']

                    # Checks if user attempted entering a verification code
                    if verificationCodeFromUser:
                        # Clears verification code and sets phone as verified if verified code is correct
                        if verificationCodeFromUser == databaseInfo[6]:
                            sql.updateVal(emailOfUser, 'VerifiedPhone', True)
                            sql.updateVal(emailOfUser, 'VerificationCode', None)

                            requireSMSVerification = False

                            send("OfficeConnected: You have successfully connected your phone! Reply with 'CMD' to get a full list of commands you can do with OfficeConnected", databaseInfo[1])
                        else:
                            # Tells user that verification code is wrong through Bootstrap
                            errors.append({
                                "error" : "Invalid SMS verification code",
                                "error_description" : "You have entered an invalid verification code, make sure you've typed the right characters. If you would like a new verification code, you can reply 'LINK' to the SMS message"
                            })
                
                # Checks if user is trying to update phone the phone number to a different one from database
                if databaseInfo[1] != phoneNumber and phoneNumber:
                    # Checks if updated phone number already exists in the database and tells user error through Bootstrap
                    if sql.fetchPhone(phoneNumber).fetchone():
                        errors.append({
                            "error" : "Phone number already exists",
                            "error_description" : "An account with that phone number already exists in our database, please enter a valid phone number, or to unlink that number, text 'UNLINK' to +1 (844)-961-2701"
                        })
                    else:
                        # Updates unverified phone number in database
                        sql.updateVal(emailOfUser, 'PhoneNumber', phoneNumber)
                        sql.updateVal(emailOfUser, 'VerifiedPhone', False)
                        sql.updateVal(emailOfUser, 'VerificationCode', None)

                        # Replace html argument to updated phone number
                        htmlArguments['prefilledPhoneNumber'] = phoneNumber
                        
                        requireSMSVerification = True

                        # Notifying user over text and Bootstrap alert to verify phone number
                        send("OfficeConnected: Verify your phone by responding with the message 'LINK' to receive your verification code", phoneNumber)
                        alerts.append("A message has been sent to your phone. Please verify your phone by responding with the message 'LINK' and entering your verification code")

                # Updates if the user wants to get Teams notifications based on if the getTeamsNotification checkbox is checked in HTML
                if 'getTeamsNotifications' in request.form and request.form['getTeamsNotifications'] == 'on':
                    getTeamsNotifications = True
                    sql.updateVal(emailOfUser, 'GetSMSTeamNotifications', True)
                else:
                    getTeamsNotifications = False
                    sql.updateVal(emailOfUser, 'GetSMSTeamNotifications', False)
                
                # Updates if the user wants to allow email over SMS based on if the emailOverSMS checkbox is checked in HTML
                if 'emailOverSMS' in request.form and request.form['emailOverSMS'] == 'on':
                    emailOverSMS = True
                    sql.updateVal(emailOfUser, 'EmailOverSMS', True)
                else:
                    emailOverSMS = False
                    sql.updateVal(emailOfUser, 'EmailOverSMS', False)
            
            # Checks if the deleteAccount button has been pressed, and clears user from database
            elif 'deleteAccount' in request.form:
                sql.delete(emailOfUser)
                return redirect(url_for("logout"))

        # sets respective HTML arguments to their variables on Python to be passed through in Flask
        htmlArguments['getTeamsNotificationsBool'] = getTeamsNotifications
        htmlArguments['emailOverSMSBool'] = emailOverSMS
        htmlArguments['requireSMSVerification'] = requireSMSVerification
        
        # Passes through basic user info to Flask
        htmlArguments['user'] = session['user']

    # Passes through Bootstrap alerts and errors to HTML
    htmlArguments['errors'] = errors
    htmlArguments['alerts'] = alerts

    # Renders the HTML, with htmlArguments as it's arguments
    return render_template('home.html', **htmlArguments)

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
   

# Function that goes through the database to update and send data to the user
def accessDatabase():
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

            # Setting up 1/2 sec delay to allow small gaps for SQL input
            time.sleep(0.5)
        except:
            pass
        
# Redirect from OAuth2 login
@app.route(app_config.REDIRECT_PATH)
def authorized():
    # Checks if the state has been changed from the login and redirects back to the index page
    if request.args.get('state') != session.get("state"):
        return redirect(url_for("index", error="Login failed", error_description="Login has failed, please try again"))

    # Error in the authentication/authorization (such as cancelling approval of allowing permissions) and redirect back with error
    if "error" in request.args:
        return redirect(url_for("index", **request.args))
    
    # If login was somewhat successfuly
    if request.args.get('code'):
        # Gets cached data
        cache = _load_cache()

        # Gets token of user
        result = _build_msal_app(cache=cache).acquire_token_by_authorization_code(
            request.args['code'],
            scopes=app_config.SCOPE,
            redirect_uri=url_for("authorized", _external=True, _scheme=protocolScheme))
        
        # Checks if token is invalid and redirects back to index with error
        if "error" in result:
            return redirect(url_for("index", **request.args))
        
        # Saves token into session and cache
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)

    # Inserts user information into SQL database
    sql.insert(_get_token_from_cache(app_config.SCOPE)['refresh_token'], session["user"]["preferred_username"])
    
    # Redirects user back to index
    return redirect(url_for("index"))

# User log out (clears data locally)
@app.route("/logout")
def logout():
    # Wipes token and user data from session
    session.clear()

    # Redirects user back to index
    return redirect(url_for("index"))

# Microsoft Authentication Library (MSAL) functions

# Loads data from cache
def _load_cache():
    # Serialization token cache object for MSAL
    cache = msal.SerializableTokenCache()

    # Checks if token cache is stored in session and deserializes token cache and returns the cache
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache

# Saves cache (if changed)
def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()

# Creates MSAL app object (with AAD App info)
def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        app_config.CLIENT_ID, authority=authority or app_config.AUTHORITY,
        client_credential=app_config.CLIENT_SECRET, token_cache=cache)

# Creates url that the user logins into for OAuth
def _build_auth_url(authority=None, scopes=None, state=None):
    return _build_msal_app(authority=authority).get_authorization_request_url(
        scopes or [],
        state=state or str(uuid.uuid4()),
        redirect_uri=url_for("authorized", _external=True, _scheme=protocolScheme))

# Gets token from cache
def _get_token_from_cache(scope=None):
    # Gets cache
    cache = _load_cache()

    # Gets MSAL app
    cca = _build_msal_app(cache=cache)

    # Gets list of accounts logged in
    accounts = cca.get_accounts()

    # So all account(s) belong to the current signed-in user
    if accounts:
        # Getting token with refresh token and saving to cache
        result = cca.acquire_token_silent(scope, account=accounts[0], force_refresh=True)
        _save_cache(cache)
        return result

# New thread for constantly checking for database
accessDatabaseThread = threading.Thread(target=accessDatabase)
accessDatabaseThread.start()

# Starts Flask server
if __name__ == "__main__":
    app.run()

