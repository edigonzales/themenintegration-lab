# Themenintegration Lab

Erster ausführbarer MVP für lokale Schema-Erstellung mit einem OpenCode-Themenintegrator.
Die Werkzeuge laufen auch ohne LLM über die CLI im benachbarten `netl-mcp`-Repository.
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
docker compose up -d --build --wait
docker compose exec -T edit-db psql -U netl -d edit -v ON_ERROR_STOP=1 < scripts/bootstrap-roles.sql
docker compose exec -T pub-db psql -U netl -d pub -v ON_ERROR_STOP=1 < scripts/bootstrap-roles.sql
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
es gibt keine zusätzliche pauschale Freigabefrage. Der Themenintegrator besitzt nur Lesezugriff und die sechs Schema-Werkzeuge.
Shell, Dateiänderungen, Subagenten und andere MCP-Werkzeuge sind gesperrt.

Die MCP-Konfiguration verwendet `../netl-mcp/bin/netl --workspace . mcp`. STDOUT ist ausschliesslich
MCP-Protokoll. Eine lokale Installation kann den Startbefehl anpassen, ohne die Agentenrolle zu ändern.

## Thema und Konfiguration

`themes/demo/standorte/schemas.json` definiert die beiden Schema-Identifier `edit` und `pub`,
Basisnamen, Schema-Versionen, Datenbanken, lokale Modelle, Profile und SQL-Dateien. Das Edit-Modell enthält Organisationen,
Standorte und deren Beziehung; das Pub-Modell eine flache Standortklasse. Die Geometrie ist ein LV95-Punkt.
Die Modelle benötigen ausser der eingebauten INTERLIS-Sprache keine externen Modelle.

Die Profile liegen versioniert im `netl-mcp`-JAR. Ihre einzige Abweichung ist `nameByTopic`:
`lab-edit-v1=true`, `lab-pub-v1=false`. Entsprechend entstehen `standorte_standort` und `standort`.
Weitere Defaults stammen aus der festgelegten GRETL-/ili2pg-Version. Dies sind Lab-Profile, keine AGI-Standards.
Die JSON Schemas liegen in `netl-mcp/src/main/resources/schemas-v1.schema.json` und `schemas-v2.schema.json`.

Modelldateien werden für jeden Lauf kopiert und per SHA-256 dokumentiert. GRETL erhält ausschliesslich
dieses lokale Modellverzeichnis; es erfolgt keine Suche in entfernten Modellrepositories.
Modelldateien und alle ihre Abhängigkeiten müssen in `modelFiles` stehen; Basenames müssen eindeutig sein.
Overrides sind nur für die im Profil aufgelisteten Optionen erlaubt. `defaultSrsCode` ist eine Zeichenkette,
alle anderen unterstützten Optionen sind boolesch. Unbekannte Optionen werden abgewiesen.

## Versionen, SQL und Berechtigungen

Neue Manifeste verwenden `formatVersion: 2`. Jeder Eintrag enthält `ident`, `baseName`, `database`,
`models`, `modelFiles` und `profile`. Optional sind `schemaVersion` (positive ganze Zahl), `overrides`,
`schemaComment`, `roleSuffix` und `sqlFiles`. Beispiel:

```json
{
  "ident": "edit",
  "baseName": "demo_standorte_edit",
  "schemaVersion": 2,
  "database": "edit",
  "models": ["Lab_Standorte_Edit"],
  "modelFiles": ["modelle/Lab_Standorte_Edit.ili"],
  "profile": "lab-edit-v1",
  "sqlFiles": {"grants": "grants.sql"}
}
```

Daraus entsteht `demo_standorte_edit_v2`. Ohne `schemaVersion` bleibt der Basisname unverändert.
Schema-Version, Profilversion und INTERLIS-Modellversion sind unabhängig. Format 1 bleibt unterstützt:
`name` ist dort weiterhin der vollständige physische Name. Eine explizite Formatumstellung muss diesen
Namen und die Rollennamen erhalten; NETL interpretiert vorhandene `_v1`-Suffixe niemals automatisch.

