"""Builds an original score + sound design for one animatic from events_<page>.json.

Usage: python3 sound.py b   -> mix_b.wav
Music is synthesised (A minor, 75 BPM); SFX are synthesised plus licence-traceable
Mixkit files in sfx/ (Mixkit Sound Effects Free License).
"""
import json, sys, wave
import numpy as np

SR = 48000
page = sys.argv[1]
ev = json.load(open(f'events_{page}.json'))
DUR = ev['dur']; N = int(SR * DUR); MU = ev['music']
rng = np.random.default_rng(7)
ML = np.zeros(N); MR = np.zeros(N); L = np.zeros(N); R = np.zeros(N)

def tt(d): return np.arange(int(d * SR)) / SR
def S(*xs):
    n = max(len(x) for x in xs); o = np.zeros(n)
    for x in xs: o[:len(x)] += x
    return o
def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
NT = {'A1': 33, 'E2': 40, 'F2': 41, 'G2': 43, 'A2': 45, 'Bb2': 46, 'B2': 47, 'C3': 48, 'D3': 50, 'E3': 52, 'G#3': 56, 'A3': 57, 'B3': 59,
      'C#4': 61, 'E4': 64, 'A4': 69, 'C5': 72, 'E5': 76, 'A5': 81, 'F3': 53, 'G3': 55}
def f(n): return midi(NT[n])
def expdec(d, k): return np.exp(-tt(d) * k)
def sine(fr, d): return np.sin(2 * np.pi * fr * tt(d))
def glide(f0, f1, d):
    t = tt(d); fr = f0 * (f1 / f0) ** (t / d); return np.sin(2 * np.pi * np.cumsum(fr) / SR)
def saw(fr, d, harm=24, bright=None):
    t = tt(d); out = np.zeros_like(t); nh = int(min(harm, (SR / 2 - 200) / fr))
    for k in range(1, nh + 1):
        a = 1 / k
        if bright is not None: a = a * np.clip(bright * nh - k + 1, 0, 1)
        out += a * np.sin(2 * np.pi * fr * k * t + k * .3)
    return out * .5
def noise(d): return rng.standard_normal(int(d * SR))
def band(x, lo, hi):
    X = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR); m = np.ones_like(fr)
    if lo: m *= 1 / (1 + (lo / np.maximum(fr, 1)) ** 4)
    if hi: m *= 1 / (1 + (fr / hi) ** 4)
    return np.fft.irfft(X * m, len(x))
def reverb(x, dec=2.2, wet=.25, seed=1):
    r = np.random.default_rng(seed); n = int(dec * SR)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / SR * (6.9 / dec)); ir = band(ir, 200, 9000); ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n; F = 1 << (m - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, F) * np.fft.rfft(ir, F), F)[:len(x)]
    return x * (1 - wet) + y * wet * 1.4
def put(sig, t0, g=1.0, pan=0.0, bus='s'):
    i = int(t0 * SR)
    if i >= N or i < 0: return
    sig = sig[:N - i]; l = g * np.sqrt(1 - pan); r = g * np.sqrt(1 + pan)
    if bus == 's': L[i:i + len(sig)] += sig * l; R[i:i + len(sig)] += sig * r
    else: ML[i:i + len(sig)] += sig * l; MR[i:i + len(sig)] += sig * r
def load(name):
    with wave.open(f'sfx/{name}.wav') as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
    return a.reshape(-1, 2)
def put_st(a, t0, g):
    i = int(t0 * SR); n = min(len(a), N - i)
    if n > 0: L[i:i + n] += a[:n, 0] * g; R[i:i + n] += a[:n, 1] * g

# ---------- instruments ----------
def pluck(n, d=.28, bright=.4): return band(saw(f(n), d, harm=30, bright=bright) * expdec(d, 11), 60, 3200)
def taiko(d=.6): return glide(95, 42, d) * expdec(d, 7) + band(noise(d), 40, 700) * expdec(d, 30) * .5
def metal(d=.18): return band(noise(d), 2500, 9000) * expdec(d, 28)
def braam(notes, d=2.6, g=1.0, bright=.9):
    out = np.zeros(int(d * SR))
    for n in notes:
        for det in (-.12, 0, .12): out += saw(midi(NT[n] + det), d, harm=36, bright=bright * np.exp(-tt(d) * 1.2) + .08)
    env = np.minimum(1, tt(d) / .015) * np.exp(-tt(d) * 1.4)
    return band(np.tanh(out * env * 1.6) * g, 35, 6000)
