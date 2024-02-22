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

def get_binary_file_downloader_html(bin_file, file_label='File'):
    with open(bin_file, 'rb') as f:
        data = f.read()
    bin_str = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{bin_str}" download="{os.path.basename(bin_file)}">Download {file_label}</a>'
    return href

def initialize_database():
    conn = sqlite3.connect('./db/fide_data.db')
    cursor = conn.cursor()

    # Create the player_data table if it doesn't exist
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

    # Create the game_history table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS game_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fide_id TEXT,
        date TEXT,
        tournament_name TEXT,
        country TEXT,
        player_name TEXT,
        player_rating TEXT,
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
    # Strip the prefix from the Base64 string
    base64_image = base64_image.split(",")[1]

    # Decode the Base64 string
    image_data = base64.b64decode(base64_image)

    # Convert to a PIL image
    image = Image.open(BytesIO(image_data))

    # Display the image in Streamlit
    st.image(image, width=350)
    
def getPlayersFromQuery(query):

    # Set the URL for the search query
    url = "https://fide.com/search"

    # Headers based on the information provided
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

    # The query parameters
    params = {'query': query}

    # Making the GET request
    response = requests.get(url, headers=headers, params=params)

    # Checking if the request was successful
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        search_blocks = soup.find_all('div', class_='member-block')
    
        # Initialize a list to store player information
        players = []

        for block in search_blocks:
            player_entries = block.find_all(class_="member-block__one")
            
            for entry in player_entries:
                # Extract player name
                player_name = entry.find(class_="member-block-info-position").get_text(strip=True)
                
                # Extract player title if available
                player_title = entry.find(class_="member-block-info-name")
                player_title = player_title.get_text(strip=True) if player_title else "No title"
                
                # Extract player profile URL
                player_url = entry.find('a')['href']
                
                # Extract player ID from URL using regex
                player_id_match = re.search(r'/profile/(\d+)', player_url)
                player_id = player_id_match.group(1) if player_id_match else "No ID"

                # Append the extracted information to the players list
                if 'profile' in player_url and 'news' not in player_url:
                    players.append({
                        'name': player_name,
                        'title': player_title,
                        'url': player_url,
                        'id': player_id  # Add player ID to the dictionary
                    })   
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}")

    return players

def scrapePlayerData(fide_id):
    url = f'https://ratings.fide.com/profile/{fide_id}'
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')

    player_data = {}
    player_data = {'fide_id': fide_id}  # Include the fide_id in the player_data
    player_data['name'] = soup.find('div', class_='profile-top-title').text.strip()
    player_data['world_rank'] = soup.find('div', text='World Rank (Active):').find_next_sibling('div').text
    player_data['federation'] = soup.find('div', text='Federation:').find_next_sibling('div').text
    player_data['b_year'] = soup.find('div', text='B-Year:').find_next_sibling('div').text
    player_data['sex'] = soup.find('div', text='Sex:').find_next_sibling('div').text
    player_data['fide_title'] = soup.find('div', text='FIDE title:').find_next_sibling('div').text
    profile_photo_div = soup.find('div', class_='profile-top__photo')
    img_tag = profile_photo_div.find('img') if profile_photo_div else None
    src_value = img_tag['src'] if img_tag else None
    player_data['profile_photo'] = src_value

    # Extracting rating info
    ratings = soup.select('.profile-top-rating-data')
    for rating in ratings:
        rating_type = rating.find('span').text.strip().lower()  
        rating_value = ''.join(filter(str.isdigit, rating.text))  
        player_data[f'{rating_type}_rating'] = rating_value

    return player_data

