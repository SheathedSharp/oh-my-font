#!/usr/bin/env python3
"""Run each full reference family/format separately; retain every universal result.

The only scoped exception is the existing U+03A3/U+03C3 coverage pair. A scoped
pass is not a green universal profile. Unexpected FAIL/ERROR remains blocking.
"""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import importlib.metadata,json,subprocess,sys
from pathlib import Path
from build import OUT,FAMILIES,sha

def run(pair):
    family,fmt=pair;path=OUT/'fonts'/f'{family}FullDraft-Reference.{fmt}'
    report=OUT/f'fontbakery-{family}-{fmt}.json'
    cmd=[str(Path(sys.executable).with_name('fontbakery')),'check-universal','--skip-network','--no-progress','--no-colors','--full-lists','--json',str(report),str(path)]
    with report.with_suffix('.log').open('w') as log:process=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    data=json.loads(report.read_text());accepted=[];unexpected=[];warnings=[]
    for section in data['sections']:
      for check in section['checks']:
        if check['result'] not in ('WARN','FAIL','ERROR','FATAL'):continue
        logs=[r for r in check['logs'] if r['status'] in ('WARN','FAIL','ERROR','FATAL')]
        row={'module':check['module'],'result':check['result'],'messages':[r['message'] for r in logs]}
        if check['result']=='WARN':warnings.append(row);continue
        text=json.dumps(row['messages'])
        allowed=(check['module']=='case_mapping' and check['result']=='FAIL' and len(logs)==1 and
                 isinstance(logs[0]['message'],dict) and logs[0]['message'].get('code')=='missing-case-counterparts' and
                 'U+03A3:' in text and 'U+03C3:' in text and text.count('U+')==2)
        (accepted if allowed else unexpected).append(row)
    if len(accepted)!=1:unexpected.append({'error':'Expected exactly one pre-existing Sigma coverage finding'})
    if process.returncode not in (0,1):unexpected.append({'process_exit':process.returncode})
    result={'family':family,'format':fmt,'file':path.relative_to(OUT).as_posix(),'sha256':sha(path),'raw_exit':process.returncode,
            'result':data['result'],'accepted_failures':accepted,'unexpected':unexpected,'warnings':warnings,
            'warning_modules':dict(Counter(r['module'] for r in warnings)),'scoped_gate':'passed' if not unexpected else 'failed'}
    print(f'{family} {fmt}: raw={process.returncode}, unexpected={len(unexpected)}, warnings={len(warnings)}',flush=True)
    return result

def main():
    with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(run,[(f,t) for f in FAMILIES for t in ('ttf','otf')]))
    result={'fontbakery_version':importlib.metadata.version('fontbakery'),'scope':__doc__,'groups':rows,'passed':all(r['scoped_gate']=='passed' for r in rows)}
    (OUT/'fontbakery-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['passed'] else 1
if __name__=='__main__':sys.exit(main())
