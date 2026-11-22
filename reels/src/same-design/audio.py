"""Original score + sound design for 'Same design. Different factory.'

Everything musical is synthesised here (A minor, 75 BPM: beat = 0.8 s), so the
music is owned outright. Five licence-traceable Mixkit SFX (sfx/*.wav, Mixkit
SFX Free License) are layered on transitions. Writes mix_raw.wav (48 kHz stereo).
"""
import json, wave
import numpy as np

SR = 48000
DUR = 33.6
N = int(SR * DUR)
rng = np.random.default_rng(11)
L = np.zeros(N); R = np.zeros(N)          # SFX bus
ML = np.zeros(N); MR = np.zeros(N)        # music bus

def midi(n): return 440.0 * 2 ** ((n - 69) / 12)
NOTE = {'A1': 33, 'E2': 40, 'F2': 41, 'G2': 43, 'A2': 45, 'B2': 47, 'C3': 48, 'D3': 50, 'E3': 52, 'F3': 53,
        'G3': 55, 'G#3': 56, 'A3': 57, 'B3': 59, 'C4': 60, 'C#4': 61, 'D4': 62, 'E4': 64, 'A4': 69, 'C5': 72, 'E5': 76, 'A5': 81, 'Bb2': 46}
def f(n): return midi(NOTE[n])

def put(sig, t0, gain=1.0, pan=0.0, bus='sfx'):
    i = int(t0 * SR)
    if i >= N: return
    sig = sig[: N - i]
    if i < 0: sig = sig[-i:]; i = 0
    l = gain * np.sqrt((1 - pan) / 2) * np.sqrt(2); r = gain * np.sqrt((1 + pan) / 2) * np.sqrt(2)
    if bus == 'sfx':
        L[i:i + len(sig)] += sig * l; R[i:i + len(sig)] += sig * r
    else:
        ML[i:i + len(sig)] += sig * l; MR[i:i + len(sig)] += sig * r

def S(*xs):
    n=max(len(x) for x in xs); o=np.zeros(n)
    for x in xs: o[:len(x)]+=x
    return o

def tt(d): return np.arange(int(d * SR)) / SR

def adsr(d, a=.01, rel=.2, curve=1.0):
    t = tt(d); e = np.minimum(1, t / max(a, 1e-4))
    e *= np.clip((d - t) / max(rel, 1e-4), 0, 1) ** curve
    return e

def expdec(d, k): return np.exp(-tt(d) * k)

def saw(freq, d, harm=24, bright=None):
    t = tt(d); out = np.zeros_like(t)
    nh = int(min(harm, (SR / 2 - 200) / freq))
    for k in range(1, nh + 1):
        amp = 1 / k
        if bright is not None: amp = amp * np.clip(bright * nh - k + 1, 0, 1)
        out += amp * np.sin(2 * np.pi * freq * k * t + k * .3)
    return out * .5

def sine(freq, d, phase=0): t = tt(d); return np.sin(2 * np.pi * freq * t + phase)

def glide(f0, f1, d, curve='exp'):
    t = tt(d); fr = f0 * (f1 / f0) ** (t / d) if curve == 'exp' else f0 + (f1 - f0) * t / d
    return np.sin(2 * np.pi * np.cumsum(fr) / SR)

def noise(d): return rng.standard_normal(int(d * SR))

def band(x, lo, hi):
    X = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(fr)
    if lo: m *= 1 / (1 + (lo / np.maximum(fr, 1)) ** 4)
    if hi: m *= 1 / (1 + (fr / hi) ** 4)
    return np.fft.irfft(X * m, len(x))

def reverb(x, dec=2.2, wet=.3, seed=1):
    r = np.random.default_rng(seed); n = int(dec * SR)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / SR * (6.9 / dec)); ir = band(ir, 200, 9000); ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n; F = 1 << (m - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, F) * np.fft.rfft(ir, F), F)[: len(x)]
    return x * (1 - wet) + y * wet * 1.4

def load(name):
    with wave.open(f'sfx/{name}.wav') as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
    a = a.reshape(-1, 2); return a

def put_st(a, t0, gain):
    i = int(t0 * SR); n = min(len(a), N - i)
    L[i:i + n] += a[:n, 0] * gain; R[i:i + n] += a[:n, 1] * gain

