import os
import sys
import logging
import random
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ingest_floods")

# Carregar variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or "your-project-id" in SUPABASE_URL:
    logger.error("Credenciais do Supabase não configuradas corretamente no arquivo .env!")
    logger.info("Por favor, crie o arquivo .env contendo SUPABASE_URL e SUPABASE_KEY válidos.")
    sys.exit(1)

try:
    # Inicializar cliente do Supabase
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Conexão com o Supabase estabelecida com sucesso!")
except Exception as e:
    logger.critical(f"Erro ao conectar ao Supabase: {e}")
    sys.exit(1)


def seed_dim_cidades():
    """Popula a dimensão de cidades (dim_cidades) e retorna o mapeamento de nomes para IDs."""
    logger.info("Populando dim_cidades...")
    cidades = [
        {"nome_cidade": "São Paulo", "estado": "SP"},
        {"nome_cidade": "São José do Rio Preto", "estado": "SP"}
    ]
    
    try:
        response = supabase.table("dim_cidades").upsert(cidades, on_conflict="nome_cidade,estado").execute()
        cidades_map = {row["nome_cidade"]: row["id_cidade"] for row in response.data}
        logger.info(f"dim_cidades populada com sucesso! Cidades salvas: {list(cidades_map.keys())}")
        return cidades_map
    except Exception as e:
        logger.error(f"Erro ao popular dim_cidades: {e}")
        raise e


def seed_dim_bairros(cidades_map):
    """Popula a dimensão de bairros (dim_bairros) ramificada e retorna o mapeamento de nomes para IDs."""
    logger.info("Populando dim_bairros...")
    
    # Bairros de monitoramento real com suas respectivas coordenadas geográficas
    bairros = [
        # São Paulo
        {
            "nome_bairro": "Butantã", 
            "id_cidade": cidades_map["São Paulo"], 
            "latitude": -23.5714, 
            "longitude": -46.7086
        },
        {
            "nome_bairro": "Marginal Tietê", 
            "id_cidade": cidades_map["São Paulo"], 
            "latitude": -23.5186, 
            "longitude": -46.6433
        },
        {
            "nome_bairro": "Ipiranga", 
            "id_cidade": cidades_map["São Paulo"], 
            "latitude": -23.5901, 
            "longitude": -46.6102
        },
        # São José do Rio Preto
        {
            "nome_bairro": "Av. Bady Bassitt", 
            "id_cidade": cidades_map["São José do Rio Preto"], 
            "latitude": -20.8122, 
            "longitude": -49.3792
        },
        {
            "nome_bairro": "Represa Municipal", 
            "id_cidade": cidades_map["São José do Rio Preto"], 
            "latitude": -20.8197, 
            "longitude": -49.3598
        },
        {
            "nome_bairro": "Av. Alberto Andaló", 
            "id_cidade": cidades_map["São José do Rio Preto"], 
            "latitude": -20.8252, 
            "longitude": -49.3775
        }
    ]
    
    try:
        response = supabase.table("dim_bairros").upsert(bairros, on_conflict="nome_bairro,id_cidade").execute()
        bairros_map = {row["nome_bairro"]: row["id_bairro"] for row in response.data}
        logger.info(f"dim_bairros populada com sucesso! Bairros salvos: {list(bairros_map.keys())}")
        return bairros_map
    except Exception as e:
        logger.error(f"Erro ao popular dim_bairros: {e}")
        raise e


def seed_dim_fontes():
    """Popula a dimensão de fontes de dados (dim_fontes_dados) e retorna o mapeamento para IDs."""
    logger.info("Populando dim_fontes_dados...")
    fontes = [
        {"nome_api": "Open-Meteo Weather API", "tipo_sensor": "Pluviômetro Virtual"},
        {"nome_api": "Telemetria IoT Municipal", "tipo_sensor": "Sensor Ultrassônico de Nível"},
        {"nome_api": "CEMADEN Nacional", "tipo_sensor": "Pluviômetro Físico de Alta Precisão"}
    ]
    
    try:
        response = supabase.table("dim_fontes_dados").upsert(fontes, on_conflict="nome_api,tipo_sensor").execute()
        fontes_map = {(row["nome_api"], row["tipo_sensor"]): row["id_fonte"] for row in response.data}
        logger.info("dim_fontes_dados populada com sucesso!")
        return fontes_map
    except Exception as e:
        logger.error(f"Erro ao popular dim_fontes_dados: {e}")
        raise e


