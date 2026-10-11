#!/usr/bin/env python3
"""Run full universal profiles for every family and desktop format.

64 files: 2 families × 16 styles × TTF/OTF. WOFF2 is not profiled separately.

Retains the existing exact Sigma coverage failure only. A scoped pass is not an
all-green universal profile; every warning and raw failure stays in the report.
"""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import importlib.metadata,json,subprocess,sys
from pathlib import Path
from release_support import DIST,WORK,FAMILIES,read_build,sha,styles,font_path

def sigma_log(log):
    message=log.get('message')
    text=json.dumps(message)
    return log.get('status')=='FAIL' and isinstance(message,dict) and message.get('code')=='missing-case-counterparts' and 'U+03A3:' in text and 'U+03C3:' in text and text.count('U+')==2

def run(pair):
    """One invocation per family and desktop format, so family checks see siblings."""
    family,fmt=pair
    paths=[DIST/font_path(fmt,family,row['weight'],row['oblique']) for row in styles()]
    report=WORK/f'fontbakery-{family}-{fmt}.json'
    cmd=[str(Path(sys.executable).with_name('fontbakery')),'check-universal','--skip-network','--no-progress','--no-colors','--full-lists','--json',str(report),*[str(p) for p in paths]]
    with report.with_suffix('.log').open('w') as log:process=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    data=json.loads(report.read_text())
    buckets={path.name:{'accepted':[],'unexpected':[],'warnings':[]} for path in paths}
    family_unexpected=[];family_warnings=[]
    for section in data['sections']:
        for check in section['checks']:
            if check['result'] not in ('WARN','FAIL','ERROR','FATAL'):continue
            logs=[r for r in check['logs'] if r['status'] in ('WARN','FAIL','ERROR','FATAL')]
            row={'module':check['module'],'result':check['result'],'messages':[r['message'] for r in logs]}
            bucket=buckets.get(check.get('filename'))
            if check['result']=='WARN':
                (bucket['warnings'] if bucket else family_warnings).append(row);continue
            allowed=check['module']=='case_mapping' and check['result']=='FAIL' and len(logs)==1 and sigma_log(logs[0])
            if bucket is None:
                family_unexpected.append(row);continue
            (bucket['accepted'] if allowed else bucket['unexpected']).append(row)
    if process.returncode not in (0,1):family_unexpected.append({'error':'Unexpected FontBakery process exit','code':process.returncode})
    rows=[]
    for path in paths:
        bucket=buckets[path.name]
        if len(bucket['accepted'])!=1:bucket['unexpected'].append({'error':'Expected one reviewed Sigma-only finding','got':len(bucket['accepted'])})
        unexpected=bucket['unexpected']+family_unexpected
        rows.append({'file':path.relative_to(DIST).as_posix(),'sha256':sha(path),'family':family,'format':fmt,'raw_exit':process.returncode,'result':data['result'],
                     'accepted_failures':bucket['accepted'],'unexpected':unexpected,'warnings':bucket['warnings'],
                     'warning_modules':dict(Counter(r['module'] for r in bucket['warnings'])),
                     'scoped_gate':'passed' if not unexpected else 'failed'})
        print(f'{path.name}: unexpected={len(unexpected)}, warnings={len(bucket["warnings"])}',flush=True)
    return {'rows':rows,'family_warnings':family_warnings,'family':family,'format':fmt}

def main():
    read_build();WORK.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:batches=list(pool.map(run,[(family,fmt) for family in FAMILIES for fmt in ('ttf','otf')]))
    rows=[row for batch in batches for row in batch['rows']]
    result={'version':importlib.metadata.version('fontbakery'),'groups':rows,'family_warnings':[{'family':b['family'],'format':b['format'],'warnings':b['family_warnings']} for b in batches],
            'passed':all(r['scoped_gate']=='passed' for r in rows)}
    result={'version':importlib.metadata.version('fontbakery'),'groups':rows,'passed':all(r['scoped_gate']=='passed' for r in rows)}
    (WORK/'fontbakery-summary.json').write_text(json.dumps(result,indent=2)+'\n');return 0 if result['passed'] else 1
if __name__=='__main__':sys.exit(main())
