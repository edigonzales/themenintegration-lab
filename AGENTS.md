# Themenintegration Lab

Dieses Repository erprobt lokale Themenintegration mit synthetischen INTERLIS-Modellen.
Die Implementierung der Schema-Werkzeuge liegt im benachbarten `netl-mcp`-Repository.

## Fachliche Regeln

- Themenkonfiguration und versionierte Profile sind die Quelle für Schema-Optionen.
- Keine Schema-Optionen erraten. Nicht gesetzte Optionen verwenden die dokumentierte Runner-Version.
- Statusmeldungen müssen auf Tool-Ergebnissen beruhen. MATCHING bedeutet Übereinstimmung mit einem aufgezeichneten erfolgreichen Lauf, keine vollständige semantische Verifikation.
- Fehlende Erreichbarkeit ist nicht dasselbe wie ein fehlendes Schema.
- Keine Produktionssysteme und keine echten Fachdaten verwenden.

## Rolle themenintegrator

Die eingeschränkte Laufzeitrolle ist in `.opencode/agents/themenintegrator.md` definiert.
Sie liest und orchestriert; Änderungen an Code, Modellen oder Konfiguration sind Entwicklungsarbeit ausserhalb dieser Rolle.

## Entwicklung

Java 21. Unit-Tests und Build in `../netl-mcp` mit `./gradlew test bootJar`.
Der vollständige lokale Testablauf ist im README beschrieben. Integrationstests verwenden eigene Testschemas
und räumen ausschliesslich diese wieder auf. Compose-Volumes des Labs dürfen nur bei einem bewusst angeforderten Reset gelöscht werden.
