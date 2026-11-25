// Shared engine for the beanie animatics. Each storyboard page calls these builders,
// then fills `tl` (a paused GSAP timeline) and pushes per-frame updaters to FRAME.
const NS='http://www.w3.org/2000/svg';
const PAPER='#F4F3F1', CYAN='#00CEFF', RED='#B0212F', INK='#0B0C0E', DIM='#8A8D94';
const YARN={red:'#C8202E',black:'#2A2B30',blue:'#1F3FB8',grey:'#A9ADB3'};
const $=id=>document.getElementById(id);
function el(tag,attrs,parent){const e=document.createElementNS(NS,tag);for(const k in attrs)e.setAttribute(k,attrs[k]);if(parent)parent.appendChild(e);return e;}
function div(cls,html,style,parent){const d=document.createElement('div');if(cls)d.className=cls;if(html!=null)d.innerHTML=html;if(style)d.style.cssText=style;(parent||$('ov')).appendChild(d);return d;}
function rnd(seed){let s=seed>>>0||1;return()=>{s^=s<<13;s>>>=0;s^=s>>>17;s^=s<<5;s>>>=0;return (s%100000)/100000;};}
const lerp=(a,b,k)=>a+(b-a)*k;
const tl=gsap.timeline({paused:true});
const FRAME=[];           // functions(t) run every frame
const SFX=[];             // [time,type,gain,pan] -> audio script
const HITS=[];            // [time,size] music hits
const E='expo.out', EI='expo.in';
const sfx=(t,type,g=1,pan=0)=>SFX.push([+t.toFixed(3),type,g,pan]);

// ---------- scenes / overlays ----------
function scene(id){const d=document.createElement('div');d.className='scene';d.id=id;$('world').insertBefore(d,$('ov'));
  const s=el('svg',{class:'full',viewBox:'0 0 1080 1920'});d.appendChild(s);return {d,svg:s,id:'#'+id};}
const show=(ids,t)=>tl.set(ids,{visibility:'visible'},t);
const hide=(ids,t)=>tl.set(ids,{visibility:'hidden'},t);
function lines(id,top,rows,opt={}){ // rows: [[text,size,cls]]
  const box=div('txt','',`top:${top}px;${opt.center?'text-align:center;left:60px;width:960px;':''}`);box.id=id;
  rows.forEach(([t,sz,cls],i)=>{const ln=document.createElement('span');ln.className='ln';const sp=document.createElement('span');sp.className='h '+(cls||'');sp.style.fontSize=sz+'px';sp.innerHTML=t;sp.id=id+'_'+i;ln.appendChild(sp);box.appendChild(ln);});
  return rows.map((_,i)=>'#'+id+'_'+i);}
function rise(ids,t,d=.45,st=.1){gsap.set(ids,{yPercent:115});tl.fromTo(ids,{yPercent:115},{yPercent:0,duration:d,stagger:st,ease:E},t);}
function slam(ids,t,st=.4,s=1.35){[].concat(ids).forEach((id,i)=>{gsap.set(id,{yPercent:115});tl.fromTo(id,{yPercent:115,scale:s},{yPercent:0,scale:1,duration:.42,ease:E,transformOrigin:'0% 100%'},t+i*st);sfx(t+i*st,'hit',.5);});}
function sink(ids,t){tl.to(ids,{yPercent:-115,duration:.26,stagger:.04,ease:EI},t);}
function textIn(id,t,ids,mode='rise',st=.1){show('#'+id,t);mode==='slam'?slam(ids,t,st):rise(ids,t,.45,st);}
function textOut(id,ids,t){sink(ids,t);hide('#'+id,t+.35);}
function tag(id,html,style,cls='c'){const d=div('tagF '+cls,html,style);d.id=id;return '#'+id;}
function tagIn(id,t,snd=true){show(id,t);tl.fromTo(id,{scale:1.5,opacity:0},{scale:1,opacity:1,duration:.26,ease:'back.out(3)',transformOrigin:'50% 50%'},t);if(snd)sfx(t,'tick',.6);}
function chapter(id,num,title){const d=div('chap',`<div class="rule"></div><span class="n">${num}</span><span class="t">${title}</span>`);d.id=id;return '#'+id;}
function chapIn(id,t){show(id,t);tl.fromTo(id+' .rule',{scaleX:0},{scaleX:1,duration:.5,ease:'expo.inOut'},t);
  tl.fromTo(id+' .n',{yPercent:70,opacity:0},{yPercent:0,opacity:1,duration:.4,ease:E},t+.05);
  tl.fromTo(id+' .t',{xPercent:-10,opacity:0},{xPercent:0,opacity:1,duration:.4,ease:E},t+.12);sfx(t,'swoosh',.4);}
