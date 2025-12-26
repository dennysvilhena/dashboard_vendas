import streamlit as st
import pandas as pd
import time
from sqlalchemy import create_engine
from urllib.parse import quote_plus

# Configuração da Página
st.set_page_config(layout="wide")
st.title('DADOS BRUTOS :memo:')

# --- CONEXÃO COM O BANCO ---
db_user = st.secrets["postgres"]["user"]
db_pass = st.secrets["postgres"]["password"]
db_host = st.secrets["postgres"]["host"]
db_port = st.secrets["postgres"]["port"]
db_name = st.secrets["postgres"]["dbname"]

encoded_pass = quote_plus(db_pass)
connection_string = f'postgresql+psycopg2://{db_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}'
engine = create_engine(connection_string)

# Carrega os dados
@st.cache_data
def carrega_dados():
    query = "SELECT * FROM vendas_analitico"
    df = pd.read_sql(query, engine)
    df['data_venda'] = pd.to_datetime(df['data_venda'])
    return df

dados = carrega_dados()

# --- FUNÇÃO DE CONVERSÃO PARA CSV ---
@st.cache_data
def converte_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- FUNÇÃO DE MENSAGEM DE SUCESSO ---
def mensagem_sucesso():
    sucesso = st.success('Arquivo baixado com sucesso!', icon="✅")
    time.sleep(5)
    sucesso.empty()

# =========================================================
# FILTROS (BARRA LATERAL)
# =========================================================
st.sidebar.title('Filtros')

with st.sidebar.expander('Nome do produto'):
    produtos = st.multiselect('Selecione os produtos', dados['produto'].unique(), dados['produto'].unique())

with st.sidebar.expander('Preço do produto'):
    preco = st.slider('Selecione o preço', 
                      float(dados['valor'].min()), 
                      float(dados['valor'].max()), 
                      (float(dados['valor'].min()), float(dados['valor'].max())))

with st.sidebar.expander('Data da compra'):
    data_compra = st.date_input('Selecione a data', (dados['data_venda'].min(), dados['data_venda'].max()))

with st.sidebar.expander('Vendedor'):
    vendedores = st.multiselect('Selecione os vendedores', dados['vendedor'].unique(), dados['vendedor'].unique())

with st.sidebar.expander('Local da compra'):
    local_compra = st.multiselect('Selecione o local da compra', dados['loja'].unique(), dados['loja'].unique())

# =========================================================
# LÓGICA DE FILTRAGEM (QUERY)
# =========================================================
query = '''
produto in @produtos and \
@preco[0] <= valor <= @preco[1] and \
@data_compra[0] <= data_venda <= @data_compra[1] and \
vendedor in @vendedores and \
loja in @local_compra
'''

dados_filtrados = dados.query(query)

# =========================================================
# EXIBIÇÃO E DOWNLOAD
# =========================================================

# Filtro de Colunas visual
with st.expander('Colunas'):
    colunas = st.multiselect('Selecione as colunas', list(dados_filtrados.columns), list(dados_filtrados.columns))

if colunas:
    # Exibe tabela filtrada
    dados_exibicao = dados_filtrados[colunas]
    
    st.dataframe(dados_exibicao, column_config={
        "data_venda": st.column_config.DateColumn("Data da Venda", format="DD/MM/YYYY"),
        "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
    }, use_container_width=True)

    # Exibe métricas
    st.markdown(f'A tabela possui :blue[{dados_exibicao.shape[0]}] linhas e :blue[{dados_exibicao.shape[1]}] colunas')
    
    st.markdown("---")

    # --- ÁREA DE DOWNLOAD ---
    st.markdown('### Download da Tabela')
    st.markdown('Escreva um nome para o arquivo:')
    
    coluna1, coluna2 = st.columns(2)
    
    with coluna1:
        nome_arquivo = st.text_input('', label_visibility='collapsed', value='dados_vendas')
        nome_arquivo += '.csv'
        
    with coluna2:
        st.download_button(
            'Fazer o download da tabela em CSV',
            data=converte_csv(dados_exibicao),
            file_name=nome_arquivo,
            mime='text/csv',
            on_click=mensagem_sucesso
        )
        
else:
    st.warning("Selecione pelo menos uma coluna.")
