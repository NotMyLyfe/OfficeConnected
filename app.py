import uuid
import requests
from flask import Flask, render_template, session, request, redirect, url_for
from flask_session import Session
import msal
import app_config
import pyodbc
from sql import *

app = Flask(__name__)
app.config.from_object(app_config)
Session(app)

testing = False # Set to True if running a local Flask server, if deploying to Azure, set to False
# LEAVING THIS FALSE IN AZURE OR TRUE IN LOCAL FLASK RESULTS IN AN ERROR, OAUTH REQUIRES HTTPS, EXCEPT LOCALLY (Learnt that the hard way bashing my head against the keyboard for 3 hours)

if testing:
    protocolScheme = 'http'
else:
    protocolScheme = 'https'


@app.route("/")
def index():
    if not session.get("user"):
        session["state"] = str(uuid.uuid4())
        auth_url = _build_auth_url(scopes=app_config.SCOPE, state=session["state"])
        return render_template('home.html', auth_url=auth_url)
    return render_template('home.html', user=session["user"])

@app.route(app_config.REDIRECT_PATH)  # Its absolute URL must match your app's redirect_uri set in AAD
def authorized():
    if request.args.get('state') != session.get("state"):
        return redirect(url_for("index"))  # No-OP. Goes back to Index page
    if "error" in request.args:  # Authentication/Authorization failure
        session["state"] = str(uuid.uuid4())
        auth_url = _build_auth_url(scopes=app_config.SCOPE, state=session["state"])
        return render_template("home.html", errors=request.args, auth_url=auth_url)
    if request.args.get('code'):
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_authorization_code(
            request.args['code'],
            scopes=app_config.SCOPE,  # Misspelled scope would cause an HTTP 400 error here
            redirect_uri=url_for("authorized", _external=True, _scheme=protocolScheme))
        if "error" in result:
            session["state"] = str(uuid.uuid4())
            auth_url = _build_auth_url(scopes=app_config.SCOPE, state=session["state"])
            return render_template("home.html", errors=result, auth_url=auth_url)
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()  # Wipe out user and its token cache from session
    return redirect(  # Also logout from your tenant's web session
        app_config.AUTHORITY + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True))

@app.route("/graphcall")
def graphcall():
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))
    graph_data = requests.get(  # Use token to call downstream service
        app_config.ENDPOINT + '/me/joinedTeams',
        headers={'Authorization': 'Bearer ' + token['access_token']},
        ).json()
    
    for i in graph_data['value']:
        print(i['id'])

    return render_template('display.html', result=graph_data)


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
        result = cca.acquire_token_silent(scope, account=accounts[0])
        _save_cache(cache)
        return result

app.jinja_env.globals.update(_build_auth_url=_build_auth_url)  # Used in template

if __name__ == "__main__":
    app.run()

