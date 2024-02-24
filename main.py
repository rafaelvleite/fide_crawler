import streamlit as st
from database.database_management import initialize_database, remove_duplicates_in_db
from ui.streamlit_ui import user_input_sidebar, displayPlayerProfile, displayPlayerELOEvolution,\
        displayPlayerLast3Tournaments, displayPlayerPerformanceDetails, displayPlayerGamesHistory, \
        getLanguage, displayDownloadDbButton

# Inicializar o banco de dados e as tabelas
initialize_database()
remove_duplicates_in_db()

# Layout
st.set_page_config(layout="wide")

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

# Display credits based on the selected language
if lang == 'pt':  # For Portuguese
    st.markdown("""
    **Créditos:**  
    Rafael Leite, Canal Xadrez Brasil  
    [youtube.com/@xadrezbrasil](https://www.youtube.com/@xadrezbrasil)  
    [xadrezbrasil.com.br](https://xadrezbrasil.com.br)
    """, unsafe_allow_html=True)
else:  # For English
    st.markdown("""
    **Credits:**  
    Rafael Leite, Master Move Channel  
    [youtube.com/@mastermovechess](https://www.youtube.com/@mastermovechess)  
    [mastermoveapp.com](https://mastermoveapp.com)
    """, unsafe_allow_html=True)