# =========================== MUSIC ===========================
# --- drone bed 0 - 22.15 (cut before the statement) ---
d = 22.15
bed = (sine(f('A1'), d) * .55 + saw(f('A2'), d, harm=10) * .35 + saw(f('E2'), d, harm=6) * .22)
t = tt(d); swell = np.clip(t / .25, 0, 1) * (0.55 + 0.45 * np.clip((t - 4.8) / 17, 0, 1))
swell *= np.clip((d - t) / .03, 0, 1)
bed *= swell * (1 + .12 * np.sin(2 * np.pi * .19 * t))
put(band(bed, 30, 1800), 0, .55, 0, 'm')
# high tension string (fifth) from 8.0
d = 14.15; ten = saw(f('E4'), d, harm=12) * .5 + saw(f('A3'), d, harm=12) * .5
t = tt(d); ten *= np.clip(t / 3, 0, 1) * np.clip((d - t) / .03, 0, 1) * (1 + .3 * np.sin(2 * np.pi * 5.2 * t) * .1)
put(band(ten, 300, 4000), 8.0, .09, .2, 'm')

# --- ostinato plucks ---
riff = ['A2', 'A2', 'A2', 'C3', 'A2', 'A2', 'G2', 'A2']
def pluck(n, d=.28, bright=.5):
    s = saw(f(n), d, harm=30, bright=bright) * expdec(d, 11)
    return band(s, 60, 3200)
k = 0
for t0, t1, step, g in [(4.8, 12.0, .4, .55), (12.0, 16.0, .2, .42), (16.0, 19.2, .4, .5), (19.2, 22.0, .2, .5)]:
    x = t0
    while x < t1 - 1e-6:
        ramp = g * (1 + .5 * (x - 19.2) / 2.8) if t0 == 19.2 else g
        put(pluck(riff[k % 8], bright=.35 + .3 * ((k % 4) == 0)), x, ramp * .5, (-.25 if k % 2 else .25), 'm')
        k += 1; x += step

# --- percussion: taiko kicks + metal ---
def taiko(d=.6):
    s = glide(95, 42, d) * expdec(d, 7); s += band(noise(d), 40, 700) * expdec(d, 30) * .5
    return s
def metal(d=.18): return band(noise(d), 2500, 9000) * expdec(d, 28)
b = 8.0
while b < 22.0 - 1e-6:
    put(taiko(), b, .75, 0, 'm')
    if abs(((b - 8.0) / .8) % 4 - 3) < 1e-6: put(taiko(.4), b + .4, .45, 0, 'm')
    if b >= 12.0: put(metal(), b + .4, .18, .4, 'm')
    b += .8

# --- braams / hits ---
def braam(notes, d=2.6, gain=1.0, bright=.9):
    out = np.zeros(int(d * SR))
    for n in notes:
        for det in (-.12, 0, .12):
            out += saw(midi(NOTE[n] + det), d, harm=36, bright=bright * np.exp(-tt(d) * 1.2) + .08)
    env = np.minimum(1, tt(d) / .015) * np.exp(-tt(d) * 1.4)
    out = np.tanh(out * env * 1.6) * gain
    return band(out, 35, 6000)
def boom(d=2.2, f0=70, f1=28):
    return glide(f0, f1, d) * np.exp(-tt(d) * 2.2) + band(noise(d), 20, 160) * np.exp(-tt(d) * 6) * .4
def crash(d=2.5): return band(noise(d), 3000, 14000) * np.exp(-tt(d) * 2.6)

put(braam(['A1', 'A2', 'E3'], 2.6, .5), 0.0, .9, 0, 'm'); put(boom(), 0.0, 1.0, 0, 'm')
put(boom(1.2, 80, 40), 0.8, .45, 0, 'm')
put(braam(['A1', 'E2', 'A2'], 1.4, .35, .6), 1.6, .8, 0, 'm'); put(boom(1.4, 75, 35), 1.6, .7, 0, 'm')
put(braam(['A1', 'Bb2', 'E3'], 1.6, .4), 2.4, .8, 0, 'm'); put(boom(1.2), 2.4, .6, 0, 'm')
put(braam(['A1', 'A2', 'C4'], 1.8, .3, .5), 4.8, .7, 0, 'm')
put(braam(['A1', 'E2', 'A2'], 1.0, .3, .5), 8.0, .7, 0, 'm'); put(boom(1.0), 8.0, .5, 0, 'm')

