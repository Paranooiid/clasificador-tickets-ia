-- Tickets por categoría y prioridad
SELECT c.categoria,
       SUM(c.prioridad = 'alta')  AS alta,
       SUM(c.prioridad = 'media') AS media,
       SUM(c.prioridad = 'baja')  AS baja,
       COUNT(*)                   AS total
FROM clasificaciones c
GROUP BY c.categoria
ORDER BY total DESC;

-- Cola de trabajo: tickets de prioridad alta, del más antiguo al más nuevo
SELECT t.id, t.fecha, t.equipo, c.categoria, t.descripcion
FROM tickets t
JOIN clasificaciones c ON c.ticket_id = t.id
WHERE c.prioridad = 'alta'
ORDER BY t.fecha, t.id;

-- Equipos con más tickets (candidatos a mantención o recambio)
SELECT t.equipo,
       COUNT(*) AS tickets,
       GROUP_CONCAT(DISTINCT c.categoria) AS categorias
FROM tickets t
JOIN clasificaciones c ON c.ticket_id = t.id
GROUP BY t.equipo
HAVING COUNT(*) > 1
ORDER BY tickets DESC, t.equipo;

-- Tickets de red por prioridad
SELECT c.prioridad, COUNT(*) AS tickets
FROM clasificaciones c
WHERE c.categoria = 'red'
GROUP BY c.prioridad
ORDER BY CASE c.prioridad WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END;
