import streamlit as st
from PIL import Image
import base64
from io import BytesIO
from datetime import datetime
from dateutil import relativedelta
from localization.localization import load_localization
from data_processing.data_fetching_processing import fetch_players
from data_processing.data_fetching_processing import fetch_player_data, fetch_game_history, process_game_history
from visualizations.visualization import plot_rating_time_series, create_pie_chart, create_enhanced_bar_chart
import pandas as pd
import os

def displayProfilePhoto(base64_image):
    # Remover o prefixo da string Base64
    base64_image = base64_image.split(",")[1]

    # Decodificar a string Base64
    image_data = base64.b64decode(base64_image)

    # Converter para uma imagem PIL
    image = Image.open(BytesIO(image_data))

    # Exibir a imagem no Streamlit
    st.image(image, width=350)

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

def user_input_sidebar():
    # Barra lateral para entradas
    players = []
    with st.sidebar:
        lang = st.sidebar.selectbox("Choose your language / Escolha o seu idioma", ["en", "pt"])
        localization_data = load_localization(lang)
        st.title(localization_data['player_search'])
        query = st.text_input(localization_data['surename_input'])
        starting_date = st.date_input(localization_data['start_date'], value=datetime.now() - relativedelta.relativedelta(years=1))
        end_date = st.date_input(localization_data['end_date'], value=datetime.now())
        # Ajustar datas para o primeiro dia do mês
        starting_date = starting_date   .replace(day=1)
        end_date = end_date.replace(day=1)

        if query:  # Proceder apenas se uma consulta for inserida
            with st.spinner(localization_data['player_searching']):
                players = fetch_players(query)
            
            if players:
                player_options = [localization_data['player_select']] + [f"{player['name']} ({player['title']})" for player in players]
                selected_option = st.selectbox(localization_data['player_select_title'], player_options)
            else:
                st.write(localization_data['player_not_found'])
                return localization_data, None, None, None, None, None
    
            return localization_data, players, query, starting_date, end_date, selected_option
        else:
            return localization_data, None, None, None, None, None
        