# --- riser into the statement 19.2 -> 22.15 ---
d = 2.95; t = tt(d)
rs = band(noise(d), 400, 9000) * (t / d) ** 2.6
tone = glide(180, 1100, d) * (t / d) ** 2 * .35
sh = sum(glide(110 * 2 ** j, 110 * 2 ** j * 4, d) for j in range(3)) * (t / d) ** 2 * .12
r = (rs + tone + sh) * np.clip((d - t) / .02, 0, 1)
put(r, 19.2, .55, 0, 'm')

# --- THE STATEMENT 22.4 (biggest hit) ---
put(braam(['A1', 'E2', 'A2', 'C3', 'E3', 'A3'], 3.8, .75, 1.0), 22.4, 1.0, 0, 'm')
put(boom(3.0, 62, 24), 22.4, 1.25, 0, 'm'); put(crash(3.0), 22.4, .32, 0, 'm')
put(taiko(.9), 22.4, .9, 0, 'm')
for t0, g in [(23.2, .5), (24.4, .6)]:
    put(boom(1.4, 70, 30), t0, g, 0, 'm'); put(taiko(.6), t0, .55, 0, 'm')
# statement pad Am held
d = 3.6; pad = sum(saw(f(n), d, harm=14) for n in ['A2', 'C3', 'E3', 'A3']) / 4
t = tt(d); pad *= np.clip(t / .8, 0, 1) * np.clip((d - t) / .4, 0, 1)
put(band(pad, 80, 2600), 22.6, .32, 0, 'm')
# bell motif
def bell(n, d=1.6):
    fr = f(n); s = sine(fr, d) + .35 * sine(fr * 2.01, d) + .15 * sine(fr * 3.02, d)
    return s * np.minimum(1, tt(d) / .004) * np.exp(-tt(d) * 3)
for t0, n in [(23.2, 'E5'), (24.0, 'C5'), (24.4, 'A4'), (25.2, 'E5'), (25.6, 'C5')]:
    put(bell(n), t0, .16, .3, 'm')

# --- resolution 26.4 -> 30.4 : F - G - E, then A major at 30.4 ---
chords = [(26.4, 1.6, ['F2', 'C3', 'F3', 'A3']), (28.0, 1.6, ['G2', 'D3', 'G3', 'B3']), (29.6, .8, ['E2', 'B2', 'E3', 'G#3'])]
for t0, d, ch in chords:
    pad = sum(saw(f(n), d + .3, harm=16) for n in ch) / 4; t = tt(d + .3)
    pad *= np.clip(t / .12, 0, 1) * np.clip((d + .3 - t) / .3, 0, 1)
    put(band(pad, 60, 3000), t0, .36, 0, 'm')
    put(sine(f(ch[0]) / 2, d) * np.clip(tt(d) / .05, 0, 1) * np.clip((d - tt(d)) / .1, 0, 1), t0, .35, 0, 'm')
    x = t0
    while x < t0 + d - 1e-6:   # gentle 8th arpeggio
        put(pluck(ch[int((x - t0) / .4) % 4], d=.35, bright=.25), x, .22, .3 if int(x / .4) % 2 else -.3, 'm'); x += .4
for x in np.arange(26.4, 30.0, .8): put(taiko(.45), x, .35, 0, 'm')

# --- FINAL 30.4 : A major, final bass hit, long tail ---
put(braam(['A1', 'E2', 'A2', 'C#4', 'E3'], 3.2, .7, .8), 30.4, .95, 0, 'm')
put(boom(3.2, 58, 22), 30.4, 1.3, 0, 'm'); put(crash(3.0), 30.4, .25, 0, 'm')
put(boom(1.6, 70, 30), 31.0, .7, 0, 'm'); put(taiko(.7), 31.0, .6, 0, 'm')
d = 3.2; pad = sum(saw(f(n), d, harm=14) for n in ['A2', 'C#4', 'E3', 'A3']) / 4; t = tt(d)
pad *= np.clip(t / .5, 0, 1) * np.clip((d - t) / 1.6, 0, 1)
put(band(pad, 80, 2500), 30.5, .3, 0, 'm')
for t0, n in [(31.0, 'A4'), (31.4, 'C#4'), (31.8, 'E5'), (32.2, 'A5')]:
    put(bell(n if n != 'C#4' else 'C#4', 2.0), t0, .12, .2, 'm')

