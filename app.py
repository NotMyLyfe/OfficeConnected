# app.py
# Gordon Lin and Evan Lu
# 

import uuid, requests, msal, app_config, pyodbc, sql, multiprocessing, os, random, string
from flask import Flask, render_template, session, request, redirect, url_for
from flask_session import Session
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

# Creates Flask app and session with config
app = Flask(__name__)
app.config.from_object(app_config)
Session(app)

testing = False     # Set to True if running a local Flask server, if deploying to Azure, set to False
# INPUTTING THE WRONG VALUE WILL CAUSE OAUTH2 TO RUN INTO AN ERROR
# If encountering error AADSTS50011, change the value to opposite value

# Changes protocol scheme based on if running on localhost or not, since OAuth2 requires HTTPS, except when running it locally, as you can't create an HTTPS request to localhost
if testing:
    protocolScheme = 'http' 
else:
    protocolScheme = 'https'

# Messaging service for Twilio
def send(text, to):
    client = Client(os.getenv("TWILIOSID"), os.getenv("TWILIOAUTH")) # Creates Twilio client process with TWILIOSID and TWILIOAUTH environment variables
    # Sends message with body text, from phone number registered under shared account
    message = client.messages.create(
            body = text,
            from_='+18449612701',
            to='+1'+str(to)
        )

@app.route("/sms", methods=['POST'])     # Webhook request from Twilio to server (if a message via SMS is received from user)
def sms_reply():
    number = request.form['From']     # Gets phone number of user
    resp = MessagingResponse()     # creates MessageResponse object
    
    if len(number) != 12 or number[0:2] != "+1": # Checks if phone number is from a North American number
        resp.message("OfficeConnected: Sorry, the country where you're messaging from is currently unsupported")
    else:
        number = number[2:]     # Removes international code
        data = sql.fetchPhone(number).fetchone()     # Finds data of user in the database

        if not data:     # if user doesn't exist or is not linked
            resp.message("OfficeConnected: Your phone number is currently not saved on our database, please visit https://officeconnect.azurewebsites.net to connect your phone")
        else:     # if user does exist and is linked
            token = _build_msal_app().acquire_token_by_refresh_token(refresh_token=data[0], scopes=app_config.SCOPE)
            email = data[3]
            if "error" in token:
                resp.message("OfficeConnected: Your login credentials have expired, please relogin to refresh credentials at https://officeconnected.azurewebsites.net")
            else:
                message_body = request.form['Body']     # Gets SMS message from user
                if not data[5]:
                    if message_body.upper() == 'LINK':
                        verificationCode = str("".join(random.choice(string.ascii_letters + string.digits) for i in range(6)))
                        resp.message("OfficeConnected: Your verification code is %s" % verificationCode)
                        sql.updateVal(email, 'VerificationCode', verificationCode)
                    else:
                        resp.message("OfficeConnected: You're phone number is currently unverified on our system. Please verify your phone number by responding with 'LINK' and entering your code at our website https://officeconnected.azurewebsites.net")
                else:
                    if message_body.upper() == 'CANCELCMD':
                        if data[6]:
                            resp.message("OfficeConmnected: Alright, your recent command has been cancelled")
                            sql.updateVal(email, 'ContinuedCommand', None)
                        else:
                            resp.message("OfficeConnected: You have no active continuing commands to cancel.")
                    elif message_body.upper() == 'LINK':
                        resp.message("OfficeConnected: You already have your phone number linked, no need to link it again. If you wish to unlink your phone, reply with 'UNLINK'.")
                    elif message_body.upper() == 'UNLINK':
                        resp.message("OfficeConnected: Alright, your phone has been unlinked from your account. To delete your account, please login at https://officeconnected.azurewebsites.net and hit 'Delete Account'")
                        sql.updateVal(email, 'PhoneNumber', None)
                        sql.updateVal(email, 'VerifiedPhone', False)
                        sql.updateVal(email, 'VerificationCode', None)
                    elif message_body.upper() == 'CMD':
                        print("List of commands here....")
                        #resp.message()
                    else:
                        resp.message("OfficeConnected: Your command is not recognized by our system. Make sure you've typed it correctly or to find a list of commands, reply with 'CMD")
                        
    return str(resp)

