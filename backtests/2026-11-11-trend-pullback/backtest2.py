"""Same trend-pullback rules as backtest.py, with a fee model and a design/test split.
usage: backtest2.py <data_dir> <max_bars> <taker|maker> [split YYYY-MM-DD]"""
import json, os, sys, time, statistics as st, calendar
D, MAXBARS, FEES = sys.argv[1], int(sys.argv[2]), sys.argv[3]
SPLIT = calendar.timegm(time.strptime(sys.argv[4] if len(sys.argv)>4 else '2026-01-01','%Y-%m-%d'))*1000
SYMS=["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","ADAUSDT","LINKUSDT"]
RISK=0.01; TGT_R=2.0; LOOK=6; BUF=0.002
TAKER=0.0015  # 0.10% fee + 0.05% slippage, per side
MAKER=0.0004  # 0.04% limit-order fee, per side
def fee(why):
    if FEES=='taker': return 2*TAKER
    return MAKER + (MAKER if why=='target' else TAKER)
def ema(x,n):
    k=2/(n+1); out=[x[0]]
    for v in x[1:]: out.append(out[-1]+k*(v-out[-1]))
    return out
data={s:json.load(open(os.path.join(D,s+'.json'))) for s in SYMS}
E={s:(ema([r[4] for r in data[s]],20),ema([r[4] for r in data[s]],50)) for s in SYMS}
def trend(s,i):
    b=data[s]; e20,e50=E[s]
    if i<60: return 0
    if b[i][4]<e50[i] and e50[i]<e50[i-6]: return -1
    if b[i][4]>e50[i] and e50[i]>e50[i-6]: return 1
    return 0
bt_idx={r[0]:i for i,r in enumerate(data['BTCUSDT'])}
trades=[]
for s in SYMS:
    b=data[s]; e20,_=E[s]; i=60
    while i<len(b)-2:
        t=trend(s,i)
        if s!='BTCUSDT' and t:
            j=bt_idx.get(b[i][0]); t=t if (j is not None and trend('BTCUSDT',j)==t) else 0
        o,h,l,c=b[i][1:5]; sig=0
        if t==-1 and h>=e20[i] and c<e20[i] and c<o: sig=-1
        if t==1 and l<=e20[i] and c>e20[i] and c>o: sig=1
        if not sig: i+=1; continue
        entry=b[i+1][1]
        stop=(max(r[2] for r in b[i-LOOK+1:i+1])*(1+BUF)) if sig==-1 else (min(r[3] for r in b[i-LOOK+1:i+1])*(1-BUF))
        risk=abs(entry-stop)/entry
        if risk<0.005 or risk>0.08 or (stop-entry)*sig>=0: i+=1; continue
        tgt=entry+sig*TGT_R*abs(entry-stop); exit_px=None; k=i+1
        while k<len(b) and k<=i+MAXBARS:
            hk,lk=b[k][2],b[k][3]
            if (hk>=stop if sig==-1 else lk<=stop): exit_px,why=stop,'stop'; break
            if (lk<=tgt if sig==-1 else hk>=tgt): exit_px,why=tgt,'target'; break
            k+=1
        if exit_px is None:
            if k>=len(b): break
            k=min(k,i+MAXBARS); exit_px,why=b[k][4],'time'
        R=sig*(exit_px-entry)/abs(entry-stop) - fee(why)/risk
        trades.append(dict(sym=s[:-4],side='LONG' if sig==1 else 'SHORT',entry_t=b[i+1][0],exit_t=b[k][0],risk_pct=risk*100,why=why,R=R))
        i=k+1
def stats(tr):
    if not tr: return None
    R=[x['R'] for x in tr]; w=[r for r in R if r>0]; ls=[r for r in R if r<=0]
    eq=peak=1.0; mdd=0
    for x in sorted(tr,key=lambda x:x['exit_t']): eq*=1+RISK*x['R']; peak=max(peak,eq); mdd=max(mdd,1-eq/peak)
    mx=s_=0
    for r in R: s_=s_+1 if r<=0 else 0; mx=max(mx,s_)
    return dict(n=len(R),win=100*len(w)/len(R),exp=st.mean(R),pf=(sum(w)/abs(sum(ls))) if ls else 99,ret=(eq-1)*100,dd=mdd*100,streak=mx)
design=[x for x in trades if x['entry_t']<SPLIT]; test=[x for x in trades if x['entry_t']>=SPLIT]
out=dict(design=stats(design),test=stats(test),test_short=stats([x for x in test if x['side']=='SHORT']),test_long=stats([x for x in test if x['side']=='LONG']))
print(json.dumps(out))