# =========================== SOUND DESIGN ===========================
def click(d=.03, fr=3000):
    return (band(noise(d), 1500, 12000) * expdec(d, 400) * .6 + sine(fr, d) * expdec(d, 160) * .5)
def thunk(fr=150, d=.06): return sine(fr, d) * expdec(d, 55)
def tear(d):
    t = tt(d); x = band(noise(d), 900, 7000)
    cr = (rng.random(len(t)) < (0.004 + 0.03 * t / d)).astype(float); cr = band(cr, 1500, 9000) * 4
    env = np.clip(t / .05, 0, 1) * np.clip((d - t) / .12, 0, 1)
    return (x * .6 + cr) * env * (0.6 + 0.4 * np.sin(2 * np.pi * 31 * t) ** 2)
def crack(d=.5):
    s = band(noise(d), 2000, 12000) * expdec(d, 45)
    for _ in range(5): s += sine(3000 + rng.random() * 5000, d) * expdec(d, 18 + rng.random() * 20) * .25
    return s
def zap(d=.25): x = noise(d); x = np.round(x * 3) / 3; return band(x, 800, 6000) * expdec(d, 12)
def swish(d=.6):
    t = tt(d); return band(noise(d), 300, 3500) * np.sin(np.pi * t / d) ** 2

# S1 : hoodie strokes + same-spec ticks
for t0 in [.15, .22]: put(swish(.7), t0, .25, -.4 if t0 < .2 else .4)
put(click(), 1.15, .35, -.3); put(click(), 1.2, .35, .3)
put_st(load('impact-cine'), 1.6, .35)
# S2 : falls apart
put(tear(.85), 2.6, .55, -.3)
put(zap(), 2.8, .45, -.2); put(thunk(90, .2), 2.8, .6)
put(crack(), 3.2, .6, -.1); put(thunk(70, .3), 3.2, .5)
put(tear(.4), 3.6, .5, -.4); put(thunk(80, .25), 3.6, .55)
for i in range(6): put(click(.02, 5000 + i * 300), 3.62 + i * .035, .18, -.5)
put_st(load('whoosh-fast'), 3.92, .35)
put(sine(1400, .9) * expdec(.9, 4) * .4 + sine(2100, .9) * expdec(.9, 5) * .25, 4.2, .3, .3)
# S3
put_st(load('whoosh-fast'), 4.72, .4)
put_st(load('transition-snap'), 6.28, .5)
for i in range(4): put(click(.03, 2600), 6.8 + i * .1, .25, -.4)
put_st(load('whoosh-fast'), 7.3, .55)
# S4 fabric : swish in, soft fabric texture, loupe ticks
put_st(load('swoosh-quick'), 8.0, .4)
d = 4.0; t = tt(d); fab = band(noise(d), 400, 2500) * (0.5 + 0.5 * np.sin(2 * np.pi * .52 * t) ** 2) * np.clip(t / .5, 0, 1) * np.clip((d - t) / .3, 0, 1)
put(fab, 8.0, .07, 0)
for t0 in [9.0]: put(swish(.5), t0, .25, -.3)
for t0 in [9.55, 10.35, 11.15]: put(click(.04, 2400), t0, .4, .3); put(thunk(200, .05), t0, .3)
put_st(load('whoosh-fast'), 11.65, .4)
# S5 construction : machine
drops = json.load(open('drops.json'))
put_st(load('swoosh-quick'), 12.0, .35)
for x in drops['A']: put(S(thunk(120, .07), click(.02, 1800) * .7), x, .55, -.25)
for i, x in enumerate(drops['B']): put(S(thunk(160, .04) * .8, click(.015, 3200) * .6), x, .32, .25)
d = 2.3; t = tt(d); motor = band(saw(92, d, harm=20), 60, 1400) * (0.6 + 0.4 * np.sin(2 * np.pi * 16 * t) ** 2)
put(motor * np.clip(t / .1, 0, 1) * np.clip((d - t) / .15, 0, 1), 12.35, .12, .1)
put(S(glide(900, 260, .35) * expdec(.35, 7), click(.03, 4000)), 13.75, .45, -.3)   # thread snaps
put(thunk(70, .3), 13.78, .55)
put_st(load('transition-snap'), 14.5, .4)
d = .55; t = tt(d); creak = band(saw(1, d) * 0 + glide(110, 240, d), 80, 2000) * (t / d) + band(noise(d), 600, 3000) * (t / d) * .4
put(creak, 14.85, .3)
put(S(click(.04, 2500), thunk(90, .25) * 1.2, glide(420, 180, .3) * expdec(.3, 9) * .5), 15.4, .6)
put_st(load('whoosh-fast'), 15.66, .4)
# S6 embroidery buzz
put_st(load('swoosh-quick'), 16.0, .35)
put(swish(.7), 16.2, .2, 0)
x = 16.75
while x < 18.2:
    put(S(click(.012, 2800 + 600 * np.sin(x * 9)) * .7, thunk(240, .02) * .5), x, .16, .2 * np.sin(x * 7)); x += 1 / 22
