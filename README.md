# Themenintegration Lab

Erster ausführbarer MVP für lokale Schema-Erstellung mit einem OpenCode-Themenintegrator.
Die vier Werkzeuge laufen auch ohne LLM über die CLI im benachbarten `netl-mcp`-Repository.
Es werden ausschliesslich synthetische Modelle und eigene lokale Datenbanken verwendet.

## Voraussetzungen und Start

- Java 21 oder neuer zum Starten, JDK 21 für den Gradle-Build (`JAVA_HOME` setzen).
- Docker mit Compose und laufendem Daemon. Auf Apple Silicon muss AMD64-Emulation verfügbar sein:
  das festgelegte PostGIS-Image besitzt hier keine ARM64-Variante.
- `netl-mcp` ist direkt neben diesem Repository geklont. Keine weiteren Repositories nötig.
- OpenCode ist nur für die Agentenoberfläche erforderlich; ein Modellprovider muss bereits konfiguriert sein.

```sh
# Im netl-mcp-Repository:
./gradlew test bootJar

# Im themenintegration-lab-Repository:
mkdir -p .netl
docker compose up -d --wait
../netl-mcp/bin/netl --workspace . schema list demo/standorte --json
../netl-mcp/bin/netl --workspace . schema plan demo/standorte edit --json
../netl-mcp/bin/netl --workspace . schema create demo/standorte edit --json
../netl-mcp/bin/netl --workspace . schema create demo/standorte pub --json
../netl-mcp/bin/netl --workspace . schema inspect demo/standorte edit --json
../netl-mcp/bin/netl --workspace . schema inspect demo/standorte pub --json
```

Bei einer frischen Umgebung meldet `inspect` zunächst `MISSING`. Nach erfolgreicher Erstellung lautet
es `MATCHING`; ein zweites `create` liefert `ALREADY_PRESENT`, ohne Änderungen auszuführen.
CLI-Ausgabe ist immer JSON (mit `--json` kompakt). Fehler und blockierte/abweichende Zustände liefern Exitcode 1;
falsche CLI-Aufrufe Exitcode 2.

## OpenCode

OpenCode aus diesem Repository starten, mit derselben Java-Umgebung wie die CLI:

```sh
opencode
```

`themenintegrator` ist der Primary Agent. Beispiele:

```text
/thema-status demo/standorte
/schema-create demo/standorte
```

Oder: „Wie ist der Stand der lokalen Schemas für demo/standorte?“ / „Erstelle die noch fehlenden Schemas für demo/standorte.“
Statusfragen dürfen keine Erstellung auslösen. Ein ausdrücklicher Erstellungsauftrag genügt;
es gibt keine zusätzliche pauschale Freigabefrage. Der Agent besitzt nur Lesezugriff und die vier NETL-Tools.
Shell, Dateiänderungen, Subagenten und andere MCP-Werkzeuge sind gesperrt.

Die MCP-Konfiguration verwendet `../netl-mcp/bin/netl --workspace . mcp`. STDOUT ist ausschliesslich
MCP-Protokoll. Eine lokale Installation kann den Startbefehl anpassen, ohne die Agentenrolle zu ändern.

## Thema und Konfiguration

`themes/demo/standorte/schemas.json` definiert die beiden Schema-Identifier `edit` und `pub`,
physische Namen, Datenbanken, lokale Modelle und Profile. Das Edit-Modell enthält Organisationen,
Standorte und deren Beziehung; das Pub-Modell eine flache Standortklasse. Die Geometrie ist ein LV95-Punkt.
Die Modelle benötigen ausser der eingebauten INTERLIS-Sprache keine externen Modelle.

Die Profile liegen versioniert im `netl-mcp`-JAR. Ihre einzige Abweichung ist `nameByTopic`:
`lab-edit-v1=true`, `lab-pub-v1=false`. Entsprechend entstehen `standorte_standort` und `standort`.
Weitere Defaults stammen aus der festgelegten GRETL-/ili2pg-Version. Dies sind Lab-Profile, keine AGI-Standards.
Das JSON Schema für die Konfiguration liegt in `netl-mcp/src/main/resources/schemas-v1.schema.json`.

Modelldateien werden für jeden Lauf kopiert und per SHA-256 dokumentiert. GRETL erhält ausschliesslich
dieses lokale Modellverzeichnis; es erfolgt keine Suche in entfernten Modellrepositories.
Modelldateien und alle ihre Abhängigkeiten müssen in `modelFiles` stehen; Basenames müssen eindeutig sein.
Overrides sind nur für die im Profil aufgelisteten Optionen erlaubt. `defaultSrsCode` ist eine Zeichenkette,
alle anderen unterstützten Optionen sind boolesch. Unbekannte Optionen werden abgewiesen.

## Zustände und Grenzen

