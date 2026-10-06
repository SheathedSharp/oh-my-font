#!/usr/bin/env python3
"""Run full universal profiles for the exact two official families/desktop formats.

Retains the existing exact Sigma coverage failure only. A scoped pass is not an
all-green universal profile; every warning and raw failure stays in the report.
"""
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import importlib.metadata,json,subprocess,sys
from pathlib import Path
from release_support import DIST,WORK,FAMILIES,read_build,sha

def run(pair):
    family,fmt=pair;path=DIST/fmt/family/f'{family}-Regular.{fmt}';report=WORK/f'fontbakery-{family}-{fmt}.json'
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
            allowed=(check['module']=='case_mapping' and check['result']=='FAIL' and len(logs)==1 and isinstance(logs[0]['message'],dict)
                     and logs[0]['message'].get('code')=='missing-case-counterparts' and 'U+03A3:' in text and 'U+03C3:' in text and text.count('U+')==2)
            (accepted if allowed else unexpected).append(row)
    if len(accepted)!=1:unexpected.append({'error':'Expected one reviewed Sigma-only finding'})
    if process.returncode not in (0,1):unexpected.append({'error':'Unexpected FontBakery process exit','code':process.returncode})
    result={'file':path.relative_to(DIST).as_posix(),'sha256':sha(path),'family':family,'format':fmt,'raw_exit':process.returncode,'result':data['result'],
            'accepted_failures':accepted,'unexpected':unexpected,'warnings':warnings,'warning_modules':dict(Counter(r['module'] for r in warnings)),
            'scoped_gate':'passed' if not unexpected else 'failed'}
    print(f'{family} {fmt}: unexpected={len(unexpected)}, warnings={len(warnings)}, raw_exit={process.returncode}',flush=True);return result

def main():
    read_build();WORK.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(run,[(f,t) for f in FAMILIES for t in ('ttf','otf')]))
    result={'version':importlib.metadata.version('fontbakery'),'groups':rows,'passed':all(r['scoped_gate']=='passed' for r in rows)}
    (WORK/'fontbakery-summary.json').write_text(json.dumps(result,indent=2)+'\n');return 0 if result['passed'] else 1
if __name__=='__main__':sys.exit(main())
