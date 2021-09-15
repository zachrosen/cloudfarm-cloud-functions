import calendar
from datetime import date, datetime, timezone
import time

import firebase_admin
import copy
from firebase_admin import auth, credentials, firestore
from ravencoin import getNanopoolLogs, updateNanopoolBalance
from flexpool import getFlexpoolLogs, updateFlexpoolBalance

cred = credentials.Certificate(
    "cloudfarm-f94f3-firebase-adminsdk-zmpu5-b3a0bedb3a.json")
default_app = firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://cloudfarm-f94f3.firebaseio.com/'
})
db = firestore.client()

globalCoinRef = db.collection('global').document('coinSettings')
masterSettingsRef = db.collection('global').document('masterSettings')

globalCoinData = globalCoinRef.get().to_dict()
ethWallet = globalCoinData['eth']['walletAddress']
rvnWallet = globalCoinData['rvn']['walletAddress']

page = auth.list_users()
uidList = []
while page:
    for user in page.users:
        uidList.append(user.uid)
    # Get next batch of users.
    page = page.get_next_page()

def updateFirebase(request): 
    
    updateFlexpoolBalance(globalCoinRef, 'eth', ethWallet)
    updateNanopoolBalance(globalCoinRef, 'rvn', rvnWallet)
    updateNextPaymentDate()


    for uid in uidList:
        user = auth.get_user(uid)
        userRef = db.collection('users').document(user.uid)
        userData = userRef.get().to_dict()
        if userData:
            for rig in userData['rigs']:
                updateWorkerShares(rig, userData, userRef)
    
    print('executed properly and ended at ', datetime.now(), ' PST')
    return 'success'







def updateNextPaymentDate():
    todays_date = date.today()
    lastDayofMonth = todays_date.replace(
        day=calendar.monthrange(todays_date.year, todays_date.month)[1])
    unixTime = time.mktime(lastDayofMonth.timetuple())
    masterSettingsRef.update({'nextPaymentDate': unixTime})
    return

# def updateWorkerShares(rigID, userData, userRef):
addedShareTracker = {'eth': 0, 'rvn': 0}
def updateWorkerShares(rigID, userData, userRef):
    newShares = {}
    initialShares = {}
    updatedLogs = {}
    
    # rigID = 'rig999'
    # workerNameRVN = 'gn6'
    # rvnWallet = 'RDthzQkTYcPWzAMdaUeNnwBnmVy3pMV321'
    # workerNameETH = 'SA0002'
    # ethWallet = '0x709303b9E7E95C59920BC9C41Be4CD40377801C7'  
    # userRef = db.collection('users').document('testUID')
    # userData = userRef.get().to_dict()

    shortWorkerName = rigID[0:32]
    coinDict = {
        'eth':
        {'logs': getFlexpoolLogs('ETH', ethWallet, shortWorkerName)}, 
        'rvn':
        {'logs': getNanopoolLogs(rvnWallet, shortWorkerName)},
    }
    

    
    for coin in coinDict:
        rigData = userData['rigs'][rigID]
        if coin not in rigData:
            rigData[coin] = { 'logs': {}, 'unpaidShares': 0}
        coinData = rigData[coin]
        workerShareLogs = coinDict[coin]['logs']
        count = coinData['unpaidShares']
        initialCount = copy.copy(count)
        initialShares[coin] = initialCount

        if 'logs' in coinData:
            print('logs exist for ', coin)
            pastWorkerLogs = coinData['logs']
        else:
            print('no logs found for', coin)
            pastWorkerLogs = []

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
        newShares[coin] = count
        updatedLogs[coin] = workerShareLogs

        # masterUnpaidShares = globalCoinData[coin]['unpaidShares']
        
        addedShareTracker[coin] += (newShares[coin] - initialShares[coin])
        print('added share tracker: ', addedShareTracker)
        print('rig ', rigID, 'mined', newShares[coin] - initialShares[coin], 'additional shares of ', coin)


    globalCoinRef.set({ 
            'eth':
                {
                    'unpaidShares': addedShareTracker['eth'],
                    'lastUpdated': time.time(),
                },
            'rvn':
                {
                    'unpaidShares': addedShareTracker['rvn'],
                    'lastUpdated': time.time(),
                },
                
                }, merge=True)
    print('added ', addedShareTracker['eth'], ' shares of ETH and ', addedShareTracker['rvn'], ' shares of RVN to master')
    userRef.set({
        'rigs': {
            rigID: {
                'eth': {
                    'logs': updatedLogs['eth'],
                    'unpaidShares': newShares['eth'],
                   
                },
                'rvn': {
                    'logs': updatedLogs['rvn'],
                    'unpaidShares': newShares['rvn'],
                }
            }
        },
    },
        merge=True
    )
    return 'success'
