
  
    

  create  table "postgres"."gold"."gld_processos_pendentes__dbt_tmp"
  
  
    as
  
  (
    

SELECT *
FROM "postgres"."silver"."slv_processos"
WHERE status_atual = 'Pendente'
  );
  