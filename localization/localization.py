import json

def load_localization(lang='en'):
    # O caminho do arquivo é relativo ao diretório de onde o script Python é executado
    path = 'localization/localization.json'
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get(lang, {})