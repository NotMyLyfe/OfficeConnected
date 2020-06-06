# sql.py
# Gordon Lin and Evan Lu
# SQL functions for the main application of OfficeConnected to update or retrieve data from the main database

import pyodbc, os

# Creates a connection to SQL server
connection = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=officeconnected.database.windows.net;'
    'PORT=1433;'
    'DATABASE=OfficeConnected;'
    'UID=OfficeConnected;'
    'PWD='+os.getenv('SQL_PASSWORD')
)

# 2 cursors for SQL, one for writing and one for reading
cursor = connection.cursor()
rcursor = connection.cursor()

# Query for inserting a new row in SQL
insert_query = '''SET NOCOUNT ON; INSERT INTO userData (Token, PhoneNumber, GetSMSTeamNotifications, Email, EmailOverSMS, VerifiedPhone, VerificationCode, ContinuedCommand) VALUES (?, ?, ?, ?, ?, ?, ?, ?);'''

# Query for getting all rows in SQL
read_query = '''SET NOCOUNT ON; SELECT * FROM userData;'''

# Query for getting specific rows in SQL (based on Email or PhoneNumber)
readSpecific_query = '''SET NOCOUNT ON; SELECT * FROM userData WHERE Email LIKE ?;'''
readSpecific_queryPhone = '''SET NOCOUNT ON; SELECT * FROM userData WHERE PhoneNumber = ?;'''

# Queries for update a value of a row
update = {
    'Token' : '''SET NOCOUNT ON; UPDATE userData SET Token = ? WHERE Email LIKE ?;''',
    'PhoneNumber' : '''SET NOCOUNT ON; UPDATE userData SET PhoneNumber = ? WHERE Email LIKE ?;''',
    'GetSMSTeamNotifications' : '''SET NOCOUNT ON; UPDATE userData SET GetSMSTeamNotifications = ? WHERE Email LIKE ?;''',
    'EmailOverSMS' : '''SET NOCOUNT ON; UPDATE userData SET EmailOverSMS = ? WHERE Email LIKE ?;''',
    'VerifiedPhone' : '''SET NOCOUNT ON; UPDATE userData SET VerifiedPhone = ? WHERE Email LIKE ?;''',
    'VerificationCode' : '''SET NOCOUNT ON; UPDATE userData SET VerificationCode = ? WHERE Email LIKE ?;''',
    'ContinuedCommand' : '''SET NOCOUNT ON; UPDATE userData SET ContinuedCommand = ? WHERE Email LIKE ?;'''
}

# Query for deleting the whole row
delete_query = '''SET NOCOUNT ON; DELETE FROM userData WHERE Email LIKE ?;'''

# While loops to attempt a connection to SQL, and will wait until connection is free and available

# Updating a value of a row
def updateVal(Email, column, value):
    # Executes query and commits it
    while True:
        try:
            cursor.execute(update[column], (value, Email))
            cursor.commit()
            break
        except:
            pass

# Inserts a new row in SQL
def insert(Token, Email):
    while True:
        # Checks if email doesn't already exist and creates new row, else just updates the Token value of the row
        try:
            if not fetch(Email).fetchone():
                cursor.execute(insert_query, (Token, None, False, Email, False, False, None, None))
                cursor.commit()
            else:
                updateVal(Email, 'Token', Token)
            break
        except:
            pass

# Finds the row containing the specified email
def fetch(Email):
    while True:
        try:
            data = rcursor.execute(readSpecific_query, (Email))
            return data
        except:
            pass

# Finds the row containing the specified phone number
def fetchPhone(PhoneNumber):
    while True:
        try:
            data = rcursor.execute(readSpecific_queryPhone, (PhoneNumber))
            return data
        except:
            pass

# Gets all the rows in SQL
def getAll():
    while True:
        try:
            data = rcursor.execute(read_query)
            return data
        except:
            pass

# Deletes the specific row in SQL
def delete(Email):
    # Checks if row exists before deleting
    while True:
        try:
            if fetch(Email).fetchone():
                cursor.execute(delete_query, Email)
                cursor.commit()
            break
        except:
            pass