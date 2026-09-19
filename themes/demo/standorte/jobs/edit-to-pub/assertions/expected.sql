WITH expected(kennung, aname, organisation, x, y) AS (
    VALUES ('N1','Depot','Werk Nord',2600000,1200000),
           ('N2','Büro','Werk Nord',2600100,1200100),
           ('S1','Lager','Werk Süd',2600200,1200200)
), actual AS (
    SELECT kennung, aname, organisation, ST_X(geometrie) AS x, ST_Y(geometrie) AS y
    FROM ${targetSchema}.standort
)
(SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
UNION ALL
(SELECT * FROM actual EXCEPT ALL SELECT * FROM expected);
