

# CREATE VIEW job_station_status AS

# SELECT 
#     jo.id AS job_order_id,
#     jo.job_order_number,
#     p."name",
#     jo.batch_id,
#     jo.quantity,
#     COALESCE(MAX(CASE WHEN ss.station_id = 1 THEN 'passed' END), 'not passed') AS cut,
#     COALESCE(MAX(CASE WHEN ss.station_id = 2 THEN 'passed' END), 'not passed') AS cnc,
#     COALESCE(MAX(CASE WHEN ss.station_id = 3 THEN 'passed' END), 'not passed') AS assembly,
#     COALESCE(MAX(CASE WHEN ss.station_id = 4 THEN 'passed' END), 'not passed') AS qc
# FROM job_orders jo
# LEFT JOIN station_scans ss ON ss.job_order_id = jo.job_order_number::int
# left join products p on p.id = jo.product_id 
# GROUP BY jo.id, jo.job_order_number, jo.batch_id, jo.quantity, p.name
# ORDER BY jo.job_order_number;

# SELECT * FROM job_station_status WHERE batch_id IN (1, 6);