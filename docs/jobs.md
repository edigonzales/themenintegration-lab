# Datenumbaujobs

NETL 0.3.0 führt vollständige, vom LLM geschriebene GRETL-Jobs im persistenten Lab-Runner aus.
Ein erfolgreicher Gradle-Prozess, bestandene generische Prüfungen und bestätigte fachliche
Abnahme sind getrennte Aussagen. Kein Produktionsbetrieb, keine echten Fachdaten.

## Artefaktvertrag

Ein Job liegt in `themes/<amt>/<thema>/jobs/<job>/`. Referenz ist
`themes/demo/standorte/jobs/edit-to-pub`. Der Autor schreibt `job.json`, `build.gradle` und
`sql/*.sql`; der Prüfer schreibt `tests.json`, `fixtures/*.sql`, `assertions/*.sql`.
Die NETL-Schreibwerkzeuge prüfen Pfade, Grössen und die Trennung dieser Fähigkeiten.
Der delegierende Integrator nennt den exakten Themen-/Job-Identifier; die Rollen dürfen
nicht auf andere Jobs ausweichen. Keine allgemeinen Dateischreibrechte oder Shellrechte.

`job.json` hat `formatVersion: 1`, `source`/`target` als konfigurierte Schema-Identifier,
`task`, `sqlFiles` und `tables`. Pro Tabelle: `name`, fachlicher `key` (Spaltenliste),
`columns` für den Wiederholungsvergleich; optional `allowEmpty` (standardmässig false).
Vergleichsspalten enthalten alle fachlichen Werte, aber keine automatisch erzeugten IDs.
Quellschema muss in edit, Ziel in pub liegen. Tabellen/Spalten sind einfache PostgreSQL-Identifier.

`tests.json` hat `formatVersion: 1`, `requirements` (fachlicher Klartext), `fixtures`
(Dateiliste) und `assertions` (Liste). Jede Assertion hat `id`, `description`, `origin`,
`scope` (`fixture` oder `local`), `sql` und `expected: "zero_violations"`.
`local`-Assertions laufen sowohl im Fixture-Test als auch im lokalen Ziellauf.
Assertion-SQL läuft in der Pub-Datenbank und liefert Verletzungszeilen, nicht einen Boolean.
NETL ersetzt `${sourceSchema}`/`${targetSchema}` in Fixtures/Assertions durch quotierte Namen.
Erwartete und tatsächliche Fixture-Datensätze mit `EXCEPT ALL` in beiden Richtungen vergleichen.

Gradle erhält `dbUriEdit`, `dbUserEdit`, `dbPwdEdit`, entsprechende `Pub`-Properties,
`sourceSchema` und `targetSchema`. Ein normaler `Db2Db`-Task setzt beispielsweise
`sqlParameters = [sourceSchema: sourceSchema]` und
`new TransferSet('sql/standorte.sql', "${targetSchema}.standort", true)`.
`true` löscht vorhandene Zielzeilen innerhalb des Transfers; kein TRUNCATE-Recht erforderlich.
GRETL übernimmt die Parameterersetzung im Transformations-SQL. Der Runner liefert immer
`/home/gradle/init.gradle`; keine eigene Init-Datei oder zusätzlichen Downloads hinzufügen.

## Ablauf und CLI

Alle Befehle vom Lab aus mit `../netl-mcp/bin/netl --workspace .` ausführen:

```text
job context demo/standorte
job validate demo/standorte edit-to-pub
job confirm demo/standorte edit-to-pub <expectationsRevision>
job test demo/standorte edit-to-pub
job status demo/standorte edit-to-pub
job plan demo/standorte edit-to-pub
job run demo/standorte edit-to-pub <planToken>
```

`confirm` ist ausschliesslich die Umsetzung einer ausdrücklichen Benutzerbestätigung der
angezeigten Erwartungen. Der Integrator darf das nicht selbst entscheiden. Bestätigt wird
ein Hash aus Testdateien, Manifest und aufgelöster Schemakonfiguration. Transformations-SQL
und build.gradle können korrigiert werden, ohne Erwartungen zu ändern. Bestätigte Testdateien
sind für das Prüfer-Werkzeug eingefroren; geänderte Anforderungen brauchen einen neuen Job.
Manuelle Änderungen bleiben möglich, machen aber Bestätigung und Tests ungültig.

Ohne Bestätigung kann der Test `GENERIC_ONLY` zurückgeben: auch vorhandene fachliche Queries
werden ausgeführt, aber es gibt keine fachliche Abnahme und keine lokale Freigabe.
Die Demo enthält vorgeschlagene Erwartungen, keine vorgetäuschte Benutzerbestätigung.

