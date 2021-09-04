import requests
import time

def getNanopoolLogs(masterWalletAddress, workerName):
    recentShareLogs = []

    response = requests.get('https://api.nanopool.org/v1/rvn/shareratehistory/' + masterWalletAddress + '/' + workerName)
    data = response.json()
    workerShareLogs = data['data']
    last24hrs = time.time() - 87000

    for shareLog in workerShareLogs:    
        if shareLog['date'] > last24hrs:
            recentShareLogs.append(shareLog)
    recentShareLogs = standardizeLogs(recentShareLogs)
    return recentShareLogs


def standardizeLogs(logs):
    for log in logs:
        log['timestamp'] = log.pop('date')
        log['validShares'] = log.pop('shares')
    return logs


def updateNanopoolBalance(globalCoinRef, coin, rvnWallet):
    response = requests.get(
        'https://api.nanopool.org/v1/rvn/balance/' + rvnWallet)
    data = response.json()
    globalCoinRef.set({
        coin:
        {
        'unpaidBalance': data['data']
        }}, merge=True)
    return