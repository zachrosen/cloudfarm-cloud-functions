import calendar
from datetime import date, datetime, timedelta

import firebase_admin
import requests
from firebase_admin import auth, credentials, firestore

cred = credentials.Certificate("cloudfarm-f94f3-firebase-adminsdk-zmpu5-b3a0bedb3a.json")
default_app = firebase_admin.initialize_app(cred, {
    'databaseURL' : 'https://cloudfarm-f94f3.firebaseio.com/'
})
db = firestore.client()
uid = 'EtbRYkdlyqh201M4ZxDUKXCcXSX2'
user = auth.get_user(uid)
globalData = db.collection('global').document('settings').get().to_dict()
coin = globalData['coin']
masterWalletAddress = globalData['address']


# # currently cloud functions are running unauthenticated--need to change prior to production
# masterWalletAddress = '0x589e8eF749C6A9520Cbb7Ad93513A66829A3446F'
# workerName = 'RX_6800'
# currentHashArray = []
# timestampArray = []

def getFlexpoolCoin(masterWalletAddress):
    response = requests.get("https://api.flexpool.io/v2/miner/locateAddress?address=" + masterWalletAddress)
    data = response.json()
    flexPoolCoin = data['result']
    return flexPoolCoin

# worker change not registering, URL is wrong
def getWorkerInfo(workerName, masterWalletAddress, coin):
    response = requests.get('https://api.flexpool.io/v2/miner/workers?coin=' + coin + '&address=' + masterWalletAddress)
    data = response.json()
    workerList = []
    for worker in data['result']:
        if worker['name'] == workerName:
            workerList.append([workerName, worker['isOnline'], worker['currentEffectiveHashrate'], worker['averageEffectiveHashrate']])
    return workerList

# def convertTime(unixTime):
#     time = (datetime.fromtimestamp(unixTime) - timedelta(hours=2)).strftime('%H:%M')
#     return time

# # still needs to be tested

# def getGraph(coin, masterWalletAddress):
#     response = requests.get('https://api.flexpool.io/v2/miner/chart?coin=' + coin + '&address=' + masterWalletAddress)
#     data = response.json()
#     currentHashArray = []
#     timestampArray = []
#     for i in range(0, len(data['result'])):
#         formattedTime = convertTime(data['result'][i]['timestamp'])
#         timestampArray.append(formattedTime)
#         currentHashArray.append(data['result'][i]['effectiveHashrate'] / 1000000)
#     timestampArray.reverse()
#     currentHashArray.reverse()
#     return [timestampArray, currentHashArray]

def getDailyRewardsperGhs(coin):
    response = requests.get('https://api.flexpool.io/v2/pool/dailyRewardPerGigahashSec?coin=' + coin)
    data = response.json()
    dailyRewardsperGhs = data['result']
    return dailyRewardsperGhs

def getCoinPrice(coin):
    response = requests.get('https://min-api.cryptocompare.com/data/price?fsym=' + coin + '&tsyms=USD')
    data = response.json()
    coinPrice = data['USD']
    return coinPrice

def updateMasterUnpaidBalance():
    response = requests.get('https://api.flexpool.io/v2/miner/balance?coin=' + coin + '&address=' + masterWalletAddress)
    data = response.json()
    masterUnpaidBalance = round(data['result']['balance'] / 1000000000000000000, 5)
    db.collection('global').document('settings').update({'master_unpaid_balance': masterUnpaidBalance})
    return 
    
def getWorkerShareLogs(coin, masterWalletAddress, workerName):
    print(workerName)
    response = requests.get('https://api.flexpool.io/v2/miner/chart?address=' + masterWalletAddress + '&coin=' + coin + '&worker=' + workerName)
    data = response.json()
    # workerShareLogs = {workerName: data['result']}
    workerShareLogs = data['result']
    return workerShareLogs

def updateWorkerShares(workerID):
    pastWorkerLogs = db.collection('users').document(user.uid).collection('Rigs').document(workerID).get()
    pastWorkerLogs = pastWorkerLogs.to_dict()['logs']
    workerShareLogs = getWorkerShareLogs(coin, masterWalletAddress, workerID)
    overlapLogs = []
    newLogs = workerShareLogs
    count = db.collection('users').document(user.uid).get().to_dict()['unpaidShares']    
    for pastLog in pastWorkerLogs:
        for currentLog in workerShareLogs:
            if pastLog['timestamp'] == currentLog['timestamp']:
                overlapLogs.append(currentLog)
    for overlapLog in overlapLogs:
        for currentLog in newLogs:
            if currentLog['timestamp'] == overlapLog['timestamp']:
                newLogs.remove(overlapLog)
    for log in newLogs:
        count += log['validShares']
    db.collection('users').document(user.uid).collection('Rigs').document(workerID).update({'logs': workerShareLogs})
    db.collection('users').document(user.uid).update({'unpaidShares': count})
    return

