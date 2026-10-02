"""Independent report/count/provenance checks; run after analysis, no inference."""
import csv
from pathlib import Path
import numpy as np
from common import ROOT,read,rows,load,sha,LABELS,FIELDS,probabilities,predicted,rescale
from run import verify
from make_dataset import make_cases


def main():
    verify()
    generated=make_cases()
    for split in ['train','dev','test']:
        assert read(split)==[c for c in generated if c['split']==split], 'Generator no longer reproduces data'
    data=read('test');predictions=rows(ROOT/'runs/laya-test.jsonl')
    assert len(predictions)==len(data)==288
    selection=load(ROOT/'runs/selection.json');meta=load(ROOT/'runs/laya-test-metadata.json')
    assert selection['created_utc']<meta['started_utc'], 'Selection was not frozen before test'
    assert meta['selection_sha256']==sha(ROOT/'runs/selection.json')
    summary=load(ROOT/'artifacts/metrics.json')
    assert summary['test_predictions_sha256']==sha(ROOT/'runs/laya-test.jsonl')
    assert summary['test_families']==36
    p=probabilities(predictions,data);labels=predicted(p)
    matches=[all(labels[k][i]==c['expected'][k] for k in FIELDS) for i,c in enumerate(data)]
    assert np.isclose(sum(matches)/288,summary['systems']['laya_raw']['exact']['estimate'])
    calibrated=predicted(rescale(p,selection['temperatures']))
    assert all(np.array_equal(labels[k],calibrated[k]) for k in FIELDS)
    for name,metrics in summary['systems'].items():
        assert metrics['exact']['families']==36
        for k in FIELDS:
            matrix=np.array(metrics['fields'][k]['confusion'])
            assert int(matrix.sum())==288
            expected_counts=[sum(c['expected'][k]==label for c in data) for label in LABELS[k]]
            np.testing.assert_array_equal(matrix.sum(axis=1),expected_counts)
        policy=metrics['routing']
        assert 0<=policy['errors']<=policy['routes']<=288
        if policy['routes']==0:assert policy['error_rate'] is None
    with (ROOT/'artifacts/case-results.csv').open() as f:assert len(list(csv.DictReader(f)))==288*5
    with (ROOT/'artifacts/blind-review.csv').open() as f:
        review=list(csv.DictReader(f));assert len(review)==288
        assert all(not r[k] for r in review for k in ['reviewer_owner','reviewer_impact','reviewer_evidence'])
    for figure in ['accuracy','conditions','reliability','risk-coverage']:
        for ext in ['png','svg']:assert (ROOT/'artifacts'/f'{figure}.{ext}').stat().st_size>1000
    print('Verified: frozen provenance, exact regeneration, 288 complete test predictions, 36 families, ranking invariance, report counts, 8 figures, and pending blinded review.')

if __name__=='__main__':main()
