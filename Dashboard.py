import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from urllib.parse import quote_plus

# Configuração da página
st.set_page_config(layout="wide")

# Função de formatação
def formata_numero(valor, prefixo = ''):
    for unidade in ['', 'mil']:
        if valor < 1000:
            return f'{prefixo} {valor:.2f} {unidade}'
        valor /= 1000
    return f'{prefixo} {valor:.2f} milhões'

st.title('DASHBOARD DE VENDAS :shopping_cart:')

# --- CONEXÃO COM O BANCO ---
db_user = st.secrets["postgres"]["user"]
db_pass = st.secrets["postgres"]["password"]
db_host = st.secrets["postgres"]["host"]
db_port = st.secrets["postgres"]["port"]
db_name = st.secrets["postgres"]["dbname"]

encoded_pass = quote_plus(db_pass)
connection_string = f'postgresql+psycopg2://{db_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}'
engine = create_engine(connection_string)

try:
    # 1. CARREGAMENTO DOS DADOS
    query = "SELECT * FROM vendas_analitico"
    dados = pd.read_sql(query, engine)
    dados['data_venda'] = pd.to_datetime(dados['data_venda'])

    # ---------------------------------------------------------
    # --- BARRA LATERAL (FILTROS) ---
    # ---------------------------------------------------------
    st.sidebar.title('Filtros')

    # --- FILTRO 1: REGIÃO ---
    # Como seu banco tem Estados (loja) e não Regiões, fazemos o de-para:
    regioes = ['Brasil', 'Centro-Oeste', 'Nordeste', 'Norte', 'Sudeste', 'Sul']
    regiao = st.sidebar.selectbox('Região', regioes)

    if regiao != 'Brasil':
        # Dicionário para mapear Região -> Siglas dos Estados
        # Adicionei as siglas principais. Se sua base tiver outros estados, adicione aqui.
        mapa_regioes = {
            'Sudeste': ['SP', 'RJ', 'MG', 'ES'],
            'Sul': ['RS', 'SC', 'PR'],
            'Nordeste': ['BA', 'PE', 'CE', 'RN', 'PB', 'MA', 'AL', 'SE', 'PI'],
            'Centro-Oeste': ['DF', 'GO', 'MT', 'MS'],
            'Norte': ['AM', 'PA', 'AC', 'RR', 'RO', 'AP', 'TO']
        }
        # Filtra onde a coluna 'loja' está dentro da lista de estados da região selecionada
        estados_da_regiao = mapa_regioes.get(regiao, [])
        dados = dados[dados['loja'].isin(estados_da_regiao)]

    # --- FILTRO 2: ANO ---
    todos_anos = st.sidebar.checkbox('Dados de todo o período', value=True)
    if not todos_anos:
        # Pega o ano mínimo e máximo dos seus dados para configurar o slider automaticamente
        ano_min = int(dados['data_venda'].dt.year.min())
        ano_max = int(dados['data_venda'].dt.year.max())
        ano = st.sidebar.slider('Ano', ano_min, ano_max, ano_max)
        
        # Filtra pelo ano selecionado
        dados = dados[dados['data_venda'].dt.year == ano]

    # --- FILTRO 3: VENDEDORES ---
    filtro_vendedores = st.sidebar.multiselect('Vendedores', dados['vendedor'].unique())
    if filtro_vendedores:
        # Filtra apenas os vendedores selecionados
        dados = dados[dados['vendedor'].isin(filtro_vendedores)]

    # ---------------------------------------------------------
    # --- PREPARAÇÃO DOS DADOS (PÓS-FILTRO) ---
    # ---------------------------------------------------------
    # Daqui para baixo, a variável 'dados' já está filtrada.
    # Tudo o que for calculado usará apenas o que o usuário escolheu.

    lat_lon_data = {
        'loja': ['SP', 'RJ', 'MG', 'RS', 'PR', 'SC', 'ES'], 
        'lat': [-23.55, -22.90, -19.91, -30.03, -25.42, -27.59, -20.31],
        'lon': [-46.63, -43.17, -43.93, -51.22, -49.27, -48.54, -40.30]
    }
    df_lat_lon = pd.DataFrame(lat_lon_data)
    dados = pd.merge(dados, df_lat_lon, on='loja', how='left')

    dados['Mes'] = dados['data_venda'].dt.month
    dados['Ano'] = dados['data_venda'].dt.year.astype(str)

    # ---------------------------------------------------------
    # --- CRIAÇÃO DOS GRÁFICOS ---
    # ---------------------------------------------------------
    
    # Mapa Receita
    dados_mapa = dados.groupby(['loja', 'lat', 'lon'])[['valor']].sum().reset_index()
    fig_mapa_receita = px.scatter_geo(dados_mapa, lat='lat', lon='lon', size='valor', hover_name='loja', scope='south america', title='Mapa de Receita', size_max=30, template='seaborn')

    # Linha Mensal Receita
    receita_mensal = dados.groupby(['Ano', 'Mes'])[['valor']].sum().reset_index()
    fig_receita_mensal = px.line(receita_mensal, x='Mes', y='valor', markers=True, range_y=(0, receita_mensal['valor'].max()), color='Ano', line_dash='Ano', title='Receita Mensal')
    fig_receita_mensal.update_layout(yaxis_title='Receita')

    # Barras Estados Receita
    receita_estados = dados.groupby('loja')[['valor']].sum().sort_values('valor', ascending=False).reset_index()
    fig_receita_estados = px.bar(receita_estados, x='loja', y='valor', title='Receita por Estado')

    # Barras Categorias Receita
    receita_categorias = dados.groupby('produto')[['valor']].sum().sort_values('valor', ascending=False).reset_index()
    fig_receita_categorias = px.bar(receita_categorias, x='produto', y='valor', title='Receita por Categoria')

    # -- Gráficos Aba Quantidade --
    vendas_estados = dados.groupby(['loja', 'lat', 'lon'])[['valor']].count().reset_index().rename(columns={'valor': 'quantidade'})
    fig_mapa_vendas = px.scatter_geo(vendas_estados, lat='lat', lon='lon', scope='south america', template='seaborn', size='quantidade', hover_name='loja', title='Vendas por Estado (Qtd)')

    vendas_mensal = dados.groupby(['Ano', 'Mes'])[['valor']].count().reset_index().rename(columns={'valor': 'quantidade'})
    fig_vendas_mensal = px.line(vendas_mensal, x='Mes', y='quantidade', markers=True, range_y=(0, vendas_mensal['quantidade'].max()), color='Ano', line_dash='Ano', title='Quantidade de Vendas Mensal')
    fig_vendas_mensal.update_layout(yaxis_title='Qtd Vendas')

    vendas_estados_top = dados.groupby('loja')[['valor']].count().sort_values('valor', ascending=False).head(5).reset_index().rename(columns={'valor': 'quantidade'})
    fig_vendas_estados = px.bar(vendas_estados_top, x='loja', y='quantidade', text_auto=True, title='Top 5 Estados (Qtd)')

    vendas_categorias = dados.groupby('produto')[['valor']].count().sort_values('valor', ascending=False).reset_index().rename(columns={'valor': 'quantidade'})
    fig_vendas_categorias = px.bar(vendas_categorias, x='produto', y='quantidade', text_auto=True, title='Vendas por Categoria (Qtd)')


    # ---------------------------------------------------------
    # --- VISUALIZAÇÃO (TABS) ---
    # ---------------------------------------------------------
    
    aba1, aba2, aba3, aba4 = st.tabs(['Dados', 'Receita', 'Quantidade', 'Vendedores'])

    with aba1:
        st.markdown("### Base de Dados Detalhada")
        st.dataframe(dados, column_config={"data_venda": st.column_config.DateColumn("Data da Venda", format="DD/MM/YYYY")})

    with aba2: # ABA RECEITA
        coluna1, coluna2 = st.columns(2)
        with coluna1:
            st.metric('Receita', formata_numero(dados['valor'].sum(), 'R$'))
            st.plotly_chart(fig_mapa_receita, use_container_width=True)
            st.plotly_chart(fig_receita_estados, use_container_width=True)
        with coluna2:
            st.metric('Quantidade de vendas', formata_numero(dados.shape[0]))
            st.plotly_chart(fig_receita_mensal, use_container_width=True)
            st.plotly_chart(fig_receita_categorias, use_container_width=True)

    with aba3: # ABA QUANTIDADE
        coluna1, coluna2 = st.columns(2)
        with coluna1:
            st.metric('Quantidade Total', formata_numero(dados.shape[0]))
            st.plotly_chart(fig_mapa_vendas, use_container_width=True)
            st.plotly_chart(fig_vendas_estados, use_container_width=True)
        with coluna2:
            st.metric('Receita Total', formata_numero(dados['valor'].sum(), 'R$'))
            st.plotly_chart(fig_vendas_mensal, use_container_width=True)
            st.plotly_chart(fig_vendas_categorias, use_container_width=True)

    with aba4: # ABA VENDEDORES
        qtd_vendedores = st.number_input('Quantidade de vendedores', 2, 10, 5)
        
        vendedores = pd.DataFrame(dados.groupby('vendedor')['valor'].agg(['sum', 'count']))

        fig_receita_vendedores = px.bar(
            vendedores[['sum']].sort_values('sum', ascending=False).head(qtd_vendedores),
            x='sum', y=vendedores[['sum']].sort_values('sum', ascending=False).head(qtd_vendedores).index,
            text_auto=True, title=f'Top {qtd_vendedores} vendedores (receita)'
        )
        fig_receita_vendedores.update_layout(yaxis=dict(autorange="reversed"))

        fig_vendas_vendedores = px.bar(
            vendedores[['count']].sort_values('count', ascending=False).head(qtd_vendedores),
            x='count', y=vendedores[['count']].sort_values('count', ascending=False).head(qtd_vendedores).index,
            text_auto=True, title=f'Top {qtd_vendedores} vendedores (quantidade)'
        )
        fig_vendas_vendedores.update_layout(yaxis=dict(autorange="reversed"))

        coluna1, coluna2 = st.columns(2)
        with coluna1:
            st.metric('Receita', formata_numero(dados['valor'].sum(), 'R$'))
            st.plotly_chart(fig_receita_vendedores, use_container_width=True)
        with coluna2:
            st.metric('Quantidade de vendas', formata_numero(dados.shape[0]))
            st.plotly_chart(fig_vendas_vendedores, use_container_width=True)

except Exception as e:
    st.error(f"Erro: {e}")