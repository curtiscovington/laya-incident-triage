"""Freeze, infer, fit and analyze the local controlled study."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import socket
import sys
import time
from collections import Counter
import numpy as np
from common import ROOT, FIELDS, LABELS, SEED, sha, read, dump, load, rows, probabilities, exact, normalized, rescale, select_threshold, triage


def audit():
    all_cases=[]; seen=set();groups={}
    manifest=load(ROOT/'data/manifest.json')
    for split in ['train','dev','test']:
        cases=read(split)
        if sha(ROOT/'data'/f'{split}.json')!=manifest['splits'][split]['sha256']:raise ValueError('Dataset hash mismatch')
        inputs=load(ROOT/'data'/f'{split}-inputs.json')
        if inputs != [{'id':c['id'],'incident':c['incident']} for c in cases]:raise ValueError('Input-only projection mismatch')
        families={c['family'] for c in cases}
        if any(f in groups for f in families):raise ValueError('Family leakage')
        groups.update({f:split for f in families})
        for c in cases:
            if c['id'] in seen:raise ValueError('Duplicate ID')
            seen.add(c['id'])
            if set(c['expected'])!=set(FIELDS) or any(c['expected'][k] not in LABELS[k] for k in FIELDS):raise ValueError('Invalid gold label')
            if c['split']!=split:raise ValueError('Incorrect split field')
            body=triage.payload(c)
            if set(body['state'])!={'runbook','incident'}:raise ValueError('Prediction input includes metadata')
        for family in families:
            members=[c for c in cases if c['family']==family]
            if len(members)!=8 or {c['variant'] for c in members}!=set(manifest['variants']):raise ValueError('Incomplete family')
            by={c['variant']:c for c in members}
            for variant in ['paraphrase','distractor','injection']:
                if by[variant]['expected']!=by['clean']['expected']:raise ValueError('Broken invariant')
            if by['missing_owner']['expected']['owner']!='unknown':raise ValueError('Missing-owner oracle')
            if by['missing_impact']['expected']['impact']!='unknown':raise ValueError('Missing-impact oracle')
            if by['conflicting_impact']['expected']['evidence']!='conflicting':raise ValueError('Conflict oracle')
            if by['resolved']['expected']['impact']!='low':raise ValueError('Resolution oracle')
        all_cases+=cases
    if len({c['incident'] for c in all_cases})!=len(all_cases):raise ValueError('Exact duplicate incident text')
    return {'cases':len(all_cases),'families':len(groups),'family_overlap':0,'exact_duplicates':0,
            'independent_human_review':False,'shared_condition_templates':True}


def frozen_paths():
    return [ROOT/'PROTOCOL.md',ROOT/'make_dataset.py',ROOT/'common.py',ROOT/'run.py',ROOT/'analyze.py',
            ROOT.parent/'triage.py',ROOT.parent/'runbook.md',ROOT/'environment.lock.txt',
            ROOT/'test_study.py',
            *[ROOT/'data'/f'{s}.json' for s in ['train','dev','test','manifest','train-inputs','dev-inputs','test-inputs']]]


def freeze():
    path=ROOT/'FREEZE.json'
    if path.exists():raise ValueError('Protocol is already frozen')
    result=audit()
    sources={str(p.relative_to(ROOT.parent)):sha(p) for p in frozen_paths()}
    dump(path,{'created_utc':datetime.now(timezone.utc).isoformat(),'sources':sources,'audit':result,
               'weights_sha256':sha(ROOT.parent/'models/laya/model.safetensors'),
               'scope':'local synthetic protocol freeze; not an externally registered preregistration'})
    print(json.dumps(result,indent=2))


def verify():
    record=load(ROOT/'FREEZE.json')
    for p,digest in record['sources'].items():
        if sha(ROOT.parent/p)!=digest:raise ValueError('Frozen file changed: '+p)
    return record


def offline():
    def block(*args,**kwargs):raise RuntimeError('Network connections forbidden during study inference')
    socket.socket.connect=block;socket.socket.connect_ex=block
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HUB_DISABLE_TELEMETRY']='1'


def infer(split):
    record=verify();offline()
    if sha(ROOT.parent/'models/laya/model.safetensors')!=record['weights_sha256']:raise ValueError('Weights changed')
    selection=ROOT/'runs/selection.json'
    if split=='test' and not selection.exists():raise ValueError('Fit and freeze development selection before test inference')
    out=ROOT/'runs'/f'laya-{split}.jsonl'
    existing=rows(out) if out.exists() else []
    if len({r['id'] for r in existing})!=len(existing):raise ValueError('Duplicate completed predictions')
    cases=load(ROOT/'data'/f'{split}-inputs.json')
    if [r['id'] for r in existing]!=[c['id'] for c in cases[:len(existing)]]:raise ValueError('Resume order mismatch')
    metadata_path=ROOT/'runs'/f'laya-{split}-metadata.json'
    if metadata_path.exists():
        prior=load(metadata_path)
        if prior['freeze_sha256']!=sha(ROOT/'FREEZE.json'):raise ValueError('Resume freeze mismatch')
        if split=='test' and prior['selection_sha256']!=sha(selection):raise ValueError('Selection changed')
    elif existing:raise ValueError('Predictions lack metadata')
    start=time.perf_counter();engine=triage.local_engine(ROOT.parent/'models/laya','cpu')
    load_seconds=time.perf_counter()-start
    # Preflight all budgets before doing scored inference; no outcome labels involved.
    for c in cases:triage.check_token_budget(engine,triage.payload(c))
    triage.call_local(engine,triage.payload(read('train')[0]))
    if not metadata_path.exists():
        dump(metadata_path,{'started_utc':datetime.now(timezone.utc).isoformat(),'freeze_sha256':sha(ROOT/'FREEZE.json'),
                           'selection_sha256':sha(selection) if split=='test' else None,
                           'weights_sha256':record['weights_sha256'],'model':triage.MODEL,'device':str(engine.device),
                           'threads':4,'warmup':'first training incident; excluded','load_seconds':load_seconds,
                           'runtime_config':engine.cfg,'network':'socket connect/connect_ex blocked'})
    with out.open('a') as f:
        for i,c in enumerate(cases[len(existing):],start=len(existing)):
            response,latency,_=triage.call_local(engine,triage.payload(c));triage.validate(response)
            row={'id':c['id'],'probabilities':from_response(response),'response':response,'latency_ms':latency}
            f.write(json.dumps(row,allow_nan=False)+'\n');f.flush()
            if (i+1)%16==0 or i+1==len(cases):print(f'{split}: {i+1}/{len(cases)} complete',flush=True)
    print(f'Completed {split}; no accuracy calculated by inference runner.',flush=True)


def from_response(response):return {k:[response['answers'][k]['probabilities'][v] for v in LABELS[k]] for k in FIELDS}


def fit_classifier(train,regularization):
    from sklearn.pipeline import FeatureUnion,Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    vectorizer=FeatureUnion([('word',TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True)),
                             ('char',TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),sublinear_tf=True))])
    x=vectorizer.fit_transform([c['incident'] for c in train])
    models={k:LogisticRegression(C=regularization,max_iter=2000,random_state=SEED).fit(x,[c['expected'][k] for c in train]) for k in FIELDS}
    return vectorizer,models


def classifier_probs(bundle,cases):
    vectorizer,models=bundle;x=vectorizer.transform([c['incident'] for c in cases]);out={}
    for k,model in models.items():
        p=model.predict_proba(x);out[k]=p[:,[list(model.classes_).index(v) for v in LABELS[k]]]
    return out


def majority_probs(train,cases):
    out={}
    for k in FIELDS:
        count=Counter(c['expected'][k] for c in train)
        out[k]=np.tile([count[v]/len(train) for v in LABELS[k]],(len(cases),1))
    return out


def fit():
    verify()
    target=ROOT/'runs/selection.json'
    if target.exists():raise ValueError('Selection is frozen; refusing to overwrite')
    if (ROOT/'runs/laya-test.jsonl').exists():raise ValueError('Test inference already started')
    train,dev=read('train'),read('dev');raw=probabilities(rows(ROOT/'runs/laya-dev.jsonl'),dev)
    temperatures={}
    for k,p0 in raw.items():
        y=np.array([LABELS[k].index(c['expected'][k]) for c in dev]);p=normalized(p0)
        candidates=[]
        for t in np.geomspace(.25,4,81):
            scaled=rescale({k:p},{k:float(t)})[k]
            nll=float(-np.log(scaled[np.arange(len(p)),y]).mean());candidates.append((nll,float(t)))
        temperatures[k]=min(candidates)[1]
    grid=[];best=None
    for c in [.1,1.,10.]:
        bundle=fit_classifier(train,c);p=classifier_probs(bundle,dev);score=float(exact(p,dev).mean())
        grid.append({'C':c,'dev_exact':score})
        if best is None or score>best[0]:best=(score,c,bundle,p)
    import joblib
    model_path=ROOT/'runs/tfidf.joblib';joblib.dump(best[2],model_path)
    calibrated=rescale(raw,temperatures)
    if any(not np.array_equal(raw[k].argmax(1),calibrated[k].argmax(1)) for k in FIELDS):raise ValueError('Temperature scaling changed argmax')
    systems={'laya_raw':raw,'laya_calibrated':calibrated,'tfidf':best[3],'majority':majority_probs(train,dev)}
    result={'created_utc':datetime.now(timezone.utc).isoformat(),'freeze_sha256':sha(ROOT/'FREEZE.json'),
            'development_predictions_sha256':sha(ROOT/'runs/laya-dev.jsonl'),
            'classifier_sha256':sha(model_path),'C_grid':grid,'chosen_C':best[1],'temperatures':temperatures,
            'policies':{name:select_threshold(p,dev) for name,p in systems.items()}}
    dump(target,result);print(json.dumps(result,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['audit','freeze','dev','fit','test','analyze']);args=parser.parse_args()
    if args.action=='audit':print(json.dumps(audit(),indent=2))
    elif args.action=='freeze':freeze()
    elif args.action in ['dev','test']:infer(args.action)
    elif args.action=='fit':fit()
    else:
        verify()
        from analyze import analyze
        analyze()

if __name__=='__main__':main()
