import os
import petl
import pymssql
import configparser
import requests
import datetime
import json
import decimal

#request data from url
try:
    BOCResponse = requests.get("https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?start_date=2020-01-01")
except Exception as e:
    print('could not make the request'+str(e))
    sys.exit()
# initialize list of lists for data storage
BOCDates = []
BOCRates = []

# check response status and process BOC JSON object
if (BOCResponse.status_code == 200):
    BOCRaw = json.loads(BOCResponse.text)

    # extract observation data into column arrays
    for row in BOCRaw['observations']:
        BOCDates.append(datetime.datetime.strptime(row['d'],'%Y-%m-%d'))
        BOCRates.append(decimal.Decimal(row['FXUSDCAD']['v']))

    # create petl table from column arrays and rename the columns
    exchangeRates = petl.fromcolumns([BOCDates,BOCRates],header=['date','rate'])

    # print (exchangeRates)

    # load expense document
    try:
        expenses = petl.io.xlsx.fromxlsx('Expenses.xlsx')
    except Exception as e:
        print('could not open expenses.xlsx:' + str(e))
        sys.exit()

    # join tables
    expenses = petl.outerjoin(exchangeRates,expenses,key='date')

    # fill down missing values
    expenses = petl.filldown(expenses,'rate')

    # remove dates with no expenses
    expenses = petl.select(expenses,lambda rec: rec.USD != None)

    # add CDN column
    expenses = petl.addfield(expenses,'CAD', lambda rec: decimal.Decimal(rec.USD) * rec.rate)

    # intialize database connection
    try:
        dbConnection = pymssql.connect(server=destServer,database=destDatabase)
    except Exception as e:
        print('could not connect to database:' + str(e))
        sys.exit()

    # populate Expenses database table
    try:
        petl.io.todb (expenses,dbConnection,'Expenses')
    except Exception as e:
        print('could not write to database:' + str(e))
    print (expenses)
