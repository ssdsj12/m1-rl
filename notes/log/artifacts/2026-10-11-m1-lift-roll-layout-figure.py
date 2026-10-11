"""Render the exact20cm candidate manifest, not a hand-drawn obstacle sketch."""
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
from ame_baseline.m1_lift_roll_layout import candidate_blocks

fig,axes=plt.subplots(3,1,figsize=(14,8),sharex=True)
fig.patch.set_facecolor('#f4f6f8')
for row,ax in enumerate(axes,1):
    ax.set_facecolor('#edf6f1')
    for block in candidate_blocks(row,fill_gap=.20):
        ax.add_patch(Rectangle((block.x-block.length/2,block.y-block.width/2),block.length,block.width,
                     facecolor='#e97524' if block.required_crossing else '#8b99ab',
                     edgecolor='#a64206' if block.required_crossing else '#6b7b90',linewidth=.5))
    for y in (-.215,.215):
        ax.axhline(y,color='#398261',ls='--',lw=.8,zorder=0)
        for dx in (-.3295,.3295):
            ax.add_patch(Circle((-2+dx,y),.119208,fill=False,edgecolor='#245bc1',lw=1.2))
    ax.add_patch(Rectangle((-2.55,-.8),1.1,1.6,fill=False,edgecolor='#245bc1',ls=':',lw=1))
    for i,b in enumerate(b for b in candidate_blocks(row,fill_gap=.20) if b.required_crossing):
        ax.text(b.x,.60 if b.y>0 else -.64,f'{i+1}: '+('L' if b.y>0 else 'R'),ha='center',fontsize=8,
                color='#202a36',bbox=dict(facecolor='white',edgecolor='none',alpha=.85,pad=1))
    ax.set(xlim=(-3,7.5),ylim=(-1,1),ylabel='Y (m)')
    ax.set_title(f'Stage {row}: height {dict(enumerate((3,6,10),1))[row]} cm | {len([b for b in candidate_blocks(row,fill_gap=.20) if b.required_crossing])} targets + 70 physical fills / tile',loc='left',fontsize=11)
    ax.grid(axis='x',alpha=.15);ax.set_aspect('equal',adjustable='box')
    ax.spines[['top','right']].set_visible(False)
axes[-1].set_xlabel('Forward +X (m), relative to tile center')
fig.suptitle('Candidate only - single-wheel lift + three-wheel roll; same-side front then rear',fontsize=15,y=.975)
fig.text(.07,.025,'Orange: required targets | Gray: collidable fill | Blue: spawn / nominal wheel envelopes\nCentral corridor zoom. Full tile16x16m; fill extends toY=+/-7.95m. Rolling strips Y=+/-0.215m, width0.26m. Fill gap0.20m. Not yet production-accepted.',fontsize=9)
fig.subplots_adjust(top=.91,bottom=.12,hspace=.52)
fig.savefig(sys.argv[1],dpi=160,facecolor=fig.get_facecolor())
