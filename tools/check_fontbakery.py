#!/usr/bin/env python3
"""Run full universal profiles and fail on any unreviewed FAIL/ERROR.
A scoped release gate is not a claim that the full universal profile is green.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def run_group(pair: tuple[str, str]) -> dict:
    fmt, family = pair
    work = ROOT / '.release-work'
    work.mkdir(exist_ok=True)
    report = work / f'fontbakery-{fmt}-{family}.json'
    executable = Path(sys.executable).with_name('fontbakery')
    command = [str(executable), 'check-universal', '--skip-network', '--no-progress', '--no-colors', '--jobs', '2', '--json', str(report), str(ROOT/'dist'/fmt/family/f'*.{fmt}')]
    with report.with_suffix('.log').open('w') as log:
        process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    result = json.loads(report.read_text())
    failures, warnings, unexpected, accepted = [], [], [], []
    for section in result['sections']:
        for check in section['checks']:
            if check['result'] == 'WARN':
                warnings.append(check['module'])
            if check['result'] not in ('FAIL', 'FATAL', 'ERROR'):
                continue
            record = {'file': check.get('filename'), 'module': check['module'], 'result': check['result']}
            logs = [log for log in check['logs'] if log['status'] in ('FAIL', 'FATAL', 'ERROR')]
            messages = [str(log['message']) for log in logs]
            record['messages'] = messages
            failures.append(record)
            # The only accepted FAIL is the intentionally limited Greek-symbol
            # inventory: U+03A3 Sigma has no U+03C3 lowercase partner. No generic
            # missing-character or case-mapping failures are swallowed here.
            allowed = (check['result'] == 'FAIL' and check['module'] == 'case_mapping'
                       and len(logs) == 1 and logs[0]['message'].get('code') == 'missing-case-counterparts'
                       and 'U+03A3:' in messages[0] and 'U+03C3:' in messages[0]
                       and messages[0].count('U+') == 2)
            (accepted if allowed else unexpected).append(record)
    # Unexpected disappearance/expansion also requires a deliberate policy review.
    if len(accepted) != 16:
        unexpected.append({'error': f'Expected 16 reviewed Sigma findings, got {len(accepted)}'})
    if process.returncode not in (0, 1):
        unexpected.append({'error': f'FontBakery process exit {process.returncode}'})
    summary = {'group': f'{fmt}-{family}', 'raw_exit': process.returncode,
               'result': result['result'], 'accepted_failures': accepted,
               'warning_modules': dict(Counter(warnings)), 'unexpected': unexpected,
               'scoped_release_gate': 'passed' if not unexpected else 'failed'}
    print(json.dumps({k:v for k,v in summary.items() if k not in ('accepted_failures',)}, ensure_ascii=True), flush=True)
    return summary

def main() -> int:
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run_group, [(fmt, family) for fmt in ('ttf', 'otf') for family in ('LihuiT', 'zayJu')]))
    output = ROOT/'.release-work/fontbakery-summary.json'
    output.write_text(json.dumps(results, ensure_ascii=True, indent=2)+'\n')
    return 0 if all(row['scoped_release_gate']=='passed' for row in results) else 1

if __name__ == '__main__':
    sys.exit(main())
