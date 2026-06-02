import os
import sys
import logging
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
logger = logging.getLogger("clear_database")

# Carregar variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or "your-project-id" in SUPABASE_URL:
    logger.error("Credenciais do Supabase não configuradas no arquivo .env!")
    sys.exit(1)

try:
    # Inicializar cliente do Supabase
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Conexão com o Supabase estabelecida com sucesso!")
except Exception as e:
    logger.critical(f"Erro ao conectar ao Supabase: {e}")
    sys.exit(1)


def limpar_tabela(nome_tabela, chave_id="id"):
    """
    Remove todos os registros de uma tabela específica usando filtros da API do Supabase.
    Como postgREST exige um filtro para operações de delete em lote por segurança,
    deletamos registros onde a chave primária é maior ou igual a zero (para PKs numéricas serial).
    """
    logger.info(f"Limpando tabela '{nome_tabela}'...")
    try:
        # Deleta registros cujo ID/Chave primária seja >= 0 (cobre todos os ids gerados por SERIAL)
        response = supabase.table(nome_tabela).delete().gte(chave_id, 0).execute()
        total_deletado = len(response.data) if response.data else 0
        logger.info(f"Tabela '{nome_tabela}' limpa com sucesso! {total_deletado} registros removidos.")
    except Exception as e:
        logger.error(f"Erro ao limpar tabela '{nome_tabela}': {e}")
        raise e


def main():
    logger.warning("=== ALERTA: INICIANDO PROCESSO DE LIMPEZA DO BANCO DE DADOS ===")
    
    # Pergunta de confirmação básica via terminal (caso executado interativamente)
    print("\nVocê tem certeza que deseja deletar TODOS os dados do Supabase?")
    print("Isso apagará todas as medições de chuva, bairros, cidades, tempos e fontes de dados.")
    confirmacao = input("Digite 'SIM' para continuar: ")
    
    if confirmacao.strip().upper() != "SIM":
        logger.info("Operação cancelada pelo usuário.")
        sys.exit(0)
        
    try:
        # A ordem aqui é CRÍTICA devido às restrições de Chaves Estrangeiras (FK - Foreign Keys)
        # Devemos apagar primeiro as tabelas filhas e depois as tabelas pais.
        
        # 1. Apagar Fatos (fato_medicoes_chuva) -> Aponta para Bairros, Tempo e Fontes
        limpar_tabela("fato_medicoes_chuva", chave_id="id")
        
        # 2. Apagar Dimensão Bairros -> Aponta para Cidades
        limpar_tabela("dim_bairros", chave_id="id_bairro")
        
        # 3. Apagar Dimensão Cidades -> Não aponta para ninguém
        limpar_tabela("dim_cidades", chave_id="id_cidade")
        
        # 4. Apagar Dimensão Tempo -> Não aponta para ninguém
        limpar_tabela("dim_tempo", chave_id="id_tempo")
        
        # 5. Apagar Dimensão Fontes de Dados -> Não aponta para ninguém
        limpar_tabela("dim_fontes_dados", chave_id="id_fonte")
        
        logger.info("=== BANCO DE DADOS LIMPO COM SUCESSO! A estrutura física das tabelas foi mantida. ===")
        logger.info("Você já pode rodar 'python ingest.py' novamente para carregar novos dados.")
        
    except Exception as e:
        logger.critical(f"Falha ao limpar o banco de dados completamente: {e}")
        logger.info("Alguns dados podem ter sido apagados parcialmente. Verifique a integridade das tabelas.")
        sys.exit(1)


if __name__ == "__main__":
    main()