# Actual website that the user will see
@app.route("/", methods=['POST', 'GET'])     # Index page, that only accepts POST and GET requests
def index():
    alerts = []     # Any alerts that will show up using Bootstrap
    errors = []

    htmlArguments = {}

    if 'error' in request.args:
        errors.append({
            'error' : request.args['error'],
            'error_description' : request.args['error_description']
        })

    if not session.get("user"): # Checks if login credentials of user are stored in current session
        session["state"] = str(uuid.uuid4()) # Creates the state for OAuth
        auth_url = _build_auth_url(scopes=app_config.SCOPE, state=session["state"]) # Creates the URL to be redirected to and to be authenticated
        htmlArguments['auth_url'] = auth_url
    else:
        emailOfUser = session["user"]["preferred_username"]
        databaseInfo = sql.fetch(emailOfUser).fetchone() # Gets the information regarding the user by searching for their email stored in SQL
        if not databaseInfo:
            session.clear()
            return redirect(url_for("index"))

        requireSMSVerification = databaseInfo[1] and not databaseInfo[5]
        getTeamsNotifcations = databaseInfo[2]
        emailOverSMS = databaseInfo[4]

        if databaseInfo[1]:
            htmlArguments['prefilledPhoneNumber'] = databaseInfo[1]
        else:
            htmlArguments['prefilledPhoneNumber'] = ""

        if request.method == 'POST':
            if 'updateButton' in request.form:
                phoneNumber = request.form['phoneNumber']

                if requireSMSVerification:
                    verificationCodeFromUser = request.form['smsVerificationCode']

                if requireSMSVerification and verificationCodeFromUser:
                    if verificationCodeFromUser == databaseInfo[6]:
                        sql.updateVal(emailOfUser, 'VerifiedPhone', True)
                        sql.updateVal(emailOfUser, 'VerificationCode', None)

                        requireSMSVerification = False

                        send("OfficeConnected: You have successfully connected your phone! Reply with 'CMD' to get a full list of commands you can do with OfficeConnected", databaseInfo[1])
                    else:
                        errors.append({
                            "error" : "Invalid SMS verification code",
                            "error_description" : "You have entered an invalid verification code, make sure you've typed the right characters. If you would like a new verification code, you can reply 'LINK' to the SMS message"
                        })
                    
                if databaseInfo[1] != phoneNumber and phoneNumber:
                    if sql.fetchPhone(phoneNumber).fetchone():
                        errors.append({
                            "error" : "Phone number already exists",
                            "error_description" : "An account with that phone number already exists in our database, please enter a valid phone number, or to unlink that number, text 'UNLINK' to +1 (844)-961-2701"
                        })
                    else:
                        sql.updateVal(emailOfUser, 'PhoneNumber', phoneNumber)
                        sql.updateVal(emailOfUser, 'VerifiedPhone', False)
                        sql.updateVal(emailOfUser, 'VerificationCode', None)

                        htmlArguments['prefilledPhoneNumber'] = phoneNumber
                        
                        requireSMSVerification = True

                        send("OfficeConnected: Verify your phone by responding with the message 'LINK' to receive your verification code", phoneNumber)

                        alerts.append("A message has been sent to your phone. Please verify your phone by responding with the message 'LINK' and entering your verification code")

                if 'getTeamsNotifications' in request.form and request.form['getTeamsNotifications'] == 'on':
                    getTeamsNotifications = True
                    sql.updateVal(emailOfUser, 'GetSMSTeamNotifications', True)
                else:
                    getTeamsNotifications = False
                    sql.updateVal(emailOfUser, 'GetSMSTeamNotifications', False)
                if 'emailOverSMS' in request.form and request.form['emailOverSMS'] == 'on':
                    emailOverSMS = True
                    sql.updateVal(emailOfUser, 'EmailOverSMS', True)
                else:
                    emailOverSMS = False
                    sql.updateVal(emailOfUser, 'EmailOverSMS', False)
                    
            elif 'deleteAccount' in request.form:
                sql.delete(emailOfUser)
                return redirect(url_for("logout"))

        htmlArguments['getTeamsNotificationsBool'] = getTeamsNotifications
        htmlArguments['emailOverSMSBool'] = emailOverSMS

        htmlArguments['requireSMSVerification'] = requireSMSVerification
        htmlArguments['user'] = session['user']

    htmlArguments['errors'] = errors
    htmlArguments['alerts'] = alerts

    return render_template('home.html', **htmlArguments)