def boom(d=2.2, f0=70, f1=28): return glide(f0, f1, d) * np.exp(-tt(d) * 2.2) + band(noise(d), 20, 160) * np.exp(-tt(d) * 6) * .4
def crash(d=2.5): return band(noise(d), 3000, 14000) * np.exp(-tt(d) * 2.6)
def bell(n, d=1.6):
    fr = f(n); s = sine(fr, d) + .35 * sine(fr * 2.01, d) + .15 * sine(fr * 3.02, d)
    return s * np.minimum(1, tt(d) / .004) * np.exp(-tt(d) * 3)
def click(d=.03, fr=3000): return band(noise(d), 1500, 12000) * expdec(d, 400) * .6 + sine(fr, d) * expdec(d, 160) * .5
def thunk(fr=150, d=.06): return sine(fr, d) * expdec(d, 55)
def swish(d=.6): t = tt(d); return band(noise(d), 300, 3500) * np.sin(np.pi * t / d) ** 2

pay, end, pf, rf = MU['payoff'], MU['end'], MU['pulseFrom'], MU['riserFrom']
B = MU.get('beat', .8)
# drone bed until payoff (cut 0.25 s early for a breath)
d = pay - .25; t = tt(d)
bed = sine(f('A1'), d) * .55 + saw(f('A2'), d, harm=10) * .35 + saw(f('E2'), d, harm=6) * .22
bed *= np.clip(t / .25, 0, 1) * (.55 + .45 * t / d) * np.clip((d - t) / .03, 0, 1) * (1 + .12 * np.sin(2 * np.pi * .19 * t))
put(band(bed, 30, 1800), 0, .5, 0, 'm')
# ostinato from pulseFrom to payoff, 16ths in the last third
riff = ['A2', 'A2', 'A2', 'C3', 'A2', 'A2', 'G2', 'A2']; x = pf; k = 0
while x < pay - .3:
    step = B / 4 if x > pf + (pay - pf) * .6 else B / 2
    put(pluck(riff[k % 8], bright=.35 + .3 * (k % 4 == 0)), x, .26, -.25 if k % 2 else .25, 'm'); k += 1; x += step
b = pf + 4 * B
while b < pay - .3:
    put(taiko(), b, .7, 0, 'm'); put(metal(), b + B / 2, .15, .4, 'm'); b += B
# riser into payoff
d = pay - .25 - rf; t = tt(d)
r = band(noise(d), 400, 9000) * (t / d) ** 2.6 + glide(180, 1100, d) * (t / d) ** 2 * .35
put(r * np.clip((d - t) / .02, 0, 1), rf, .5, 0, 'm')
# hits
for t0, size in ev['hits']:
    if size == 'big':
        put(braam(['A1', 'E2', 'A2', 'C3', 'E3', 'A3'], 3.4, .75, 1.0), t0, 1.0, 0, 'm'); put(boom(3, 62, 24), t0, 1.2, 0, 'm'); put(crash(3), t0, .3, 0, 'm'); put(taiko(.9), t0, .8, 0, 'm')
    else:
        put(braam(['A1', 'A2', 'E3'], 1.4, .35, .6), t0, .6, 0, 'm'); put(boom(1.3, 75, 35), t0, .65, 0, 'm')
# payoff section: driving beat + chords to end card
seq = [['A2', 'C3', 'E3', 'A3'], ['F2', 'C3', 'F3', 'A3'], ['G2', 'D3', 'G3', 'B3'], ['E2', 'B2', 'E3', 'G#3']]
seg = (end - pay) / 4
for i, ch in enumerate(seq):
    t0 = pay + i * seg; pad = sum(saw(f(n), seg + .3, harm=14) for n in ch) / 4; tp = tt(seg + .3)
    pad *= np.clip(tp / .1, 0, 1) * np.clip((seg + .3 - tp) / .3, 0, 1); put(band(pad, 60, 3000), t0, .3, 0, 'm')
    x = t0
    while x < t0 + seg - 1e-6: put(pluck(ch[int((x - t0) / (B / 4)) % 4], d=.3, bright=.3), x, .2, .3 if int(x / (B / 4)) % 2 else -.3, 'm'); x += B / 4
b = pay
while b < end - .1: put(taiko(.5), b, .55, 0, 'm'); put(metal(), b + B / 2, .16, -.3, 'm'); b += B
# end card: A major resolve
d = DUR - end; pad = sum(saw(f(n), d, harm=14) for n in ['A2', 'C#4', 'E3', 'A3']) / 4; tp = tt(d)
pad *= np.clip(tp / .4, 0, 1) * np.clip((d - tp) / 1.5, 0, 1); put(band(pad, 80, 2500), end + .1, .3, 0, 'm')
for i, n in enumerate(['A4', 'C#4', 'E5', 'A5']): put(bell(n, 2.0), end + B + i * B / 2, .12, .2, 'm')

