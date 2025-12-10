import telebot, json, requests, gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from time import sleep
from datetime import datetime
import os 
import base64 
from dotenv import load_dotenv # Importação necessária para rodar localmente com .env

# =================================================================
# SUPORTE LOCAL (.env)
# 
# Esta função tenta carregar as variáveis de ambiente (incluindo 
# GSPREAD_JSON_BASE64) a partir do arquivo .env, se ele existir.
# É ignorado no ambiente Railway.
# =================================================================
load_dotenv() 

# =================================================================
# CARREGAMENTO E AUTENTICAÇÃO COM GOOGLE SHEETS (VIA BASE64)
# =================================================================

# Tenta obter a string Base64 da variável de ambiente.
# (Vem do .env localmente ou do painel do Railway em produção)
GSPREAD_JSON_BASE64 = os.environ.get('GSPREAD_JSON_BASE64') 

if not GSPREAD_JSON_BASE64:
    print("ERRO FATAL: Variável de ambiente 'GSPREAD_JSON_BASE64' não encontrada.")
    print("Por favor, crie esta variável no Railway (se estiver em produção) ou no seu arquivo .env local.")
    exit(1)

try:
    # 1. Decodifica a string Base64 para o dicionário completo de credenciais
    creds_json_string = base64.b64decode(GSPREAD_JSON_BASE64).decode('utf-8')
    full_creds_dict = json.loads(creds_json_string)
    
    # Extrai o dicionário específico para a autenticação do gspread
    gspread_creds_dict = full_creds_dict['api_sheets']

    # --- CORREÇÃO DA CHAVE PRIVADA ---
    # Este passo é crucial para converter o '\n' literal em quebras de linha reais,
    # que o gspread/google-auth espera.
    private_key_value = gspread_creds_dict['private_key']
    gspread_creds_dict['private_key'] = private_key_value.replace('\\n', '\n')
    # --------------------------------

    # Autorizando o gspread
    gc = gspread.service_account_from_dict(gspread_creds_dict)
    
    print("Autenticação com Google Sheets realizada com sucesso!")

except Exception as e:
    print(f"ERRO DE AUTENTICAÇÃO: No key could be detected.")
    print(f"Detalhes do erro: {e}")
    print("Verifique se o valor da variável 'GSPREAD_JSON_BASE64' foi copiado corretamente e se o JSON de origem está válido.")
    exit(1)

# =================================================================
# Configurando bot e planilha (usando os valores decodificados)
# =================================================================
bot = telebot.TeleBot(full_creds_dict['telegram']['bot_token'])
sheet_url = full_creds_dict['planilha']
shortner_url = full_creds_dict['encurtador']
# Agora usa o chat_id_prod (ID do seu Canal)
chat_id = full_creds_dict['telegram']['chat_id_prod'] 

try:
    sheet = gc.open_by_url(sheet_url)
    worksheet = sheet.sheet1
    df = pd.DataFrame(worksheet.get_all_records())
except Exception as e:
    print(f"ERRO ao acessar a planilha ou ao carregar o DataFrame: {e}")
    print("Verifique se o link da planilha está correto e se o email de serviço tem permissão de leitura.")
    exit(1)


print(f"[FROGGY-LOG] Iniciando as atividades! - {datetime.now()}")
print('-=' * 30)

# Envio da primeira mensagem
bot.send_message(chat_id, "Fala pessoal! Promoções novas hoje!")

# Restante das funções (envioUnico, envioEmLote, etc.) permanece inalterado.

def envioUnico():
    global df, worksheet

    # Descobre o índice da coluna STATUS
    status_col_index = df.columns.get_loc("STATUS") + 1  # +1 porque gspread começa em 1
    # Filtra apenas as linhas que não estão "ENVIADO"
    df_to_send = df[df['STATUS'] != "ENVIADO"]

    if df_to_send.empty:
        print("[FROGGY-LOG] Nenhum produto para enviar.")
        return

    # Pega a primeira linha que precisa enviar
    i = df_to_send.index[0]
    product = df.loc[i].to_dict()


    print(f"[FROGGY-LOG] ERRO ao encurtar URL ({shortner_url}): {e}. Usando link original.")
    final_link = product['LINK']
    
    print(f"[FROGGY-LOG] PRODUTO ENVIADO! ID: {i} | NOME: {product['NOME']} | - {datetime.now()}")

    # Mensagem
    mensagem = f""" 
{product['FRASE']} 🐸

<b>{product['NOME']}</b>

De: <s>{product['VALOR_ANTIGO']}</s>        

<b>Por: {product['VALOR_PROMO']} 😍</b>
<i>CUPOM: {product['CUPOM']} ✨</i>​

Compre aqui:
🛍️ {final_link}
"""
    # Envia foto
    bot.send_photo(chat_id, photo=product["IMAGEM"], caption=mensagem, parse_mode="HTML")
    print('-=' * 30)

    # Atualiza STATUS na planilha
    try:
        worksheet.update_cell(i + 2, status_col_index, "ENVIADO")  # +2 por causa do cabeçalho
        print(f"[FROGGY-LOG] STATUS atualizado para ENVIADO na linha {i+2}")
    except Exception as e:
        print(f"[FROGGY-LOG] ERRO ao atualizar status na planilha: {e}")


def envioEmLote():
    for i in range(len(df)):
        product = df.iloc[i].to_dict()
        print(f"Produto: {product['NOME']} | Preço: {product['VALOR_PROMO']}")
        print(f"Produto: {product['NOME']} | Preço: {product['VALOR_PROMO']}")
        
        bot.send_message(
            chat_id, 
            f"""
            OFERTAS DO SAPO LOUCO 🐸
            {product['FRASE']}

            {product['NOME']}

            De: ~~{product['VALOR_ANTIGO']}~~         
            Por: {product['VALOR_PROMO']} 😍
            CUPOM: {product['CUPOM']} ✨​

            Compre aqui:
            🛍️ {product['LINK']}

            """, parse_mode="HTML")
        print('-=' * 30)

# Executando o código de acordo com o fluxo
envioUnico()
print(f"[FROGGY-LOG] Finalizando envio! - {datetime.now()}")
print(f"[FROGGY-LOG] Aguardando horário...")