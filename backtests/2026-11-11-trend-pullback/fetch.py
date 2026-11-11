import json, time, urllib.request, sys, os
OUT=sys.argv[1]; SYMS=["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","BNBUSDT","DOGEUSDT","ADAUSDT","LINKUSDT"]
def get(sym,end=None):
    u=f"https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval=4h&limit=1000"+(f"&endTime={end}" if end else "")
    return json.load(urllib.request.urlopen(u,timeout=30))
for s in SYMS:
    rows=[]; end=None
    for _ in range(5):  # 5 x 1000 bars ~ 2.3 years
        k=get(s,end)
        if not k: break
        rows=k+rows; end=k[0][0]-1; time.sleep(.3)
    seen=set(); bars=[]
    for r in rows:
        if r[0] in seen: continue
        seen.add(r[0]); bars.append([r[0],float(r[1]),float(r[2]),float(r[3]),float(r[4])])
    bars.sort(); bars=bars[:-1]  # drop the still-open candle
    json.dump(bars,open(os.path.join(OUT,s+".json"),"w"))
    print(s,len(bars),time.strftime('%Y-%m-%d',time.gmtime(bars[0][0]/1000)),'->',time.strftime('%Y-%m-%d %H:%M',time.gmtime(bars[-1][0]/1000)))
