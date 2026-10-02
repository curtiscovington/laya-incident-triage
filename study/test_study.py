import copy
import json
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import LABELS,FIELDS,read,cluster_ci,paired_comparison,rescale,predicted,select_threshold,metrics,probabilities,route_mask
from run import audit


def example(n=24):
    cases=[]
    for i in range(n):
        cases.append({'id':f'{i}','family':f'f{i//2}','variant':'clean' if i%2==0 else 'paraphrase',
                      'expected':{'owner':'database','impact':'degraded','evidence':'sufficient'}})
    probs={}
    for k in FIELDS:
        p=np.full((n,len(LABELS[k])),.02/(len(LABELS[k])-1))
        p[:,LABELS[k].index(cases[0]['expected'][k])]=.98
        probs[k]=p
    return cases,probs


class StudyTests(unittest.TestCase):
    def test_splits_and_invariants(self):
        result=audit();self.assertEqual(result['families'],72);self.assertEqual(result['cases'],576)
        self.assertEqual([len(read(s)) for s in ['train','dev','test']],[192,96,288])

    def test_repeated_rows_do_not_increase_independent_units(self):
        cases,_=example(12);values=[0,0,1,1,0,0,1,1,1,1,0,0]
        first=cluster_ci(values,cases)
        second=cluster_ci([v for v in values for _ in range(9)],[c for c in cases for _ in range(9)])
        self.assertEqual(first,second)
        self.assertEqual(first['families'],6)

    def test_identical_models_have_zero_gap_and_p_one(self):
        cases,_=example();a=np.arange(24)%2
        result=paired_comparison(a,a,cases)
        self.assertEqual(result['estimate'],0);self.assertEqual(result['low'],0);self.assertEqual(result['sign_flip_p'],1)

    def test_temperature_preserves_every_label(self):
        _,p=example()
        p['owner'][3]=[.3,.4,.2,.1]
        scaled=rescale(p,{k:2.7 for k in FIELDS})
        for k in FIELDS:
            np.testing.assert_array_equal(predicted(p)[k],predicted(scaled)[k])
            np.testing.assert_allclose(scaled[k].sum(1),1)

    def test_development_policy_can_disable(self):
        cases,p=example(16)
        self.assertIsNone(select_threshold(p,cases)['threshold'])
        self.assertFalse(route_mask(p,None).any())

    def test_policy_uses_all_three_labels_and_minimum_support(self):
        cases,p=example(24)
        self.assertIsNotNone(select_threshold(p,cases)['threshold'])
        wrong=copy.deepcopy(cases)
        for c in wrong:c['expected']['impact']='critical'
        self.assertIsNone(select_threshold(p,wrong)['threshold'])
        single=copy.deepcopy(cases)
        for c in single:c['family']='one'
        self.assertIsNone(select_threshold(p,single)['threshold'])

    def test_review_conditions_override_confidence(self):
        _,p=example()
        p['evidence'][:]=[0,1,0]
        self.assertFalse(route_mask(p,0).any())

    def test_predictions_require_exact_id_coverage(self):
        cases,p=example()
        records=[{'id':c['id'],'probabilities':{k:p[k][i].tolist() for k in FIELDS}} for i,c in enumerate(cases)]
        probabilities(records,cases)
        with self.assertRaises(ValueError):probabilities(records[:-1],cases)
        with self.assertRaises(ValueError):probabilities(records+[records[0]],cases)
        records[0]['probabilities']['owner'][0]=float('nan')
        with self.assertRaises(ValueError):probabilities(records,cases)

    def test_no_routes_yields_null_risk(self):
        cases,p=example();result=metrics(p,cases,None)
        self.assertEqual(result['routing']['routes'],0)
        self.assertIsNone(result['routing']['error_rate'])
        self.assertIsNone(result['routing']['error_rate_cluster_ci'])
        self.assertEqual(result['exact']['estimate'],1)

if __name__=='__main__':unittest.main()