# Multiprocessing functions (for running things in the background)
def getTeamMeetings(token):
    teams_data = requests.get(  # Use token to call downstream service
        app_config.ENDPOINT + '/me/joinedTeams',
        headers={'Authorization': 'Bearer ' + token},
        ).json()
    for joinedTeams in teams_data['value']:
        channels_data = requests.get(  # Use token to call downstream service
            app_config.ENDPOINT + '/teams/' + joinedTeams['id'] + '/channels',
            headers={'Authorization': 'Bearer ' + token},
            ).json()
        #print(channels_data)

def getTeamMessages(token):
    teams_data = requests.get(  # Use token to call downstream service
        app_config.ENDPOINT + '/me/joinedTeams',
        headers={'Authorization': 'Bearer ' + token},
        ).json()
    for joinedTeams in teams_data['value']:
        channels_data = requests.get(  # Use token to call downstream service
            app_config.ENDPOINT + '/teams/' + joinedTeams['id'] + '/channels',
            headers={'Authorization': 'Bearer ' + token},
            ).json()
        for channels in channels_data['value']:
            messages_data = requests.get(  # Use token to call downstream service
                app_config.ENDPOINT + '/teams/' + joinedTeams['id'] + '/channels/' + channels['id'] + '/messages',
                headers={'Authorization': 'Bearer ' + token},
                ).json()

def accessDatabase():
    while True:
        data = sql.getAll()
        for rows in data:
            refreshToken = rows[0]
            phoneNumber = rows[1]
            getSMSTeamsNotifications = rows[2]
            
            token = _build_msal_app().acquire_token_by_refresh_token(refresh_token=refreshToken, scopes=app_config.SCOPE)
            if "error" not in token:
                if rows[2]:
                    #getTeamMessages(token['access_token'])
                    getTeamMeetings(token['access_token'])
            else:
                if phoneNumber:
                    send("Your login credentials have expired, please relogin to refresh credentials at https://officeconnected.azurewebsites.net", rows[1])
                sql.delete(rows[3])

@app.route(app_config.REDIRECT_PATH)  # Its absolute URL must match your app's redirect_uri set in AAD
def authorized():
    if request.args.get('state') != session.get("state"):
        return redirect(url_for("index"))  # No-OP. Goes back to Index page
    if "error" in request.args:  # Authentication/Authorization failure
        return redirect(url_for("index", **request.args))
    if request.args.get('code'):
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_authorization_code(
            request.args['code'],
            scopes=app_config.SCOPE,  # Misspelled scope would cause an HTTP 400 error here
            redirect_uri=url_for("authorized", _external=True, _scheme=protocolScheme))
        if "error" in result:
            return redirect(url_for("index", **request.args))
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)

    sql.insert(_get_token_from_cache(app_config.SCOPE)['refresh_token'], session["user"]["preferred_username"])

    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()  # Wipe out user and its token cache from session
    return redirect(url_for("index"))

# Some random Microsoft Authentication Library Stuff (Just don't touch it.... it's very complicated)
def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache

def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()

def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        app_config.CLIENT_ID, authority=authority or app_config.AUTHORITY,
        client_credential=app_config.CLIENT_SECRET, token_cache=cache)

def _build_auth_url(authority=None, scopes=None, state=None):
    return _build_msal_app(authority=authority).get_authorization_request_url(
        scopes or [],
        state=state or str(uuid.uuid4()),
        redirect_uri=url_for("authorized", _external=True, _scheme=protocolScheme))

def _get_token_from_cache(scope=None):
    cache = _load_cache()  # This web app maintains one cache per session
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0], force_refresh=True) # Allowing refresh tokens so we retrieve them in SQL database
        _save_cache(cache)
        return result

app.jinja_env.globals.update(_build_auth_url=_build_auth_url)  # Used in template

if __name__ == "__main__":
    send("Main", os.getenv('testPhoneNumber'))
    accessDatabaseProcess = multiprocessing.Process(target=accessDatabase)
    accessDatabaseProcess.start()
    app.run()
    accessDatabaseProcess.join()
elif __name__ == "app":
    send("App", os.getenv('testPhoneNumber'))
else:
    send(str(__name__), os.getenv('testPhoneNumber'))