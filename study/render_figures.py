"""Presentation-only layout pass added after analysis. Reads saved metrics; no inference or statistics."""
from pathlib import Path
import json
import hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np

OUT=Path(__file__).resolve().parent/'artifacts'
LABEL={'laya_raw':'Laya','laya_calibrated':'Laya + calibration','tfidf':'TF-IDF classifier','keyword':'Keyword rules','majority':'Training majority'}
COLOR={'laya_raw':'#d97706','laya_calibrated':'#a855f7','tfidf':'#2563eb','keyword':'#6b7280','majority':'#9ca3af'}


def finish(fig,name):
    fig.tight_layout()
    for suffix in ['png','svg']:fig.savefig(OUT/f'{name}.{suffix}',bbox_inches='tight')
    plt.close(fig)


def main():
    before=hashlib.sha256((OUT/'metrics.json').read_bytes()).hexdigest()
    data=json.loads((OUT/'metrics.json').read_text());models=data['systems']
    plt.rcParams.update({'font.size':10,'figure.dpi':150,'axes.spines.top':False,'axes.spines.right':False})
    names=['majority','keyword','tfidf','laya_raw'];v=[models[n]['exact'] for n in names]
    fig,ax=plt.subplots(figsize=(8,4));x=np.arange(len(names));y=np.array([r['estimate'] for r in v])
    err=np.array([[r['estimate']-r['low'] for r in v],[r['high']-r['estimate'] for r in v]])
    ax.bar(x,y,color=[COLOR[n] for n in names]);ax.errorbar(x,y,yerr=err,fmt='none',capsize=4,color='black')
    ax.set_xticks(x,[LABEL[n] for n in names]);ax.set_ylim(0,1);ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set_ylabel('All-three exact accuracy');ax.set_title('Held-out synthetic mechanisms\n95% family-bootstrap intervals')
    finish(fig,'accuracy')
    conditions=list(models['laya_raw']['conditions']);x=np.arange(len(conditions));width=.25
    fig,ax=plt.subplots(figsize=(10,4.8))
    for i,n in enumerate(['keyword','tfidf','laya_raw']):
        ax.bar(x+(i-1)*width,[models[n]['conditions'][c]['exact_accuracy'] for c in conditions],width,label=LABEL[n],color=COLOR[n])
    ax.set_xticks(x,[c.replace('_','\n') for c in conditions]);ax.set_ylim(0,1.04)
    ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set_ylabel('All-three exact accuracy')
    ax.set_title('Condition breakdown · 36 mechanisms per condition')
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.19),ncol=3,frameon=False)
    finish(fig,'conditions')
    fig,ax=plt.subplots(figsize=(7,4.8));ax.plot([0,1],[0,1],'--',color='#9ca3af')
    for n in ['laya_raw','laya_calibrated','tfidf']:
        bins=[b for b in models[n]['calibration']['impact']['bins'] if b['n']]
        ax.plot([b['mean_probability'] for b in bins],[b['accuracy'] for b in bins],'o-',label=LABEL[n],color=COLOR[n])
    ax.set(xlim=(-.02,1.02),ylim=(-.02,1.02),xlabel='Mean selected probability',ylabel='Observed accuracy',title='Impact reliability · descriptive bins')
    ax.xaxis.set_major_formatter(PercentFormatter(1));ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.18),ncol=3,frameon=False);finish(fig,'reliability')
    curves=json.loads((OUT/'risk-coverage.json').read_text());fig,ax=plt.subplots(figsize=(7,4.8))
    for n,points in curves.items():
        ax.plot([p['coverage'] for p in points],[p['error'] for p in points],label=LABEL[n],color=COLOR[n])
    ax.set(xlim=(-.02,1.02),ylim=(-.02,1.02),xlabel='Fraction of test cases routed',ylabel='Error among routed cases',title='Risk / coverage\nDescriptive curves; test thresholds were not selected here')
    ax.xaxis.set_major_formatter(PercentFormatter(1));ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.18),ncol=3,frameon=False);finish(fig,'risk-coverage')
    assert before==hashlib.sha256((OUT/'metrics.json').read_bytes()).hexdigest()
    print('Rendered saved measurements with clearer labels and legends; metrics unchanged.')

if __name__=='__main__':main()
