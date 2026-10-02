import copy
import json
import unittest
from unittest.mock import patch
import triage


def response(owner='database', impact='degraded', evidence='sufficient', probability=.97):
    choices = dict(owner=owner, impact=impact, evidence=evidence)
    return {'model': 'fixture-only', 'answers': {k: {
        'type': 'choice', 'choice': choices[k], 'confidence': .9,
        'probabilities': {v: probability if v == choices[k] else (1-probability)/(len(opts)-1) for v in opts}
    } for k, opts in triage.CRITERIA.items()}}


class TriageTests(unittest.TestCase):
    def test_labels_and_metadata_cannot_leak(self):
        case = {'id': 'secret', 'category': 'secret', 'expected': 'SECRET_GOLD', 'incident': 'Observed fault'}
        body = triage.payload(case)
        self.assertNotIn('SECRET_GOLD', json.dumps(body))
        self.assertEqual(set(body['state']), {'runbook', 'incident'})

    def test_valid_distribution_can_route(self):
        answers = triage.validate(response())
        self.assertEqual(triage.recommendation(answers, .9)['action'], 'route')

    def test_missing_conflicting_and_unknown_always_review(self):
        for kwargs in [{'evidence':'missing'}, {'evidence':'conflicting'}, {'owner':'unknown'}, {'impact':'unknown'}]:
            with self.subTest(kwargs=kwargs):
                self.assertEqual(triage.recommendation(triage.validate(response(**kwargs)), .9)['action'], 'human_review')

    def test_probability_not_confidence_controls_threshold(self):
        r = response(probability=.7)
        for a in r['answers'].values():
            a['confidence'] = 1
        self.assertEqual(triage.recommendation(triage.validate(r), .9)['action'], 'human_review')

    def test_invalid_distributions_rejected(self):
        for value in [float('nan'), float('inf'), -.1, 1.1, '0.9', True]:
            r = response()
            r['answers']['owner']['probabilities']['database'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                triage.validate(r)
        r = response()
        r['answers']['owner']['probabilities']['network'] = .9
        with self.assertRaises(ValueError):
            triage.validate(r)

    def test_wrong_maximum_rejected(self):
        r = response()
        r['answers']['owner']['choice'] = 'network'
        with self.assertRaises(ValueError):
            triage.validate(r)

    def test_empty_routed_set_has_no_fake_zero_error_rate(self):
        r = response(evidence='missing')
        row = {'predicted': {k:a['choice'] for k,a in r['answers'].items()},
               'expected': {'owner':'database','impact':'degraded','evidence':'missing'},
               'response':r, 'recommendation':triage.recommendation(triage.validate(r), .9), 'latency_ms':1}
        summary = triage.summarize([row], 'laya')
        self.assertIsNone(summary['routing_error_rate'])
        self.assertEqual(summary['routing_coverage'], 0)

    def test_all_cases_have_valid_gold(self):
        cases = json.loads((triage.ROOT/'cases.json').read_text())
        self.assertEqual(len(cases), len({c['id'] for c in cases}))
        for case in cases:
            for name, criteria in triage.CRITERIA.items():
                self.assertIn(case['expected'][name], criteria)

if __name__ == '__main__':
    unittest.main()