function chapOut(id,t){tl.to(id,{opacity:0,y:-40,duration:.22,ease:EI},t);hide(id,t+.25);}
function whipIn(id,t,dir=1){show(id,t);tl.fromTo(id,{x:dir*520,filter:'blur(26px)',opacity:0},{x:0,filter:'blur(0px)',opacity:1,duration:.3,ease:E},t);sfx(t-.05,'whoosh',.5);}
function whipOut(id,t,dir=-1){tl.to(id,{x:dir*520,filter:'blur(26px)',opacity:0,duration:.22,ease:EI},t);hide(id,t+.25);}
function fadeIn(id,t,d=.3){show(id,t);tl.fromTo(id,{opacity:0},{opacity:1,duration:d},t);}
function shock(t,x,y,color=PAPER,R=1100,d=.9){const c=el('circle',{cx:x,cy:y,r:0,fill:'none',stroke:color,'stroke-width':14,opacity:0},$('fx'));
  tl.set(c,{attr:{r:10},opacity:.9},t);tl.to(c,{attr:{r:R,'stroke-width':1},opacity:0,duration:d,ease:'expo.out'},t);}
function shake(t,a=20,d=.35){tl.to('#world',{keyframes:[{x:a,y:-a*.6},{x:-a*.8,y:a*.5},{x:a*.5,y:a*.3},{x:-a*.3,y:-a*.2},{x:0,y:0}],duration:d,ease:'none'},t);}
function flash(t,o=.8,d=.3){tl.to('#flash',{opacity:o,duration:.02},t);tl.to('#flash',{opacity:0,duration:d,ease:'power2.out'},t+.03);}
function sweep(t,d=.7){tl.set('#sweep',{opacity:1},t);tl.fromTo('#sweep',{x:-700},{x:1400,duration:d,ease:'power2.inOut'},t);tl.set('#sweep',{opacity:0},t+d);}
function bigHit(t,x=540,y=900,color=PAPER,size='big'){flash(t,size==='big'?.85:.5);shock(t,x,y,color,1300,1);shake(t,size==='big'?28:16,.4);HITS.push([t,size]);}

// ---------- photo layers ----------
// a full-frame photo with a camera you animate: {x,y,s,r} where x,y = focus point in image px
function photo(id,src,iw=1932,ih=2576){const d=document.createElement('div');d.className='scene photo';d.id=id;
  const img=document.createElement('img');img.src=src;img.style.cssText=`position:absolute;left:0;top:0;width:${iw}px;height:${ih}px;transform-origin:0 0;filter:saturate(1.12) contrast(1.08) brightness(.96)`;d.appendChild(img);
  $('world').insertBefore(d,$('ov'));const cam={x:iw/2,y:ih/2,s:1920/ih,r:0};
  FRAME.push(()=>{img.style.transform=`translate(540px,960px) rotate(${cam.r}deg) scale(${cam.s}) translate(${-cam.x}px,${-cam.y}px)`;});
  return {id:'#'+id,cam,d};}

// ---------- beanie line drawing (front view, centre 0,0, ~500 wide) ----------
function beanie(parent,{x=540,y=960,s=1,color=PAPER,w=3.4,logo='LOGO',patch=true}){
  const outer=el('g',{},parent), g=el('g',{transform:`translate(${x},${y}) scale(${s})`},outer);
  const P={};
  const add=(k,d,extra={})=>P[k]=el('path',Object.assign({d,fill:'none',stroke:color,'stroke-width':w/s,'stroke-linecap':'round','stroke-linejoin':'round',pathLength:1,'stroke-dasharray':'1 1','stroke-dashoffset':1},extra),g);
  add('dome','M-236,40 C-236,-205 -120,-262 0,-264 C120,-262 236,-205 236,40');
  add('cuff','M-252,40 L252,40 Q258,120 252,200 L-252,200 Q-258,120 -252,40 Z');
  const ribs=[];
  for(let i=-7;i<=7;i++){const bx=i*30;ribs.push(add('rd'+i,`M${bx},40 Q${bx*.92},-150 ${bx*.32},-246`,{'stroke-width':(w*.45)/s,opacity:.55}));}
  for(let i=-10;i<=10;i++){const bx=i*23.5;ribs.push(add('rc'+i,`M${bx},50 L${bx},190`,{'stroke-width':(w*.45)/s,opacity:.55}));}
  let patchG=null;
  if(patch){patchG=el('g',{opacity:0},g);
    el('rect',{x:-125,y:78,width:250,height:84,rx:8,fill:INK,stroke:'#3A3D45','stroke-width':3/s},patchG);
    const tx=el('text',{x:0,y:138,'text-anchor':'middle','font-family':'BS','font-weight':900,'font-size':58,fill:PAPER,'letter-spacing':2},patchG);tx.textContent=logo;}
  return {g:outer,inner:g,P,ribs,patchG,main:[P.dome,P.cuff]};}
