"""Prespecified held-out analysis and standalone figures."""
import csv
import json
from pathlib import Path
import numpy as np
from common import ROOT,FIELDS,LABELS,read,rows,load,dump,sha,probabilities,exact,metrics,cluster_ci,paired_comparison,rescale,normalized,route_mask,calibration,predicted,triage


def analyze():
    import joblib
    from run import classifier_probs,majority_probs
    selection=load(ROOT/'runs/selection.json')
    meta=load(ROOT/'runs/laya-test-metadata.json')
    if meta['selection_sha256']!=sha(ROOT/'runs/selection.json'):raise ValueError('Test selection hash mismatch')
    if sha(ROOT/'runs/tfidf.joblib')!=selection['classifier_sha256']:raise ValueError('Classifier changed')
    if sha(ROOT/'runs/laya-dev.jsonl')!=selection['development_predictions_sha256']:raise ValueError('Development predictions changed')
    cases=read('test');train=read('train');test_rows=rows(ROOT/'runs/laya-test.jsonl')
    raw=probabilities(test_rows,cases)
    systems={'laya_raw':raw,'laya_calibrated':rescale(raw,selection['temperatures']),
             'tfidf':classifier_probs(joblib.load(ROOT/'runs/tfidf.joblib'),cases),
             'majority':majority_probs(train,cases)}
    if any(not np.array_equal(predicted(raw)[k],predicted(systems['laya_calibrated'])[k]) for k in FIELDS):
        raise ValueError('Calibration changed class ranking')
    output={name:metrics(p,cases,selection['policies'][name]['threshold']) for name,p in systems.items()}
    # One-hot encoding is used solely to reuse label metrics, never reported as probabilities.
    labels=[triage.baseline(c) for c in cases]
    keyword={k:np.eye(len(LABELS[k]))[[LABELS[k].index(r[k]) for r in labels]] for k in FIELDS}
    output['keyword']=metrics(keyword,cases,0)
    output['keyword'].pop('calibration')
    output['keyword']['routing']['threshold']=None
    output['keyword']['routing']['policy']='known owner and impact; sufficient evidence; no probability threshold'
    primary=paired_comparison(exact(raw,cases),exact(systems['tfidf'],cases),cases)
    brier_deltas=[]
    for field in FIELDS:
        y=np.array([LABELS[field].index(c['expected'][field]) for c in cases]);target=np.eye(len(LABELS[field]))[y]
        before=np.sum((normalized(raw[field])-target)**2,axis=1)
        after=np.sum((systems['laya_calibrated'][field]-target)**2,axis=1)
        brier_deltas.append(before-after)
    brier_ci=cluster_ci(np.mean(brier_deltas,axis=0),cases)
    latency=np.array([r['latency_ms'] for r in test_rows])
    summary={'scope':'held-out mechanisms within an authored synthetic template distribution; no real incidents or TypeSafe Jev',
             'test_records':len(cases),'test_families':len({c['family'] for c in cases}),
             'freeze_sha256':sha(ROOT/'FREEZE.json'),'selection_sha256':sha(ROOT/'runs/selection.json'),
             'test_predictions_sha256':sha(ROOT/'runs/laya-test.jsonl'),
             'primary_laya_minus_tfidf':primary,'descriptive_mean_brier_improvement':brier_ci,
             'systems':output,'latency_ms':{'median':float(np.median(latency)),
               'p95_nearest_rank':float(np.sort(latency)[int(np.ceil(.95*len(latency)))-1]),
               'note':'CPU, four threads, one training warmup, batch one, token checks included, loading excluded; Laya only'}}
    artifact=ROOT/'artifacts';artifact.mkdir(exist_ok=True)
    dump(artifact/'metrics.json',summary)
    dump(artifact/'selection.json',selection)
    systems_all={**systems,'keyword':keyword}
    with (artifact/'case-results.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['case_id','family','condition','model','owner','impact','evidence','exact','route'])
        for name,p in systems_all.items():
            pred=predicted(p);ok=exact(p,cases);mask=route_mask(p,0 if name=='keyword' else selection['policies'][name]['threshold'])
            for i,c in enumerate(cases):writer.writerow([c['id'],c['family'],c['variant'],name,*[pred[k][i] for k in FIELDS],int(ok[i]),int(mask[i])])
    # Blind review export has opaque IDs, no family names, labels or predictions.
    import hashlib,random
    review=list(cases);random.Random(20261002).shuffle(review)
    with (artifact/'blind-review.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['review_id','incident','reviewer_owner','reviewer_impact','reviewer_evidence','notes'])
        for c in review:writer.writerow([hashlib.sha256(c['id'].encode()).hexdigest()[:12],c['incident'],'','','',''])
    dump(artifact/'review-key.json',{hashlib.sha256(c['id'].encode()).hexdigest()[:12]:c['id'] for c in cases})
    plots(summary,systems_all,cases,artifact)
    markdown(summary,selection,artifact)
    print(json.dumps({'primary':primary,'exact_accuracy':{k:v['exact'] for k,v in output.items()}},indent=2))
    print('Report:',artifact/'REPORT.md')


def plots(summary,systems,cases,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'figure.dpi':140,'axes.spines.top':False,'axes.spines.right':False})
    names=['majority','keyword','tfidf','laya_raw'];titles=['Training majority','Keyword rules','TF-IDF logistic','Laya raw']
    vals=[summary['systems'][n]['exact'] for n in names]
    fig,ax=plt.subplots(figsize=(7,3.5))
    x=np.arange(len(names));y=np.array([v['estimate'] for v in vals])
    err=np.array([[v['estimate']-v['low'] for v in vals],[v['high']-v['estimate'] for v in vals]])
    ax.bar(x,y,color=['#9ca3af','#6b7280','#2563eb','#d97706']);ax.errorbar(x,y,yerr=err,fmt='none',color='black',capsize=4)
    ax.set_xticks(x,titles);ax.set_ylim(0,1);ax.set_ylabel('All-three exact accuracy');ax.set_title('Held-out synthetic mechanisms · 95% family bootstrap intervals')
    fig.tight_layout();fig.savefig(out/'accuracy.png');fig.savefig(out/'accuracy.svg');plt.close(fig)
    conditions=list(summary['systems']['laya_raw']['conditions'])
    fig,ax=plt.subplots(figsize=(9,4));x=np.arange(len(conditions));width=.25
    for i,name in enumerate(['keyword','tfidf','laya_raw']):
        values=[summary['systems'][name]['conditions'][c]['exact_accuracy'] for c in conditions]
        ax.bar(x+(i-1)*width,values,width,label=name)
    ax.set_xticks(x,[c.replace('_','\n') for c in conditions]);ax.set_ylim(0,1);ax.set_ylabel('Exact accuracy');ax.legend();ax.set_title('Condition breakdown · 36 mechanisms per condition')
    fig.tight_layout();fig.savefig(out/'conditions.png');fig.savefig(out/'conditions.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(5,4));ax.plot([0,1],[0,1],'--',color='#9ca3af')
    for name in ['laya_raw','laya_calibrated','tfidf']:
        bins=summary['systems'][name]['calibration']['impact']['bins'];bins=[b for b in bins if b['n']]
        ax.plot([b['mean_probability'] for b in bins],[b['accuracy'] for b in bins],'o-',label=name)
    ax.set(xlim=(0,1),ylim=(0,1),xlabel='Mean selected probability',ylabel='Observed accuracy',title='Impact reliability · descriptive bins')
    ax.legend();fig.tight_layout();fig.savefig(out/'reliability.png');fig.savefig(out/'reliability.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(5,4));curves={}
    for name in ['laya_raw','laya_calibrated','tfidf']:
        p=systems[name];ok=exact(p,cases);points=[]
        for t in np.linspace(0,1,101):
            mask=route_mask(p,float(t))
            if mask.any():points.append({'threshold':float(t),'coverage':float(mask.mean()),'error':float((~ok[mask]).mean())})
        curves[name]=points
        ax.plot([p['coverage'] for p in points],[p['error'] for p in points],label=name)
    ax.set(xlim=(0,1),ylim=(0,1),xlabel='Fraction of all test cases routed',ylabel='Error among routed cases',title='Risk/coverage · descriptive, not policy selection')
    ax.legend();fig.tight_layout();fig.savefig(out/'risk-coverage.png');fig.savefig(out/'risk-coverage.svg');plt.close(fig)
    dump(out/'risk-coverage.json',curves)


def percent(x):return 'n/a' if x is None else f'{100*x:.1f}%'


def markdown(summary,selection,out):
    primary=summary['primary_laya_minus_tfidf'];systems=summary['systems']
    lines=['# Local incident-triage study v1','',
      '**Scope:** Laya and local baselines on synthetic incidents. This is not TypeSafe Jev, a real-incident benchmark, or a production validation.','',
      'The fixed test set contains **288 records from 36 held-out fault mechanisms**. All eight variants of a mechanism remain in one split. Confidence intervals resample entire mechanisms, not individual rows.','',
      '## Primary result','',
      f"Laya minus TF-IDF exact accuracy: **{100*primary['estimate']:+.1f} percentage points**, 95% paired family-bootstrap CI [{100*primary['low']:+.1f}, {100*primary['high']:+.1f}]. Prespecified two-sided family sign-flip p = {primary['sign_flip_p']:.5f}.",'',
      'This is the only prespecified inferential comparison. It compares a pretrained decision model with a task-trained classifier; it does not isolate architecture or training-data effects. The p-value assumes exchangeability under the null.','',
      '| System | Exact accuracy [95% CI] | Owner | Impact | Evidence |','|---|---|---|---|---|']
    for name,m in systems.items():
        e=m['exact'];lines.append(f"| {name} | {percent(e['estimate'])} [{percent(e['low'])}, {percent(e['high'])}] | "+' | '.join(percent(m['fields'][k]['accuracy']) for k in FIELDS)+' |')
    lines+=['','![Accuracy](accuracy.png)','','## Development-only selection','',
            f"TF-IDF C selected: {selection['chosen_C']}. Laya temperatures (applied to clipped, returned probabilities): `{json.dumps(selection['temperatures'])}`.",'',
            'Temperature scaling preserves label rankings. Its effect on calibration is descriptive; no temperature or routing policy was chosen on test.','',
            '| System | Mean field Brier | Mean field NLL |','|---|---|---|']
    for name,m in systems.items():
        if 'calibration' in m:
            lines.append(f"| {name} | {np.mean([m['calibration'][k]['brier'] for k in FIELDS]):.4f} | {np.mean([m['calibration'][k]['nll'] for k in FIELDS]):.4f} |")
    ci=summary['descriptive_mean_brier_improvement']
    lines +=['',f"Raw-minus-calibrated mean Brier change: {ci['estimate']:+.4f}, descriptive 95% family CI [{ci['low']:+.4f}, {ci['high']:+.4f}]. Positive means improvement.",'',
             '![Reliability](reliability.png)','','## Routing and failure modes','',
             'Development threshold selection required at least 20 routed records from five mechanisms and empirical error at most 5%. This is not a certified risk bound. A disabled policy means no qualifying threshold was found.','',
             '| System | Frozen threshold | Test routes | Families routed | Coverage | Routed errors | Error rate | Critical recall |','|---|---|---|---|---|---|---|---|']
    for name,m in systems.items():
        r=m['routing'];threshold='label rules' if name=='keyword' else 'disabled' if r['threshold'] is None else str(r['threshold'])
        lines.append(f"| {name} | {threshold} | {r['routes']} | {r['families_routed']} | {percent(r['coverage'])} | {r['errors']} | {percent(r['error_rate'])} | {percent(m['critical_recall']['recall'])} |")
    lines+=['','No routed decisions means an undefined routed error rate, not 0% error. Critical recall covers all critical cases regardless of whether the routing gate accepts them. Full intervals and counts are in metrics.json.','',
            '![Risk coverage](risk-coverage.png)','','![Conditions](conditions.png)','','| System / transform | Clean-correct families | Became wrong | Conditional failure rate |','|---|---|---|---|']
    for name in ['keyword','tfidf','laya_raw']:
        for v,m in systems[name]['paired_transforms'].items():lines.append(f"| {name} / {v} | {m['clean_correct_families']} | {m['clean_correct_to_wrong']} | {percent(m['conditional_failure_rate'])} |")
    latency=summary['latency_ms']
    lines+=['','## Runtime and reproducibility','',f"Laya CPU inference median: {latency['median']/1000:.2f} s per incident; p95: {latency['p95_nearest_rank']/1000:.2f} s. Four threads, three questions, batch size one, training-case warmup; includes budget checks, excludes model loading. No speed comparison with the baselines is claimed.",'',
      'Inference ran in-process with Python socket connections blocked and local weights. Frozen protocol/source/data/weight hashes, development selections, and raw predictions are retained under study/. Each condition passed the token-budget guard.','',
      '## Limits and next steps','',
      '- The templates are shared across train/dev/test; only fault mechanisms are held out. A classifier can learn template cues. These intervals describe the authored mechanism distribution conditional on that design, not arbitrary prose or operational incidents.',
      '- Some fault mechanisms are semantically related even when their IDs differ. There are 36 resampling units, not 288 independent real incidents; bootstrap assumptions remain approximate.',
      '- Labels are mechanically checked oracle labels authored with the generator. Independent human review has not happened. Use blind-review.csv before making stronger claims; record corrections as a new dataset version.',
      '- Class mix is engineered. Evidence sufficiency is partly determined by other labels. Scores are not estimates under a real incident base rate.',
      '- Laya probabilities are rounded checkpoint outputs with existing temperature scaling. The additional temperature fit is small-sample and task-specific.',
      '- No generative local LLM, second decision-model checkpoint, fine-tuning comparison, or external dataset is included. They remain extensions, not implied evidence.',
      '- Protocol was frozen locally before evaluation, not externally registered. No prompt changes were made using study predictions. Secondary plots and comparisons are descriptive.',
      '', 'A defensible blog claim should name Laya and this synthetic task, report the baseline and uncertainty, and show concrete failure cases.','',
      '## Artifacts','',
      '- [Protocol](../PROTOCOL.md) and [freeze manifest](../FREEZE.json)',
      '- [Full metrics](metrics.json), [case results](case-results.csv), [development selection](selection.json)',
      '- [Blinded review sheet](blind-review.csv) (pending review)',
      '- Figures are available as PNG and SVG next to this report.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':analyze()
