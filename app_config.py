# app_config.py
# Gordon Lin and Evan Lu
# Configuration file for app.py with data about OAuth and Flask
import os

# Gets the CLIENT SECRET of Azure Active Directory (AAD) App (for OAuth)
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Authority for AAD App (OAuth) login
AUTHORITY = "https://login.microsoftonline.com/organizations"

# Client Secret for AAD App (OAuth) login
CLIENT_ID = os.getenv("CLIENT_ID")

# OAuth redirect path after being logged in
REDIRECT_PATH = "/getAToken"

# Microsoft Graphs API endpoint
ENDPOINT = 'https://graph.microsoft.com/beta'

# Scopes (permissions) to access Microsoft Graphs API
SCOPE = ["User.ReadBasic.All", "User.Read.All", "Calendars.ReadWrite", "Files.ReadWrite.All", "Mail.ReadWrite", "Mail.Send", "People.Read.All", "Group.Read.All", "Group.ReadWrite.All"]

# Setting token cache to be stored in sever-side session
SESSION_TYPE = "filesystem"

