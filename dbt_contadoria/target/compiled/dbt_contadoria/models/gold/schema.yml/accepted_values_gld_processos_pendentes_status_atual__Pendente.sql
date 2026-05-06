
    
    

with all_values as (

    select
        status_atual as value_field,
        count(*) as n_records

    from "postgres"."public_gold"."gld_processos_pendentes"
    group by status_atual

)

select *
from all_values
where value_field not in (
    'Pendente'
)


