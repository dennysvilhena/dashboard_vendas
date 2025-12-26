import streamlit as st
import pandas as pd
import time

# Configuração da Página
st.set_page_config(layout="wide")
st.title('DADOS BRUTOS :memo:')

# --- CARREGAMENTO DE DADOS (VIA CSV) ---
@st.cache_data
def carrega_dados():
    # Lê o mesmo arquivo que está na raiz do projeto
    df = pd.read_csv('vendas.csv')
    df['data_venda'] = pd.to_datetime(df['data_venda'])
    return df

dados = carrega_dados()

# --- FUNÇÕES AUXILIARES ---
@st.cache_data
def converte_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def mensagem_sucesso():
    sucesso = st.success('Arquivo baixado com sucesso!', icon="✅")
    time.sleep(5)
    sucesso.empty()

# ---------------------------------------------------------
# DAQUI PARA BAIXO O CÓDIGO CONTINUA IGUAL...
# ... (Barra lateral, filtros, query, etc.)
