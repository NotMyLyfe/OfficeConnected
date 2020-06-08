from twilio.rest import Client
import os

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