Die gemeinsame Logik liegt versioniert im NETL-Image; Herkunft und Abweichungen von `schema-jobs/shared`
sind in `../netl-mcp/runtime/README.md` dokumentiert. Reihenfolge: Schema/Rollen anlegen, INTERLIS importieren,
Kommentar setzen, optionale SQL-Dateien `views`, `postscript`, `stdcols` ausführen, Standardrechte setzen,
optionale `grants` ausführen. Pfade sind relativ zum Thema. Alle Dateien werden kopiert und gehasht.
In SQL werden `${dbSchema}` und `${roleSuffix}` ersetzt. SQL ist vertrauenswürdiger, vorab geprüfter
Code ausserhalb der Agentenrollen; kein SQL-Sandboxing. Weitere Spezialrollen werden nicht automatisch verwaltet.

Standardrollen sind `<physischer Name><roleSuffix>_read` und `_write`. `roleSuffix` ist normalerweise leer;
bei Bedarf wird etwa `_editdb` explizit konfiguriert. Leser erhalten Schema-USAGE und Tabellen-SELECT;
Schreiber zusätzlich INSERT/UPDATE/DELETE und Sequenz-USAGE. Dies gilt für vorhandene Objekte,
nicht für später angelegte Tabellen. Empfängerrollen stehen im themenspezifischen Grants-SQL.

Ein Versionswechsel legt das neue Schema daneben an. Es gibt keine automatische Datenmigration,
Umschaltung oder Löschung. `schema list` zeigt auch aufgezeichnete ältere Versionen und deren Laufstatus;
dieser Laufstatus ersetzt keine aktuelle Inspection. Vorgänger bedeutet exakt n-1, nicht die letzte vorhandene Version.

Nur mit ausdrücklichem Löschauftrag:

```sh
../netl-mcp/bin/netl --workspace . schema plan demo/standorte edit drop-previous --json
../netl-mcp/bin/netl --workspace . schema drop-previous demo/standorte edit PLAN_TOKEN --json
```

CLI/MCP löschen ausschliesslich den nachgewiesenen Vorgänger und dessen verwaltete Rollen.
Unversionierte Schemas und Version 1 haben keinen solchen Vorgänger. Externe Abhängigkeiten blockieren.
Die Löschung wird protokolliert; alte erfolgreiche Laufverzeichnisse bleiben erhalten.

Bestehende Demo-Schemas aus dem alten Runner werden nicht verändert. Ein geänderter Runner-Fingerprint
führt zu DRIFTED, fehlende Rollenverwaltung zu `LEGACY_UNVERIFIED`. Nur ein expliziter Neuaufbau kann
die neue Logik anwenden; gleichnamige Rollen ohne passenden Erstellungsnachweis werden nicht übernommen.

## Konfiguration mit einem Agenten vorbereiten

Die separate Primary-Rolle `themenkonfigurator` liest vorhandene lokale Modelle und darf ausschliesslich
über die Konfigurationswerkzeuge `schemas.json` schreiben. Der `themenintegrator` bleibt die Standardrolle.

```text
/thema-config demo/standorte
```

Beispielauftrag an den Themenkonfigurator:

> Erstelle für demo/standorte eine Konfiguration mit dem Modell Lab_Standorte_Edit aus
> modelle/Lab_Standorte_Edit.ili, Identifier edit, Datenbank edit, Schemaname demo_standorte_edit_v1
> und Profil lab-edit-v1. Validiere und speichere sie.

Themenverzeichnis und Modelldateien müssen bereits existieren. Fehlende fachliche Angaben werden
geklärt. Ein reiner Vorschlagsauftrag speichert nichts. Ein ausdrücklicher Konfigurationsauftrag
erlaubt die Speicherung ohne zusätzliche pauschale Bestätigung und verändert niemals die Datenbank.
Bestehende Identifier, Datenbankziele, Basisnamen und Rollensuffixe bleiben erhalten. Explizite Versionswechsel
und neue Einträge sind möglich. Modelle, SQL-Dateien und Profile werden nicht bearbeitet.