def getPlayerData(fide_id):
    with sqlite3.connect('./db/fide_data.db') as conn:
        cursor = conn.cursor()

        # Check if player data already exists
        cursor.execute("SELECT * FROM player_data WHERE fide_id = ?", (fide_id,))
        player_data = cursor.fetchone()

        if player_data:
            keys = ['fide_id', 'name', 'federation', 'b_year', 'sex', 'fide_title', 
                    'std_rating', 'rapid_rating', 'blitz_rating', 'profile_photo', 'world_rank' ]
            return dict(zip(keys, player_data))
        else:
            # Your web scraping logic here to fetch player data
            fetched_player_data = scrapePlayerData(fide_id)
            # After fetching, insert the data into the database
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

    # Updated DataFrame columns to reflect game-level details
    gameDf = pd.DataFrame(columns=['date', 'tournament_name', 'country', 'player_name', 'player_rating', 'opponent_name', 'opponent_rating', 'result', 'chg', 'k', 'k_chg'])

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
            
            for limiter in limiters:
                tournament_name = tableDf.iloc[limiter - 3, 0]
                tournament_date = tableDf.iloc[limiter - 3, 7]
                player_rating = tableDf.iloc[limiter - 1, 1]
                if limiters.index(limiter) < len(limiters) - 1:
                    localDf = tableDf.iloc[limiter + 1:limiters[limiters.index(limiter) + 1] - 3, :]
                else:
                    localDf = tableDf.iloc[limiter + 1:, :]
                
                # Iterate over each game in the tournament
                for _, row in localDf.iterrows():
                    game_details = {
                        'date': tournament_date,
                        'tournament_name': tournament_name,
                        'country': row['Unnamed: 4'],
                        'player_name': playerName,
                        'player_rating': player_rating,
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
    if len(gameDf) > 0:
        gameDf['opponent_rating'] = gameDf['opponent_rating'].astype(str).str.replace(r'\D', '', regex=True)
        gameDf['opponent_rating'] = pd.to_numeric(gameDf['opponent_rating'], errors='coerce')
        gameDf['result'] = gameDf['result'].astype(float)


    return gameDf

def getPlayerGamesHistory(fide_id, playerName, startingPeriod, endPeriod):
    with sqlite3.connect('./db/fide_data.db') as conn:
        cursor = conn.cursor()

        # Check if games for the player exist within the date range
        cursor.execute("SELECT date FROM game_history WHERE fide_id = ? AND date BETWEEN ? AND ?", (fide_id, startingPeriod, endPeriod))
        existing_dates = cursor.fetchall()

        # Convert list of tuples to list of strings for easier comparison
        existing_dates = [date[0] for date in existing_dates]
        
        # Generate a list of all months in the requested period
        requested_period = pd.date_range(start=startingPeriod, end=endPeriod, freq='MS').strftime('%Y-%m-%d').tolist()

        # Determine which months in the requested period are missing from the database
        missing_months = [date for date in requested_period if date not in existing_dates]

        # If there are missing months, fetch data for those months and update the database
        if missing_months:
            for month in missing_months:
                # Assuming scrapePlayerGamesHistory fetches data for a single month
                # You may need to adjust this part to fit your actual data fetching and processing logic
                fetched_games_df = scrapePlayerGamesHistory(fide_id, playerName, month, month)
                if not fetched_games_df.empty:
                    # After fetching and processing, insert the data into the database
                    for index, row in fetched_games_df.iterrows():
                        cursor.execute("INSERT INTO game_history (fide_id, date, tournament_name, country, player_name, player_rating, opponent_name, opponent_rating, result, chg, k, k_chg) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                                       (fide_id, row['date'], row['tournament_name'], row['country'], row['player_name'], row['player_rating'], row['opponent_name'], row['opponent_rating'], row['result'], row['chg'], row['k'], row['k_chg']))
                    conn.commit()

        # Fetch and return the complete data for the requested period, now that the database is up to date
        cursor.execute("SELECT * FROM game_history WHERE fide_id = ? AND date BETWEEN ? AND ?", (fide_id, startingPeriod, endPeriod))
        games = cursor.fetchall()
        games_df = pd.DataFrame(games, columns=['id', 'fide_id', 'date', 'tournament_name', 'country', 'player_name', 'player_rating', 'opponent_name', 'opponent_rating', 'result', 'chg', 'k', 'k_chg'])
        
        return games_df

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
            width: 100%; /* Makes the card width responsive */
            box-sizing: border-box; /* Includes padding and border in the element's total width and height */
            margin-top: 0.5em; /* Adds space between cards */
        }}
        .metric-title {{
            color: #0e1117;
            margin-bottom: 0em;
            font-size: 1rem; /* Responsive font size */
        }}
        .metric-value {{
            color: #0e1117;
            margin-top: 0;
            font-size: 1.5rem; /* Responsive font size */
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
        # Ensure 'Date' is in datetime format and 'Player Rating' is numeric
        games_df['date'] = pd.to_datetime(games_df['date'])
        games_df['player_rating'] = pd.to_numeric(games_df['player_rating'], errors='coerce')

        # Sort the DataFrame by 'Date' to ensure the plot follows chronological order
        games_df.sort_values('date', inplace=True)

        plt.figure(figsize=(10, 4))
        plt.plot(games_df['date'], games_df['player_rating'], marker='o', linestyle='-')

        # Optionally, invert the y-axis if desired - to remove this inversion, comment out or remove the next line
        # plt.gca().invert_yaxis()  # Uncomment this line if you actually want to invert the y-axis

        plt.title('Standard Rating Over Time')
        plt.xlabel('Date')
        plt.ylabel('Standard Rating')
        plt.grid(True)
        plt.tight_layout()
        st.pyplot(plt)
    else:
        st.write("No rating data available to plot.")

# Initialize the database and tables
initialize_database()

st.set_page_config(layout="wide")

# Sidebar for inputs
players = []
with st.sidebar:
    st.title('Search for FIDE Player')
    query = st.text_input('Enter player name:')
    starting_date = st.date_input('Start Date', value=datetime.now() - relativedelta.relativedelta(years=1))
    end_date = st.date_input('End Date', value=datetime.now())

    if query:  # Only proceed if a query has been entered
        with st.spinner('Searching for players...'):
            players = getPlayersFromQuery(query)
        
        if players:
            player_options = ["Select a player..."] + [f"{player['name']} ({player['title']})" for player in players]
            selected_option = st.selectbox('Select a player:', player_options)
        else:
            st.write("No players found. Please try a different query.")

# Streamlit app title
st.title('FIDE Player and Game Statistics')

if players and 'selected_option' in locals() and selected_option != "Select a player...":
    selected_player_info = next(player for player in players if f"{player['name']} ({player['title']})" == selected_option)
    selected_fide_id = selected_player_info['id']
    
    with st.spinner(f'Fetching data for {selected_player_info["name"]}...'):
        player_data = getPlayerData(selected_fide_id)
        player_games_history = getPlayerGamesHistory(selected_fide_id, player_data['name'], starting_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
    
    st.header('Player Profile')
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        displayProfilePhoto(player_data.get('profile_photo', 'N/A'))

    metric_card('Name', player_data.get('name', 'N/A'), col2)
    metric_card('Federation', player_data.get('federation', 'N/A'), col2)
    metric_card('World Rank', player_data.get('world_rank', 'N/A'), col2)

    b_year = player_data.get('b_year', 'N/A')
    metric_card('Year of Birth', b_year, col3)
    metric_card('FIDE Title', player_data.get('fide_title', 'N/A'), col3)
        
    metric_card('Current Classical Rating', player_data.get('std_rating', 'N/A'), col2)
    metric_card('Current Rapid Rating', player_data.get('rapid_rating', 'N/A'), col3)
    metric_card('Current Blitz Rating', player_data.get('blitz_rating', 'N/A'), col3)
    
    # Ensure player_games_history is sorted by date
    player_games_history.sort_values('date', inplace=True)
    player_games_history['player_rating'] = pd.to_numeric(player_games_history['player_rating'], errors='coerce')

    # Calculating and displaying game statistics
    if not player_games_history.empty:
        initial_rating = player_games_history.iloc[0]['player_rating']
        final_rating = player_games_history.iloc[-1]['player_rating']
        delta_rating = final_rating - initial_rating
        
        player_games_history['opponent_rating'] = pd.to_numeric(player_games_history['opponent_rating'], errors='coerce')
        avg_opponent_rating = player_games_history['opponent_rating'].mean()
        player_games_history['result'] = player_games_history['result'].astype(float)
        results = player_games_history['result'].value_counts(normalize=True) * 100
        win_rate = results.get(1.0, 0)
        draw_rate = results.get(0.5, 0)
        loss_rate = results.get(0.0, 0)
        
        avg_opponent_rating_win = player_games_history[player_games_history['result'] == 1.0]['opponent_rating'].mean()
        avg_opponent_rating_draw = player_games_history[player_games_history['result'] == 0.5]['opponent_rating'].mean()
        avg_opponent_rating_loss = player_games_history[player_games_history['result'] == 0.0]['opponent_rating'].mean()
        
        minDateString = player_games_history['date'].min()
        maxDateString = player_games_history['date'].max()
        st.header(f'Rating Evolution')
        st.info(f'Games found from {minDateString} to {maxDateString}')
        super_metrics_col1, super_metrics_col2, = st.columns([1, 2])  
        metric_card('Total Games (Count)', f"{len(player_games_history)}", super_metrics_col1)
        metric_card('Overall Avg. Opponent Rating', f"{avg_opponent_rating:.2f}", super_metrics_col1)
        metric_card('Delta Rating', f"{delta_rating}", super_metrics_col1)
        with super_metrics_col2:
            plot_rating_time_series(player_games_history)
            
        st.header('Game Statistics')
                
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)  
        
        metric_card('Win Rate', f"{win_rate:.2f}%", metrics_col1)  
        metric_card('Draw Rate', f"{draw_rate:.2f}%", metrics_col2)  
        metric_card('Loss Rate', f"{loss_rate:.2f}%", metrics_col3)  
        opponent_metrics_col1, opponent_metrics_col2, opponent_metrics_col3 = st.columns(3)
        metric_card('Avg. Rating of Opponents (Wins)', f"{avg_opponent_rating_win:.2f}", opponent_metrics_col1)
        metric_card('Avg. Rating of Opponents (Draws)', f"{avg_opponent_rating_draw:.2f}", opponent_metrics_col2)
        metric_card('Avg. Rating of Opponents (Losses)', f"{avg_opponent_rating_loss:.2f}", opponent_metrics_col3)
        
        # Assuming player_games_history['result'] contains the game outcomes as float (1.0 for win, 0.5 for draw, 0.0 for loss)

        # Calculating result counts
        results_counts = player_games_history['result'].value_counts()

        # Extracting counts for win, draw, and loss
        win_count = results_counts.get(1.0, 0)
        draw_count = results_counts.get(0.5, 0)
        loss_count = results_counts.get(0.0, 0)

        # You can display these counts similarly to how you've displayed the rates
        metric_card('Wins (Count)', f"{win_count}", metrics_col1)  
        metric_card('Draws (Count)', f"{draw_count}", metrics_col2)  
        metric_card('Losses (Count)', f"{loss_count}", metrics_col3)  
        
        # Display Games History Section
        st.header('Games History')
        # Ensure numeric columns are of a numeric dtype
        numeric_cols = ['player_rating', 'opponent_rating', 'result', 'chg', 'k', 'k_chg']
        for col in numeric_cols:
            player_games_history[col] = pd.to_numeric(player_games_history[col], errors='coerce')

        # Now apply formatting and display the DataFrame
        st.table(player_games_history[['date', 'tournament_name', 'country', 'player_name', 'player_rating', 'opponent_name', 'opponent_rating', 'result', 'chg', 'k', 'k_chg']])

    else:
        st.write("No games found in the specified period.")

# Promotional Message Section
st.sidebar.write("---")  # Draws a horizontal line for visual separation
st.sidebar.image("XB-logo.png", width=100)
st.sidebar.header("Improve Your Chess with XB PRO")
st.sidebar.write("""
Looking to elevate your chess game? Check out [XB PRO](https://xadrezbrasil.com.br) - your ultimate destination for chess learning and improvement. Whether you're a beginner or an advanced player, XB PRO offers tailored content to help you grow. 
""")
# Using st.markdown to create a link that looks like a button
button_style = """
<a href='https://xadrezbrasil.com.br' target='_blank'>
    <button style='color: white; background-color: #4CAF50; border: none; padding: 10px 20px; text-align: center; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer; border-radius: 12px;'>
        Visit XB PRO Now!
    </button>
</a>
"""
st.sidebar.markdown(button_style, unsafe_allow_html=True)
st.sidebar.write("---")  # Draws a horizontal line for visual separation

# Path to your SQLite database
db_path = './db/fide_data.db'

# Check if the file exists to avoid errors
#if os.path.isfile(db_path):
    # Streamlit's way to create a download button
#    with open(db_path, "rb") as fp:
#        btn = st.sidebar.download_button(
#            label="Download Database",
#            data=fp,
#            file_name="fide_data.db",
#            mime="application/x-sqlite3"
#        )
#else:
#    st.error("Database file not found!")



