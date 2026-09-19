# Abnahme NETL-Jobs, 19. September 2026

- `./gradlew test bootJar`: erfolgreich, 24 Unit-Tests.
- Vollständiger Integrationstestlauf: 19 Schema- und 8 Job-Tests erfolgreich.
  Nach der Kontextverkürzung erneut alle 8 Job-Tests erfolgreich.
- `python3 scripts/mcp_smoke.py ../themenintegration-lab --create`: erfolgreich;
  neue Werkzeugliste und bestehende Schema-/Konfigurationsabläufe geprüft.
- Delegierter OpenCode-Smoke: erfolgreich mit dem konfigurierten Modell
  `infomaniak/google/gemma-4-31B-it`, bekanntem Demo-Referenzfall und getrennten Schreibwerkzeugen.
  Nachweis: `.netl/acceptance/job-9c807d76b9bc/` (inklusive exportierter Subagentensitzungen).
- Negativprobe im selben Smoke: Gradle erfolgreich, fachliche Assertion
  `expected_standorte` wegen absichtlich falscher Organisation fehlgeschlagen.

Der Job-Smoke misst 896 ms für den ersten Transfer und 505 ms für die Wiederholung,
mit identischer Container-ID `2728ec7f80ad4479f63196403b39d04108f7d4acdfa14d7981d66e9e0a2355b1`
und Daemon `63@2728ec7f80ad` (Startzeit 1789823583336).
Dies sind Messwerte dieses lokalen Laufs, keine allgemeine Geschwindigkeitsgarantie.
Die separat gemessene Schema-Kalt-/Warmlauf-Serie steht unter `.netl/acceptance/daemon-reuse.json`.

Geprüfte Fehlerfälle umfassen falsche Zuordnungen, leere Ergebnisse, doppelte Inserts,
fehlerhafte Transformations-/Assertion-SQL, abgelaufene fachliche Freigabe durch Dateiänderung,
einmalige Tokens, nicht privilegierte DML-Verbindungen, BUSY sowie Timeout mit beendeten
Datenbanksitzungen. Ein Post-Commit-Assert-Fehler lässt die bereits veränderten Pub-Daten bestehen
und wird entsprechend gemeldet; kein automatischer Rollback oder Retry.

Freie LLM-Entwürfe im Vorlauf enthielten unter anderem erfundene Fixture-Tabellen. Diese wurden
bei der tatsächlichen Ausführung zurückgewiesen; keine fachliche Abnahme wurde daraus abgeleitet.
Der Job-Kontext wurde deshalb auf den relevanten Katalog gekürzt. Die endgültige Infrastrukturabnahme
verwendet die bekannte Referenz. Die Qualität neuer fachlicher Entwürfe muss weiterhin getestet werden.

Die mitgelieferte Demo wurde zusätzlich isoliert ausgeführt: Gradle und sämtliche Prüfungen bestanden,
aber Status `GENERIC_ONLY`, weil die fachliche Benutzerbestätigung noch aussteht.
Nachweis: `.netl/job-runs/test-17549493590948253974/`.
Es wurde kein Job gegen die vorhandenen konfigurierten Demo-Schemas ausgeführt und kein solches
Schema neu aufgebaut. Der neue Runner-Fingerprint macht ältere Nachweise sichtbar DRIFTED.
Abschlusskontrolle: keine temporären `netl_jr_*`-Login-Rollen und keine `netl_jt_*`-Fixture-Schemas
in beiden Datenbanken. Nur eigene Testressourcen wurden gelöscht; Logs bleiben erhalten.
Keine Compose-Volumes zurückgesetzt. Vorhandene `.DS_Store`-Dateien unverändert belassen.
