job_order_query = """ 
with details as (
select p2.id, p2.ma_number, p.parent_id, bill_of_materials.part_id, p.dimension_x, p.dimension_y, p.dimension_z, p.color_id, p.material_id, c.color_name, m.material_code, p2."name", p2.type_id, p2.description, pt.type_code    from bill_of_materials
inner join parts p on bill_of_materials.part_id = p.id
left join colors c on c.id = p.color_id
left join materials m on m.id = p.material_id
left join products p2 on bill_of_materials.product_id = p2.id
left join product_type pt on pt.id = p2.type_id
where p.parent_id is Null
order by p2.ma_number ASC
)

select jo.job_order_number, jo.batch_id, jo.quantity, details.* from job_orders jo
left join details on details.id = jo.product_id 
where jo.batch_id = 3
order by jo.job_order_number ASC"""