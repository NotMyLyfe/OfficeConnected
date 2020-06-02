import pyodbc
import os

cursor = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=officeconnected.database.windows.net;'
    'PORT=1433;'
    'DATABASE=OfficeConnected;'
    'UID=OfficeConnected;'
    'PWD='+os.getenv('SQL_PASSWORD')
).cursor()

insert_query = '''INSERT INTO userData (Token, PhoneNumber, GetSMSTeamNotifications, Email, EmailOverSMS, VerifiedPhone, VerificationCode) VALUES (?, ?, ?, ?, ?, ?, ?);'''
read_query = '''SELECT * FROM userData;'''
readSpecific_query = '''SELECT * FROM userData WHERE Email LIKE ?;'''
readSpecific_queryPhone = '''SELECT * FROM userData WHERE PhoneNumber = ?;'''
update = {
    'Token' : '''UPDATE userData SET Token = ? WHERE Email LIKE ?;''',
    'PhoneNumber' : '''UPDATE userData SET PhoneNumber = ? WHERE Email LIKE ?;''',
    'GetSMSTeamNotifications' : '''UPDATE userData SET GetSMSTeamNotifications = ? WHERE Email LIKE ?;''',
    'EmailOverSMS' : '''UPDATE userData SET EmailOverSMS = ? WHERE Email LIKE ?;''',
    'VerifiedPhone' : '''UPDATE userData SET VerifiedPhone = ? WHERE Email LIKE ?;''',
    'VerificationCode' : '''UPDATE userData SET VerificationCode = ? WHERE Email LIKE ?;'''
}

delete_query = '''DELETE FROM userData WHERE Email LIKE ?;'''

def updateVal(Email, column, value):
    cursor.execute(update[column], (value, Email))
    cursor.commit()

def insert(Token, Email):
    if not fetch(Email).fetchone():
        cursor.execute(insert_query, (Token, None, False, Email, False, False, None))
        cursor.commit()
    else: updateVal(Email, 'Token', Token)

# Not needed as of this moment, update and implement if needed
# 'all' : ''' UPDATE userData SET Token = ?, PhoneNumber = ?, GetSMSTeamNotifications = ?, EmailOverSMS = ? WHERE Email LIKE ?;'''

def fetch(Email):
    return cursor.execute(readSpecific_query, (Email))

def fetchPhone(PhoneNumber):
    return cursor.execute(readSpecific_queryPhone, (PhoneNumber))

def getAll():
    return cursor.execute(read_query)

def delete(Email):
    if fetch(Email).fetchone():
        cursor.execute(delete_query, Email)
        cursor.commit()
        return True
    return False