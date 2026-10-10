"""Export presentation charts from measured valid cohorts only."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

def plot(source,output):
    data=json.loads(Path(source).read_text());rows=data['runs']
    seeds=sorted({r['seed'] for r in rows if r.get('run_id')})
    policies=['fixed','actuated','pressure'];colours=['#566675','#be9140','#087e8b']
    fig,axes=plt.subplots(1,3,figsize=(15,5),layout='constrained')
    for ax,key,title in zip(axes,['journey_s','mean_waiting_s','co2_kg'],['Mean journey including entry delay (s)','Mean stopped waiting (s)','SUMO-modelled CO2 (kg)']):
        x=np.arange(len(seeds))
        for i,(policy,colour) in enumerate(zip(policies,colours)):
            values=[]
            for seed in seeds:
                matches=[r for r in rows if r['seed']==seed and r['policy']==policy and r.get('valid')]
                values.append(matches[-1].get(key,float('nan')) if matches else float('nan'))
            bars=ax.bar(x+(i-1)*.24,values,.22,label=policy,color=colour)
            ax.bar_label(bars,fmt='%.1f',fontsize=8,padding=3)
        ax.set_xticks(x,[f'Seed {s}\n'+str(next((r.get('demand_per_hour') for r in rows if r['seed']==s),''))+' veh/h' for s in seeds]);ax.set_title(title,fontsize=11);ax.set_ylim(bottom=0);ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    axes[0].legend(frameon=False,fontsize=9)
    fig.suptitle('Traffix · matched synthetic SUMO experiments',fontsize=16,fontweight='bold')
    fig.supxlabel('Valid complete cohorts only · assumed demand and fleet · CO2 mapping unreviewed',fontsize=10)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(output.with_suffix('.png'),dpi=180);fig.savefig(output.with_suffix('.svg'));plt.close(fig)
    for seed in seeds:
        fig,ax=plt.subplots(figsize=(10,4),layout='constrained')
        for policy,colour in zip(policies,colours):
            matching=[r for r in rows if r['seed']==seed and r['policy']==policy and r.get('valid')]
            if not matching:continue
            recording=Path('runs')/matching[-1]['run_id']/'recording.json'
            if not recording.exists():continue
            frames=json.loads(recording.read_text()).get('frames',[])
            ax.plot([f['sim_time_s'] for f in frames],[f.get('metrics',{}).get('queued',0) for f in frames],label=policy,color=colour,linewidth=1.7)
        ax.set_title(f'Seed {seed}: measured network queue over the whole run')
        ax.set_xlabel('Simulated time (s)');ax.set_ylabel('Stopped vehicles (<0.1 m/s)');ax.set_ylim(bottom=0)
        ax.legend(frameon=False);ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.15)
        fig.savefig(output.parent/f'queue-timeline-seed-{seed}.png',dpi=180)
        fig.savefig(output.parent/f'queue-timeline-seed-{seed}.svg');plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--output',required=True);a=p.parse_args();plot(a.source,a.output)
