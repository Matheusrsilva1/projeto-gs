import os
import datetime
import math
import random
import pandas as pd
import plotly.express as px
import plotly.graph_objects as dict_gr
from plotly.subplots import make_subplots
import streamlit as st
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="URBAN-FLOW - Monitoramento de Enchentes",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS Customizado para Design Premium (Glassmorphism e Cores Harmoniosas)
st.markdown("""
<style>
    /* Importação do Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700;800&display=swap');

    /* Estilização Geral da Página */
    .stApp {
        background-color: #0b0e17;
        color: #f1f3f9;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Títulos e Headers */
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        letter-spacing: -0.5px;
    }
    
    /* Cartões Glassmorphism Premium */
    .metric-card {
        background: rgba(30, 41, 59, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .metric-card:hover {
        transform: translateY(-8px) scale(1.02);
        border-color: rgba(56, 189, 248, 0.5);
        box-shadow: 0 12px 40px rgba(56, 189, 248, 0.15);
    }
    .metric-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        color: #94a3b8;
        font-weight: 600;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-family: 'Outfit', sans-serif !important;
        font-size: 2.4rem;
        font-weight: 800;
        margin: 5px 0;
        color: #ffffff;
    }
    .metric-indicator {
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        margin-top: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Alertas Estilizados */
    .alert-normal {
        background: rgba(16, 185, 129, 0.12) !important;
        color: #10b981 !important;
        border: 1px solid rgba(16, 185, 129, 0.25) !important;
    }
    .alert-warning {
        background: rgba(245, 158, 11, 0.12) !important;
        color: #f59e0b !important;
        border: 1px solid rgba(245, 158, 11, 0.25) !important;
    }
    .alert-critical {
        background: rgba(239, 68, 68, 0.12) !important;
        color: #ef4444 !important;
        border: 1px solid rgba(239, 68, 68, 0.25) !important;
        animation: pulse 2s infinite;
    }
    
    /* Animação Pulsante Suave (Ripple) para Alertas Críticos */
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    
    /* Estilização da Barra Lateral (Sidebar) */
    [data-testid="stSidebar"] {
        background-color: #07090e !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Estilização de Elementos do Streamlit na Sidebar */
    .stMultiSelect, .stDateInput {
        background-color: rgba(30, 41, 59, 0.3) !important;
        border-radius: 8px !important;
    }
    
    /* Remover a faixa branca do cabeçalho superior do Streamlit */
    header, [data-testid="stHeader"] {
        background-color: rgba(0, 0, 0, 0) !important;
        background: transparent !important;
    }
    
    /* Reduzir o espaço superior sobressalente da página para visualização encostada */
    .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 2rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CONEXÃO COM O BANCO DE DADOS (SUPABASE)
# ==============================================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@st.cache_resource(show_spinner="Sincronizando dados meteorológicos com o Supabase...")
def rodar_ingestao_automatica(url, key):
    """Executa a ingestão de dados de clima da API e popula o Supabase apenas uma vez por ciclo do servidor."""
    if url and key and "your-project-id" not in url:
        try:
            import sys
            import logging
            # Garante que o diretório do projeto esteja no path
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            import ingest
            
            # Desativa os logs repetitivos do HTTP do Supabase/requests no Streamlit
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("httpcore").setLevel(logging.WARNING)
            
            ingest.main()
            return True, "Base de dados atualizada em tempo real via Open-Meteo API!"
        except Exception as e:
            return False, f"Falha na sincronização automatizada: {e}"
    return False, "Credenciais do Supabase ausentes ou inválidas."

@st.cache_data(ttl=120)  # Cache de 2 minutos para performance
def carregar_dados_supabase(url, key):
    """Conecta ao Supabase e lê os dados realizando os JOINs necessários pelo Snowflake."""
    from supabase import create_client
    try:
        supabase = create_client(url, key)
        # Realiza os joins relacionando Fato -> Tempo, Bairros -> Cidades e Fato -> Fontes
        query_res = supabase.table("fato_medicoes_chuva").select(
            "*, dim_tempo(*), dim_bairros(*, dim_cidades(*)), dim_fontes_dados(*)"
        ).order("id", desc=False).execute()
        
        data = query_res.data
        if not data:
            return None, "O banco de dados está conectado, mas as tabelas estão vazias. Execute o script 'ingest.py' para povoá-lo."
        
        # Aplanar o JSON retornado em um DataFrame do Pandas
        flat_records = []
        for row in data:
            if not row.get("dim_tempo") or not row.get("dim_bairros"):
                continue  # Evitar registros corrompidos ou inconsistentes
            
            bairro_data = row["dim_bairros"]
            cidade_data = bairro_data.get("dim_cidades") if bairro_data else None
            tempo_data = row["dim_tempo"]
            fonte_data = row.get("dim_fontes_dados")
            
            flat_records.append({
                "id": row["id"],
                "volume_chuva_mm": row["volume_chuva_mm"],
                "nivel_rio_metros": row["nivel_rio_metros"],
                "risco_enchente": row["risco_enchente"],
                "data": tempo_data["data"],
                "hora": tempo_data["hora"],
                "data_hora": pd.to_datetime(f"{tempo_data['data']} {tempo_data['hora']}"),
                "dia_da_semana": tempo_data["dia_da_semana"],
                "mes": tempo_data["mes"],
                "ano": tempo_data["ano"],
                "bairro": bairro_data["nome_bairro"] if bairro_data else "Desconhecido",
                "latitude": float(bairro_data["latitude"]) if bairro_data else 0.0,
                "longitude": float(bairro_data["longitude"]) if bairro_data else 0.0,
                "cidade": cidade_data["nome_cidade"] if cidade_data else "Desconhecido",
                "estado": cidade_data["estado"] if cidade_data else "Desconhecido",
                "fonte_dados": fonte_data["nome_api"] if fonte_data else "API",
                "tipo_sensor": fonte_data["tipo_sensor"] if fonte_data else "Sensor"
            })
            
        df = pd.DataFrame(flat_records)
        return df, None
        
    except Exception as e:
        return None, f"Erro na conexão/consulta: {e}"


@st.cache_data(ttl=15)  # Cache curto de 15 segundos para tempo real nos chamados
def carregar_reports_supabase(url, key):
    """Busca do Supabase todos os reports de alagamento enviados por cidadãos."""
    from supabase import create_client
    try:
        supabase = create_client(url, key)
        query_res = supabase.table("reports_alagamento").select(
            "*, dim_bairros(*, dim_cidades(*))"
        ).order("created_at", desc=True).execute()
        return query_res.data, None
    except Exception as e:
        return None, str(e)


def registrar_alerta_cidadao(url, key, bairro_nome, ponto_ref, gravidade, descricao):
    """Registra uma nova ocorrência de alagamento enviada de forma colaborativa por um cidadão."""
    from supabase import create_client
    try:
        supabase = create_client(url, key)
        # Buscar ID do bairro pelo nome
        bairro_res = supabase.table("dim_bairros").select("id_bairro").eq("nome_bairro", bairro_nome).execute()
        if not bairro_res.data:
            return False, f"Bairro '{bairro_nome}' não localizado no banco de dados."
            
        id_bairro = bairro_res.data[0]["id_bairro"]
        
        # Inserir o report
        report_data = {
            "id_bairro": id_bairro,
            "ponto_referencia": ponto_ref,
            "gravidade": gravidade,
            "descricao": descricao
        }
        supabase.table("reports_alagamento").insert(report_data).execute()
        return True, None
    except Exception as e:
        return False, str(e)


# ==============================================================================
# FALLBACK: GERADOR DE DADOS PARA MODO DEMONSTRAÇÃO
# ==============================================================================
def gerar_dados_mock():
    """Gera um DataFrame mock simulando os dados hidrológicos caso o Supabase não esteja disponível."""
    hoje = datetime.datetime.now()
    start_date = hoje - datetime.timedelta(days=15)
    
    cidades = {
        "São Paulo": {
            "estado": "SP",
            "bairros": {
                "Butantã": {"lat": -23.5714, "lon": -46.7086},
                "Marginal Tietê": {"lat": -23.5186, "lon": -46.6433},
                "Ipiranga": {"lat": -23.5901, "lon": -46.6102}
            }
        },
        "São José do Rio Preto": {
            "estado": "SP",
            "bairros": {
                "Av. Bady Bassitt": {"lat": -20.8122, "lon": -49.3792},
                "Represa Municipal": {"lat": -20.8197, "lon": -49.3598},
                "Av. Alberto Andaló": {"lat": -20.8252, "lon": -49.3775}
            }
        }
    }
    
    fontes = [
        {"nome": "Open-Meteo Weather API", "sensor": "Pluviômetro Virtual"},
        {"nome": "Telemetria IoT Municipal", "sensor": "Sensor Ultrassônico de Nível"}
    ]
    
    tempo_records = []
    current_time = start_date
    dias_semana_tradutor = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
    
    while current_time <= hoje:
        dt = current_time.replace(minute=0, second=0, microsecond=0)
        tempo_records.append(dt)
        current_time += datetime.timedelta(hours=1)
        
    tempestades = [
        {"dia_offset": -12, "duracao": 6, "max_chuva": 65.0},
        {"dia_offset": -6, "duracao": 8, "max_chuva": 85.0},
        {"dia_offset": -1, "duracao": 4, "max_chuva": 55.0}
    ]
    
    flat_records = []
    id_counter = 1
    
    historico_chuva = {}
    
    for dt_atual in tempo_records:
        data_str = dt_atual.strftime("%Y-%m-%d")
        hora_str = dt_atual.strftime("%H:%M:%S")
        dia_semana = dias_semana_tradutor[dt_atual.weekday()]
        
        for cid_nome, cid_info in cidades.items():
            for bai_nome, coords in cid_info["bairros"].items():
                key = f"{cid_nome}_{bai_nome}"
                if key not in historico_chuva:
                    historico_chuva[key] = []
                    
                chuva = 0.0
                for temp in tempestades:
                    dia_tempestade = hoje + datetime.timedelta(days=temp["dia_offset"])
                    if dt_atual.date() == dia_tempestade.date():
                        janela_inicio = 14
                        janela_fim = janela_inicio + temp["duracao"]
                        if janela_inicio <= dt_atual.hour < janela_fim:
                            progresso = (dt_atual.hour - janela_inicio) / temp["duracao"]
                            chuva = temp["max_chuva"] * math.sin(progresso * math.pi) + random.uniform(0, 5)
                            chuva = max(0.0, round(chuva, 2))
                
                if chuva == 0.0 and random.random() < 0.05:
                    chuva = round(random.uniform(0.5, 8.0), 2)
                    
                historico_chuva[key].append(chuva)
                chuvas_recentes = historico_chuva[key][-4:]
                
                nivel_base = 1.2 if "Represa" not in bai_nome else 3.0
                impacto_chuva = sum(chuvas_recentes) * 0.045
                flutuacao = random.uniform(-0.05, 0.05)
                
                nivel_rio = nivel_base + impacto_chuva + flutuacao
                nivel_rio = round(max(0.2, nivel_rio), 2)
                
                limite_rio = 4.2 if "Represa" in bai_nome else 2.6
                risco = (chuva > 45.0) or (nivel_rio > limite_rio)
                
                fonte = random.choice(fontes)
                
                flat_records.append({
                    "id": id_counter,
                    "volume_chuva_mm": chuva,
                    "nivel_rio_metros": nivel_rio,
                    "risco_enchente": risco,
                    "data": data_str,
                    "hora": hora_str,
                    "data_hora": dt_atual,
                    "dia_da_semana": dia_semana,
                    "mes": dt_atual.month,
                    "ano": dt_atual.year,
                    "bairro": bai_nome,
                    "latitude": coords["lat"],
                    "longitude": coords["lon"],
                    "cidade": cid_nome,
                    "estado": cid_info["estado"],
                    "fonte_dados": fonte["nome"],
                    "tipo_sensor": fonte["sensor"]
                })
                id_counter += 1
                
    return pd.DataFrame(flat_records)

# ==============================================================================
# CARREGAMENTO DO DATASET PRINCIPAL
# ==============================================================================
st.sidebar.image("https://img.icons8.com/clouds/200/000000/flood.png", width=120)
st.sidebar.markdown("<h2 style='text-align: center; margin-bottom: 0px;'>URBAN-FLOW 🌊</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.85rem;'>Global Solution - Monitoramento</p>", unsafe_allow_html=True)
st.sidebar.divider()

# Navegação de Telas do Sistema
opcao_menu = st.sidebar.radio(
    "🌐 Navegação do Sistema:",
    options=["📊 Painel de Monitoramento", "📢 Canal do Cidadão (Reportar)"]
)
st.sidebar.divider()

modo_demo = False
df = None

# Tentar sincronizar e carregar via Supabase
if SUPABASE_URL and SUPABASE_KEY and "your-project-id" not in SUPABASE_URL:
    # 1. Executa a ingestão automática (uma única vez por ciclo de vida do servidor)
    sucedido, status_msg = rodar_ingestao_automatica(SUPABASE_URL, SUPABASE_KEY)
    if sucedido:
        st.sidebar.success(f"✔️ Sincronização: {status_msg}")
    else:
        st.sidebar.warning(f"⚠️ {status_msg}")

    # 2. Carrega os dados atualizados
    with st.spinner("Conectando ao banco de dados Supabase e baixando modelo Snowflake..."):
        df, erro = carregar_dados_supabase(SUPABASE_URL, SUPABASE_KEY)
        if erro:
            st.sidebar.warning(f"⚠️ Falha no Supabase: {erro}")
            st.sidebar.info("🔄 Ativando Modo de Demonstração com dados locais simulados.")
            modo_demo = True
            df = gerar_dados_mock()
else:
    modo_demo = True
    df = gerar_dados_mock()

if modo_demo:
    st.info("💡 **Modo de Demonstração Local Ativo**: Exibindo dados simulados. Para conectar ao Supabase real, configure o arquivo `.env` com suas credenciais.")

# Tentar carregar reports comunitários ativos
reports_data = None
if not modo_demo:
    reports_data, _ = carregar_reports_supabase(SUPABASE_URL, SUPABASE_KEY)
else:
    if "reports_mock" not in st.session_state:
        st.session_state["reports_mock"] = []
    reports_data = st.session_state["reports_mock"]

# ==============================================================================
# PÁGINA 2: CANAL DO CIDADÃO (REPORTAR ALAGAMENTO) - RENDERIZAÇÃO E ST.STOP()
# ==============================================================================
if opcao_menu == "📢 Canal do Cidadão (Reportar)":
    st.markdown("<h1>Canal de Segurança do Cidadão</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 1.05rem;'>Espaço colaborativo e de crowdsourcing para reportar pontos de alagamento e inundações em tempo real nas ruas de São Paulo.</p>", unsafe_allow_html=True)
    st.divider()
    
    st.markdown("### 📝 Enviar Relato de Alagamento")
    
    # Formulário principal
    with st.form("form_report_alagamento"):
        lista_bairros_cidade = sorted(list(df["bairro"].unique()))
        bairro_report = st.selectbox("Selecione o Bairro Afetado:", options=lista_bairros_cidade)
        
        ponto_ref = st.text_input(
            "Ponto de Referência Próximo:", 
            placeholder="Ex: Próximo à estação de Metrô Pinheiros, ao lado do mercado Ipiranga X, altura do número 1200...",
            max_chars=150
        )
        
        gravidade = st.selectbox(
            "Gravidade/Intensidade Visual do Alagamento:",
            options=["Leve (Água acumulando na altura do meio-fio)", 
                     "Moderada (Água cobrindo metade das rodas dos carros, via parcialmente intransitável)", 
                     "Crítica (Transbordamento total da via, carros boiando, correnteza perigosa)"]
        )
        
        descricao_report = st.text_area(
            "Informações Adicionais / Detalhes (Opcional):",
            placeholder="Relate as condições de tráfego local, bueiros entupidos de lixo ou riscos para pedestres...",
            max_chars=500
        )
        
        enviado = st.form_submit_button("📢 Enviar Alerta Comunitário")
        
        if enviado:
            if not ponto_ref.strip():
                st.error("⚠️ Por favor, informe um ponto de referência próximo para que a Defesa Civil possa localizar o chamado!")
            else:
                # Extrair o nível do texto de gravidade para gravação curta no banco
                gravidade_curta = "Leve"
                if "Moderada" in gravidade:
                    gravidade_curta = "Moderada"
                elif "Crítica" in gravidade:
                    gravidade_curta = "Crítica"
                
                with st.spinner("Registrando alerta de segurança comunitária..."):
                    if not modo_demo:
                        sucedido, erro_msg = registrar_alerta_cidadao(
                            SUPABASE_URL, SUPABASE_KEY, 
                            bairro_report, ponto_ref, gravidade_curta, descricao_report
                        )
                    else:
                        # Fallback modo demo - Salvar em session state
                        st.session_state["reports_mock"].insert(0, {
                            "id": int(random.uniform(1000, 9999)),
                            "gravidade": gravidade_curta,
                            "ponto_referencia": ponto_ref,
                            "descricao": descricao_report,
                            "created_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                            "dim_bairros": {
                                "nome_bairro": bairro_report,
                                "dim_cidades": {
                                    "nome_cidade": "São Paulo"
                                }
                            }
                        })
                        sucedido, erro_msg = True, None
                        
                if sucedido:
                    st.success("🎉 **Alerta Enviado com Sucesso!** Muito obrigado pela sua colaboração cidadã. O seu chamado já está ativo e em tempo real no painel de monitoramento principal!")
                    st.balloons()
                else:
                    st.error(f"❌ Falha ao registrar alerta no Supabase: {erro_msg}")
                    
    st.divider()
    # Roda-pé institucional do Canal
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.8rem;'>Sistema desenvolvido para avaliação da Global Solution (GS). Crowdsourcing de dados e resiliência comunitária.</p>", unsafe_allow_html=True)
    st.stop()

# ==============================================================================
# FILTROS DA BARRA LATERAL (SIDEBAR)
# ==============================================================================
st.sidebar.markdown("### 🔍 Filtros de Monitoramento")

# Filtro de Cidades
lista_cidades = sorted(list(df["cidade"].unique()))
default_cidades = [c for c in ["São Paulo"] if c in lista_cidades]
if not default_cidades and lista_cidades:
    default_cidades = [lista_cidades[0]]
cidades_selecionadas = st.sidebar.multiselect("Cidades:", options=lista_cidades, default=default_cidades)

# Filtro de Bairros dinâmico com base nas Cidades Selecionadas
df_filtrado_cidade = df[df["cidade"].isin(cidades_selecionadas)]
lista_bairros = sorted(list(df_filtrado_cidade["bairro"].unique()))
bairros_selecionados = st.sidebar.multiselect("Bairros:", options=lista_bairros, default=lista_bairros)

# Filtro de Período Temporal
datas_unicas = sorted(list(pd.to_datetime(df["data"]).dt.date.unique()))
data_inicio, data_fim = st.sidebar.date_input(
    "Período Temporal:",
    value=(datas_unicas[0], datas_unicas[-1]),
    min_value=datas_unicas[0],
    max_value=datas_unicas[-1]
)

# Aplicar filtros ao DataFrame
df_filtrado = df[
    (df["cidade"].isin(cidades_selecionadas)) &
    (df["bairro"].isin(bairros_selecionados)) &
    (pd.to_datetime(df["data"]).dt.date >= data_inicio) &
    (pd.to_datetime(df["data"]).dt.date <= data_fim)
]

# ==============================================================================
# CONTEÚDO PRINCIPAL - DASHBOARD ANALÍTICO
# ==============================================================================
st.markdown("<h1>Painel Integrado de Monitoramento de Enchentes</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #94a3b8; font-size: 1.05rem;'>Dashboard analítico em tempo real com modelagem dimensional Snowflake alimentado por sensores IoT.</p>", unsafe_allow_html=True)
st.divider()

if df_filtrado.empty:
    st.warning("⚠️ Nenhum dado encontrado para a combinação de filtros selecionada. Ajuste os filtros na barra lateral!")
else:
    # --------------------------------------------------------------------------
    # 1. LINHA DE KPIs (INDICADORES PRINCIPAIS)
    # --------------------------------------------------------------------------
    col1, col2, col3 = st.columns(3)
    
    # Calcular métricas baseadas no período selecionado
    chuva_acumulada = round(df_filtrado["volume_chuva_mm"].sum(), 1)
    
    # Obter os últimos registros (estado atual)
    bairros_grupo = df_filtrado.sort_values("data_hora").groupby("bairro").last().reset_index()
    nivel_rio_max = round(bairros_grupo["nivel_rio_metros"].max(), 2)
    
    # Risco geral ativo no momento (última medição de qualquer bairro no filtro)
    tem_risco = bairros_grupo["risco_enchente"].any()
    
    # Definir Alerta Geral
    if tem_risco:
        status_alerta = "CRÍTICO (Risco Ativo)"
        classe_alerta = "alert-critical"
        emoji_alerta = "🚨"
    elif nivel_rio_max > 2.2:
        status_alerta = "ATENÇÃO (Nível Elevado)"
        classe_alerta = "alert-warning"
        emoji_alerta = "⚠️"
    else:
        status_alerta = "NORMAL"
        classe_alerta = "alert-normal"
        emoji_alerta = "✅"
        
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🌧️ Volume Chuva Acumulado</div>
            <div class="metric-value">{chuva_acumulada} <span style="font-size: 1.2rem; color: #38bdf8;">mm</span></div>
            <span class="metric-indicator alert-normal">Total no Período</span>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📏 Nível Máximo do Rio (Atual)</div>
            <div class="metric-value">{nivel_rio_max} <span style="font-size: 1.2rem; color: #818cf8;">m</span></div>
            <span class="metric-indicator {'alert-warning' if nivel_rio_max > 2.2 else 'alert-normal'}">Última Leitura</span>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📢 Status de Alerta do Sistema</div>
            <div class="metric-value" style="font-size: 1.5rem; padding: 6px 0;">{emoji_alerta} {status_alerta}</div>
            <span class="metric-indicator {classe_alerta}">Situação dos Bairros</span>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # 2. SEÇÃO INTERATIVA: MAPA E GRÁFICO CORRELACIONAL
    # --------------------------------------------------------------------------
    layout_col1, layout_col2 = st.columns([1, 1])
    
    with layout_col1:
        st.markdown("### 🗺️ Mapa Temático de Áreas de Risco")
        st.markdown("Marcadores coloridos apontam o nível de risco local baseado nos sensores.")
        
        # Preparar dados para o mapa (obter a última coordenada e medição de cada bairro)
        mapa_df = df_filtrado.sort_values("data_hora").groupby("bairro").last().reset_index()
        
        # Criar rótulo de alerta descritivo para o mapa
        def descrever_risco(row):
            if row["risco_enchente"]:
                return "CRÍTICO"
            elif row["nivel_rio_metros"] > 2.2:
                return "ATENÇÃO"
            return "NORMAL"
            
        mapa_df["Alerta"] = mapa_df.apply(descrever_risco, axis=1)
        
        # Mapeamento de Cores para o Mapa Plotly Mapbox
        cores_alerta = {"CRÍTICO": "#ef4444", "ATENÇÃO": "#f59e0b", "NORMAL": "#10b981"}
        
        # Renderização do Mapa Plotly (Estilo Carto Darkmatter Premium)
        fig_mapa = px.scatter_mapbox(
            mapa_df,
            lat="latitude",
            lon="longitude",
            color="Alerta",
            color_discrete_map=cores_alerta,
            size="nivel_rio_metros",
            size_max=22,
            hover_name="bairro",
            hover_data={
                "cidade": True,
                "nivel_rio_metros": ":.2f m",
                "volume_chuva_mm": ":.2f mm",
                "Alerta": True,
                "latitude": False,
                "longitude": False
            },
            zoom=11 if len(cidades_selecionadas) == 1 and "São Paulo" in cidades_selecionadas else 6,
            mapbox_style="carto-darkmatter"
        )
        
        fig_mapa.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                title="Status de Alerta",
                yanchor="top",
                y=0.95,
                xanchor="left",
                x=0.02,
                bgcolor="rgba(15, 18, 29, 0.8)",
                font=dict(color="#f1f3f9")
            )
        )
        
        st.plotly_chart(fig_mapa, width="stretch")

    with layout_col2:
        st.markdown("### 📈 Correlação: Volume de Chuva vs. Nível do Rio")
        st.markdown("Análise temporal correlacionando picos de chuva e elevação hidrológica lag-response.")
        
        # Agrupar dados por data e hora (média dos bairros filtrados) para visualizar a linha temporal
        tempo_df = df_filtrado.groupby("data_hora").agg({
            "volume_chuva_mm": "mean",
            "nivel_rio_metros": "mean"
        }).reset_index()
        
        # Criar gráfico de eixo duplo usando Plotly
        fig_timeline = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Chuva representada por barras azuis claras (Eixo Secundário)
        fig_timeline.add_trace(
            dict_gr.Bar(
                x=tempo_df["data_hora"],
                y=tempo_df["volume_chuva_mm"],
                name="Chuva (mm)",
                marker_color="rgba(56, 189, 248, 0.4)",
                hovertemplate="%{y:.1f} mm<extra></extra>"
            ),
            secondary_y=True,
        )
        
        # Nível do Rio representado por linha roxa brilhante (Eixo Principal)
        fig_timeline.add_trace(
            dict_gr.Scatter(
                x=tempo_df["data_hora"],
                y=tempo_df["nivel_rio_metros"],
                name="Nível Rio (m)",
                line=dict(color="#818cf8", width=3),
                hovertemplate="%{y:.2f} m<extra></extra>"
            ),
            secondary_y=False,
        )
        
        # Estilização Premium do Gráfico
        fig_timeline.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(color="#94a3b8")
            ),
            margin={"r":10,"t":40,"l":10,"b":10},
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.01)",
            xaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.05)",
                tickfont=dict(color="#94a3b8"),
                title=dict(text="Cronologia das Leituras")
            ),
            yaxis=dict(
                title=dict(text="Nível do Rio (Metros)", font=dict(color="#818cf8")),
                tickfont=dict(color="#818cf8"),
                showgrid=True,
                gridcolor="rgba(255,255,255,0.05)"
            ),
            yaxis2=dict(
                title=dict(text="Volume de Chuva (mm)", font=dict(color="#38bdf8")),
                tickfont=dict(color="#38bdf8"),
                showgrid=False
            )
        )
        
        st.plotly_chart(fig_timeline, width="stretch")
        
        with st.expander("🔬 A Ciência por trás do URBAN-FLOW: O Efeito Lag Hidrológico"):
            st.markdown("""
            O gráfico acima evidencia um fenômeno físico e científico real monitorado por engenheiros hidrólogos: o **Lag Hidrológico (Tempo de Resposta)** da bacia urbana.
            
            * **O que o gráfico demonstra?**
              Observe que os picos das barras azuis (chuva intensa capturada em tempo real pela API Open-Meteo) ocorrem **algumas horas antes** do pico da linha roxa (nível máximo atingido pelo rio). 
            
            * **Como isso é modelado matematicamente?**
              O sistema URBAN-FLOW não correlaciona chuva e nível de forma imediata (o que seria hidrologicamente incorreto). Ele calcula o nível do rio através do escoamento acumulado ponderado das **últimas 4 horas de precipitação**, simulando a velocidade real de escoamento da água pelas ruas, bueiros e encostas até alcançar o leito do rio.
            
            * **Por que isso é um diferencial?**
              Essa modelagem dinâmica cria curvas de dados altamente compatíveis com bacias hidrográficas reais da capital paulista monitoradas pela Defesa Civil e pelo CEMADEN, permitindo demonstrar a **capacidade de alerta preventivo** do sistema.
            """)

    # --------------------------------------------------------------------------
    # 3. PLANO DE AÇÃO, PREVENÇÃO E CONTINGÊNCIA (DINÂMICO E INTERATIVO)
    # --------------------------------------------------------------------------
    st.divider()
    st.markdown("### 🛡️ Plano de Ação, Prevenção e Contingência")
    st.markdown("Recomendações e medidas preventivas sugeridas pelo sistema URBAN-FLOW com base no nível de alerta atual dos bairros.")
    
    # Criar abas para separar ações emergenciais e soluções de longo prazo
    tab_emergencia, tab_infraestrutura = st.tabs([
        "🚨 Ações de Contingência (Emergencial)", 
        "🏗️ Melhorias de Infraestrutura (Longo Prazo)"
    ])
    
    with tab_emergencia:
        # Seção dinâmica baseada no nível de risco atual detectado no topo
        if tem_risco:
            st.error("🚨 **ALERTA CRÍTICO ATIVO: Risco Alto de Alagamento Detectado!**")
            
            col_defesa, col_populacao = st.columns(2)
            with col_defesa:
                st.markdown("""
                ##### 🏢 Ações para a Defesa Civil e Órgãos Públicos:
                * **Bloqueio de Vias:** Fechar imediatamente o tráfego nos pontos críticos inundados (ex: Marginal Tietê, Ipiranga, Pinheiros).
                * **Sistemas de Alerta:** Disparar sirenes locais e enviar alertas de emergência por SMS/WhatsApp para os residentes das áreas afetadas.
                * **Equipes de Resgate:** Mobilizar equipes do Corpo de Bombeiros e Defesa Civil para prontidão de salvamento e evacuação preventiva.
                * **Abrigos:** Ativar e preparar ginásios e abrigos municipais de emergência.
                """)
            with col_populacao:
                st.markdown("""
                ##### 🏠 Ações Recomendadas para a População Local:
                * **Evite Deslocamentos:** Não saia de casa a menos que seja instruído por equipes de resgate. Nunca tente atravessar ruas alagadas (a pé ou de carro).
                * **Proteção de Bens:** Suba móveis, eletrodomésticos e documentos importantes para os andares superiores de sua residência.
                * **Desligue a Energia:** Corte a chave geral de eletricidade e o registro de gás para evitar curtos-circuitos e explosões.
                * **Kit de Emergência:** Separe água potável, alimentos não perecíveis, lanternas, documentos e medicamentos de uso contínuo.
                """)
        elif nivel_rio_max > 2.2:
            st.warning("⚠️ **ESTADO DE ATENÇÃO: Nível Hidrológico Elevado!**")
            
            col_defesa, col_populacao = st.columns(2)
            with col_defesa:
                st.markdown("""
                ##### 🏢 Ações para a Defesa Civil e Órgãos Públicos:
                * **Monitoramento Contínuo:** Intensificar a leitura dos sensores IoT em tempo real para os bairros em estado de atenção.
                * **Limpeza Emergencial:** Realizar a desobstrução rápida de bueiros e grades de retenção nos pontos de escoamento principal.
                * **Pré-Alerta:** Emitir boletim de atenção meteorológica para as comunidades próximas aos córregos.
                """)
            with col_populacao:
                st.markdown("""
                ##### 🏠 Ações Recomendadas para a População Local:
                * **Acompanhamento:** Fique atento aos boletins oficiais de rádio, TV e internet sobre o avanço das chuvas na sua região.
                * **Verificação Preventiva:** Cheque se ralos e bueiros residenciais estão limpos e desobstruídos.
                * **Rotas de Fuga:** Planeje com sua família uma rota de fuga segura para áreas altas caso o nível do rio continue a subir de forma acelerada.
                """)
        else:
            st.success("✅ **SITUAÇÃO NORMAL: Baixo Nível de Risco Hidrológico**")
            st.markdown("""
            * **Monitoramento Rotineiro:** O URBAN-FLOW está operando em regime estável de coleta. A Defesa Civil deve manter as rondas ordinárias de rotina.
            * **Manutenção Preventiva:** Excelente janela de oportunidade para a limpeza e desassoreamento de córregos e galerias pluviais urbanas antes do próximo ciclo de tempestades.
            """)
            
    with tab_infraestrutura:
        st.markdown("##### 🏗️ Soluções Urbanas e Tecnológicas de Longo Prazo")
        st.markdown("Medidas estruturais recomendadas pelo URBAN-FLOW para mitigar as enchentes de forma sustentável na cidade de São Paulo:")
        
        col_sbn, col_cinza, col_iot = st.columns(3)
        
        with col_sbn:
            st.subheader("🌱 Soluções Baseadas na Natureza")
            st.markdown("""
            * **Jardins de Chuva:** Expandir áreas verdes rebaixadas e canteiros drenantes nas calçadas para reter e infiltrar a água da chuva direto no lençol freático, aliviando as galerias subterrâneas.
            * **Parques Lineares:** Desenvolver parques e faixas de vegetação nativa nas várzeas dos rios (ex: Pinheiros e Tietê) para permitir o transbordamento natural seguro sem atingir áreas residenciais ou comerciais.
            """)
            
        with col_cinza:
            st.subheader("🧱 Infraestrutura Cinza")
            st.markdown("""
            * **Modernização de Piscinões:** Construir novos reservatórios de detenção subterrâneos ("piscinões") de alta capacidade nas bacias dos córregos mais críticos para armazenar a água nos picos de tempestade e escoá-la gradativamente.
            * **Asfalto Permeável:** Adotar pavimentação porosa e blocos drenantes em estacionamentos públicos, calçadões e ciclovias para aumentar o coeficiente de infiltração do solo urbano.
            """)
            
        with col_iot:
            st.subheader("📡 Tecnologia e IoT")
            st.markdown("""
            * **Sensores de Bueiros Inteligentes:** Instalar grades com sensores ultrassônicos em bueiros para alertar automaticamente as subprefeituras quando o acúmulo de lixo atingir 75% da capacidade de vazão.
            * **Modelagem Preditiva com IA:** Utilizar dados históricos acumulados no Supabase para treinar modelos de machine learning capazes de prever transbordamentos com até 2 horas de antecedência.
            """)

    # --------------------------------------------------------------------------
    # 4. TABELAS DETALHADAS DE OCORRÊNCIAS (SENSORES VS. CIDADÃOS)
    # --------------------------------------------------------------------------
    st.divider()
    
    col_tabela_sensores, col_tabela_cidados = st.columns([3, 2])
    
    with col_tabela_sensores:
        st.markdown("### 📋 Medições dos Sensores IoT")
        st.markdown("Últimas leituras consolidadas capturadas pelas estações telemétricas.")
        
        # Tabela com as leituras mais recentes para análise tabular
        df_table = df_filtrado.sort_values("data_hora", ascending=False).head(20).copy()
        
        # Formatação descritiva
        df_table["Volume Chuva"] = df_table["volume_chuva_mm"].apply(lambda x: f"{x:.1f} mm")
        df_table["Nível do Rio"] = df_table["nivel_rio_metros"].apply(lambda x: f"{x:.2f} m")
        df_table["Status de Alerta"] = df_table["risco_enchente"].apply(lambda x: "🚨 CRÍTICO" if x else "✅ NORMAL")
        df_table["Data/Hora"] = df_table["data_hora"].dt.strftime("%d/%m/%Y %H:%M")
        
        df_display = df_table[["Data/Hora", "cidade", "bairro", "Volume Chuva", "Nível do Rio", "Status de Alerta", "fonte_dados", "tipo_sensor"]].rename(
            columns={
                "cidade": "Cidade",
                "bairro": "Bairro",
                "fonte_dados": "Origem da Leitura",
                "tipo_sensor": "Sensor"
            }
        )
        
        st.dataframe(df_display, width="stretch", hide_index=True)
        
    with col_tabela_cidados:
        st.markdown("### 📢 Alertas Comunitários Recentes")
        st.markdown("Ocorrências e pontos de alagamento reportados diretamente por cidadãos.")
        
        if reports_data:
            # Filtrar reports para mostrar apenas os correspondentes aos filtros de Bairros selecionados na sidebar
            reports_filtrados = []
            for rep in reports_data:
                bairro_rep = rep.get("dim_bairros", {}).get("nome_bairro")
                if bairro_rep in bairros_selecionados:
                    reports_filtrados.append(rep)
                    
            if reports_filtrados:
                # Mostrar os reports mais recentes em cartões com design glassmorphic customizado
                # Limitar aos 5 reports mais recentes para não poluir
                for rep in reports_filtrados[:5]:
                    grav = rep["gravidade"]
                    bairro_rep = rep.get("dim_bairros", {}).get("nome_bairro")
                    ponto = rep["ponto_referencia"]
                    desc = rep["descricao"] if rep["descricao"] else "Sem informações adicionais."
                    
                    # Tratar data
                    try:
                        dt_rep = pd.to_datetime(rep["created_at"]).strftime("%d/%m/%Y %H:%M")
                    except:
                        dt_rep = rep["created_at"]
                        
                    # Mapear cores do alerta do cidadão
                    if grav == "Crítica":
                        prefix = "🚨 CRÍTICO"
                        cor_borda = "rgba(239, 68, 68, 0.4)"
                        cor_texto = "#ef4444"
                    elif grav == "Moderada":
                        prefix = "⚠️ MODERADO"
                        cor_borda = "rgba(245, 158, 11, 0.4)"
                        cor_texto = "#f59e0b"
                    else:
                        prefix = "ℹ️ LEVE"
                        cor_borda = "rgba(56, 189, 248, 0.4)"
                        cor_texto = "#38bdf8"
                        
                    st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid {cor_borda}; border-radius: 12px; padding: 16px; margin-bottom: 12px; backdrop-filter: blur(5px);">
                        <span style="font-size: 0.75rem; color: #94a3b8; float: right; margin-top: 2px;">🕒 {dt_rep}</span>
                        <strong style="color: {cor_texto}; font-size: 0.9rem; font-family: 'Outfit', sans-serif;">{prefix} - Bairro: {bairro_rep}</strong><br>
                        <div style="margin-top: 8px; font-size: 0.85rem; color: #f1f3f9;">📍 <strong>Ref:</strong> {ponto}</div>
                        <div style="margin-top: 4px; font-size: 0.8rem; color: #94a3b8; font-style: italic;">"{desc}"</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("💡 Nenhum chamado ativo enviado por cidadãos para a região selecionada nas últimas 24h.")
        else:
            st.info("💡 Nenhum chamado de alagamento ativo enviado por cidadãos no momento.")
            
    st.divider()
    # Roda-pé institucional do Projeto
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.8rem;'>Sistema desenvolvido para avaliação da Global Solution (GS). Arquitetura Snowflake no Supabase e visualizações no Streamlit.</p>", unsafe_allow_html=True)


