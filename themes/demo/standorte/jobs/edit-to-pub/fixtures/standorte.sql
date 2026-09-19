INSERT INTO ${sourceSchema}.standorte_organisation (t_id, aname)
VALUES (101, 'Werk Nord'), (102, 'Werk Süd');
INSERT INTO ${sourceSchema}.standorte_standort (kennung, aname, organisation, geometrie)
VALUES ('N1', 'Depot', 101, ST_SetSRID(ST_MakePoint(2600000,1200000),2056)),
       ('N2', 'Büro', 101, ST_SetSRID(ST_MakePoint(2600100,1200100),2056)),
       ('S1', 'Lager', 102, ST_SetSRID(ST_MakePoint(2600200,1200200),2056));
