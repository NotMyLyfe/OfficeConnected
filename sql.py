import pyodbc
import os

password = os.getenv('SQL_PASSWORD')
cnxn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=officeconnected.database.windows.net;'
    'PORT=1433;'
    'DATABASE=OfficeConnected;'
    'UID=OfficeConnected;'
    'PWD='+password
)

cursor = cnxn.cursor()

insert_query = '''INSERT INTO userData (Token, PhoneNumber, GetSMSTeamNotifications, Email) VALUES (?, ?, ?, ?);'''
read_query = '''SELECT * FROM userData;'''
readSpecific_query = '''SELECT * FROM userData WHERE Email LIKE ?;'''
update = {
    'Token' : '''UPDATE userData SET Token = ? WHERE Email LIKE ?;''',
    'PhoneNumber' : '''UPDATE userData SET PhoneNumber = ? WHERE Email LIKE ?;''',
    'GetSMSTeamNotifications' : '''UPDATE userData SET GetSMSTeamNotifications = ? WHERE Email LIKE ?;''',
    'all' : ''' UPDATE userData SET Token = ?, PhoneNumber = ?, GetSMSTeamNotifications = ? WHERE Email LIKE ?;'''
}

delete_query = '''DELETE FROM userData WHERE Email LIKE ?;'''


def insert(Token, PhoneNumber, GetSMSTeamNotifications, Email):
    cursor.execute(readSpecific_query, (Email))
    if not cursor.fetchone():
        cursor.execute(insert_query, (Token, PhoneNumber, GetSMSTeamNotifications, Email))
        cursor.commit()

def updateAll(Token, PhoneNumber, GetSMSTeamNotifications, Email):
    cursor.execute(readSpecific_query, (Email))
    if cursor.fetchone():
        cursor.execute(update['all'], (Token, PhoneNumber, GetSMSTeamNotifications, Email))

def fetch(Email):
    return cursor.execute(readSpecific_query, (Email))

def getAll():
    return cursor.execute(read_query)

def updateVal(Email, column, value):
    cursor.execute(update[column], (value, Email))
    cursor.commit()

def delete(Email):
    cursor.execute(delete_query, Email)
    cursor.commit()