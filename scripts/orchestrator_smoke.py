#!/usr/bin/env python3
"""Optional live OpenCode acceptance test. Uses the user's configured LLM provider.
Creates its own synthetic topic/schemas and removes only those after the test.
"""
import json
from pathlib import Path
import shutil
import subprocess
import uuid

root = Path(__file__).resolve().parents[1]
suffix = uuid.uuid4().hex[:12]
theme = 'tests/orchestrator_' + suffix
topic = root / 'themes' / theme
logs = root / '.netl/acceptance' / suffix
logs.mkdir(parents=True)
topic.mkdir(parents=True)
manifest = json.loads((root / 'themes/demo/standorte/schemas.json').read_text())
shutil.copytree(root / 'themes/demo/standorte/modelle', topic / 'modelle')
shutil.copyfile(root / 'themes/demo/standorte/grants.sql', topic / 'grants.sql')
def physical_name(entry):
    return entry['baseName'] + '_v' + str(entry['schemaVersion'])

for entry in manifest['schemas']:
    entry['baseName'] = 'netl_oc_' + suffix + '_' + entry['database']
# The configuration agent creates the manifest from the explicit specification below.

def run(phase, prompt, agent='themenintegrator'):
    if agent == 'themenintegrator':
        prompt += ' Für den Tool-Parameter schema ausschliesslich die Identifier edit oder pub verwenden, niemals die physischen Namen mit Versionssuffix.'
    try:
        result = subprocess.run(['opencode', 'run', '--agent', agent, '--format', 'json', prompt],
                                cwd=root, capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired as error:
        (logs / (phase + '.jsonl')).write_bytes(error.stdout or b'')
        (logs / (phase + '.stderr')).write_bytes(error.stderr or b'')
        raise
    (logs / (phase + '.jsonl')).write_text(result.stdout)
    (logs / (phase + '.stderr')).write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert not any(e.get('type') == 'error' for e in events), events
    calls = [e['part'] for e in events if e.get('type') == 'tool_use']
    assert calls, 'Agent did not use tools; check provider and MCP setup'
    for call in calls:
        allowed = ({'netl_config_context', 'netl_config_validate', 'netl_config_save', 'read', 'glob', 'grep', 'list'}
                   if agent == 'themenkonfigurator' else
                   {'netl_schema_list', 'netl_schema_plan', 'netl_schema_inspect', 'netl_schema_create', 'netl_schema_recreate', 'netl_schema_drop_previous'})
        assert call['tool'] in allowed, call
        assert call['state']['status'] == 'completed', call
    print(phase + ': ' + ', '.join(c['tool'] for c in calls), flush=True)
    return calls

def outputs(calls, tool):
    return [json.loads(c['state']['output']) for c in calls if c['tool'] == 'netl_' + tool]

try:
    calls = run('00-config', 'Erstelle und speichere die Konfiguration für ' + theme +
                '. Die lokalen synthetischen Modelle liegen bereits unter modelle/. Alle Angaben sind hier vollständig: ' +
                json.dumps(manifest) + '. Verwende config_context, config_validate und config_save. Keine Datenbankänderungen.',
                'themenkonfigurator')
    assert any(c['tool'] == 'netl_config_validate' for c in calls)
    assert any(c['tool'] == 'netl_config_save' for c in calls)
    assert json.loads((topic / 'schemas.json').read_text()) == manifest
    calls = run('01-missing', 'Wie ist der Stand der lokalen Schemas für ' + theme + '? Nur prüfen, nichts ändern.')
    assert not outputs(calls, 'schema_create')
    inspected = outputs(calls, 'schema_inspect')
    assert {r['schema']['ident'] for r in inspected if r['status'] == 'MISSING'} == {'edit', 'pub'}, inspected
    calls = run('02-create', 'Erstelle die noch fehlenden lokalen Schemas für ' + theme + '. '
                'Führe schema_create strikt nacheinander aus: zuerst edit, dessen vollständiges Ergebnis abwarten, dann pub. '
                'Niemals parallele schema_create-Aufrufe. Bei BUSY oder anderen Fehlern stoppen, nicht wiederholen.')
    planned = set()
    for call in calls:
        state = call['state']
        if call['tool'] == 'netl_schema_plan':
            assert json.loads(state['output'])['status'] == 'READY'
            planned.add(state['input']['schema'])
        if call['tool'] == 'netl_schema_create':
            assert state['input']['schema'] in planned, 'Creation without a preceding ready plan'
    created = outputs(calls, 'schema_create')
    assert len(created) == 2 and all(r['status'] == 'CREATED' for r in created), created
    calls = run('03-matching', 'Wie ist der Stand der lokalen Schemas für ' + theme + '? Nur prüfen, nichts ändern.')
    assert not outputs(calls, 'schema_create')
    inspected = outputs(calls, 'schema_inspect')
    assert {r['schema']['ident'] for r in inspected if r['status'] == 'MATCHING'} == {'edit', 'pub'}, inspected
    before_states = {(entry['database'], physical_name(entry)): (root / '.netl/state' /
                     (entry['database'] + '-' + physical_name(entry) + '.json')).read_bytes() for entry in manifest['schemas']}
    calls = run('04-edit-config', 'Bearbeite und speichere für ' + theme +
                ' ausschliesslich die Konfiguration: Setze für Identifier edit overrides.nameByTopic auf false. ' +
                'Alle anderen Einträge unverändert lassen. Kein Schema-Neuaufbau.', 'themenkonfigurator')
    assert any(c['tool'] == 'netl_config_save' for c in calls)
    changed = json.loads((topic / 'schemas.json').read_text())
    assert next(e for e in changed['schemas'] if e['ident'] == 'edit')['overrides']['nameByTopic'] is False
    for (db, name), before in before_states.items():
        assert (root / '.netl/state' / (db + '-' + name + '.json')).read_bytes() == before
    calls = run('05-recreate', 'Baue für ' + theme + ' ausschliesslich das Schema edit ausdrücklich neu auf. ' +
                'Die vorhandenen Daten darin dürfen gelöscht werden. Verwende schema_plan operation=recreate und ' +
                'schema_recreate mit dem gelieferten Token. Bei Fehler stoppen.')
    planned_tokens = set()
    for call in calls:
        if call['tool'] == 'netl_schema_plan':
            planned = json.loads(call['state']['output'])
            if planned.get('status') == 'READY' and 'planToken' in planned:
                planned_tokens.add(planned['planToken'])
        if call['tool'] == 'netl_schema_recreate':
            assert call['state']['input']['planToken'] in planned_tokens
    recreated = outputs(calls, 'schema_recreate')
    assert len(recreated) == 1 and recreated[0]['status'] == 'RECREATED', recreated
    assert recreated[0]['inspection']['status'] == 'MATCHING'
    assert {'name': 'standort'} in recreated[0]['inspection']['structure']['tables']
    pub_entry = next(e for e in manifest['schemas'] if e['ident'] == 'pub')
    assert (root / '.netl/state' / ('pub-' + physical_name(pub_entry) + '.json')).read_bytes() == before_states[('pub', physical_name(pub_entry))]
    # Track v2 for cleanup before asking the agent to create it.
    manifest['schemas'][0]['schemaVersion'] = 2
    calls = run('06-version', 'Setze für ' + theme + ' ausschliesslich beim Identifier edit schemaVersion auf 2. '
                'Validiere und speichere. Basisname, Profil, Optionen und alle übrigen Angaben unverändert lassen. Keine DB-Änderung.', 'themenkonfigurator')
    assert outputs(calls, 'config_save')[-1]['status'] == 'SAVED'
    calls = run('07-create-v2', 'Erstelle für ' + theme + ' das fehlende Schema edit in der jetzt konfigurierten Version 2. Die Vorgängerversion erhalten.')
    assert outputs(calls, 'schema_create')[-1]['status'] == 'CREATED'
    calls = run('08-drop-previous', 'Lösche für ' + theme + ' beim Identifier edit ausdrücklich die Vorgängerversion 1 mit ihren verwalteten Rollen. '
                'Die Daten dieser Vorgängerversion dürfen gelöscht werden. Verwende schema_plan operation=drop-previous und bei READY schema_drop_previous einmal mit dem Token. Bei Fehler stoppen.')
    assert outputs(calls, 'schema_drop_previous')[-1]['status'] == 'DELETED'
    print('PASS: configuration, creation, matching, recreation, version switch and explicit previous-version deletion. Evidence: ' + str(logs), flush=True)
finally:
    for entry in manifest['schemas']:
        for version in range(1, entry['schemaVersion'] + 1):
            db, name = entry['database'], entry['baseName'] + '_v' + str(version)
            assert entry['baseName'] == 'netl_oc_' + suffix + '_' + db
            subprocess.run(['docker', 'compose', 'exec', '-T', db + '-db', 'psql', '-U', 'netl', '-d', db,
                            '-v', 'ON_ERROR_STOP=1', '-c', 'DROP SCHEMA IF EXISTS "' + name + '" CASCADE; DROP ROLE IF EXISTS "' + name + '_read", "' + name + '_write"'],
                           cwd=root, check=True, capture_output=True, timeout=20)
            (root / '.netl/state' / (db + '-' + name + '.json')).unlink(missing_ok=True)
    shutil.rmtree(topic)
