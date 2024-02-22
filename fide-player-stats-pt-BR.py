import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import relativedelta
import re
import matplotlib.pyplot as plt
import sqlite3
from PIL import Image
import base64
from io import BytesIO
import os
import numpy as np
    
def remove_duplicates_in_db():
    with sqlite3.connect('./db/fide_data.db') as conn:
        cursor = conn.cursor()

        # Ativar temporariamente suporte a chaves estrangeiras, se necessário
        cursor.execute('PRAGMA foreign_keys = ON;')

        # Etapa 1: Identificar e excluir duplicatas
        delete_sql = """
        DELETE FROM game_history
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY date, tournament_name, player_name, opponent_name, result
                           ORDER BY id -- Ajuste isso para manter o registro que deseja (por exemplo, o mais antigo ou o mais recente)
                       ) AS rn
                FROM game_history
            ) 
            WHERE rn > 1 -- Isso mantém a primeira ocorrência e marca as subsequentes para exclusão
        );
        """
        cursor.execute(delete_sql)
        conn.commit()

def get_binary_file_downloader_html(bin_file, file_label='Arquivo'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">Baixar {file_label}</a>'
    return href

def initialize_database():
    conn = sqlite3.connect('./db/fide_data.db')
    cursor = conn.cursor()

    # Criar a tabela player_data se ela não existir
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS player_data (
        fide_id TEXT PRIMARY KEY,
        name TEXT,
        federation TEXT,
        b_year TEXT,
        sex TEXT,
        fide_title TEXT,
        std_rating TEXT,
        rapid_rating TEXT,
        blitz_rating TEXT,
        profile_photo TEXT,
        world_rank TEXT
    );
    ''')

    # Criar a tabela game_history se ela não existir
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS game_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fide_id TEXT,
        date TEXT,
        tournament_name TEXT,
        country TEXT,
        player_name TEXT,
        player_rating TEXT,
        player_color TEXT,
        opponent_name TEXT,
        opponent_rating TEXT,
        result TEXT,
        chg TEXT,
        k TEXT,
        k_chg TEXT,
        FOREIGN KEY(fide_id) REFERENCES player_data(fide_id)
    );
    ''')

    conn.commit()
    conn.close()
    
def displayProfilePhoto(base64_image):
    # Remover o prefixo da string Base64
    base64_image = base64_image.split(",")[1]

    # Decodificar a string Base64
    image_data = base64.b64decode(base64_image)

    # Converter para uma imagem PIL
    image = Image.open(BytesIO(image_data))

    # Exibir a imagem no Streamlit
    st.image(image, width=350)

@st.cache(allow_output_mutation=True)    
def getPlayersFromQuery(query):
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

