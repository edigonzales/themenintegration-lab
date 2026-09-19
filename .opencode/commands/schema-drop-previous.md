---
description: Löscht ausdrücklich die verwaltete Vorgängerversion eines lokalen Schemas.
agent: themenintegrator
---
Lösche für $ARGUMENTS ausdrücklich die Vorgängerversion n-1 inklusive ihrer verwalteten Rollen.
Die Daten dieser Vorgängerversion dürfen gelöscht werden. Nutze schema_plan operation=drop-previous
und bei READY genau einmal schema_drop_previous mit planToken. Bei Fehler stoppen, nicht wiederholen.
