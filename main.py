import calendar
from datetime import date, datetime, timezone
import time

import firebase_admin
import requests
import copy
from firebase_admin import auth, credentials, firestore

cred = credentials.Certificate("cloudfarm-f94f3-firebase-adminsdk-zmpu5-b3a0bedb3a.json")
default_app = firebase_admin.initialize_app(cred, {
    'databaseURL' : 'https://cloudfarm-f94f3.firebaseio.com/'
})
db = firestore.client()

globalRef = db.collection('global').document('settings')
globalData = globalRef.get().to_dict()
coin = globalData['coin']
masterWalletAddress = globalData['address']

page = auth.list_users()
uidList = []
while page:
    for user in page.users:
        uidList.append(user.uid)
    # Get next batch of users.
    page = page.get_next_page()

def updateFirebase(request):
    # this function pulls data from Flexpool APIs, updates next payment date, then stores everything in Firebase
    updateMasterUnpaidBalance()
    updateNextPaymentDate()
    for uid in uidList:
        user = auth.get_user(uid)
        userRef = db.collection('users').document(user.uid)
        userData = userRef.get().to_dict()
        if userData:
            for rig in userData['rigs']:
                updateWorkerShares(rig, userData, userRef)
    # uid = 'EtbRYkdlyqh201M4ZxDUKXCcXSX2'
    # # uid = 'yFGM2ZYURchGMQkONpLhRVQdFhp1'
    # # user = auth.get_user(uid)
    # userRef = db.collection('users').document(uid)
    # userData = userRef.get().to_dict()
    # if userData:
    #     for rig in userData['rigs']:
    #         updateWorkerShares(rig, userData, userRef)
    print('executed properly and ended at ', datetime.now(), ' PST')
    return 'success'

def updateWorkerShares(rigID, userData, userRef):
    shortWorkerName = rigID[0:32]
    workerShareLogs = getWorkerShareLogs(coin, masterWalletAddress, shortWorkerName)
    count = 0
    initialCount = copy.copy(count)

    try: 
        count = userData['unpaidShares']
        initialCount = copy.copy(count)
        
        if 'logs' in userData['rigs'][rigID]:
            print('logs exist')
            pastWorkerLogs = userData['rigs'][rigID]['logs']
        else:
            print('no logs found')
            pastWorkerLogs = []
        print('this worker is: '+ rigID)
        newLogs = copy.copy(workerShareLogs)
        overlapLogs = []   
        if workerShareLogs: 
            for pastLog in pastWorkerLogs:
                for currentLog in workerShareLogs:
                    if pastLog['timestamp'] == currentLog['timestamp']:
                        overlapLogs.append(currentLog)
            for overlapLog in overlapLogs:
                for currentLog in newLogs:
                    if currentLog['timestamp'] == overlapLog['timestamp']:
                        newLogs.remove(overlapLog)
            if newLogs:    
                for log in newLogs:
                    count += log['validShares']
        
        userRef.set({
        'rigs': {
            rigID: {
                'logs': workerShareLogs
            }
        },
        'unpaidShares': count,
        },
        merge=True
     )
        print('rig ', rigID, 'mined', count-initialCount, 'additional shares')

    except ValueError as err:
        print(err)
    
    addedShares = count - initialCount
    masterUnpaidShares = globalData['masterUnpaidShares']
    masterUnpaidShares += addedShares

    globalRef.update({ 'masterUnpaidShares': masterUnpaidShares})
    return


def updateMasterUnpaidBalance():
    response = requests.get('https://api.flexpool.io/v2/miner/balance?coin=' + coin + '&address=' + masterWalletAddress)
    data = response.json()
    masterUnpaidBalance = round(data['result']['balance'] / 1000000000000000000, 6)
    globalRef.update({'master_unpaid_balance': masterUnpaidBalance})
    return 
    
def getWorkerShareLogs(coin, masterWalletAddress, workerName):
    response = requests.get('https://api.flexpool.io/v2/miner/chart?address=' + masterWalletAddress + '&coin=' + coin + '&worker=' + workerName)
    data = response.json()
    # workerShareLogs = {workerName: data['result']}
    workerShareLogs = data['result']
    return workerShareLogs


def updateNextPaymentDate():
    todays_date = date.today()
    # print(todays_date)
    # year, month = todays_date.year, todays_date.month
    # lastDay = calendar.monthrange(year, month)[1]
    # month = calendar.month_name[month]
    # lastDayofMonth = month + ' ' + str(lastDay)
    # print(lastDayofMonth)
    lastDayofMonth = todays_date.replace(day = calendar.monthrange(todays_date.year, todays_date.month)[1])
    unixTime = time.mktime(lastDayofMonth.timetuple())
    globalRef.update({'nextPaymentDate': unixTime})
    return