const drawB=(b,t,d=.7)=>{tl.to(b.main,{attr:{'stroke-dashoffset':0},duration:d,ease:'power2.inOut'},t);tl.to(b.ribs,{attr:{'stroke-dashoffset':0},duration:d*.8,stagger:.01,ease:'power2.out'},t+d*.3);};
const setDrawn=(b,t)=>{tl.set(b.main.concat(b.ribs),{attr:{'stroke-dashoffset':0}},t);};

// ---------- rib-knit simulation: columns of V stitches growing row by row ----------
function knit(parent,{x0=80,y0=600,w=920,h=900,cols=18,rows=22,color=PAPER,needles=true}){
  const g=el('g',{},parent);const cw=w/cols, rh=h/rows; const rowsG=[];
  for(let r=0;r<rows;r++){const y=y0+h-(r+1)*rh;let d='';
    for(let c=0;c<cols;c++){const x=x0+c*cw; if(c%3===2) continue; // purl gap every third column (rib)
      d+=`M${x+cw*.04},${y} L${x+cw*.5},${y+rh*1.05} L${x+cw*.96},${y} `;}
    rowsG.push(el('path',{d,fill:'none',stroke:color,'stroke-width':9,'stroke-linecap':'round','stroke-linejoin':'round',opacity:0},g));}
  const nd=el('g',{opacity:0},g);const nl=[];
  if(needles) for(let c=0;c<cols;c++){if(c%3===2)continue;nl.push(el('line',{x1:x0+c*cw+cw*.5,x2:x0+c*cw+cw*.5,y1:0,y2:0,stroke:'#D8DCE3','stroke-width':4,'stroke-linecap':'round'},nd));}
  const st={p:0,needles:0};
  FRAME.push(t=>{const n=st.p*rows;rowsG.forEach((r,i)=>r.setAttribute('opacity',i<n?Math.min(1,(n-i)*1.5):0));
    const top=y0+h-n*rh; nd.setAttribute('opacity',st.needles);
    nl.forEach((l,i)=>{const b=Math.sin(t*26+i*1.3)*14;l.setAttribute('y1',top-70+b);l.setAttribute('y2',top+6+b);});});
  return {g,st,rows:rowsG};}

// ---------- tube -> crown closing, cuff fold ----------
function crown(parent,{x=540,y=1000,s=1,color=PAPER}){
  const g=el('g',{transform:`translate(${x},${y}) scale(${s})`},parent);
  const body=el('path',{fill:'#16181D',stroke:color,'stroke-width':4/s},g);
  const ribsG=el('g',{},g);const rl=[];for(let i=-6;i<=6;i++) rl.push(el('path',{fill:'none',stroke:color,'stroke-width':2/s,opacity:.45},ribsG));
  const gather=el('g',{opacity:0},g);for(let i=0;i<10;i++){const a=-Math.PI/2+(i-4.5)*.22;el('line',{x1:0,y1:-238,x2:Math.cos(a)*-40*(i%2?1:.6)+0,y2:-238+40,stroke:CYAN,'stroke-width':3/s},gather);}
  const cuff=el('g',{},g);
  const cuffRect=el('path',{d:'M-210,200 L210,200 L214,360 L-214,360 Z',fill:'#1E2128',stroke:color,'stroke-width':4/s},cuff);
  const cl=[];for(let i=-8;i<=8;i++) cl.push(el('line',{x1:i*24,x2:i*24,y1:206,y2:354,stroke:color,'stroke-width':2/s,opacity:.45},cuff));
  const st={c:0,f:0};
  FRAME.push(()=>{const c=st.c;const ty=lerp(-160,-10,c), cy=lerp(-160,-245,c), cx=lerp(200,200,c);
    body.setAttribute('d',`M-200,200 L-200,${ty} C-200,${cy} 200,${cy} 200,${ty} L200,200 Z`);
    rl.forEach((p,i)=>{const bx=(i-6)*30;p.setAttribute('d',`M${bx},196 Q${bx*lerp(1,.9,c)},${lerp(-40,-120,c)} ${bx*lerp(1,.3,c)},${lerp(-156,-232,c)}`);});
    gather.setAttribute('opacity',Math.max(0,c*2-1));
    const f=st.f; cuff.setAttribute('transform',`translate(0,${200}) scale(1,${1-2*f}) translate(0,-200)`);
    cuffRect.setAttribute('fill',f>.5?'#2A2E37':'#1E2128');});
  return {g,st};}

