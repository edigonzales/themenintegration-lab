#!/usr/bin/env python3
"""Live delegated OpenCode acceptance, using only an owned synthetic topic.
Uses the configured provider. Does not confirm or mutate the demo's job/schemas.
"""
import json
from pathlib import Path
import shutil
import subprocess
import uuid

root = Path(__file__).resolve().parents[1]
suffix = uuid.uuid4().hex[:12]
theme = 'tests/job_smoke_' + suffix
topic = root / 'themes' / theme
logs = root / '.netl/acceptance' / ('job-' + suffix)
logs.mkdir(parents=True)
topic.mkdir(parents=True)
manifest = json.loads((root / 'themes/demo/standorte/schemas.json').read_text())
shutil.copytree(root / 'themes/demo/standorte/modelle', topic / 'modelle')
for entry in manifest['schemas']:
    entry['baseName'] = 'netl_js_' + suffix + '_' + entry['database']
    entry.pop('sqlFiles', None)
(topic / 'schemas.json').write_text(json.dumps(manifest))


def cli(*args):
    result = subprocess.run(['../netl-mcp/bin/netl', '--workspace', '.', *args, '--json'],
                            cwd=root, capture_output=True, text=True, timeout=180)
    return json.loads(result.stdout)


def agent(phase, prompt):
    result = subprocess.run(['opencode', 'run', '--agent', 'themenintegrator', '--format', 'json', prompt],
                            cwd=root, capture_output=True, text=True, timeout=480)
    (logs / (phase + '.jsonl')).write_text(result.stdout)
    (logs / (phase + '.stderr')).write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert not any(e.get('type') == 'error' for e in events), events
    calls = [e['part'] for e in events if e.get('type') == 'tool_use']
    assert calls, 'No tool calls'
    allowed = {'task', 'read', 'glob', 'grep', 'list', 'netl_job_context', 'netl_job_validate',
               'netl_job_confirm', 'netl_job_test', 'netl_job_status'}
    for call in calls:
        assert call['tool'] in allowed, call
        assert call['state']['status'] == 'completed', call
        if call['tool'] == 'task':
            assert call['state']['input']['subagent_type'] in {'job-autor', 'job-pruefer'}, call
    print(phase + ': ' + ', '.join(c['tool'] for c in calls), flush=True)
    # Export contains the child references and full permission/tool evidence for review.
    session = next((e.get('sessionID') for e in events if e.get('sessionID')), None)
    if session:
        export = subprocess.run(['opencode', 'export', session], cwd=root, capture_output=True, text=True, timeout=30)
        (logs / (phase + '.session.json')).write_text(export.stdout)
    for index, call in enumerate(calls):
        if call['tool'] == 'task':
            child = call['state'].get('metadata', {}).get('sessionId')
            if child:
                exported = subprocess.run(['opencode', 'export', child], cwd=root, capture_output=True, text=True, timeout=30)
                (logs / (phase + '.child-' + str(index) + '.json')).write_text(exported.stdout)
    return calls


