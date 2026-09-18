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
for entry in manifest['schemas']:
    entry['name'] = 'netl_oc_' + suffix + '_' + entry['database']
(topic / 'schemas.json').write_text(json.dumps(manifest, indent=2))

def run(phase, prompt):
    result = subprocess.run(['opencode', 'run', '--agent', 'themenintegrator', '--format', 'json', prompt],
                            cwd=root, capture_output=True, text=True, timeout=240)
    (logs / (phase + '.jsonl')).write_text(result.stdout)
    (logs / (phase + '.stderr')).write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert not any(e.get('type') == 'error' for e in events), events
    calls = [e['part'] for e in events if e.get('type') == 'tool_use']
    assert calls, 'Agent did not use tools; check provider and MCP setup'
    for call in calls:
        assert call['tool'] in {'netl_schema_list', 'netl_schema_plan', 'netl_schema_inspect', 'netl_schema_create'}, call
        assert call['state']['status'] == 'completed', call
    print(phase + ': ' + ', '.join(c['tool'] for c in calls), flush=True)
    return calls

def outputs(calls, tool):
    return [json.loads(c['state']['output']) for c in calls if c['tool'] == 'netl_' + tool]

try:
    calls = run('01-missing', 'Wie ist der Stand der lokalen Schemas für ' + theme + '? Nur prüfen, nichts ändern.')
    assert not outputs(calls, 'schema_create')
    inspected = outputs(calls, 'schema_inspect')
    assert {r['schema']['ident'] for r in inspected if r['status'] == 'MISSING'} == {'edit', 'pub'}, inspected
    calls = run('02-create', 'Erstelle die noch fehlenden lokalen Schemas für ' + theme + '.')
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
    print('PASS: actual OpenCode status -> creation -> matching. Evidence: ' + str(logs), flush=True)
finally:
    for entry in manifest['schemas']:
        db, name = entry['database'], entry['name']
        assert name == 'netl_oc_' + suffix + '_' + db
        subprocess.run(['docker', 'compose', 'exec', '-T', db + '-db', 'psql', '-U', 'netl', '-d', db,
                        '-v', 'ON_ERROR_STOP=1', '-c', 'DROP SCHEMA IF EXISTS "' + name + '" CASCADE'],
                       cwd=root, check=True, capture_output=True, timeout=20)
        (root / '.netl/state' / (db + '-' + name + '.json')).unlink(missing_ok=True)
    shutil.rmtree(topic)
