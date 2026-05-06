
  create view "postgres"."public_gold"."gld_processos_pendentes__dbt_tmp"
    
    
  as (
    

SELECT *
FROM "postgres"."public_silver"."slv_processos"
WHERE status_atual = 'Pendente'
  );