| Zustand | Bedeutung |
| --- | --- |
| `MISSING` | Schema fehlt; Erstellung möglich |
| `MATCHING` | Konfiguration, Modellbytes und erfasste DB-Struktur passen zum aufgezeichneten erfolgreichen Lauf |
| `UNMANAGED` | Schema vorhanden, aber kein Laufprotokoll dieses Workspaces |
| `DRIFTED` | Konfiguration, Modellbytes oder erfasste DB-Struktur geändert |
| `INCOMPLETE` | Vorheriger Lauf fehlgeschlagen oder unterbrochen; manuell untersuchen |
| `ERROR` | Prüfung nicht möglich; Fehlercode beachten, niemals als fehlendes Schema interpretieren |

`schema_plan` liefert `READY` oder `BLOCKED`, Optionen, Modell-Fingerprints und Voraussetzungen.
Es führt keinen Schemaimport aus und ist kein vollständiger DDL-Diff oder Modellcompiler.
Der echte Schemaimport kompiliert die Modelle. Fehlerhafte Modelle ergeben keinen erfolgreichen Lauf.

`MATCHING` ist keine unabhängige semantische Modellverifikation und keine Datenvalidierung.
Verglichen werden Tabellen, Spalten, Defaults, Constraints, Indizes und Geometrieangaben.
Berechtigungs-/Rollenkonzepte, Trigger, Views, Datenmigration und Publikationsjobs gehören nicht zum MVP.
Bei Änderungen wird nichts automatisch gelöscht, migriert oder repariert.

## Lokale Umgebung und Protokolle

- Compose-Projekt: `themenintegration-lab`; feste Ports nur auf `127.0.0.1`: Edit `55431`, Pub `55432`.
- Eigene Volumes: `themenintegration-lab_edit-data`, `themenintegration-lab_pub-data`.
- Lokaler Benutzer `netl`, Passwort `netl-local`. Die Rolle ist für dieses wegwerfbare Lab privilegiert.
- Keine benutzerweite Properties-Datei; keine Remote-DB-Parameter in CLI oder MCP.
- Images sind zusätzlich per SHA-256-Digest festgehalten, damit erneutes Pull dieselbe Laufzeit liefert.
- GRETL `3.2.861`, ili2pg `5.5.1`, ili2c `5.6.8`, PostGIS-Image `18-3.6`.
- Der getestete Image-Stand enthält PostgreSQL `18.6` und PostGIS `3.6.4`.

Der GRETL-Service prüft die Zuordnung zum Workspace. Jeder Import läuft in einem eigenen kurzlebigen
GRETL-Container im Lab-Netzwerk. Nach 120 Sekunden wird dieser Container inklusive Gradle-Prozessen beendet.
Die Datenbankverbindung hält währenddessen eine Advisory Lock pro Ziel-Schema; parallele Erstellung liefert `BUSY`.

Läufe liegen unter `.netl/runs/`, der letzte Zustand pro Schema unter `.netl/state/`.
Jeder Lauf enthält Modellkopien, effektive Eingabe, Log, Ergebnis und bei Erfolg die Strukturaufnahme.
Diese Dateien werden nicht eingecheckt. Auch unvollständige Läufe blockieren automatische Wiederholungen.
Die Umgebungsprüfung verhindert gewöhnliche Fehlkonfiguration; sie ist keine Sandbox gegen einen Angreifer
mit Kontrolle über Docker oder den Workspace.

## Tests

```sh
# Im netl-mcp-Repository bei laufender Lab-Umgebung:
./gradlew test integrationTest bootJar
python3 scripts/mcp_smoke.py ../themenintegration-lab --create
```

Integrationstests erstellen eindeutig benannte Testschemas und entfernen nur diese wieder.
Der MCP-Smoke-Test verwendet die echten Demo-Schemas; `--create` erlaubt deren Erstellung ausdrücklich.
Er prüft STDIO, parallele Antworten, alle vier Tools, CLI-Parität und Wiederholbarkeit. Ohne `--create` bleibt er lesend.

Ein optionaler echter OpenCode-Test verwendet den bereits konfigurierten Modellprovider:

```sh
# Im Lab-Repository; verursacht Modellprovider-Nutzung:
python3 scripts/orchestrator_smoke.py
```

Er legt ein eigenes temporäres Thema an, prüft „fehlt → erstellen → passend“ und räumt nur seine
Testschemas wieder auf. Protokolle liegen unter `.netl/acceptance/`.

## Stoppen und bewusster Reset

Stoppen ohne Datenverlust:

```sh
docker compose stop
```

**Der folgende manuelle Reset löscht alle Daten des Labs und dessen Zustandszuordnung.**
Nur aus diesem Repository ausführen, nicht als automatische Fehlerbehandlung:

```sh
docker compose down --volumes
rm -rf .netl/state
docker compose up -d --wait
```

Logs unter `.netl/runs/` bleiben zur Diagnose erhalten. Nach einem kompletten Reset sind die Demo-Schemas
wieder `MISSING`. Ein isoliertes Löschen der Zustandsdateien bei weiterhin vorhandenen Schemas ergibt `UNMANAGED`.