@st.cache(allow_output_mutation=True)
def getPlayerData(fide_id):
    with sqlite3.connect('./db/fide_data.db') as conn:
        cursor = conn.cursor()

        # Verificar se os dados do jogador já existem
        cursor.execute("SELECT * FROM player_data WHERE fide_id = ?", (fide_id,))
        player_data = cursor.fetchone()

        if player_data:
            keys = ['fide_id', 'name', 'federation', 'b_year', 'sex', 'fide_title', 
                    'std_rating', 'rapid_rating', 'blitz_rating', 'profile_photo', 'world_rank' ]
            return dict(zip(keys, player_data))
        else:
            # Sua lógica de web scraping aqui para buscar dados do jogador
            fetched_player_data = scrapePlayerData(fide_id)
            # Após buscar, inserir os dados no banco de dados
            cursor.execute("INSERT INTO player_data (fide_id, name, federation, b_year, sex, fide_title, std_rating, rapid_rating, blitz_rating, profile_photo, world_rank) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                           (fetched_player_data['fide_id'], fetched_player_data['name'], fetched_player_data['federation'], fetched_player_data['b_year'], fetched_player_data['sex'], fetched_player_data['fide_title'], fetched_player_data['std_rating'], fetched_player_data['rapid_rating'], fetched_player_data['blitz_rating'], fetched_player_data['profile_photo'], fetched_player_data['world_rank']))
            conn.commit()
            return fetched_player_data

def scrapePlayerGamesHistory(fide_id, playerName, startingPeriod, endPeriod):
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

    for link in allLinks:
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

@st.cache(allow_output_mutation=True)
def getPlayerGamesHistory(fide_id, playerName, startingPeriod, endPeriod):
    with sqlite3.connect('./db/fide_data.db') as conn:
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

def insertGameData(cursor, games_df, fide_id):
    if not games_df.empty:
        for index, row in games_df.iterrows():
            cursor.execute("INSERT INTO game_history (fide_id, date, tournament_name, country, player_name, player_rating, player_color, opponent_name, opponent_rating, result, chg, k, k_chg) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                           (fide_id, row['date'], row['tournament_name'], row['country'], row['player_name'], row['player_rating'], row['player_color'], row['opponent_name'], row['opponent_rating'], row['result'], row['chg'], row['k'], row['k_chg']))

def metric_card(title, value, col):
    col.markdown(f"""
    <style>
        .metric-card {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            border: 2px solid #f0f2f6;
            border-radius: 10px;
            padding: 0em;
            background-color: #ffffff;
            box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
            width: 100%; /* Torna a largura do cartão responsiva */
            box-sizing: border-box; /* Inclui padding e borda na largura e altura total do elemento */
            margin-top: 0.5em; /* Adiciona espaço entre os cartões */
        }}
        .metric-title {{
            color: #0e1117;
            margin-bottom: 0em;
            font-size: 1rem; /* Tamanho de fonte responsivo */
        }}
        .metric-value {{
            color: #0e1117;
            margin-top: 0;
            font-size: 1.5rem; /* Tamanho de fonte responsivo */
            font-weight: bold;
        }}
    </style>
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def plot_rating_time_series(games_df):
    if not games_df.empty:
        # Garantir que 'Date' esteja no formato datetime e 'Player Rating' seja numérico
        games_df['date'] = pd.to_datetime(games_df['date'])
        games_df['player_rating'] = pd.to_numeric(games_df['player_rating'], errors='coerce')

        # Ordenar o DataFrame por 'Date' para garantir que o gráfico siga a ordem cronológica
        games_df.sort_values('date', inplace=True)

        plt.figure(figsize=(10, 4))
        plt.plot(games_df['date'], games_df['player_rating'], marker='o', linestyle='-')

        # Opcionalmente, inverter o eixo y, se desejado - para remover essa inversão, comente ou remova a próxima linha
        # plt.gca().invert_yaxis()  # Descomente esta linha se você realmente quiser inverter o eixo y

        plt.title('Rating Clássico ao Longo do Tempo')
        plt.xlabel('Data')
        plt.ylabel('Rating Clássico')
        plt.grid(True)
        plt.tight_layout()
        st.pyplot(plt)
    else:
        st.write("Nenhum dado de rating disponível para plotar.")

def clean_and_prepare_dataframe(df):
    if not df.empty:
        duplicate_columns = ['date', 'tournament_name', 'player_name', 'opponent_name', 'result']
        df.drop_duplicates(subset=duplicate_columns, inplace=True)
        df.sort_values('date', inplace=True)
        df.dropna(inplace=True)
        df.reset_index(drop=True, inplace=True)
    return df

# Função para criar gráficos de pizza
def create_pie_chart(sizes, labels, title):
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    plt.title(title)
    return fig

# Função Aprimorada para Criar um Gráfico de Barras
def create_enhanced_bar_chart(values, categories, title):
    fig, ax = plt.subplots(figsize=(16, 6))
    colors = ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink']
    ax.bar(categories, values, color=colors)
    ax.set_ylabel('Rating Médio do Oponente')
    ax.set_title(title)
    plt.xticks(rotation=45)
    for i, v in enumerate(values):
        ax.text(i, v + 3, f"{v:.0f}", ha='center', va='bottom')
    return fig

# Inicializar o banco de dados e as tabelas
initialize_database()
remove_duplicates_in_db()

st.set_page_config(layout="wide")

# Barra lateral para entradas
players = []
with st.sidebar:
    st.title('Pesquisar Jogador da FIDE')
    query = st.text_input('Digite o Sobrenome do Jogador:')
    starting_date = st.date_input('Data de Início', value=datetime.now() - relativedelta.relativedelta(years=1))
    end_date = st.date_input('Data de Fim', value=datetime.now())
    # Ajustar datas para o primeiro dia do mês
    starting_date = starting_date.replace(day=1)
    end_date = end_date.replace(day=1)

    if query:  # Proceder apenas se uma consulta for inserida
        with st.spinner('Pesquisando jogadores...'):
            players = getPlayersFromQuery(query)
        
        if players:
            player_options = ["Selecione um jogador..."] + [f"{player['name']} ({player['title']})" for player in players]
            selected_option = st.selectbox('Selecione um jogador:', player_options)
        else:
            st.write("Nenhum jogador encontrado. Tente uma consulta diferente.")

# Título do aplicativo Streamlit
st.title('Estatísticas de Jogadores e Jogos da FIDE')

if players and 'selected_option' in locals() and selected_option != "Selecione um jogador...":
    selected_player_info = next(player for player in players if f"{player['name']} ({player['title']})" == selected_option)
    selected_fide_id = selected_player_info['id']
    
    with st.spinner(f'Buscando dados para {selected_player_info["name"]}...'):
        player_data = getPlayerData(selected_fide_id)
        player_games_history = getPlayerGamesHistory(selected_fide_id, player_data['name'], starting_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        player_games_history = clean_and_prepare_dataframe(player_games_history)

    st.header('Perfil do Jogador')
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        displayProfilePhoto(player_data.get('profile_photo', 'N/A'))

    metric_card('Nome', player_data.get('name', 'N/A'), col2)
    metric_card('Federação', player_data.get('federation', 'N/A'), col2)
    metric_card('Classificação Mundial', player_data.get('world_rank', 'N/A') if player_data.get('world_rank') else "-", col2)

    b_year = player_data.get('b_year', 'N/A')
    metric_card('Ano de Nascimento', b_year, col3)
    metric_card('Título da FIDE', player_data.get('fide_title', 'N/A'), col3)
        
    metric_card('Rating Clássico Atual', player_data.get('std_rating', 'N/A'), col2)
    metric_card('Rating Rápido Atual', player_data.get('rapid_rating', 'N/A'), col3)
    metric_card('Rating Blitz Atual', player_data.get('blitz_rating', 'N/A'), col3)

    # Calcular e exibir estatísticas de jogo
    if not player_games_history.empty:
        # Garantir que player_games_history esteja ordenado por data
        player_games_history['date'] = pd.to_datetime(player_games_history['date'])
        player_games_history.sort_values('date', inplace=True)
        player_games_history['player_rating'] = pd.to_numeric(player_games_history['player_rating'], errors='coerce')
        
        initial_rating = player_games_history.iloc[0]['player_rating']
        final_rating = player_games_history.iloc[-1]['player_rating']
        delta_rating = final_rating - initial_rating
        
        player_games_history['opponent_rating'] = pd.to_numeric(player_games_history['opponent_rating'], errors='coerce')
        avg_opponent_rating = player_games_history['opponent_rating'].mean()
        player_games_history['result'] = player_games_history['result'].astype(float)
        results = player_games_history['result'].value_counts(normalize=True) * 100
        taxa_de_vitória = results.get(1.0, 0)
        taxa_de_empate = results.get(0.5, 0)
        taxa_de_derrota = results.get(0.0, 0)
        
        avg_opponent_rating_win = player_games_history[player_games_history['result'] == 1.0]['opponent_rating'].mean()
        avg_opponent_rating_draw = player_games_history[player_games_history['result'] == 0.5]['opponent_rating'].mean()
        avg_opponent_rating_loss = player_games_history[player_games_history['result'] == 0.0]['opponent_rating'].mean()
        
        minDateString = player_games_history['date'].min().strftime("%Y-%m-%d")
        maxDateString = player_games_history['date'].max().strftime("%Y-%m-%d")
        st.header(f'Evolução do Rating')
        st.info(f'Jogos encontrados de {minDateString} a {maxDateString}')
        super_metrics_col1, super_metrics_col2, = st.columns([1, 2])  
        metric_card('Total de Jogos (Contagem)', f"{len(player_games_history)}", super_metrics_col1)
        metric_card('Rating Médio do Oponente - Geral', f"{avg_opponent_rating:.2f}", super_metrics_col1)
        metric_card('Delta de Rating', f"{delta_rating}", super_metrics_col1)
        with super_metrics_col2:
            plot_rating_time_series(player_games_history)
            
        st.header('Estatísticas de Jogo')
        # Calcular estatísticas para gráficos de pizza
        win_count = len(player_games_history[player_games_history['result'] == 1.0])
        draw_count = len(player_games_history[player_games_history['result'] == 0.5])
        loss_count = len(player_games_history[player_games_history['result'] == 0.0])

        games_as_white = player_games_history[player_games_history['player_color'] == 'white']
        win_white = len(games_as_white[games_as_white['result'] == 1.0])
        draw_white = len(games_as_white[games_as_white['result'] == 0.5])
        loss_white = len(games_as_white[games_as_white['result'] == 0.0])

        games_as_black = player_games_history[player_games_history['player_color'] == 'black']
        win_black = len(games_as_black[games_as_black['result'] == 1.0])
        draw_black = len(games_as_black[games_as_black['result'] == 0.5])
        loss_black = len(games_as_black[games_as_black['result'] == 0.0])

        # Calcular classificações médias do oponente para gráfico de barras
        overall_avg_rating = player_games_history['opponent_rating'].mean()
        white_avg_rating = games_as_white['opponent_rating'].mean()
        black_avg_rating = games_as_black['opponent_rating'].mean()

        # Gráficos de pizza
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Desempenho Geral")
            fig1 = create_pie_chart([win_count, draw_count, loss_count], ['Vitórias', 'Empates', 'Derrotas'], 'Geral')
            st.pyplot(fig1)

        with col2:
            st.subheader("Desempenho como Brancas")
            fig2 = create_pie_chart([win_white, draw_white, loss_white], ['Vitórias', 'Empates', 'Derrotas'], 'Como Brancas')
            st.pyplot(fig2)

        with col3:
            st.subheader("Desempenho como Pretas")
            fig3 = create_pie_chart([win_black, draw_black, loss_black], ['Vitórias', 'Empates', 'Derrotas'], 'Como Pretas')
            st.pyplot(fig3)
            
        # Calculando a média detalhada de rating dos oponentes para gráfico de barras
        categorias = ['Geral', 'Vitória como Brancas', 'Empate como Brancas', 'Derrota como Brancas',
                    'Vitória como Pretas', 'Empate como Pretas', 'Derrota como Pretas']

        overall_avg = player_games_history['opponent_rating'].mean()

        wins_white_avg = player_games_history[(player_games_history['player_color'] == 'white') & (player_games_history['result'] == 1.0)]['opponent_rating'].mean()
        draws_white_avg = player_games_history[(player_games_history['player_color'] == 'white') & (player_games_history['result'] == 0.5)]['opponent_rating'].mean()
        losses_white_avg = player_games_history[(player_games_history['player_color'] == 'white') & (player_games_history['result'] == 0.0)]['opponent_rating'].mean()

        wins_black_avg = player_games_history[(player_games_history['player_color'] == 'black') & (player_games_history['result'] == 1.0)]['opponent_rating'].mean()
        draws_black_avg = player_games_history[(player_games_history['player_color'] == 'black') & (player_games_history['result'] == 0.5)]['opponent_rating'].mean()
        losses_black_avg = player_games_history[(player_games_history['player_color'] == 'black') & (player_games_history['result'] == 0.0)]['opponent_rating'].mean()

        valores = [overall_avg, wins_white_avg, draws_white_avg, losses_white_avg,
                wins_black_avg, draws_black_avg, losses_black_avg]

        # Gráficos de pizza em colunas para distribuição visual de vitórias, empates e derrotas
        col1, col2, col3 = st.columns(3)
        # Usar a função create_pie_chart para col1, col2, col3 como antes

        # Gráfico de barras aprimorado para uma comparação detalhada de ratings médios dos oponentes
        st.subheader("Métricas de Desempenho Detalhadas")
        fig = create_enhanced_bar_chart(valores, categorias, 'Ratings Médios dos Adversários')
        st.pyplot(fig)

        # Seção de Histórico de Jogos
        st.write(" ")
        st.write(" ")
        st.header('Histórico de Jogos')

        # Garantir que colunas numéricas sejam do tipo numérico
        player_games_history['result'] = pd.to_numeric(player_games_history['result'], errors='coerce')

        # Aplicar filtros
        filtered_games_history = player_games_history.copy()  # Criar uma cópia para evitar modificar o DataFrame original

        # Opções de filtro
        filter_options = {
            'Resultado do Jogo': st.multiselect('Selecione o resultado do jogo:', ['Vitória', 'Empate', 'Derrota']),
            'Nome do Oponente Contém': st.text_input('Digite um substring do nome do oponente:')
        }

        # Filtrar por resultado do jogo
        if 'Resultado do Jogo' in filter_options and filter_options['Resultado do Jogo']:
            filtered_results = []
            if 'Vitória' in filter_options['Resultado do Jogo']:
                filtered_results.append(1.0)
            if 'Empate' in filter_options['Resultado do Jogo']:
                filtered_results.append(0.5)
            if 'Derrota' in filter_options['Resultado do Jogo']:
                filtered_results.append(0.0)
            filtered_games_history = filtered_games_history[filtered_games_history['result'].isin(filtered_results)]

        # Filtrar por substring do nome do oponente
        if 'Nome do Oponente Contém' in filter_options and filter_options['Nome do Oponente Contém']:
            substring = filter_options['Nome do Oponente Contém'].strip().lower()
            filtered_games_history = filtered_games_history[filtered_games_history['opponent_name'].str.lower().str.contains(substring)]
            oponentes_no_filtro = list(filtered_games_history['opponent_name'].unique())
            oponentes_no_filtro.sort()
            oponentes_no_filtro = '/ '.join(oponentes_no_filtro)
            st.info(f'Jogos encontrados contra {oponentes_no_filtro}')
            num_vitorias = (filtered_games_history['result'] == 1.0).sum()
            num_empates = (filtered_games_history['result'] == 0.5).sum()
            num_derrotas = (filtered_games_history['result'] == 0.0).sum()
            scoreCol1, scoreCol2, scoreCol3 = st.columns(3)
            metric_card('Vitórias (Contagem)', f"{num_vitorias}", scoreCol1)
            metric_card('Empates (Contagem)', f"{num_empates}", scoreCol2)
            metric_card('Derrotas (Contagem)', f"{num_derrotas}", scoreCol3)
            
        # Agora aplicar formatação e exibir o DataFrame filtrado
        st.table(filtered_games_history[['date', 'tournament_name', 'player_name', 'player_rating', 'player_color', 'opponent_name', 'opponent_rating', 'result', 'chg', 'k', 'k_chg']])

else:
    st.text(" ")
    st.text(" ")
    st.subheader("Nenhum jogo encontrado no período especificado.")

# Seção de Mensagem Promocional
st.sidebar.write("---")  # Desenha uma linha horizontal para separação visual
st.sidebar.image("XB-logo.png", width=100)
st.sidebar.header("Melhore Seu Xadrez com o XB PRO")
st.sidebar.write("""
Procurando elevar seu jogo de xadrez? Confira o [XB PRO](https://xadrezbrasil.com.br) - seu destino final para aprendizado e melhoria no xadrez. Seja você iniciante ou jogador avançado, o XB PRO oferece conteúdo personalizado para ajudá-lo a crescer.
""")
# Usando st.markdown para criar um link que parece um botão
estilo_do_botao = """
<a href='https://xadrezbrasil.com.br' target='_blank'>
    <button style='color: white; background-color: #4CAF50; border: none; padding: 10px 20px; text-align: center; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer; border-radius: 12px;'>
        Visite o XB PRO Agora!
    </button>
</a>
"""
st.sidebar.markdown(estilo_do_botao, unsafe_allow_html=True)
st.sidebar.write("---")  # Desenha uma linha horizontal para separação visual

# Caminho para o seu banco de dados SQLite
caminho_db = './db/fide_data.db'

# Verificar se o arquivo existe para evitar erros
#if os.path.isfile(caminho_db):
    # Maneira do Streamlit de criar um botão de download
#    with open(caminho_db, "rb") as fp:
#        btn = st.sidebar.download_button(
#            label="Baixar Banco de Dados",
#            data=fp,
#            file_name="fide_data.db",
#            mime="application/x-sqlite3"
#        )
#else:
#    st.error("Arquivo do banco de dados não encontrado!")

