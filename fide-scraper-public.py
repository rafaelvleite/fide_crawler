import time
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from datetime import datetime
from dateutil import relativedelta
from gspread_dataframe import set_with_dataframe
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os 
import Levenshtein as lev
from googleapiclient.discovery import build
from retry import retry
import socket
from performanceCalculator import ratingPerformance


timeout_in_sec = 10 # 5 seconds timeout limit
socket.setdefaulttimeout(timeout_in_sec)

#playerName = 'Niemann, Hans Moke'
#playerName = 'Gukesh D'
playerName = 'Erigaisi Arjun'
#FIDE_ID = '2093596'
#FIDE_ID = '46616543'
FIDE_ID = '35009192'
startingPeriod = '2018-05-01'
endPeriod = '2022-09-01'

my_api_key = "YOUR_GOOGLE_PROJECT_API" #The API_KEY you acquired
my_cse_id = "YOUR_SEARCH_ENGINE_API" #The search-engine-ID you created here https://programmablesearchengine.google.com/controlpanel/all


start = datetime.now()
startingPeriodDate = datetime.strptime(startingPeriod, "%Y-%m-%d")
endPeriodDate = datetime.strptime(endPeriod, "%Y-%m-%d")
walkingDate = startingPeriodDate
fullDateRange = []

while walkingDate <= endPeriodDate:
    fullDateRange.append(datetime.strftime(walkingDate, "%Y-%m-%d"))
    walkingDate = walkingDate + relativedelta.relativedelta(months=1)

def instantiateDriver():
    #####################
    # Instantiate driver
    print("Instantiating Chrome Browser...")
    options = webdriver.ChromeOptions()
    options.add_argument("start-maximized")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-popup-blocking")
    prefs = {}
    prefs["profile.default_content_settings.popups"] = 0
    prefs["download.default_directory"] = os.getcwd()
    prefs["credentials_enable_service"] = False
    prefs["profile.password_manager_enabled"] = False
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    driver.set_page_load_timeout(60)

    print("Instantiating Chrome Browser done!")
    time.sleep(2)
    #####################
    #####################
    
    return driver


