-- ==============================================================================
-- MODELAGEM DE BANCO DE DADOS - SNOWFLAKE (SISTEMA DE MONITORAMENTO DE ENCHENTES)
-- PROJETO GLOBAL SOLUTION (GS)
-- ==============================================================================

-- Habilitar extensões se necessário (ex: UUID se fôssemos usar, mas usaremos chaves sequenciais limpas)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------------------------
-- 1. DIMENSÃO CIDADES (Pai da normalização de localização)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_cidades (
    id_cidade SERIAL PRIMARY KEY,
    nome_cidade VARCHAR(100) NOT NULL,
    estado VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_cidade_estado UNIQUE (nome_cidade, estado)
);

COMMENT ON TABLE dim_cidades IS 'Tabela que armazena as cidades e estados monitorados.';

-- ------------------------------------------------------------------------------
-- 2. DIMENSÃO BAIRROS (Filho da normalização - Ramificação do Snowflake)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_bairros (
    id_bairro SERIAL PRIMARY KEY,
    nome_bairro VARCHAR(100) NOT NULL,
    id_cidade INTEGER NOT NULL,
    latitude NUMERIC(10, 8) NOT NULL,
    longitude NUMERIC(11, 8) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dim_bairros_cidade FOREIGN KEY (id_cidade) 
        REFERENCES dim_cidades(id_cidade) ON DELETE CASCADE,
    CONSTRAINT unique_bairro_cidade UNIQUE (nome_bairro, id_cidade)
);

COMMENT ON TABLE dim_bairros IS 'Tabela que armazena os bairros monitorados e suas coordenadas geográficas.';

-- ------------------------------------------------------------------------------
-- 3. DIMENSÃO TEMPO
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_tempo (
    id_tempo SERIAL PRIMARY KEY,
    data DATE NOT NULL,
    hora TIME NOT NULL,
    dia_da_semana VARCHAR(20) NOT NULL,
    mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    ano INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_data_hora UNIQUE (data, hora)
);

COMMENT ON TABLE dim_tempo IS 'Tabela dimensional para análise temporal de enchentes.';

-- ------------------------------------------------------------------------------
-- 4. DIMENSÃO FONTES DE DADOS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_fontes_dados (
    id_fonte SERIAL PRIMARY KEY,
    nome_api VARCHAR(100) NOT NULL,
    tipo_sensor VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_api_sensor UNIQUE (nome_api, tipo_sensor)
);

COMMENT ON TABLE dim_fontes_dados IS 'Tabela que armazena as fontes de dados meteorológicos e tipos de sensores.';

-- ------------------------------------------------------------------------------
-- 5. TABELA FATO: MEDIÇÕES DE CHUVA E NÍVEL DE RIOS
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fato_medicoes_chuva (
    id SERIAL PRIMARY KEY,
    id_tempo INTEGER NOT NULL,
    id_localizacao INTEGER NOT NULL, -- FK apontando para dim_bairros
    id_fonte INTEGER NOT NULL,
    volume_chuva_mm DOUBLE PRECISION NOT NULL DEFAULT 0.0 CHECK (volume_chuva_mm >= 0),
    nivel_rio_metros DOUBLE PRECISION NOT NULL DEFAULT 0.0 CHECK (nivel_rio_metros >= 0),
    risco_enchente BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_fato_tempo FOREIGN KEY (id_tempo) 
        REFERENCES dim_tempo(id_tempo) ON DELETE CASCADE,
    CONSTRAINT fk_fato_localizacao FOREIGN KEY (id_localizacao) 
        REFERENCES dim_bairros(id_bairro) ON DELETE CASCADE,
    CONSTRAINT fk_fato_fonte FOREIGN KEY (id_fonte) 
        REFERENCES dim_fontes_dados(id_fonte) ON DELETE CASCADE,
    CONSTRAINT unique_fato_registro UNIQUE (id_tempo, id_localizacao, id_fonte)
);

COMMENT ON TABLE fato_medicoes_chuva IS 'Tabela fato central que armazena medições climáticas, níveis de rios e riscos.';
