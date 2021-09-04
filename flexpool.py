import requests
import time

def updateFlexpoolBalance(globalCoinRef, coin, ethWallet):
    response = requests.get(
        'https://api.flexpool.io/v2/miner/balance?coin=' + coin + '&address=' + ethWallet)
    data = response.json()
    masterUnpaidBalance = round(
        data['result']['balance'] / 1000000000000000000, 6)
    globalCoinRef.set({
        coin:
        {
        'unpaidBalance': masterUnpaidBalance
        }}, merge=True)
    return

def getFlexpoolLogs(coin, masterWalletAddress, workerName):
    response = requests.get('https://api.flexpool.io/v2/miner/chart?address=' + masterWalletAddress + '&coin=' + coin + '&worker=' + workerName)
    data = response.json()
    # workerShareLogs = {workerName: data['result']}
    workerShareLogs = data['result']
    return workerShareLogs