Die Konfigurationswerkzeuge funktionieren ohne Docker oder Datenbank. `VALID` bedeutet, dass die
Manifest- und Dateiprüfungen bestanden wurden; Modellkompilierbarkeit und vollständige
INTERLIS-Abhängigkeiten werden dabei nicht nachgewiesen.

```sh
../netl-mcp/bin/netl --workspace . config context demo/standorte --json
../netl-mcp/bin/netl --workspace . config validate demo/standorte /pfad/entwurf.json --json
../netl-mcp/bin/netl --workspace . config save demo/standorte /pfad/entwurf.json REVISION --json
```

`REVISION` ist der Inhalts-Hash aus `config_context`, bei fehlender Datei `ABSENT`.
`config_save` prüft erneut, sperrt konkurrierende Werkzeugschreibzugriffe und ersetzt die Datei atomar.
`CONFIG_CONFLICT` verlangt erneutes Lesen und Abgleichen. Vorher/Nachher und Speicherungsergebnis
werden unter `.netl/config/` protokolliert. Nicht gesetzte Optionen bleiben bei Profil-/Runner-Defaults.

## Verwaltetes Schema ausdrücklich neu aufbauen

```text
/schema-recreate demo/standorte edit
```

Oder: „Baue das lokale Schema edit für demo/standorte ausdrücklich neu auf; die vorhandenen
Daten darin dürfen gelöscht werden.“

**Ein Neuaufbau löscht alle Daten im Ziel-Schema.** Die Konfiguration bleibt die Quelle für den
anschliessenden Import. Eine gewöhnliche Erstellung oder Konfigurationsbearbeitung autorisiert
keinen Neuaufbau. Es gibt keine automatische Migration, Datensicherung oder Wiederherstellung.

```sh
../netl-mcp/bin/netl --workspace . schema plan demo/standorte edit recreate --json
../netl-mcp/bin/netl --workspace . schema recreate demo/standorte edit PLAN_TOKEN --json
```

Der Plan prüft die lokale Umgebung und den Laufnachweis. Eine transaktionale, zurückgerollte
Löschprobe prüft PostgreSQLs tatsächliche Kaskade; sie verändert keine Schemaobjekte dauerhaft,
benötigt aber DDL-Rechte und kann kurz sperren. Der privilegierte Lab-Benutzer besitzt diese Rechte.
Abhängige Objekte ausserhalb des Ziels blockieren den Vorgang; interne TOAST-Speicherobjekte zählen
zum Ziel. Der Plan speichert ein einmaliges Token unter `.netl/plans/`. Daher ist diese Planvariante
kein rein lesendes Werkzeug. Der bisherige Standardplan `create` bleibt lesend.

Nur Schemas mit zum Workspace, Thema, Identifier und Datenbankziel passendem Laufnachweis sind
zulässig; auch `DRIFTED` oder `INCOMPLETE` kann auf ausdrücklichen Auftrag neu aufgebaut werden.
`UNMANAGED` bleibt gesperrt. Änderungen an Konfiguration, Modellbytes, erfasster Struktur oder
Laufzustand machen das Token ungültig. Das Token ersetzt keinen Nutzerauftrag.

Die Ausführung hält dieselbe Advisory Lock wie `create`, prüft erneut und schützt die tatsächliche
Löschung ebenfalls transaktional vor externen Kaskaden. Erfolg liefert `RECREATED` mit Inspection.
Löschung und GRETL-Import sind keine gemeinsame Transaktion: Scheitert der Import, ist das alte Schema
bereits gelöscht. Ein solcher Lauf bleibt `INCOMPLETE`; kein automatischer Wiederholungsversuch.
Laufprotokolle inklusive vorheriger Inspection bleiben erhalten. Ein neuer expliziter Neuaufbauauftrag
mit neuem Plan kann einen fehlgeschlagenen Lauf behandeln.

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
Rollenattribute, Mitgliedschaften, Eigentümer und Objektberechtigungen werden zusätzlich erfasst.
Views können durch lokale SQL-Dateien entstehen; Triggerdefinitionen, vollständige View-Semantik,
Datenmigration und Publikationsjobs werden nicht semantisch verifiziert.
Bei Änderungen wird nichts automatisch gelöscht, migriert oder repariert. Ein expliziter Neuaufbau ist unten beschrieben.