def seed_dim_tempo(dias_historico=15):
    """Gera registros de data e hora para a dimensão de tempo de forma horária."""
    logger.info(f"Populando dim_tempo para os últimos {dias_historico} dias (granularidade horária)...")
    
    start_date = datetime.datetime.now() - datetime.timedelta(days=dias_historico)
    end_date = datetime.datetime.now()
    
    tempo_records = []
    current_time = start_date
    
    dias_semana_tradutor = {
        0: "Segunda-feira",
        1: "Terça-feira",
        2: "Quarta-feira",
        3: "Quinta-feira",
        4: "Sexta-feira",
        5: "Sábado",
        6: "Domingo"
    }
    
    while current_time <= end_date:
        # Arredondar para a hora inteira
        dt = current_time.replace(minute=0, second=0, microsecond=0)
        
        data_str = dt.strftime("%Y-%m-%d")
        hora_str = dt.strftime("%H:%M:%S")
        dia_semana = dias_semana_tradutor[dt.weekday()]
        
        tempo_records.append({
            "data": data_str,
            "hora": hora_str,
            "dia_da_semana": dia_semana,
            "mes": dt.month,
            "ano": dt.year
        })
        
        current_time += datetime.timedelta(hours=1)
        
    try:
        # Fazer a inserção em lotes de 200 registros para evitar timeouts ou limites da API
        batch_size = 200
        saved_records = []
        for i in range(0, len(tempo_records), batch_size):
            batch = tempo_records[i:i+batch_size]
            response = supabase.table("dim_tempo").upsert(batch, on_conflict="data,hora").execute()
            saved_records.extend(response.data)
            
        tempo_map = {(row["data"], row["hora"][:8]): row["id_tempo"] for row in saved_records}
        logger.info(f"dim_tempo populada com sucesso! Total de {len(tempo_map)} horas registradas.")
        return tempo_map, tempo_records
    except Exception as e:
        logger.error(f"Erro ao popular dim_tempo: {e}")
        raise e


