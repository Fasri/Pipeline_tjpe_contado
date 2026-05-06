{{ config(materialized='table', schema='silver') }}

WITH base_processos AS (
    SELECT * FROM {{ source('supabase_bronze', 'processes') }}
),
base_users AS (
    SELECT * FROM {{ source('supabase_bronze', 'users') }}
),
base_status AS (
    SELECT * FROM {{ source('supabase_bronze', 'status') }}
)

SELECT
    p.position AS posicao,
    p.priority_position AS posicao_prioridade,
    p.number AS processo_numero,
    p.entry_date AS data_remessa,
    u.name AS Calculista,  -- Substituindo ID pelo Nome (coluna 'name' em users)
    p.status AS status_atual,   -- Usando a coluna 'status' diretamente de processes
    
    -- Lógica da Coluna Meta
    CASE 
        WHEN p.status IN (
            'Cálculo atualizado', 
            'Cálculo realizado', 
            'Devolvido: ausência de documentos para os cálculos', 
            'Devolvido: ausência de parâmetros', 
            'Devolvido: Beneficiário da Justiça Gratuita', 
            'Devolvido: Custas Satisfeitas', 
            'Devolvido: esclarecimento realizado', 
            'Partilha Realizada'
        ) THEN 1
        ELSE 0
    END AS meta,
    
    -- Cálculo de Dias Parado
    CASE 
        WHEN p.status = 'Pendente' THEN CURRENT_DATE - p.entry_date::date
        ELSE p.completion_date::date - p.entry_date::date
    END AS dias_parado,
    
    p.court AS vara,
    p.nucleus AS nucleo,
    p.priority AS prioridade,
    p.completion_date AS data_conclusao,
    p.valor_custas,
    p.observacao,
    p.created_at

FROM base_processos p
LEFT JOIN base_users u ON p.assigned_to_id = u.id  -- Corrigido para assigned_to_id