`job_test` erstellt eigene zufällig benannte Schemas mit denselben Modellen, Optionen und
strukturellen SQL-Hooks. Empfänger-Grants werden in den Testschemas bewusst ausgelassen.
Er lädt Fixtures ausschliesslich dort, führt den echten Job zweimal aus und vergleicht
fachliche Inhalte einschliesslich Multiplizität. Standardprüfungen: Existenz, nicht leer,
Pflichtwerte, eindeutige/nichtleere fachliche Schlüssel, Geometriegültigkeit und konfigurierter SRID.
Assertions verwenden eine separate reine Leserrolle und Read-only-Transaktionen mit 10 Sekunden Zeitlimit und maximal zehn
angezeigten Verletzungen. SQL-Fehler sind Prüfungsfehler. Kein stilles Überspringen.

Nach gewöhnlichem Fehler sind höchstens drei Versuche mit geändertem Transformationsjob
zulässig; Vorher-/Nachher-Inhalte stehen in `changes.json`. Timeout, BUSY und unsicherer
Runner-Stopp stoppen die automatische Schleife. Ein erfolgreicher Test startet bei einem
späteren Änderungsauftrag eine neue Serie. Aufräumfehler verhindern einen erfolgreichen Test.

`job_plan` verlangt einen bestandenen Test derselben Dateifingerprints und passende verwaltete
Schemas. Token sind einmalig und 15 Minuten gültig. `job_run` benötigt einen ausdrücklichen
zusätzlichen lokalen Umbauauftrag. Fixtures werden niemals in lokale Zielschemas geladen.
Eine nach dem Db2Db-Commit fehlgeschlagene Prüfung bedeutet **keinen Rollback**:
`FAILED` mit `targetMayHaveChanged: true`. Kein automatischer Wiederholungsversuch.
Vorher geprüfte Fixture-Erwartungen beweisen nicht die Richtigkeit beliebiger neuer Quelldaten.

## Laufzeit, Nachweise und Grenzen

Neue CLI/MCP-Funktionen: job_context, job_validate, job_confirm, job_test, job_plan,
job_run, job_status sowie die getrennten MCP-Schreibwerkzeuge job_write_transform/job_write_test.
Die Agentendelegation verwendet OpenCodes `permission.task` mit explizit erlaubten Subagenten
([offizielle Dokumentation](https://opencode.ai/docs/agents/#task-permissions)).

Unveränderte Eingabekopien, Logs, Assertions und Laufzeitmessungen liegen unter `.netl/job-runs`;
Bestätigungen und letzte Ergebnisse unter `.netl/jobs`. Flüchtige DML-Zugangsdaten werden nach
Ausführung entfernt. Pro Lauf erzeugte Login-Rollen sind keine Superuser, werden gezielt
berechtigt und anschliessend entfernt. Quell-Schreibrechte werden nach den Fixtures entzogen.
DDL übernimmt weiterhin der Schema-Service. Schema-/Container-Locks gelten für den ganzen Test.
Ein Gradle-Aufruf hat standardmässig 120 Sekunden Zeitlimit; ein Test enthält Schema-Erstellung
und zwei Transfers. Der OpenCode-MCP-Client wartet dafür bis zu zehn Minuten.
Bei Timeout stoppt NETL den Runner, beendet markierte Datenbanksitzungen und startet ihn neu.
Bei unbestätigtem Stopp bleibt die Recovery-Sperre aktiv; keine automatische Wiederholung.

Gradle ist ausführbarer Code, **keine Sandbox**. Die lokalen synthetischen Datenbankendpunkte
und das gemeinsam gemountete `.netl` bleiben eine Vertrauensgrenze. Dateiprüfung schützt vor
versehentlichen Pfadüberschreitungen, nicht vor absichtlich bösartigem Gradle-Code.
Schemas mit altem Runner-Fingerprint werden als DRIFTED gemeldet, niemals automatisch übernommen.

## Entwicklung und Abnahme

```sh
cd ../netl-mcp
./gradlew test bootJar
./gradlew integrationTest --tests '*JobIntegrationTest'
```

Im Lab: `python3 scripts/job_orchestrator_smoke.py` für einen echten delegierten LLM-Lauf.
Dieser Infrastruktur-Smoke verwendet bewusst den bekannten Demo-Fall als unveränderte Referenz;
beide Subagenten schreiben die vollständigen Artefakte über ihre Werkzeuge. Anschliessend
muss die erzeugte Assertion eine absichtlich eingebaute falsche Organisationszuordnung erkennen.
Dies ist kein Nachweis beliebiger fehlerfreier freier Codegenerierung.
Er erzeugt ein eigenes synthetisches Thema; Protokolle bleiben unter `.netl/acceptance`.
Der Smoke-Test bestätigt ausschliesslich seinen fest vorgegebenen Software-Testvertrag;
er bestätigt keine fachlichen Erwartungen anderer Themen. Bestehender Schema-Smoke-Test:
`python3 scripts/orchestrator_smoke.py`.

Die Abnahme dieser Implementierung ist in [Abnahmeprotokoll](acceptance-jobs.md) zusammengefasst.
