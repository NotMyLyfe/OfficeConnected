import pyodbc
import os

password = os.getenv('SQL_PASSWORD')
cnxn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=edoffice.database.windows.net;'
    'PORT=1433;'
    'DATABASE=EdOffice;'
    'UID=EdOffice;'
    'PWD='+password
)

cursor = cnxn.cursor()

insert_query = '''INSERT INTO userData (ID, Token, IsStudent, phoneNumber, Email) VALUES (?, ?, ?, ?, ?);'''
read_query = '''SELECT * FROM userData;'''
readSpecific_query = '''SELECT * FROM userData WHERE ID = ?;'''
update = {
    'Token' : '''UPDATE userData SET Token = ? WHERE ID = ?;''',
    'IsStudent' : '''UPDATE userData SET IsStudent = ? WHERE ID = ?;''',
    'PhoneNumber' : '''UPDATE userData SET phoneNumber = ? WHERE ID = ?;''',
    'Email' : '''UPDATE userData SET Email = ? WHERE ID = ?;''',
    'all' : ''' UPDATE userData SET Token = ?, IsStudent = ?, phoneNumber = ?, Email = ? WHERE ID = ?'''
}

delete_query = '''DELETE FROM userData WHERE ID = ?;'''

def insert(ID, token, isStudent, phoneNumber, email):
    cursor.execute(readSpecific_query, (ID))
    if not cursor.fetchone():
        cursor.execute(insert_query, (ID, token, isStudent, phoneNumber, email))
    else:
        cursor.execute(update['all'], (token, isStudent, phoneNumber, email, ID))
    cursor.commit()

def fetch(ID):
    return cursor.execute(readSpecific_query, (ID))

def getAll():
    return cursor.execute(read_query)

def updateVal(ID, column, value):
    cursor.execute(update[column], (ID, value))
    cursor.commit()

def delete(ID):
    cursor.execute(delete_query, ID)
    cursor.commit()