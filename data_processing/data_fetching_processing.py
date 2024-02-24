import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import relativedelta
import re
import sqlite3

def insertGameData(cursor, games_df, fide_id):
    if not games_df.empty:
        for index, row in games_df.iterrows():
            cursor.execute("INSERT INTO game_history (fide_id, date, tournament_name, country, player_name, player_rating, player_color, opponent_name, opponent_rating, result, chg, k, k_chg) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                           (fide_id, row['date'], row['tournament_name'], row['country'], row['player_name'], row['player_rating'], row['player_color'], row['opponent_name'], row['opponent_rating'], row['result'], row['chg'], row['k'], row['k_chg']))

@st.cache(allow_output_mutation=True)    
def fetch_players(query):
    # Definir a URL para a consulta de pesquisa
    url = "https://fide.com/search"

    # Cabeçalhos com base nas informações fornecidas
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7',
        'Content-Type': 'application/json',
        'Origin': 'https://fide.com',
        'Referer': f'https://fide.com/search?query={query}',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    # Os parâmetros da consulta
    params = {'query': query}

    # Fazer a requisição GET
    response = requests.get(url, headers=headers, params=params)

    # Verificar se a requisição foi bem-sucedida
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        search_blocks = soup.find_all('div', class_='member-block')
    
        # Inicializar uma lista para armazenar informações do jogador
        players = []

        for block in search_blocks:
            player_entries = block.find_all(class_="member-block__one")
            
            for entry in player_entries:
                # Extrair o nome do jogador
                player_name = entry.find(class_="member-block-info-position").get_text(strip=True)
                
                # Extrair o título do jogador, se disponível
                player_title = entry.find(class_="member-block-info-name")
                player_title = player_title.get_text(strip=True) if player_title else "Sem título"
                
                # Extrair a URL do perfil do jogador
                player_url = entry.find('a')['href']
                
                # Extrair o ID do jogador da URL usando regex
                player_id_match = re.search(r'/profile/(\d+)', player_url)
                player_id = player_id_match.group(1) if player_id_match else "Sem ID"

                # Anexar as informações extraídas à lista de jogadores
                if 'profile' in player_url and 'news' not in player_url:
                    players.append({
                        'name': player_name,
                        'title': player_title,
                        'url': player_url,
                        'id': player_id  # Adicionar ID do jogador ao dicionário
                    })   
    else:
        print(f"Falha ao recuperar dados. Código de status: {response.status_code}")

    return players

def safe_extract(callable, default=''):
    """Safely executes a callable for BeautifulSoup extraction and handles exceptions."""
    try:
        return callable()
    except Exception:
        return default
    
def scrapePlayerData(fide_id):
    url = f'https://ratings.fide.com/profile/{fide_id}'
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')

    player_data = {'fide_id': fide_id}  # Include the fide_id in the player_data

    # Use the safe_extract function for each piece of data to handle potential exceptions
    player_data['name'] = safe_extract(lambda: soup.find('div', class_='profile-top-title').text.strip())
    player_data['world_rank'] = safe_extract(lambda: soup.find('div', text='World Rank (Active):').find_next_sibling('div').text)
    player_data['federation'] = safe_extract(lambda: soup.find('div', text='Federation:').find_next_sibling('div').text)
    player_data['b_year'] = safe_extract(lambda: soup.find('div', text='B-Year:').find_next_sibling('div').text)
    player_data['sex'] = safe_extract(lambda: soup.find('div', text='Sex:').find_next_sibling('div').text)
    player_data['fide_title'] = safe_extract(lambda: soup.find('div', text='FIDE title:').find_next_sibling('div').text)

    # Handling profile photo separately due to the nested structure
    def get_profile_photo():
        profile_photo_div = soup.find('div', class_='profile-top__photo')
        img_tag = profile_photo_div.find('img') if profile_photo_div else None
        return img_tag['src'] if img_tag else None
    player_data['profile_photo'] = safe_extract(get_profile_photo)

    # Extracting rating info
    ratings = soup.select('.profile-top-rating-data')
    for rating in ratings:
        rating_type = safe_extract(lambda: rating.find('span').text.strip().lower())
        rating_value = safe_extract(lambda: ''.join(filter(str.isdigit, rating.text)))
        player_data[f'{rating_type}_rating'] = rating_value

    return player_data

def fetch_player_data(fide_id):
    fetched_player_data = scrapePlayerData(fide_id)
    return fetched_player_data

def scrapePlayerGamesHistory(fide_id, playerName, startingPeriod, endPeriod, progress_bar=None):
    startingPeriodDate = datetime.strptime(startingPeriod, "%Y-%m-%d")
    endPeriodDate = datetime.strptime(endPeriod, "%Y-%m-%d")
    walkingDate = startingPeriodDate
    fullDateRange = []

    while walkingDate <= endPeriodDate:
        firstDayOfMonth = walkingDate.replace(day=1)
        fullDateRange.append(firstDayOfMonth.strftime("%Y-%m-%d"))
        walkingDate = walkingDate + relativedelta.relativedelta(months=1)

    # Colunas atualizadas do DataFrame para refletir detalhes do jogo
    gameDf = pd.DataFrame(columns=['date', 'tournament_name', 'country', 'player_name', 'player_rating', 'player_color', 'opponent_name', 'opponent_rating', 'result', 'chg', 'k', 'k_chg'])

    allLinks = []
    for stringDate in fullDateRange:
        allLinks.append(f"https://ratings.fide.com/a_indv_calculations.php?id_number={fide_id}&rating_period={stringDate}&t=0")

    for index, link in enumerate(allLinks):
        # Update progress bar if it's passed as an argument
        if progress_bar is not None:
            progress_bar.progress((index + 1) / len(allLinks))
            
        html = requests.get(link).text
        parsed_html = BeautifulSoup(html, 'html.parser')
        fullTable = parsed_html.find('table', attrs={'class': 'calc_table'})
        if fullTable is not None:
            tableDf = pd.read_html(fullTable.prettify())[0]
            tableDf.drop(tableDf.index[tableDf['Unnamed: 0'] == "*  Rating difference of more than 400."], inplace=True)
            tableDf.reset_index(inplace=True, drop=True)
            limiters = tableDf.isnull().all(1)
            limiters = limiters[limiters == True].index.values.tolist()
            colors = fullTable.find_all('img')
            retrievedColors = []
            
            for img_tag in colors:
                src = img_tag.get('src')
                color = 'white' if 'clr_wh' in src else 'black'
                retrievedColors.append(color)
            
            colorIndex = 0
            
            for limiter in limiters:
                tournament_name = tableDf.iloc[limiter - 3, 0]
                tournament_date = tableDf.iloc[limiter - 3, 7]
                player_rating = tableDf.iloc[limiter - 1, 1]
                if limiters.index(limiter) < len(limiters) - 1:
                    localDf = tableDf.iloc[limiter + 1:limiters[limiters.index(limiter) + 1] - 3, :]
                else:
                    localDf = tableDf.iloc[limiter + 1:, :]
                
                # Iterar sobre cada jogo no torneio
                for _, row in localDf.iterrows():
                    game_details = {
                        'date': tournament_date,
                        'tournament_name': tournament_name,
                        'country': row['Unnamed: 4'],
                        'player_name': playerName,
                        'player_rating': player_rating,
                        'player_color': retrievedColors[colorIndex],
                        'opponent_name': row['Unnamed: 0'],  
                        'opponent_rating': row['Unnamed: 3'],  
                        'result': row['Unnamed: 5'], 
                        'chg': row['Unnamed: 7'], 
                        'k': row['Unnamed: 8'], 
                        'k_chg': row['Unnamed: 9'], 
                    }
                    gameDf = pd.concat([gameDf, pd.DataFrame([game_details])], ignore_index=True)
                    gameDf.dropna(inplace=True)
                    gameDf.reset_index(inplace=True, drop=True)
                    colorIndex += 1
    
    if len(gameDf) > 0:
        gameDf['opponent_rating'] = gameDf['opponent_rating'].astype(str).str.replace(r'\D', '', regex=True)
        gameDf['opponent_rating'] = pd.to_numeric(gameDf['opponent_rating'], errors='coerce')
        gameDf['result'] = gameDf['result'].astype(float)


    return gameDf

def fetch_game_history(fide_id, playerName, startingPeriod, endPeriod):
    with sqlite3.connect('./database/fide_data.db') as conn:
        cursor = conn.cursor()

        # Garantir que as datas de entrada estejam no início de seus respectivos meses
        startingPeriod = datetime.strptime(startingPeriod, "%Y-%m-%d").replace(day=1)
        endPeriod = datetime.strptime(endPeriod, "%Y-%m-%d").replace(day=1)

        # Verificar as datas de jogo mais antigas e mais recentes no banco de dados para o jogador
        cursor.execute("SELECT MIN(date), MAX(date) FROM game_history WHERE fide_id = ?", (fide_id,))
        min_max_date = cursor.fetchone()

        if min_max_date[0] is None or min_max_date[1] is None:
            # Se nenhum dado existir, buscar pelo período solicitado inteiro
            fetched_games_df = scrapePlayerGamesHistory(fide_id, playerName, startingPeriod.strftime('%Y-%m-%d'), endPeriod.strftime('%Y-%m-%d'))
            insertGameData(cursor, fetched_games_df, fide_id)
        else:
            db_start_date, db_end_date = [datetime.strptime(date, "%Y-%m-%d") for date in min_max_date]

            # Buscar e inserir dados para o período antes do registro mais antigo, se necessário
            if db_start_date > startingPeriod:
                fetched_games_df_before = scrapePlayerGamesHistory(fide_id, playerName, startingPeriod.strftime('%Y-%m-%d'), (db_start_date - relativedelta.relativedelta(days=1)).strftime('%Y-%m-%d'))
                insertGameData(cursor, fetched_games_df_before, fide_id)

            # Buscar e inserir dados para o período após o registro mais recente, se necessário
            if db_end_date < endPeriod:
                fetched_games_df_after = scrapePlayerGamesHistory(fide_id, playerName, (db_end_date + relativedelta.relativedelta(days=1)).strftime('%Y-%m-%d'), endPeriod.strftime('%Y-%m-%d'))
                insertGameData(cursor, fetched_games_df_after, fide_id)

        conn.commit()

        # Recuperar e retornar os dados completos para o período solicitado
        cursor.execute("SELECT * FROM game_history WHERE fide_id = ? AND date BETWEEN ? AND ?", (fide_id, startingPeriod.strftime('%Y-%m-%d'), endPeriod.strftime('%Y-%m-%d')))
        games = cursor.fetchall()
        if games:
            games_df = pd.DataFrame(games, columns=['id', 'fide_id', 'date', 'tournament_name', 'country', 'player_name', 'player_rating', 'player_color', 'opponent_name', 'opponent_rating', 'result', 'chg', 'k', 'k_chg'])
            return games_df
        else:
            return pd.DataFrame()  # Retornar um DataFrame vazio se nenhum jogo for encontrado

def process_game_history(df):
    if not df.empty:
        duplicate_columns = ['date', 'tournament_name', 'player_name', 'opponent_name', 'result'] 
        df['date'] = pd.to_datetime(df['date'])
        df.sort_values('date', inplace=True)
        df['player_rating'] = pd.to_numeric(df['player_rating'], errors='coerce')
        df['opponent_rating'] = pd.to_numeric(df['opponent_rating'], errors='coerce')
        df['result'] = df['result'].astype(float)
        df.drop_duplicates(subset=duplicate_columns, inplace=True)
        df.sort_values('date', inplace=True)
        df.dropna(inplace=True)
        df.reset_index(drop=True, inplace=True)
    return df