// ---------- rubber patch: mould, pour, layers, pop ----------
function patchMould(parent,{x=540,y=1000,s=1,logo='LOGO'}){
  const outer=el('g',{},parent), g=el('g',{transform:`translate(${x},${y}) scale(${s})`},outer);
  const uid='pm'+Math.floor(Math.random()*1e6);
  const defs=el('defs',{},g);
  const cpLogo=el('clipPath',{id:uid+'L'},defs);const lt=el('text',{x:0,y:42,'text-anchor':'middle','font-family':'BS','font-weight':900,'font-size':150,'letter-spacing':4},cpLogo);lt.textContent=logo;
  const cpBase=el('clipPath',{id:uid+'B'},defs);el('rect',{x:-300,y:-110,width:600,height:220,rx:18},cpBase);
  const plate=el('g',{},g);
  el('rect',{x:-360,y:-170,width:720,height:340,rx:20,fill:'#1A1C22',stroke:'#3A3D45','stroke-width':4},plate);
  el('rect',{x:-300,y:-110,width:600,height:220,rx:18,fill:'#0E0F12',stroke:'#4A4E58','stroke-width':3},plate);
  const cav=el('text',{x:0,y:42,'text-anchor':'middle','font-family':'BS','font-weight':900,'font-size':150,'letter-spacing':4,fill:'#07080A',stroke:CYAN,'stroke-width':2.5,'stroke-dasharray':'1800','stroke-dashoffset':'1800'},plate);cav.textContent=logo;
  const fillL=el('g',{'clip-path':`url(#${uid}L)`},g);const fl=el('rect',{x:-300,y:110,width:600,height:0,fill:PAPER},fillL);
  const fillB=el('g',{'clip-path':`url(#${uid}B)`},g);const fb=el('rect',{x:-300,y:110,width:600,height:0,fill:'#1B1C20'},fillB);
  g.appendChild(fillL); // logo above base
  const stream=el('path',{fill:'none',stroke:PAPER,'stroke-width':14,'stroke-linecap':'round',opacity:0},g);
  // finished patch (3D) shown at pop
  const pat=el('g',{opacity:0},g);
  for(let k=6;k>=1;k--){el('rect',{x:-300+k*2,y:-110+k*5,width:600,height:220,rx:18,fill:k>3?'#060708':'#111216'},pat);}
  el('rect',{x:-300,y:-110,width:600,height:220,rx:18,fill:'#1B1C20',stroke:'#3A3D45','stroke-width':3},pat);
  for(let k=4;k>=1;k--){const tx=el('text',{x:k*1.5,y:42+k*3,'text-anchor':'middle','font-family':'BS','font-weight':900,'font-size':150,'letter-spacing':4,fill:'#9A9CA3'},pat);tx.textContent=logo;}
  const top=el('text',{x:0,y:42,'text-anchor':'middle','font-family':'BS','font-weight':900,'font-size':150,'letter-spacing':4,fill:PAPER},pat);top.textContent=logo;
  const st={logo:0,base:0,pour:0,pourX:0,glow:0};
  FRAME.push(t=>{fl.setAttribute('y',110-220*st.logo);fl.setAttribute('height',220*st.logo);
    fb.setAttribute('y',110-220*st.base);fb.setAttribute('height',220*st.base);
    stream.setAttribute('opacity',st.pour);
    let d=`M${st.pourX},-900`;for(let yy=-880;yy<=-20;yy+=40)d+=` L${st.pourX+Math.sin(t*30+yy*.05)*4},${yy}`;stream.setAttribute('d',d);
    fl.setAttribute('fill',st.glow>0?`rgb(${244},${243-st.glow*40},${241-st.glow*120})`:PAPER);});
  return {g:outer,inner:g,st,cav,pat,plate,fillL,fillB};}

