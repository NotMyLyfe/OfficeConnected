import os
from twilio.rest import Client

sid = os.getenv("TWILIOSID")
auth = os.getenv("TWILIOAUTH")
serviceSid=os.getenv("TWILIOMESSAGESID")
client = Client(sid, auth)

def send(text, to):
    global client, auth, serviceSid
    message = client.messages.create(
            body = text,
            messaging_service_sid=serviceSid,
            to='+1'+str(to)
        )