## Lokale Umgebung und Protokolle

- Compose-Projekt: `themenintegration-lab`; feste Ports nur auf `127.0.0.1`: Edit `55431`, Pub `55432`.
- Eigene Volumes: `themenintegration-lab_edit-data`, `themenintegration-lab_pub-data`.
- DDL-Benutzer `netl`, Passwort `netl-local`, ist für dieses wegwerfbare Lab privilegiert.
- Synthetische DML-Benutzer: `netl_reader` / `netl-reader-local` und `netl_writer` / `netl-writer-local`.
  Das Bootstrap-SQL legt fehlende Benutzer an und verändert keine bestehenden Rollen oder Schemas.
- Keine benutzerweite Properties-Datei; keine Remote-DB-Parameter in CLI oder MCP.
- PostGIS und GRETL-Basisimage sind per Digest festgehalten. Das abgeleitete `netl/gretl:0.3.0`
  wird lokal gebaut; NETL prüft die eingebetteten Runner-Dateien per SHA-256 gegen das JAR.
- GRETL `3.2.861`, ili2pg `5.5.1`, ili2c `5.6.8`, PostGIS-Image `18-3.6`.
- Der getestete Image-Stand enthält PostgreSQL `18.6` und PostGIS `3.6.4`.

Der GRETL-Service prüft die Zuordnung zum Workspace. Alle Importe laufen per `docker exec` im dauerhaft
laufenden NETL/GRETL-Container mit Benutzer 1001, aktiviertem Daemon und gemeinsamem Gradle-Cache.
Eine Workspace-Dateisperre serialisiert alle Runner-Operationen; zusätzlich bleibt die Advisory Lock
pro Ziel-Schema bestehen. Parallele Ausführung liefert `BUSY`.
Nach 120 Sekunden wird der dedizierte Container gestoppt, seine markierten PostgreSQL-Sitzungen werden
beendet und der Container neu gestartet. Der Auftrag wird nicht wiederholt. Nach einem Host-Prozessabbruch
oder unbestätigter Terminierung blockieren `runner-active.json` bzw. `runner-recovery.json` neue Aufträge.
Zur manuellen Wiederherstellung erst sicherstellen, dass kein NETL-Prozess mehr arbeitet, den GRETL-Container
stoppen und markierte DB-Sitzungen beenden; dann die Marker nach Prüfung entfernen und den Runner starten.
Keine Volumes löschen. Ein fehlgeschlagener Schema-Lauf benötigt weiterhin einen expliziten Neuaufbauauftrag.

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
Der MCP-Smoke-Test verwendet eigene synthetische Themen und Testschemas; `--create` erlaubt
deren Erstellung und Neuaufbau ausdrücklich. Er prüft STDIO, parallele Antworten, alle acht Tools,
CLI-Parität und Wiederholbarkeit. Ohne `--create` testet er die Konfigurationsspeicherung im eigenen
Testthema, verändert aber keine Datenbankschemas.

Ein optionaler echter OpenCode-Test verwendet den bereits konfigurierten Modellprovider:

```sh
# Im Lab-Repository; verursacht Modellprovider-Nutzung:
python3 scripts/orchestrator_smoke.py
```

Er legt ein eigenes temporäres Thema an, prüft Konfigurationsvorbereitung, Erstellung, Bearbeitung ohne DB-Änderung und expliziten Neuaufbau und räumt nur seine
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
## GRETL-Datenumbaujobs

Der persistente NETL-Runner unterstützt nun auch LLM-generierte `build.gradle`- und SQL-Dateien,
isolierte synthetische Testdaten und unabhängige Assertions. Anleitung und Grenzen:
[Datenumbaujobs](docs/jobs.md).