def displayPlayerProfile(players, selected_option, starting_date, end_date, localization_data):
    if players and 'selected_option' in locals() and selected_option != localization_data['player_select']:
        selected_player_info = next(player for player in players if f"{player['name']} ({player['title']})" == selected_option)
        selected_fide_id = selected_player_info['id']
        
        with st.spinner(f'{localization_data["fetching_player"]}{selected_player_info["name"]}...'):
            player_data = fetch_player_data(selected_fide_id)
            player_games_history = fetch_game_history(selected_fide_id, player_data['name'], starting_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            player_games_history = process_game_history(player_games_history)

        st.header(localization_data["player_profile"])
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            displayProfilePhoto(player_data.get('profile_photo', 'N/A'))

        metric_card(localization_data['player_name'], player_data.get('name', 'N/A'), col2)
        metric_card(localization_data['player_federation'], player_data.get('federation', 'N/A'), col2)
        metric_card(localization_data['player_rank'], player_data.get('world_rank', 'N/A') if player_data.get('world_rank') else "-", col2)

        b_year = player_data.get('b_year', 'N/A')
        metric_card(localization_data['player_birth_year'], b_year, col3)
        metric_card(localization_data['player_title'], player_data.get('fide_title', 'N/A'), col3)
            
        metric_card(localization_data['player_std_rating'], player_data.get('std_rating', 'N/A'), col2)
        metric_card(localization_data['player_rapid_rating'], player_data.get('rapid_rating', 'N/A'), col3)
        metric_card(localization_data['player_blitz_rating'], player_data.get('blitz_rating', 'N/A'), col3)

        return player_data, player_games_history
    else:
        st.write(localization_data['no_player_selected'])
        return None, None
    
def displayPlayerELOEvolution(player_games_history, localization_data):
    st.header(localization_data['elo_evolution'])

    if len(player_games_history) == 0:
        st.write(localization_data['no_games_found'])
        return
    initial_rating = player_games_history.iloc[0]['player_rating']
    final_rating = player_games_history.iloc[-1]['player_rating']
    delta_rating = final_rating - initial_rating

    avg_opponent_rating = player_games_history['opponent_rating'].mean()
    
    minDateString = player_games_history['date'].min().strftime("%Y-%m-%d")
    maxDateString = player_games_history['date'].max().strftime("%Y-%m-%d")
    st.info(f"{localization_data['games_found']} {minDateString} a {maxDateString}")
    super_metrics_col1, super_metrics_col2, = st.columns([1, 2])  
    metric_card(localization_data['total_games_count'], f"{len(player_games_history)}", super_metrics_col1)
    metric_card(localization_data['avg_opponent_rating_general'], f"{avg_opponent_rating:.2f}", super_metrics_col1)
    metric_card(localization_data['rating_variation'], f"{delta_rating}", super_metrics_col1)
    with super_metrics_col2:
        plot_rating_time_series(player_games_history, localization_data)
    
def displayPlayerLast3Tournments(player_games_history, localization_data):
    st.header(localization_data['latest_3_tournments'])

    if len(player_games_history) == 0:
        st.write(localization_data['insufficient_data'])
        return
    # Agrupar jogos por nome do torneio e data
    player_games_history['result'] = player_games_history['result'].astype(float)
    player_games_history['date'] = pd.to_datetime(player_games_history['date']).dt.strftime('%Y-%m-%d')
    tournament_summary = player_games_history.groupby(['tournament_name', 'date']).agg({
        'opponent_rating': 'mean',  # Média do rating do oponente
        'result': ['sum', 'count']  # Soma dos resultados para calcular pontos e contagem para o número de jogos
    }).reset_index()

    # Renomear colunas para refletir as métricas agregadas
    tournament_summary.columns = ['Nome do Torneio', 'Data', 'Média de Rating do Adverário', 'Pontos', 'Partidas Jogadas']

    # Calcular a performance geral no torneio como uma string (ex: "6/7")
    tournament_summary['Resultado'] = tournament_summary.apply(lambda x: f"{x['Pontos']:.0f}" if x['Pontos'].is_integer() else f"{x['Pontos']}", axis=1) + "/" + tournament_summary['Partidas Jogadas'].astype(str)

    # Ordenar os torneios pela data, do mais recente para o mais antigo
    tournament_summary.sort_values('Data', ascending=False, inplace=True)

    # Selecionar os 3 torneios mais recentes
    latest_3_tournaments = tournament_summary.head(3)

    # Formatar a coluna 'Avg Opponent Rating' para duas casas decimais
    latest_3_tournaments['Média de Rating do Adverário'] = latest_3_tournaments['Média de Rating do Adverário'].apply(lambda x: f"{x:.2f}")
    latest_3_tournaments.reset_index(inplace=True, drop=True)
    latest_3_tournaments.index += 1
    # Exibir a tabela dos 3 torneios mais recentes
    st.table(latest_3_tournaments[['Data', 'Nome do Torneio', 'Média de Rating do Adverário', 'Resultado']])
    
def displayPlayerPerformance(player_games_history, localization_data):
    if len(player_games_history) == 0:
        return      
    
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
        
def displayPlayerPerformanceDetails(player_games_history, localization_data):
    st.subheader("Métricas de Desempenho Detalhadas")

    if len(player_games_history) == 0:
        st.write(localization_data['insufficient_data'])
        return
    # Calculando a média detalhada de rating dos oponentes para gráfico de barras
    categorias = [
        localization_data['general'],
        localization_data['win_as_white'],
        localization_data['draw_as_white'],
        localization_data['loss_as_white'],
        localization_data['win_as_black'],
        localization_data['draw_as_black'],
        localization_data['loss_as_black']
    ]

    overall_avg = player_games_history['opponent_rating'].mean()

    wins_white_avg = player_games_history[(player_games_history['player_color'] == 'white') & (player_games_history['result'] == 1.0)]['opponent_rating'].mean()
    draws_white_avg = player_games_history[(player_games_history['player_color'] == 'white') & (player_games_history['result'] == 0.5)]['opponent_rating'].mean()
    losses_white_avg = player_games_history[(player_games_history['player_color'] == 'white') & (player_games_history['result'] == 0.0)]['opponent_rating'].mean()

    wins_black_avg = player_games_history[(player_games_history['player_color'] == 'black') & (player_games_history['result'] == 1.0)]['opponent_rating'].mean()
    draws_black_avg = player_games_history[(player_games_history['player_color'] == 'black') & (player_games_history['result'] == 0.5)]['opponent_rating'].mean()
    losses_black_avg = player_games_history[(player_games_history['player_color'] == 'black') & (player_games_history['result'] == 0.0)]['opponent_rating'].mean()

    valores = [overall_avg, wins_white_avg, draws_white_avg, losses_white_avg,
            wins_black_avg, draws_black_avg, losses_black_avg]
    
    # Gráfico de barras aprimorado para uma comparação detalhada de ratings médios dos oponentes
    fig = create_enhanced_bar_chart(valores, categorias, 'Ratings Médios dos Adversários', localization_data)
    st.pyplot(fig)

def displayPlayerGamesHistory(player_games_history, localization_data):
    # Seção de Histórico de Jogos
    st.write(" ")
    st.header('Histórico de Jogos')
    
    if len(player_games_history) == 0:
        st.write(localization_data['insufficient_data'])
        return

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
    filtered_games_history['date'] = pd.to_datetime(filtered_games_history['date']).dt.strftime('%Y-%m-%d')
    st.table(filtered_games_history[['date', 'tournament_name', 'player_name', 'player_rating', 'player_color', 'opponent_name', 'opponent_rating', 'result', 'chg', 'k', 'k_chg']])

def displayXbAd():
    # Seção de Mensagem Promocional
    st.sidebar.write("---")  # Desenha uma linha horizontal para separação visual
    st.sidebar.image("./images/XB-logo.png", width=100)
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
    
def displayDownloadDbButton():
    # Caminho para o seu banco de dados SQLite
    caminho_db = './database/fide_data.db'

    # Verificar se o arquivo existe para evitar erros
    if os.path.isfile(caminho_db):
        # Maneira do Streamlit de criar um botão de download
        with open(caminho_db, "rb") as fp:
            btn = st.sidebar.download_button(
                label="Baixar Banco de Dados",
                data=fp,
                file_name="fide_data.db",
                mime="application/x-sqlite3"
            )
    else:
        st.error("Arquivo do banco de dados não encontrado!")