// ---------- end card: stitched KICKSTER ----------
function endCard(t,sub='Cut &amp; sew · Sialkot'){
  const S=scene('scEnd');const g=S.svg;
  const defs=el('defs',{},g);const cp=el('clipPath',{id:'wmClip'},defs);const rv=el('rect',{x:30,y:700,width:0,height:320},cp);
  const sg=el('g',{'clip-path':'url(#wmClip)'},g);
  const ts=el('text',{x:540,y:960,'text-anchor':'middle','font-family':'BS','font-weight':900,'font-size':236,'letter-spacing':4,fill:'none',stroke:CYAN,'stroke-width':5,'stroke-dasharray':'16 11'},sg);ts.textContent='KICKSTER';
  const tf=el('text',{x:540,y:960,'text-anchor':'middle','font-family':'BS','font-weight':900,'font-size':236,'letter-spacing':4,fill:PAPER,opacity:0},g);tf.textContent='KICKSTER';
  el('line',{x1:150,x2:930,y1:1010,y2:1010,stroke:CYAN,'stroke-width':7,'stroke-dasharray':'22 12'},g);
  const mk=el('rect',{x:140,y:995,width:800,height:30,fill:INK},g);
  const e=div('', `<div class="s dim" style="font-size:42px;letter-spacing:.2em">${sub}</div><div class="e3" style="margin-top:80px"><span class="pill">Comment “PRICE”</span></div><div class="s" style="font-size:38px;margin-top:44px;letter-spacing:.08em;opacity:.85">@kickster_brandlab</div>`,'position:absolute;left:0;top:1060px;width:1080px;text-align:center;visibility:hidden');e.id='endTxt';
  show(S.id,t);bigHit(t,540,880,CYAN,'big');
  tl.fromTo(rv,{attr:{width:0}},{attr:{width:1020},duration:.5,ease:'power2.inOut'},t+.02);
  for(let k=0;k<12;k++) sfx(t+.04+k*.04,'tick',.25,(k-6)/6);
  tl.fromTo(S.id,{scale:1.15},{scale:1,duration:3,ease:'power3.out',transformOrigin:'50% 46%'},t);
  tl.fromTo(tf,{opacity:0},{opacity:1,duration:.12},t+.6);bigHit(t+.6,540,880,PAPER,'mid');sweep(t+.65,.7);
  tl.fromTo(mk,{attr:{x:140,width:800}},{attr:{x:940,width:0},duration:.5,ease:'power2.inOut'},t+.9);
  show('#endTxt',t+.9);gsap.set('#endTxt > *',{opacity:0});
  tl.to('#endTxt > *',{opacity:1,y:0,duration:.35,stagger:.3,ease:'back.out(2)'},t+.95);sfx(t+1.25,'thud',.5);
}

// ---------- grain + boot ----------
function boot(DUR,MUSIC){
  tl.to({},{duration:.01},DUR);
  const gc=$('grain').getContext('2d');const img=gc.createImageData(540,960);
  function grain(f){let s=(f*2654435761)>>>0||7;const d=img.data;
    for(let i=0;i<d.length;i+=4){s^=s<<13;s>>>=0;s^=s>>>17;s^=s<<5;s>>>=0;const v=128+((s&255)-128)*.55;d[i]=d[i+1]=d[i+2]=v;d[i+3]=255;}
    gc.putImageData(img,0,0);}
  window.renderAt=t=>{tl.seek(t,false);FRAME.forEach(f=>f(t));grain(Math.round(t*30));};
  window.DURATION=DUR;window.SFX=SFX;window.HITS=HITS;window.MUSIC=MUSIC;
  document.fonts.ready.then(()=>Promise.all([...document.images].map(i=>i.complete?1:new Promise(r=>{i.onload=r;i.onerror=r;})))).then(()=>{renderAt(0);window.ready=true;});
}
