---
description: Ein verwaltetes lokales Schema ausdrücklich löschen und neu erstellen
agent: themenintegrator
---
Baue das lokale Schema für $ARGUMENTS ausdrücklich neu auf. Dieser Auftrag erlaubt die Löschung
aller Daten im genannten Ziel-Schema. Ermittle den Identifier mit schema_list und plane mit
schema_plan operation=recreate. Erkläre Ziel, Datenverlust und mögliche Importfehler ohne Wiederherstellung.
Nur bei READY verwende das erhaltene planToken einmal mit schema_recreate.
Bei BLOCKED oder Fehler stoppen, keine automatische Wiederholung. Berichte Inspection und Logpfad.
