import os

CLIENT_SECRET = os.getenv("CLIENT_SECRET")
if not CLIENT_SECRET:
    raise ValueError("Need to define CLIENT_SECRET environment variable")

AUTHORITY = "https://login.microsoftonline.com/organizations"  # For multi-tenant app
# AUTHORITY = "https://login.microsoftonline.com/Enter_the_Tenant_Name_Here"

CLIENT_ID = "0d1fbbd3-699d-4f2a-8670-5c2ea4683074"

REDIRECT_PATH = "/getAToken"  # It will be used to form an absolute URL
    # And that absolute URL must match your app's redirect_uri set in AAD

# You can find more Microsoft Graph API endpoints from Graph Explorer
# https://developer.microsoft.com/en-us/graph/graph-explorer
ENDPOINT = 'https://graph.microsoft.com/beta'

# You can find the proper permission names from this document
# https://docs.microsoft.com/en-us/graph/permissions-reference
SCOPE = ["User.ReadBasic.All", "User.Read.All", "Calendars.ReadWrite", "Files.ReadWrite.All", "Mail.ReadWrite", "Mail.Send", "People.Read.All", "Group.Read.All", "Group.ReadWrite.All"]

SESSION_TYPE = "filesystem"  # So token cache will be stored in server-side session