def simular_e_inserir_fatos(bairros_map, fontes_map, tempo_map, tempo_records):
    """Simula dados de chuva e rios e insere os registros correspondentes na tabela fato."""
    logger.info("Iniciando a simulação de medições ambientais (Tabela Fato)...")
    
    # Criar um mapeamento rápido das fontes
    id_fonte_pluviometro = fontes_map[("Open-Meteo Weather API", "Pluviômetro Virtual")]
    id_fonte_sensor_rio = fontes_map[("Telemetria IoT Municipal", "Sensor Ultrassônico de Nível")]
    
    # Definindo picos de chuvas para criar dinâmicas de enchentes realistas nos bairros
    # Mapeamos tempestades para criar picos de chuva
    tempestades = [
        # Tempestade 1 no dia (D - 12)
        {"dia_offset": -12, "duracao_horas": 6, "volume_max_chuva": 65.0},
        # Tempestade 2 no dia (D - 6)
        {"dia_offset": -6, "duracao_horas": 8, "volume_max_chuva": 85.0},
        # Tempestade 3 no dia (D - 1)
        {"dia_offset": -1, "duracao_horas": 4, "volume_max_chuva": 55.0}
    ]
    
    fatos_records = []
    
    # Inicializando históricos de chuva por bairro para calcular o "lag" hidrológico (aumento de nível do rio acumulado)
    historico_chuva = {bairro_nome: [] for bairro_nome in bairros_map.keys()}
    
    # Ordenar registros de tempo cronologicamente para o cálculo de lag correto
    tempo_records_ordenados = sorted(
        tempo_records, 
        key=lambda x: datetime.datetime.strptime(f"{x['data']} {x['hora']}", "%Y-%m-%d %H:%M:%S")
    )
    
    for record in tempo_records_ordenados:
        data_str = record["data"]
        hora_str = record["hora"]
        id_tempo = tempo_map[(data_str, hora_str[:8])]
        
        dt_atual = datetime.datetime.strptime(f"{data_str} {hora_str}", "%Y-%m-%d %H:%M:%S")
        hoje = datetime.datetime.now()
        
        for bairro_nome, id_bairro in bairros_map.items():
            # 1. Simulação da Chuva (mm)
            chuva = 0.0
            
            # Verificar se estamos no meio de alguma tempestade
            for temp in tempestades:
                dia_tempestade = hoje + datetime.timedelta(days=temp["dia_offset"])
                
                # Se a data atual coincide com o dia da tempestade (mesmo dia e mês)
                if dt_atual.date() == dia_tempestade.date():
                    # E se a hora está dentro da janela da tempestade (ex: das 14h às 20h)
                    janela_inicio = 14
                    janela_fim = janela_inicio + temp["duracao_horas"]
                    
                    if janela_inicio <= dt_atual.hour < janela_fim:
                        # Curva de chuva senoidal realista
                        progresso = (dt_atual.hour - janela_inicio) / temp["duracao_horas"]
                        import math
                        chuva = temp["volume_max_chuva"] * math.sin(progresso * math.pi) + random.uniform(0, 5)
                        chuva = max(0.0, round(chuva, 2))
            
            # Caso não seja dia de tempestade grande, adiciona pequenas garoas ocasionais
            if chuva == 0.0 and random.random() < 0.05:
                chuva = round(random.uniform(0.5, 8.0), 2)
            
            # Armazenar histórico de chuva do bairro
            historico_chuva[bairro_nome].append(chuva)
            # Limitar histórico recente às últimas 4 horas para cálculo do nível do rio
            chuvas_recentes = historico_chuva[bairro_nome][-4:]
            
            # 2. Simulação do Nível do Rio (metros)
            # Nível base do rio varia por bairro
            nivel_base = 1.2 if "Represa" not in bairro_nome else 3.0
            
            # Efeito lag: a chuva das últimas horas acumula e eleva o nível do rio gradativamente
            impacto_chuva = sum(chuvas_recentes) * 0.045
            
            # Adiciona flutuação natural de maré/sensor
            flutuacao = random.uniform(-0.05, 0.05)
            
            nivel_rio = nivel_base + impacto_chuva + flutuacao
            nivel_rio = round(max(0.2, nivel_rio), 2)
            
            # 3. Determinação de Risco de Enchente
            # Alerta se volume de chuva de uma única vez for muito alto (> 45mm) 
            # OU se o nível do rio passar do limite crítico (ex: 2.8m para rios normais, 4.2m para represas)
            limite_rio = 4.2 if "Represa" in bairro_nome else 2.6
            risco = (chuva > 45.0) or (nivel_rio > limite_rio)
            
            # Definir qual fonte de dados gerou o registro
            # Alternar fontes para demonstrar o modelo Snowflake ligando a fatos de forma mista
            fonte_id = id_fonte_pluviometro if random.random() < 0.5 else id_fonte_sensor_rio
            
            fatos_records.append({
                "id_tempo": id_tempo,
                "id_localizacao": id_bairro,
                "id_fonte": fonte_id,
                "volume_chuva_mm": chuva,
                "nivel_rio_metros": nivel_rio,
                "risco_enchente": risco
            })
            
    # Inserir os registros simulados na tabela fato em lotes
    try:
        batch_size = 150
        total_inserido = 0
        logger.info(f"Total de registros de fatos a inserir: {len(fatos_records)}")
        
        for i in range(0, len(fatos_records), batch_size):
            batch = fatos_records[i:i+batch_size]
            supabase.table("fato_medicoes_chuva").upsert(batch, on_conflict="id_tempo,id_localizacao,id_fonte").execute()
            total_inserido += len(batch)
            if total_inserido % 600 == 0 or total_inserido == len(fatos_records):
                logger.info(f"Progresso: {total_inserido}/{len(fatos_records)} fatos gravados no banco.")
                
        logger.info("Tabela Fato populada e sincronizada com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao inserir registros na tabela fato: {e}")
        raise e


def main():
    logger.info("=== INICIANDO PIPELINE DE INGESTÃO - GLOBAL SOLUTION (GS) ===")
    
    try:
        # 1. Cidades
        cidades_map = seed_dim_cidades()
        
        # 2. Bairros (Snowflake ramificado)
        bairros_map = seed_dim_bairros(cidades_map)
        
        # 3. Fontes de Dados
        fontes_map = seed_dim_fontes()
        
        # 4. Tempo
        tempo_map, tempo_records = seed_dim_tempo(dias_historico=15)
        
        # 5. Medições (Fato) com simulação inteligente de enchentes
        simular_e_inserir_fatos(bairros_map, fontes_map, tempo_map, tempo_records)
        
        logger.info("=== PIPELINE DE INGESTÃO FINALIZADO COM SUCESSO! ===")
        
    except Exception as e:
        logger.critical(f"Falha crítica no pipeline de ingestão: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