# ---------- SFX from the page ----------
MIX = {n: load(n) for n in ['impact-cine', 'whoosh-fast', 'transition-snap', 'swoosh-quick', 'transition-soft']}
for t0, typ, g, pan in ev['sfx']:
    dur = None
    if ':' in typ: typ, dur = typ.split(':'); dur = float(dur)
    if typ == 'hit': put(S(thunk(80, .25), click(.03, 1800) * .5), t0, .9 * g, pan)
    elif typ == 'tick': put(click(.03, 2600), t0, .55 * g, pan)
    elif typ == 'swoosh': put_st(MIX['swoosh-quick'], t0, .45 * g)
    elif typ == 'whoosh': put_st(MIX['whoosh-fast'], t0, .5 * g)
    elif typ == 'cut': put_st(MIX['transition-snap'], t0, .35 * g); put(thunk(110, .12), t0, .4 * g)
    elif typ == 'snap': put(S(click(.04, 2400), thunk(90, .25) * 1.2, glide(500, 160, .3) * expdec(.3, 9) * .5), t0, .8 * g, pan); put_st(MIX['impact-cine'], t0, .25 * g)
    elif typ == 'thud': put(S(thunk(90, .25), click(.03, 2000) * .5), t0, .7 * g, pan)
    elif typ == 'pour':
        d = 1.2; tp = tt(d); x = band(noise(d), 200, 1800) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * tp) ** 2) * np.sin(np.pi * tp / d) ** .6
        put(x + glide(500, 260, d) * .06, t0, .35 * g, pan)
    elif typ in ('knit', 'stitch', 'sew'):
        rate = 16 if typ == 'knit' else (30 if typ == 'sew' else 12); x = t0
        while x < t0 + dur: put(S(thunk(170, .04) * .8, click(.015, 3200) * .6), x, .35 * g, .2 * np.sin(x * 7)); x += 1 / rate
        d = dur; tp = tt(d); put(band(saw(92, d, harm=20), 60, 1400) * (0.6 + 0.4 * np.sin(2 * np.pi * rate * tp) ** 2) * np.clip(tp / .05, 0, 1) * np.clip((d - tp) / .1, 0, 1), t0, .12 * g)
    elif typ == 'zip': put(band(noise(.7), 1500, 7000) * np.linspace(.2, 1, int(.7 * SR)) * expdec(.7, 1.5), t0, .35 * g, pan)
    elif typ == 'fold': put(S(swish(.4), thunk(120, .15)), t0, .6 * g, pan)
    elif typ == 'sizzle': d = 1.0; put(band(noise(d), 3000, 11000) * (0.5 + 0.5 * (rng.random(int(d * SR)) > .7)) * np.sin(np.pi * tt(d) / d), t0, .25 * g, pan)
    elif typ == 'trim': put(band(noise(.6), 2000, 8000) * np.sin(np.pi * tt(.6) / .6) * (0.6 + 0.4 * np.sin(2 * np.pi * 40 * tt(.6))), t0, .35 * g, pan)
    elif typ == 'deflate': put(glide(300, 90, .5) * expdec(.5, 4) * .5 + band(noise(.5), 300, 2000) * expdec(.5, 5) * .4, t0, .5 * g, pan)
    elif typ == 'crack':
        x = band(noise(.5), 2000, 12000) * expdec(.5, 45)
        for _ in range(5): x += sine(3000 + rng.random() * 5000, .5) * expdec(.5, 18 + rng.random() * 20) * .25
        put(x, t0, .6 * g, pan)
    elif typ == 'stretch': d = dur; tp = tt(d); put(glide(110, 240, d) * (tp / d) * .4 + band(noise(d), 600, 3000) * (tp / d) * .3, t0, .5 * g, pan)

# ---------- mix ----------
music = np.stack([reverb(ML, 2.4, .22, 1), reverb(MR, 2.4, .22, 2)])
sfx = np.stack([reverb(L, 1.2, .12, 3), reverb(R, 1.2, .12, 4)])
mix = np.tanh((music + sfx * .85) * .9) / .9
g0, g1 = int((pay - .25) * SR), int(pay * SR); mix[:, g0:g1] *= .08
fade = np.ones(N); fade[-int(.6 * SR):] = np.linspace(1, 0, int(.6 * SR)) ** 1.5; mix *= fade
mix /= np.max(np.abs(mix)) * 1.05
with wave.open(f'mix_{page}.wav', 'w') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix.T * 32767).astype(np.int16).tobytes())
print('wrote', f'mix_{page}.wav')
