import pyodbc
import os

connection = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=officeconnected.database.windows.net;'
    'PORT=1433;'
    'DATABASE=OfficeConnected;'
    'UID=OfficeConnected;'
    'PWD='+os.getenv('SQL_PASSWORD')
)

cursor = connection.cursor()
rcursor = connection.cursor()

insert_query = '''SET NOCOUNT ON; INSERT INTO userData (Token, PhoneNumber, GetSMSTeamNotifications, Email, EmailOverSMS, VerifiedPhone, VerificationCode, ContinuedCommand) VALUES (?, ?, ?, ?, ?, ?, ?, ?);'''
read_query = '''SET NOCOUNT ON; SELECT * FROM userData;'''
readSpecific_query = '''SET NOCOUNT ON; SELECT * FROM userData WHERE Email LIKE ?;'''
readSpecific_queryPhone = '''SET NOCOUNT ON; SELECT * FROM userData WHERE PhoneNumber = ?;'''
update = {
    'Token' : '''SET NOCOUNT ON; UPDATE userData SET Token = ? WHERE Email LIKE ?;''',
    'PhoneNumber' : '''SET NOCOUNT ON; UPDATE userData SET PhoneNumber = ? WHERE Email LIKE ?;''',
    'GetSMSTeamNotifications' : '''SET NOCOUNT ON; UPDATE userData SET GetSMSTeamNotifications = ? WHERE Email LIKE ?;''',
    'EmailOverSMS' : '''SET NOCOUNT ON; UPDATE userData SET EmailOverSMS = ? WHERE Email LIKE ?;''',
    'VerifiedPhone' : '''SET NOCOUNT ON; UPDATE userData SET VerifiedPhone = ? WHERE Email LIKE ?;''',
    'VerificationCode' : '''SET NOCOUNT ON; UPDATE userData SET VerificationCode = ? WHERE Email LIKE ?;''',
    'ContinuedCommand' : '''SET NOCOUNT ON; UPDATE userData SET ContinuedCommand = ? WHERE Email LIKE ?;'''
}

delete_query = '''SET NOCOUNT ON; DELETE FROM userData WHERE Email LIKE ?;'''

def updateVal(Email, column, value):
    cursor.execute(update[column], (value, Email))
    cursor.commit()

def insert(Token, Email):
    if not fetch(Email).fetchone():
        cursor.execute(insert_query, (Token, None, False, Email, False, False, None, None))
        cursor.commit()
    else: updateVal(Email, 'Token', Token)

def fetch(Email):
    return rcursor.execute(readSpecific_query, (Email))

def fetchPhone(PhoneNumber):
    return rcursor.execute(readSpecific_queryPhone, (PhoneNumber))

def getAll():
    return rcursor.execute(read_query)

def delete(Email):
    if fetch(Email).fetchone():
        cursor.execute(delete_query, Email)
        cursor.commit()