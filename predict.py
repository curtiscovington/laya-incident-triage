#!/usr/bin/env python3
"""Classify your own incident locally. No server, API, or credentials."""
import argparse
import json
from pathlib import Path
import sys
from triage import ROOT, local_engine, call_local, payload, validate, recommendation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--text', help='Incident observations')
    source.add_argument('--file', type=Path, help='UTF-8 incident file')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    parser.add_argument('--threshold', type=float, default=.9)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        parser.error('threshold must be in [0,1]')
    text = args.text if args.text is not None else args.file.read_text() if args.file else sys.stdin.read()
    if not text.strip():
        parser.error('supply --text, --file, or pipe incident text on stdin')
    engine = local_engine(ROOT/'models/laya', args.device)
    response, elapsed, _ = call_local(engine, payload({'incident': text}))
    answers = validate(response)
    print(json.dumps({'model':response['model'], 'latency_ms':elapsed,
                      'recommendation':recommendation(answers, args.threshold),
                      'answers':answers}, indent=2))

if __name__ == '__main__':
    main()
