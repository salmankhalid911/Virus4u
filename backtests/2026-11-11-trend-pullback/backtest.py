import json, os, sys, time, statistics as st
D=sys.argv[1]; SYMS=["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","ADAUSDT","LINKUSDT"]
FEE_RT=0.003; RISK=0.01; TGT_R=2.0; MAXBARS=30; LOOK=6; BUF=0.002
def ema(x,n):
    k=2/(n+1); out=[x[0]]
    for v in x[1:]: out.append(out[-1]+k*(v-out[-1]))
    return out
data={s:json.load(open(os.path.join(D,s+'.json'))) for s in SYMS}
def ind(b):
    c=[r[4] for r in b]; return ema(c,20), ema(c,50)
I={s:ind(data[s]) for s in SYMS}
def trend(s,i):
    b=data[s]; e20,e50=I[s]
    if i<60: return 0
    if b[i][4]<e50[i] and e50[i]<e50[i-6]: return -1
    if b[i][4]>e50[i] and e50[i]>e50[i-6]: return 1
    return 0
btc_t={r[0]:i for i,r in enumerate(data['BTCUSDT'])}
trades=[]
for s in SYMS:
    b=data[s]; e20,e50=I[s]; i=60
    while i<len(b)-2:
        t=trend(s,i)
        if s!='BTCUSDT' and t!=0:
            j=btc_t.get(b[i][0]); t = t if (j is not None and trend('BTCUSDT',j)==t) else 0
        o,h,l,c=b[i][1:5]; sig=0
        if t==-1 and h>=e20[i] and c<e20[i] and c<o: sig=-1
        if t==1 and l<=e20[i] and c>e20[i] and c>o: sig=1
        if not sig: i+=1; continue
        entry=b[i+1][1]
        if sig==-1: stop=max(r[2] for r in b[i-LOOK+1:i+1])*(1+BUF)
        else: stop=min(r[3] for r in b[i-LOOK+1:i+1])*(1-BUF)
        risk=abs(entry-stop)/entry
        if risk<0.005 or risk>0.08 or (sig==-1 and stop<=entry) or (sig==1 and stop>=entry): i+=1; continue
        tgt=entry-sig*TGT_R*abs(entry-stop)*-1 if False else entry+sig*TGT_R*abs(entry-stop)
        exit_px=None; k=i+1
        while k<len(b) and k<=i+MAXBARS:
            hk,lk=b[k][2],b[k][3]
            hit_stop = (hk>=stop) if sig==-1 else (lk<=stop)
            hit_tgt = (lk<=tgt) if sig==-1 else (hk>=tgt)
            if hit_stop: exit_px=stop; why='stop'; break
            if hit_tgt: exit_px=tgt; why='target'; break
            k+=1
        if exit_px is None:
            k=min(k,len(b)-1)
            if k< i+MAXBARS and k==len(b)-1: break  # still open at end of data
            exit_px=b[k][4]; why='time'
        gross_R=sig*(exit_px-entry)/abs(entry-stop)
        cost_R=FEE_RT/risk
        trades.append(dict(sym=s[:-4],side='LONG' if sig==1 else 'SHORT',entry_t=b[i+1][0],exit_t=b[k][0],entry=entry,stop=stop,tgt=tgt,exit=exit_px,why=why,risk_pct=risk*100,R=gross_R-cost_R))
        i=k+1
trades.sort(key=lambda x:x['entry_t'])
def stats(tr,label):
    R=[x['R'] for x in tr]; w=[r for r in R if r>0]; ls=[r for r in R if r<=0]
    eq=1.0; peak=1.0; mdd=0; curve=[]
    for x in sorted(tr,key=lambda x:x['exit_t']):
        eq*=1+RISK*x['R']; peak=max(peak,eq); mdd=max(mdd,1-eq/peak); curve.append(eq)
    streak=mx=0
    for r in R:
        streak=streak+1 if r<=0 else 0; mx=max(mx,streak)
    pf=sum(w)/abs(sum(ls)) if ls else float('inf')
    d=lambda ms: time.strftime('%Y-%m-%d',time.gmtime(ms/1000))
    return dict(label=label,n=len(R),from_=d(tr[0]['entry_t']),to=d(tr[-1]['exit_t']),win_rate=100*len(w)/len(R),avg_win_R=st.mean(w) if w else 0,avg_loss_R=st.mean(ls) if ls else 0,
        expectancy_R=st.mean(R),total_R=sum(R),profit_factor=pf,return_pct=(eq-1)*100,max_dd_pct=mdd*100,max_losing_streak=mx,
        targets=sum(x['why']=='target' for x in tr),stops=sum(x['why']=='stop' for x in tr),timeouts=sum(x['why']=='time' for x in tr))
last100=trades[-100:]
out={'rules':dict(fee_round_trip=FEE_RT,risk_per_trade=RISK,target_R=TGT_R,max_bars=MAXBARS),'all':stats(trades,'all trades'),'last100':stats(last100,'last 100 trades'),
     'first100':stats(trades[:100],'first 100 trades')}
for side in ('LONG','SHORT'):
    t=[x for x in last100 if x['side']==side]
    if t: out['last100_'+side]=stats(t,side)
out['by_coin']={c:round(sum(x['R'] for x in last100 if x['sym']==c),2) for c in sorted({x['sym'] for x in last100})}
out['by_coin_n']={c:sum(1 for x in last100 if x['sym']==c) for c in out['by_coin']}
json.dump(dict(summary=out,trades=trades),open(os.path.join(D,'..','results.json'),'w'),indent=1)
for k in ('all','first100','last100','last100_LONG','last100_SHORT'):
    if k in out: s=out[k]; print(f"{s['label']:<16} n={s['n']:<4} {s['from_']}→{s['to']}  win={s['win_rate']:.1f}%  avgW={s['avg_win_R']:.2f}R avgL={s['avg_loss_R']:.2f}R  exp={s['expectancy_R']:+.3f}R  PF={s['profit_factor']:.2f}  ret={s['return_pct']:+.1f}%  maxDD={s['max_dd_pct']:.1f}%  streak={s['max_losing_streak']}  T/S/time={s['targets']}/{s['stops']}/{s['timeouts']}")
print('by coin (last100, R):',out['by_coin'],out['by_coin_n'])