for t0 in [17.6, 17.7, 17.8, 17.85]: put(click(.03, 3600), t0, .22, .3)
put_st(load('whoosh-fast'), 18.86, .4)
# S7 QC
put_st(load('swoosh-quick'), 19.2, .35)
d = 1.9; put(band(noise(d), 1500, 6000) * .3 * np.sin(np.pi * tt(d) / d), 19.5, .12, 0)
for t0 in [19.6, 20.2, 20.8, 21.4]:
    put(S(click(.03, 2900), sine(1760, .25) * expdec(.25, 14) * .5 + sine(2640, .25) * expdec(.25, 18) * .3), t0, .45, .2)
# S8 statement
put_st(load('impact-cine'), 22.4, .55)
for t0 in [22.8, 24.0]: put(thunk(60, .3), t0, .5)
put_st(load('swoosh-quick'), 25.0, .2)
# S9
put_st(load('transition-soft'), 25.95, .45)
for t0 in [27.0, 27.4, 27.8, 28.2, 28.6]: put(click(.03, 2300 if t0 != 28.2 else 1800), t0, .35, -.2)
for t0 in [29.0, 29.4]: put(S(thunk(90, .25), click(.03, 2000) * .5), t0, .55)
put(tear(.55), 29.95, .7, 0)
# S10 payoff
put_st(load('impact-cine'), 30.4, .5)
x = 30.42
while x < 30.92: put(S(click(.012, 3000) * .6, thunk(200, .02) * .4), x, .18, (x - 30.67) * 2); x += 1 / 26
put(sine(880, 1.2) * expdec(1.2, 3) * .3 + sine(1320, 1.2) * expdec(1.2, 4) * .2, 31.0, .25)
x = 31.3
while x < 31.8: put(click(.012, 3400) * .5, x, .14, (x - 31.55) * 2); x += 1 / 26
put(S(click(.05, 1500), thunk(110, .2)), 31.7, .4)

# =========================== MIX ===========================
music = np.stack([ML, MR]); sfx = np.stack([L, R])
music = np.stack([reverb(music[0], 2.4, .22, 1), reverb(music[1], 2.4, .22, 2)])
sfx = np.stack([reverb(sfx[0], 1.2, .12, 3), reverb(sfx[1], 1.2, .12, 4)])
mix = music * 1.0 + sfx * .85
# gentle bus glue + safety
mix = np.tanh(mix * .9) / .9
duck = np.ones(N); g0, g1 = int(22.12 * SR), int(22.4 * SR)
duck[g0:g1] = 0.06; duck[g0 - 480:g0] = np.linspace(1, .06, 480)
mix *= duck
fade = np.ones(N); fade[-int(.6 * SR):] = np.linspace(1, 0, int(.6 * SR)) ** 1.5
mix *= fade
mix /= np.max(np.abs(mix)) * 1.05
out = (mix.T * 32767).astype(np.int16)
with wave.open('mix_raw.wav', 'w') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())
print('wrote mix_raw.wav', out.shape)