def getNextPaymentDate():
    todays_date = date.today()
    year, month = todays_date.year, todays_date.month
    lastDay = calendar.monthrange(year, month)[1]
    month = calendar.month_name[month]
    lastDayofMonth = month + ' ' + str(lastDay)
    db.collection('global').document('settings').update({'nextPaymentDate': lastDayofMonth})
    return

# def estDailyProfitability(coin, avgHash):
#     response = requests.get('https://min-api.cryptocompare.com/data/price?fsym=' + coin + '&tsyms=USD')
#     data = response.json()
#     coinPrice = data['USD']
#     dailyProfitability = round(coinPrice * getDailyRewardsperGhs() * avgHash / 1000000000 / 1000000000000000000, 2) 'effectiveHashrate': 320000000, 'timestamp': 1626205200}
#     print(dailyProfitability)
#     return dailyProfitability

# # # def globalConfig(globalState):
# # #     db.collection(u'global').document(u'settings').set(globalState)

# def getUpdatedFlexData(request): 
#     # data = request.form.to_dict()
#     # uuid = data['uuid'] = firebase.auth().currentUser.uid
#     # minerAssociatedWithThisUUID = db.collection('users').document(cred.user.uuid).collection('rigs').get()
#     globalData = db.collection('global').get()
#     flexData = []
#     for entry in globalData:
#         flexData.append(entry.to_dict())
#     masterWalletAddress = flexData[0]['address']
#     coin = getFlexpoolCoin(masterWalletAddress)
#     user = auth.get_user(uid)
#     workerList = []
#     workerInfoList = []
#     workers = db.collection('users').document(user.uid).collection('Rigs').stream()
#     for worker in workers:
#         workerList.append(worker.id)
#     for worker in workerList:
#         workerInfoList.append(getWorkerInfo(worker, masterWalletAddress, coin))
#     print(workerInfoList)
#     print('Successfully fetched user data: {0}'.format(user.uid))
#     dailyRewardsperGhs = getDailyRewardsperGhs(coin)
#     return 'success'

def hourlyFlexpoolData(request):
    # dailyRewardsperGhs = getDailyRewardsperGhs(coin)
    updateMasterUnpaidBalance()
    # need to update workers to dynamically pull from Firestore
    workerList = db.collection('users').document(user.uid).collection('Rigs').stream()
    for worker in workerList:
        updateWorkerShares(worker.id)
    getNextPaymentDate()
    return 'success'




    # # now just call all the fetch requests and serilize to firestore and anything else you need
    # currentHash, avgHash,isOnline = getWorkerInfo(minerAssociatedWithThisUUID, masterwalletAddress, coin)
    # time = convertTime(unixTime)

    # # this graph one might need to be broken down further to indv worker
    # tsArr, hashArr = getGraph(coin, masterWalletAddress)
    # gHsProfitability24h = getDailyRewardsperGhs(coin)
    # workerProfitability24h = estDailyProfitability(coin, avgHash)

#     # Then from here you could store them into firebase 1 at a time, providing easy retrieval for any individual value
#     # (this requires you to store each one and manually retreive each one if you need all the data)
#     firebase.put(tsArr)
#     firebase.put(hashArr)
#     firebase.put(workerProfitability24h)
#     # .
#     # .
#     # .
#     # and so on. This could be good tho if that's intended functionality, like maybe only some of the data isfrequently used
#     # or the data are used at different times, the storing separately makes sense. If not then we can do down below:

#     # You can store them individually into firebase using a docReference for each value or maybe if you wanted to
#     # you could store them together if it makes sense by putting them all into one object and storing one object
#     # instead of multiple stored values (this saves a little bit on DB transaction but more overhead to ungroup 
#     # and regroup when you need the data). This approach is also good if you ever need to send values BACK to the calling
#     # client.

#     minerAssociatedWithThisUUID = firestore.get(uuid) 
#     masterWalletAddress = firestore.getFromCurrentConfig('masterWalletAddress')
#     coin= getFlexpoolCoin()
#     workerInfo = getWorkerInfo(minerAssociatedWithThisUUID, masterwalletAddress, coin)
#     dataSnapshot = {
#         coin: coin,
#         currentHash: workerInfo[0]
#         avgHash: workerInfo[1]
#         isOnline: workerInfo[2]
#         avgHash,isOnline = getWorkerInfo(minerAssociatedWithThisUUID, masterwalletAddress, coin)
#         convertTime(unixTime):
#         graph one might need to be broken down further to indv worker
#         hashArr = getGraph(coin, masterWalletAddress):
#         getDailyRewardsperGhs(coin):
#         estDailyProfitability(coin, avgHash):
#     }

#     return dataSnapshot
#     # # or 
#     firebase.put(someTimestamp or Id number, dataSnapshot)


# # ========================================================
# # ACTUAL END POINT END
# # ========================================================

# # getFlexpoolCoin()
# # getWorkerInfo()
# # getGraph()
# # getDailyRewardsperGhs()
# # estDailyProfitability();
