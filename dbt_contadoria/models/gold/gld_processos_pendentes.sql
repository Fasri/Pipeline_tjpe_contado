{{ config(
    materialized='table',
    schema='gold',
    post_hook=[
        "CREATE INDEX IF NOT EXISTS idx_gld_processos_calculista ON {{ this }} (calculista)",
        "CREATE INDEX IF NOT EXISTS idx_gld_processos_nucleo ON {{ this }} (nucleo)",
        "CREATE INDEX IF NOT EXISTS idx_gld_processos_vara ON {{ this }} (vara)"
    ]
) }}

SELECT *
FROM {{ ref('slv_processos') }}
WHERE status_atual = 'Pendente'
