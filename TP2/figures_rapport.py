#!/usr/bin/env python3
"""Figures du rapport, depuis les mesures de trajectoire_2.csv.

Frontieres: premiere ligne de chaque nouvelle valeur de lap.
Ce sont les detections du programme (cap commande + distance), pas des balises.
Recalage: interpolation affine de la derive ENTRE ces frontieres, hors ligne.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from plot_trajectoire import read_log, column, correct_odometry
OUT=ROOT/'TP2'/'plots'
DATA=ROOT/'TP2'/'analyse'
COLORS=['#7254a3','#007f8b','#cd6a17']
plt.rcParams.update({'font.family':'serif','font.serif':['Palatino','DejaVu Serif'],
                     'font.size':12,'axes.spines.top':False,'axes.spines.right':False,
                     'axes.grid':True,'grid.alpha':.2,'savefig.dpi':180})


def points(rows,name):
    return np.c_[column(rows,'x_'+name+'_mm'),column(rows,'y_'+name+'_mm')]


def affine_between_starts(xy,distance,boundaries):
    """Soustrait le segment joignant les positions estimees des deux retours.

    Aucun fit global ni transformation spatiale Ap+b. La derive soustraite est
    affine en distance dans chaque intervalle. La fermeture n'est pas une validation.
    """
    if len(boundaries)<2 or np.any(np.diff(distance)<0) or np.any(np.diff(distance[boundaries])<=0):
        raise ValueError('Au moins deux frontieres et distance non decroissante et intervalles non nuls requis')
    correction=np.full_like(xy,np.nan,dtype=float)
    for a,b in zip(boundaries[:-1],boundaries[1:]):
        fraction=(distance[a:b+1]-distance[a])/(distance[b]-distance[a])
        correction[a:b+1]=(1-fraction[:,None])*xy[a]+fraction[:,None]*xy[b]
    return xy-correction,correction


def replay_filter(rows,heading_scale=1.,distance_scale=1.,q=25.,r=4.):
    angle=0.;variance=1.;pose=np.zeros(2);previous_distance=0.
    xy=[];angles=[];gains=[]
    for row in rows:
        dt=float(row['dt_s']);rate=float(row['turn_rate_deg_s'])*heading_scale
        gyro=float(row['gyro_heading_deg']);distance=float(row['distance_mm'])
        angle+=rate*dt;variance+=q*dt
        gain=variance/(variance+r);angle+=gain*(gyro-angle);variance*=(1-gain)
        ds=(distance-previous_distance)*distance_scale
        pose=pose+ds*np.array([np.cos(np.deg2rad(angle)),np.sin(np.deg2rad(angle))])
        previous_distance=distance;xy.append(pose.copy());angles.append(angle);gains.append(gain)
    return np.array(xy),np.array(angles),np.array(gains)


def save(fig,name):
    fig.savefig(OUT/(name+'.png'),bbox_inches='tight',facecolor='white')
    fig.savefig(OUT/(name+'.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig)


def limits(*paths):
    xy=np.vstack(paths);lo=np.nanmin(xy,axis=0)-90;hi=np.nanmax(xy,axis=0)+90
    return lo,hi


def tracks(ax,xy,boundaries,title,extent,legend=True):
    for n,(a,b) in enumerate(zip(boundaries[:-1],boundaries[1:])):
        ax.plot(xy[a:b+1,0],xy[a:b+1,1],c=COLORS[n%len(COLORS)],lw=1.45,label='Tour '+str(n+1))
        ax.scatter(*xy[a],c=COLORS[n%len(COLORS)],s=22,zorder=3)
        ax.scatter(*xy[b],c=COLORS[n%len(COLORS)],marker='x',s=32,zorder=3)
    ax.set(xlim=(extent[0][0],extent[1][0]),ylim=(extent[0][1],extent[1][1]),
           aspect='equal',xlabel='x (mm)',ylabel='y (mm)',title=title)
    ax.scatter(0,0,c='black',s=22,zorder=4,label='Départ initial')
    if legend:ax.legend(loc='lower left',fontsize=9,framealpha=.95)


def export(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    OUT.mkdir(exist_ok=True);DATA.mkdir(exist_ok=True)
    meta,rows=read_log(str(ROOT/'trajectoire_2.csv'))
    t=np.array(column(rows,'time_s'));distance=np.array(column(rows,'distance_mm'))
    lap=np.array(column(rows,'lap'));boundaries=np.r_[0,np.flatnonzero(np.diff(lap)!=0)+1]
    if len(boundaries)!=4:raise ValueError('Le rapport attend trois intervalles complets et un quatrieme incomplet')
    end=boundaries[-1]
    odom=points(rows,'odometry');gyro=points(rows,'gyro');command=points(rows,'command')
    kalman=points(rows,'kalman')
    # Le rejeu doit retrouver exactement le code utilise pour cette acquisition.
    k0,h0,g0=replay_filter(rows,q=meta['q_deg2_s'],r=meta['r_deg2'])
    np.testing.assert_allclose(k0,kalman,atol=1e-8)
    np.testing.assert_allclose(h0,column(rows,'kalman_heading_deg'),atol=1e-8)
    initial=np.c_[*correct_odometry(rows,1.,1.)]
    np.testing.assert_allclose(initial,odom,atol=1e-8)
    recal,drift=affine_between_starts(odom[:end+1],distance[:end+1],boundaries)
    np.testing.assert_allclose(recal[boundaries],0,atol=1e-9)
    trials=[(1.,1.,'Initial : distance et cap inchangés'),(.95,1.,'Distance ×0,95 ; cap inchangé'),
            (1.,1.05,'Distance inchangée ; cap ×1,05'),(1.,1.03,'Distance inchangée ; cap ×1,03')]
    replay=[np.c_[*correct_odometry(rows,a,b)] for a,b,_ in trials]
    calibrated=replay[-1]
    k_cal,h_cal,g_cal=replay_filter(rows,heading_scale=1.03,q=meta['q_deg2_s'],r=meta['r_deg2'])
    summary={'source':'trajectoire_2.csv','samples':len(rows),'duration_s':float(t[-1]-t[0]),
             'boundary_rule':'premiere ligne du nouveau lap; detection par cap commande et distance, sans balise independante',
             'boundaries':boundaries.tolist(),'boundary_times_s':t[boundaries].tolist(),
             'boundary_distances_mm':distance[boundaries].tolist(),
             'dt_median_s':float(np.median(np.diff(t))),'trials':[],
             'q_deg2_s':meta['q_deg2_s'],'r_deg2':meta['r_deg2'],
             'gain_median':float(np.median(g_cal)),
             'recalage':'derive affine par intervalle de distance; fermeture imposee; tour 4 exclu'}
    metrics=[]
    for name,xy in [('Commande',command),('Odométrie',odom),('Gyro + commande',gyro),
                    ('Kalman nominal',kalman),('Cap ×1,03',calibrated),('Kalman cap ×1,03',k_cal),
                    ('Recalage affine',recal)]:
        for n,(a,b) in enumerate(zip(boundaries[:-1],boundaries[1:]),1):
            metrics.append({'methode':name,'tour_estime':n,'debut_s':float(t[a]),'fin_s':float(t[b]),
                            'ecart_a_origine_mm':float(np.linalg.norm(xy[b])),
                            'ecart_fin_moins_debut_mm':float(np.linalg.norm(xy[b]-xy[a])),
                            'fermeture_imposee':name=='Recalage affine'})
    export(DATA/'indicateurs.csv',metrics)
    for (a,b,label),xy in zip(trials,replay):
        summary['trials'].append({'distance_scale':a,'heading_scale':b,'D_equivalent_mm':a*meta['D_mm'],
                                 'V_equivalent_mm':a/b*meta['V_mm'],
                                 'ecart_origine_fin3_mm':float(np.linalg.norm(xy[end])),
                                 'ecart_fin_moins_debut_par_tour_mm':np.linalg.norm(np.diff(xy[boundaries],axis=0),axis=1).tolist()})
    export(DATA/'recalage_affine.csv',[{'time_s':float(t[i]),'distance_mm':float(distance[i]),
           'x_brut_mm':float(odom[i,0]),'y_brut_mm':float(odom[i,1]),
           'derive_x_mm':float(drift[i,0]),'derive_y_mm':float(drift[i,1]),
           'x_recale_mm':float(recal[i,0]),'y_recale_mm':float(recal[i,1])} for i in range(end+1)])
    export(DATA/'comparaison.csv',[{'time_s':float(t[i]),'lap':int(lap[i]),
           'x_odometrie_mm':float(odom[i,0]),'y_odometrie_mm':float(odom[i,1]),
           'x_cap_corrige_mm':float(calibrated[i,0]),'y_cap_corrige_mm':float(calibrated[i,1]),
           'x_kalman_corrige_mm':float(k_cal[i,0]),'y_kalman_corrige_mm':float(k_cal[i,1]),
           'x_gyro_commande_mm':float(gyro[i,0]),'y_gyro_commande_mm':float(gyro[i,1]),
           'cap_odometrie_deg':float(rows[i]['odometry_heading_deg']),
           'cap_gyro_deg':float(rows[i]['gyro_heading_deg']),'cap_kalman_corrige_deg':float(h_cal[i])}
           for i in range(end+1)])
    (DATA/'bilan.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')

    fig,axs=plt.subplots(1,3,figsize=(10,7.7),layout='constrained')
    extent=limits(command,odom,gyro)
    for ax,xy,title in zip(axs,[command,odom,gyro],['Consignes de vitesse\net de rotation','Mesures des roues\n(distance et angle)','Angle du gyro\n+ distance commandée']):
        tracks(ax,xy,boundaries,title,extent,legend=False)
        ax.plot(xy[end:,0],xy[end:,1],c='#888888',ls='--',lw=1.2,label='Tour 4 interrompu')
    axs[1].legend(loc='lower left',fontsize=8)
    save(fig,'rapport_methodes_revu')

    fig,axs=plt.subplots(2,2,figsize=(9,9.5),layout='constrained')
    extent=limits(*[x[:end+1] for x in replay])
    for ax,xy,(a,b,label) in zip(axs.flat,replay,trials):
        tracks(ax,xy,boundaries,label+'\nÉcart au départ après 3 tours : '+str(round(np.linalg.norm(xy[end])))+' mm',extent,False)
    axs[0,0].legend(loc='lower left',fontsize=9)
    save(fig,'rapport_calibration_revu')

    fig=plt.figure(figsize=(9,9.3),layout='constrained')
    gs=fig.add_gridspec(2,2,height_ratios=[2.9,1])
    extent=limits(odom[:end+1],recal)
    tracks(fig.add_subplot(gs[0,0]),odom,boundaries,'Avant recalage',extent)
    tracks(fig.add_subplot(gs[0,1]),recal,boundaries,'Après recalage affine par intervalle',extent,False)
    ax=fig.add_subplot(gs[1,:])
    for j,label,c in [(0,'Dérive x soustraite','#444444'),(1,'Dérive y soustraite','#007f8b')]:
        ax.plot(distance[:end+1]/1000,drift[:,j],c=c,label=label,lw=1.5)
        ax.scatter(distance[boundaries]/1000,odom[boundaries,j],c=c,s=25,zorder=3)
    ax.set(xlabel='Distance odométrique cumulée (m)',ylabel='Correction (mm)')
    ax.legend(loc='upper left',fontsize=9,ncol=2)
    save(fig,'rapport_affine_revu')

    fig,axs=plt.subplots(1,3,figsize=(10,7.7),layout='constrained')
    extent=limits(calibrated[:end+1],gyro[:end+1],k_cal[:end+1])
    for ax,xy,title in zip(axs,[calibrated,gyro,k_cal],['Mesures des roues\navec cap ×1,03','Angle du gyro\n+ distance commandée','Kalman\n+ distance des roues']):
        tracks(ax,xy,boundaries,title,extent,False)
    axs[0].legend(loc='lower left',fontsize=9)
    save(fig,'rapport_kalman_revu')
    print(json.dumps({'frontieres_s':summary['boundary_times_s'],'trials':summary['trials'],
                      'kalman_corrige':[x for x in metrics if x['methode']=='Kalman cap ×1,03']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
