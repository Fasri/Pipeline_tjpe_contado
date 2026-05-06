{{ config(materialized='view', schema='gold') }}

SELECT *
FROM {{ ref('slv_processos') }}
WHERE status_atual = 'Pendente'
