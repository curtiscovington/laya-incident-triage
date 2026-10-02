"""Study data contracts and statistics. All resampling units are incident families."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from sklearn.metrics import f1_score, confusion_matrix

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))
import triage
FIELDS=list(triage.CRITERIA)
LABELS={k:list(v) for k,v in triage.CRITERIA.items()}
SEED=20261002


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def read(split):return json.loads((ROOT/'data'/f'{split}.json').read_text())
def dump(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def load(path):return json.loads(Path(path).read_text())
def rows(path):return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def normalized(p):
    p=np.clip(np.asarray(p,dtype=float),1e-8,1)
    return p/p.sum(axis=-1,keepdims=True)


def rescale(probs,temperatures):
    result={}
    for field,prob in probs.items():
        p=normalized(prob)
        logits=np.log(p)/temperatures[field]
        exp=np.exp(logits-logits.max(axis=-1,keepdims=True))
        result[field]=exp/exp.sum(axis=-1,keepdims=True)
    return result


def from_model(result):
    # Preserve rounded provider probabilities in raw records; normalize only for scoring.
    return {k:[result['answers'][k]['probabilities'][label] for label in LABELS[k]] for k in FIELDS}


def probabilities(predictions,cases):
    by_id={p['id']:p for p in predictions}
    if len(by_id)!=len(predictions) or set(by_id)!={c['id'] for c in cases}:
        raise ValueError('Missing, duplicate, or unexpected prediction IDs')
    result={k:np.asarray([by_id[c['id']]['probabilities'][k] for c in cases],float) for k in FIELDS}
    for field,p in result.items():
        if p.shape!=(len(cases),len(LABELS[field])) or not np.isfinite(p).all() or (p<0).any() or (p>1).any() or not np.allclose(p.sum(1),1,atol=.001):
            raise ValueError('Malformed probability distribution')
    return result


def predicted(probs):return {k:np.asarray(LABELS[k])[np.argmax(p,axis=1)] for k,p in probs.items()}
def gold(cases):return {k:np.array([c['expected'][k] for c in cases]) for k in FIELDS}
def exact(probs,cases):
    pred=predicted(probs);truth=gold(cases)
    return np.all(np.stack([pred[k]==truth[k] for k in FIELDS]),axis=0)


def family_values(values,cases):
    names=sorted({c['family'] for c in cases})
    return np.array([np.mean([v for v,c in zip(values,cases) if c['family']==name]) for name in names])


def cluster_ci(values,cases,draws=10000):
    values=family_values(values,cases)
    if len(values)==0:raise ValueError('Cannot estimate an interval without families')
    rng=np.random.default_rng(SEED)
    sampled=values[rng.integers(0,len(values),size=(draws,len(values)))].mean(1)
    return {'estimate':float(values.mean()),'low':float(np.quantile(sampled,.025)),
            'high':float(np.quantile(sampled,.975)),'families':len(values)}


def paired_comparison(a,b,cases):
    differences=np.asarray(a,float)-np.asarray(b,float)
    out=cluster_ci(differences,cases)
    d=family_values(differences,cases)
    rng=np.random.default_rng(SEED)
    perm=(rng.choice([-1,1],size=(20000,len(d)))*d).mean(1)
    out['sign_flip_p']=(1+int((np.abs(perm)>=abs(d.mean())-1e-12).sum()))/20001
    return out


def calibration(probs,cases):
    truth=gold(cases);out={}
    for k,raw in probs.items():
        p=normalized(raw); y=np.array([LABELS[k].index(v) for v in truth[k]])
        target=np.eye(p.shape[1])[y];confidence=p.max(1);correct=p.argmax(1)==y
        bins=[];ece=0
        for i in range(10):
            mask=(confidence>=i/10)&((confidence<(i+1)/10) if i<9 else (confidence<=1))
            n=int(mask.sum())
            observed=float(correct[mask].mean()) if n else None
            average=float(confidence[mask].mean()) if n else None
            if n:ece+=n/len(p)*abs(observed-average)
            bins.append({'bin':[i/10,(i+1)/10],'n':n,'accuracy':observed,'mean_probability':average})
        out[k]={'brier':float(np.mean(np.sum((p-target)**2,axis=1))),
                'nll':float(-np.log(p[np.arange(len(p)),y]).mean()),'ece_10_equal_width':float(ece),
                'bins':bins}
    return out


def route_mask(probs,threshold):
    if threshold is None:return np.zeros(len(next(iter(probs.values()))),dtype=bool)
    pred=predicted(probs)
    eligible=(pred['owner']!='unknown')&(pred['impact']!='unknown')&(pred['evidence']=='sufficient')
    return eligible & (np.min(np.stack([p.max(1) for p in probs.values()]),axis=0)>=threshold)


def select_threshold(probs,cases):
    correct=exact(probs,cases)
    candidates=[]
    for step in range(101):
        threshold=step/100;mask=route_mask(probs,threshold)
        count=int(mask.sum()); families=len({c['family'] for c,m in zip(cases,mask) if m})
        if count>=20 and families>=5 and float((~correct[mask]).mean())<=.05:
            candidates.append((count,threshold,float((~correct[mask]).mean()),families))
    if not candidates:return {'threshold':None,'reason':'no development threshold met prespecified constraints'}
    count,threshold,error,nfam=max(candidates)
    return {'threshold':threshold,'development_routes':count,'development_families':nfam,'development_error':error}


def routing_metrics(probs,cases,threshold):
    mask=route_mask(probs,threshold); correct=exact(probs,cases)
    count=int(mask.sum()); errors=int((mask&~correct).sum())
    names=sorted({c['family'] for c in cases})
    routed=np.array([sum(m for c,m in zip(cases,mask) if c['family']==f) for f in names])
    wrong=np.array([sum(m and not ok for c,m,ok in zip(cases,mask,correct) if c['family']==f) for f in names])
    rng=np.random.default_rng(SEED);idx=rng.integers(0,len(names),(10000,len(names)))
    denom=routed[idx].sum(1);numer=wrong[idx].sum(1)
    nonempty=denom>0
    rates=numer[nonempty]/denom[nonempty]
    interval=None if len(rates)==0 else [float(np.quantile(rates,.025)),float(np.quantile(rates,.975))]
    return {'threshold':threshold,'routes':count,'errors':errors,'families_routed':int((routed>0).sum()),
            'coverage':float(mask.mean()),'coverage_ci':cluster_ci(mask,cases),
            'error_rate':errors/count if count else None,'error_rate_cluster_ci':interval,
            'nonempty_bootstrap_fraction':float(nonempty.mean()),
            'interval_note':'A zero-error bootstrap interval is not a certified upper risk bound.'}


def metrics(probs,cases,threshold=None):
    truth=gold(cases);pred=predicted(probs);correct=exact(probs,cases)
    report={'exact':cluster_ci(correct,cases),'fields':{},'conditions':{},'calibration':calibration(probs,cases),
            'routing':routing_metrics(probs,cases,threshold)}
    for k in FIELDS:
        report['fields'][k]={'accuracy':float(np.mean(pred[k]==truth[k])),
                            'macro_f1':float(f1_score(truth[k],pred[k],labels=LABELS[k],average='macro',zero_division=0)),
                            'labels':LABELS[k],'confusion':confusion_matrix(truth[k],pred[k],labels=LABELS[k]).tolist()}
    for variant in sorted({c['variant'] for c in cases}):
        mask=np.array([c['variant']==variant for c in cases])
        report['conditions'][variant]={'n':int(mask.sum()),'exact_accuracy':float(correct[mask].mean())}
    critical=truth['impact']=='critical'
    report['critical_recall']={'n':int(critical.sum()),'recall':float(np.mean(pred['impact'][critical]=='critical')) if critical.any() else None}
    clean={c['family']:i for i,c in enumerate(cases) if c['variant']=='clean'}
    report['paired_transforms']={}
    for variant in ['paraphrase','distractor','injection']:
        indexes=[i for i,c in enumerate(cases) if c['variant']==variant]
        if not indexes:continue
        bases=[clean[cases[i]['family']] for i in indexes]
        eligible=[(a,b) for a,b in zip(bases,indexes) if correct[a]]
        deltas=np.array([float(correct[b])-float(correct[a]) for a,b in zip(bases,indexes)])
        report['paired_transforms'][variant]={'accuracy_delta':cluster_ci(deltas,[cases[i] for i in indexes]),
            'clean_correct_families':len(eligible),'clean_correct_to_wrong':sum(not correct[b] for a,b in eligible),
            'conditional_failure_rate':sum(not correct[b] for a,b in eligible)/len(eligible) if eligible else None,
            'label_change_rate':float(np.mean([any(pred[k][a]!=pred[k][b] for k in FIELDS) for a,b in zip(bases,indexes)]))}
    return report