try:
    for ident in ('edit', 'pub'):
        result = cli('schema', 'create', theme, ident)
        assert result['status'] == 'CREATED', result
    calls = agent('01-author', 'Erstelle für Thema ' + theme + ' den Job transfer. '
                  'Delegiere seriell zuerst an job-autor und danach job-pruefer. '
                  'Der Autor muss build.gradle UND SQL selbst über job_write_transform schreiben. '
                  'Dies ist ein Infrastruktur-Abnahmetest mit dem bekannten Demo-Fall, keine neue Fachmodellierung. '
                  'Beauftrage beide ausdrücklich, ihre Referenzdateien unter themes/demo/standorte/jobs/edit-to-pub '
                  'mit read zu lesen und unverändert über ihre NETL-Schreibwerkzeuge im neuen Job zu speichern. '
                  'Autor: job.json, build.gradle, sql/standorte.sql. Prüfer: tests.json, '
                  'fixtures/standorte.sql, assertions/expected.sql. Dateinamen, Tabellen-/Spaltennamen und '
                  'Werte exakt beibehalten. Keine Dateien per Shell kopieren; jedes Artefakt über das jeweilige '
                  'Schreibwerkzeug mit vollständigem Inhalt erzeugen. Die SQL-Schemaparameter machen die '
                  'Referenz bereits unabhängig vom Thema. Insbesondere keine vereinfachten Tabellen erfinden. '
                  'Verwende exakt denselben fachlichen Testfall: N1 Depot und N2 Büro '
                  'bei Werk Nord, S1 Lager bei Werk Süd, Punkte (2600000,1200000), (2600100,1200100), '
                  '(2600200,1200200), SRID 2056. Pub muss exakt diese drei Zeilen enthalten. '
                  'Fachliche Transformation: Quelle standorte_standort hat Kennung, aname, geometrie und '
                  'organisation als Fremdschlüssel auf standorte_organisation.t_id. Die Organisation hat '
                  'aname. Ziel standort hat kennung, aname, geometrie und organisation als TEXT. '
                  'SQL muss Quelltabellen joinen und o.aname AS organisation übertragen, niemals '
                  'Fixture-Werte als konstantes VALUES-Ergebnis publizieren. Alle vier fachlichen '
                  'Spalten gehören in tables[].columns. Fixtures müssen zuerst Organisationen, dann '
                  'Standorte mit numerischem Fremdschlüssel einfügen. Das Quellschema hat keine Tabelle standort. '
                  'Keine feste Schema-Version in SQL, echte Db2Db-Ausführung vorsehen. '
                  'Noch nichts bestätigen oder ausführen. Nach beiden Delegationen job_validate verwenden '
                  'und konkrete Erwartungen anzeigen. Keine anderen Themen verändern.')
    delegated = {c['state']['input']['subagent_type'] for c in calls if c['tool'] == 'task'}
    assert delegated == {'job-autor', 'job-pruefer'}, delegated
    validated = cli('job', 'validate', theme, 'transfer')
    assert validated['status'] == 'VALID', validated
    # This test harness is the user of its disposable topic: explicitly confirms the displayed contract.
    calls = agent('02-test', 'Für meinen isolierten Software-Abnahmetest bestätige ich ausdrücklich '
                  'die folgenden angezeigten Testdateien und Erwartungen. Tool-Parameter exakt: theme="' + theme + '", job="transfer". ' +
                  json.dumps(validated['requirements'], ensure_ascii=False) + '. Die exakte '
                  'expectationsRevision ist ' + validated['expectationsRevision'] + '. '
                  'Rufe job_confirm mit diesem Wert und theme="' + theme + '", job="transfer" auf, danach job_test mit denselben Parametern genau einmal. '
                  'Bei Fehler stoppen, nichts reparieren. Danach Ergebnisprüfung an job-pruefer delegieren. '
                  'Niemals theme=demo/standorte verwenden. Keine Ausführung auf den konfigurierten lokalen Schemas.')
    assert any(c['tool'] == 'netl_job_confirm' for c in calls), calls
    assert any(c['tool'] == 'netl_job_test' for c in calls), calls
    status = cli('job', 'status', theme, 'transfer')
    (logs / 'result.json').write_text(json.dumps(status, ensure_ascii=False, indent=2))
    assert status['lastRun']['status'] == 'PASSED', status
    assert any(c['tool'] == 'task' and c['state']['input']['subagent_type'] == 'job-pruefer' for c in calls)
    # Independent mutation probe: the LLM's assertions must actually catch a wrong organisation.
    sql_file = topic / 'jobs/transfer' / validated['manifest']['sqlFiles'][0]
    original = sql_file.read_text()
    try:
        sql_file.write_text("SELECT kennung, aname, 'INTENTIONALLY WRONG'::text AS organisation, geometrie FROM (\n" +
                            original.strip().rstrip(';') + '\n) probe;\n')
        negative = cli('job', 'test', theme, 'transfer')
        (logs / 'negative-mapping.json').write_text(json.dumps(negative, ensure_ascii=False, indent=2))
        assert negative['status'] == 'FAILED' and negative.get('gradleSucceeded') is True, negative
        assert any(c['status'] == 'FAILED' and c.get('origin') for c in negative.get('checks', [])), negative
    finally:
        sql_file.write_text(original)
    print('PASS; evidence: ' + str(logs), flush=True)
finally:
    if (topic / 'jobs').exists():
        shutil.copytree(topic / 'jobs', logs / 'generated-jobs', dirs_exist_ok=True)
    # Exact schemas allocated by this harness, never any user/demo schema or volume.
    for entry in manifest['schemas']:
        name = entry['baseName'] + '_v' + str(entry['schemaVersion'])
        assert name.startswith('netl_js_' + suffix + '_')
        subprocess.run(['docker', 'exec', 'themenintegration-lab-' + entry['database'] + '-db-1',
                        'psql', '-v', 'ON_ERROR_STOP=1', '-U', 'netl', '-d', entry['database'], '-c',
                        'DROP SCHEMA IF EXISTS "' + name + '" CASCADE; DROP ROLE IF EXISTS "' + name + '_read", "' + name + '_write";'],
                       check=True, capture_output=True, text=True)
        (root / '.netl/state' / (entry['database'] + '-' + name + '.json')).unlink(missing_ok=True)
    shutil.rmtree(topic)