@retry(delay=10)
def google_search(search_term, api_key=my_api_key, cse_id=my_cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
    if "items" in res.keys(): 
        return res["items"] 
    else: 
        return None



playerDf = pd.DataFrame(columns = ['Date', 'Tournment Name', 'Player Rating', 'Performance Rating', 'Opponents Average Rating', 'Number of Games', 'Points', 'Points/Games', 'DGT'])

allLinks = []
for stringDate in fullDateRange:
    allLinks.append("https://ratings.fide.com/calculations.phtml?id_number=" + FIDE_ID + "&period=" + stringDate + "&rating=0")

for link in allLinks:
    print(link)
    driver = instantiateDriver()
    driver.get(link)
    html=driver.execute_script('return document.querySelector(".section-profile").innerHTML')
    driver.quit()
    time.sleep(1)
    parsed_html = BeautifulSoup(html,'html.parser')
    fullTable = parsed_html.find('table', attrs={'class':'calc_table'})
    if fullTable != None:
        tableDf = pd.read_html(fullTable.prettify())[0]
        tableDf.drop(tableDf.index[tableDf['Unnamed: 0'] == "*  Rating difference of more than 400."], inplace=True)
        tableDf.reset_index(inplace=True, drop=True)
        limiters = tableDf.isnull().all(1)
        limiters = limiters[limiters==True].index.values.tolist()
        
        for limiter in limiters:
            if limiters.index(limiter) < len(limiters) -1:
                localDf = tableDf.iloc[limiter+1:limiters[limiters.index(limiter)+1]-3,:]
            else:
                localDf = tableDf.iloc[limiter+1:,:]
            tournment_name = tableDf.iloc[limiter-3,0]
            tournment_date = tableDf.iloc[limiter-3,7]
            player_rating = tableDf.iloc[limiter-1,1]
            opponentsAverageRating = tableDf.iloc[limiter-1,0]
            numberOfGames = len(localDf)
            pointsValues = localDf.iloc[:,5].apply(lambda x: float(x)).tolist()
            points = sum(pointsValues)
            pointsRatio = points / numberOfGames
            localDf.loc[:, 'Unnamed: 3'] = localDf.loc[:, 'Unnamed: 3'].apply(lambda x: int(str(x)[:4]))
            ratingSum = localDf.loc[:, 'Unnamed: 3'].sum()
            totalWins = sum([x for x in pointsValues if x == 1])
            totalLosses = sum([x for x in pointsValues if x == 0])
            performance = ratingPerformance(int(numberOfGames), float(points), int(opponentsAverageRating), ratingSum, totalWins, totalLosses)
            
            playerLocalDf = pd.DataFrame(index=range(1), columns = ['Date', 'Tournment Name', 'Player Rating', 'Performance Rating', 'Opponents Average Rating', 'Number of Games', 'Points', 'Points/Games', 'DGT'])
            playerLocalDf['Date'] = tournment_date
            playerLocalDf['Tournment Name'] = tournment_name
            playerLocalDf['Player Rating'] = player_rating
            playerLocalDf['Performance Rating'] = performance
            playerLocalDf['Opponents Average Rating'] = opponentsAverageRating
            playerLocalDf['Number of Games'] = numberOfGames
            playerLocalDf['Points'] = points
            playerLocalDf['Points/Games'] = pointsRatio
            
            concat = [playerDf, playerLocalDf]
            playerDf = pd.concat(concat)
            print(playerDf)
        
playerDf.reset_index(inplace=True, drop=True)
playerDf.to_pickle("./" + playerName + ".pkl")  




# DGT Check
dgtList = []
dgtInfoList = []
dgtLinkList = []
dgtRatioList = []

for tournment in list(playerDf['Tournment Name'].values):
    print(tournment)
    text = (tournment).lower()
    
    dgt = 0
    dgtInfo = ''
    dgtLink = ''
    maxRatio = 0
    maxIndex = 0
    results = google_search(text, my_api_key, my_cse_id, num=10)
    
    if results != None:
        for result in results:
            print(result['link'])
            if 'https://www.chess.com/events/' in result['link'] or 'https://chess24.com/en/watch/live-tournaments/' in result['link'] or 'https://lichess.org/broadcast/' in result['link'] or 'https://www.chess.com/pt-BR/events/' in result['link'] or 'https://chess24.com/pt/watch/live-tournaments/' in result['link']:
                cleanedLink = result['link'].split('https://www.chess.com/events/')[-1]
                cleanedLink = result['link'].split('https://www.chess.com/pt-BR/events/')[-1]
                cleanedLink = result['link'].split('https://chess24.com/en/watch/live-tournaments/')[-1]
                cleanedLink = result['link'].split('https://chess24.com/pt/watch/live-tournaments/')[-1]
                cleanedLink = result['link'].split('https://lichess.org/broadcast/')[-1]
                cleanedLink = cleanedLink.replace("-", " ")
                ratio = lev.ratio(text,cleanedLink)
                if ratio > maxRatio:
                    maxRatio = ratio
                    maxIndex = results.index(result)
                      
        if maxRatio > 0:
            dgt = 1
            dgtInfo = results[maxIndex]['title']
            dgtLink = results[maxIndex]['link']
            print("{} || {} || {}".format(maxRatio, dgtInfo, dgtLink))

                
    dgtList.append(dgt)
    dgtInfoList.append(dgtInfo)
    dgtLinkList.append(dgtLink)
    dgtRatioList.append(maxRatio)
    time.sleep(1)

    
playerDf['DGT'] = dgtList
playerDf['DGT Search Title'] = dgtInfoList
playerDf['DGT Search Link'] = dgtLinkList
playerDf['DGT Accuracy'] = dgtRatioList

        
playerDf.to_pickle("./" + playerName + ".pkl")



# Export to Google Sheets
scope = ['https://spreadsheets.google.com/feeds']
creds = ServiceAccountCredentials.from_json_keyfile_name('YOUR_SERVICE_CREDENTIALS_FILE_FROM_GOOGLE_PROJECT.json', scope)
client = gspread.authorize(creds)

# Conectando à pasta de trabalho
googleSheets = client.open_by_key("1PP-ojHkHOHZP5EXo1PCvL0Z6DeqDZEBysYiMSIU6ARc")
  
# Capturando os dados da planilha
planilha = googleSheets.worksheet(playerName)
planilha.clear()
set_with_dataframe(planilha, playerDf)



#####################
print("Done! Job complete!")
#####################
#####################
finish = datetime.now()
print('Demorou mas foi! O job todo demorou: {}'.format(finish - start))
#####################
#####################


