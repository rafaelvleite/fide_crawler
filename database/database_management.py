import sqlite3

def initialize_database():
    conn = sqlite3.connect('./database/fide_data.db')
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

def remove_duplicates_in_db():
    with sqlite3.connect('./database/fide_data.db') as conn:
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
        
