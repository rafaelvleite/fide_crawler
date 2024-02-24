import streamlit as st
from database.database_management import initialize_database, remove_duplicates_in_db
from ui.streamlit_ui import user_input_sidebar, displayPlayerProfile, displayPlayerELOEvolution,\
        displayPlayerLast3Tournaments, displayPlayerPerformanceDetails, displayPlayerGamesHistory, \
        displayDownloadDbButton

# Inicializar o banco de dados e as tabelas
initialize_database()
remove_duplicates_in_db()

# Layout
st.set_page_config(layout="wide")

def getLanguage():
    # Initialize the language in session state if not already done
    if 'lang' not in st.session_state:
        st.session_state['lang'] = 'pt'

    # Use columns to align flags on the right
    col1, col2, col3 = st.columns([1, 0.1, 0.1])  # Adjust spacing as needed

    # Use the empty columns for spacing and the last two columns for flags
    with col2:
        if st.button('🇺🇸', key='en'):
            st.session_state['lang'] = 'en'
            
    with col3:
        if st.button('🇧🇷', key='pt'):
            st.session_state['lang'] = 'pt'

    # Return the current language from session state
    return st.session_state['lang']

# Call the function to get the current language
lang = getLanguage()


# Barra lateral para entradas de pesquisa
localization_data, players, query, starting_date, end_date, selected_option = user_input_sidebar(lang)

# Título do aplicativo Streamlit
st.title(localization_data['app_title'])

# Perfil do Jogador
player_data, player_games_history = displayPlayerProfile(players, selected_option, starting_date, end_date, localization_data)

# Calcular e exibir estatísticas de jogo
if players and 'selected_option' in locals() and selected_option != localization_data['player_select']:
    displayPlayerELOEvolution(player_games_history, localization_data)
    displayPlayerLast3Tournaments(player_games_history, localization_data)
    displayPlayerPerformanceDetails(player_games_history, localization_data)
    displayPlayerGamesHistory(player_games_history, localization_data)
    
else:
    st.text(" ")
    st.text(" ")
    st.subheader(localization_data['no_games_found'])
