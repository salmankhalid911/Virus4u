<!doctype html>  
<html lang="en">  
<head>  
  <meta charset="UTF-8" />  
  <meta name="viewport" content="width=device-width,initial-scale=1" />  
  <title>Aimen — Will you be my Valentine?</title>  
  <style>  
    :root { --pink:#ff3b7a; --bg1:#ffd6e5; --bg2:#ffeef5; --text:#1f1f1f; }  
    *{ box-sizing:border-box; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; }  
    body{  
      margin:0; min-height:100vh; display:grid; place-items:center;  
      background: radial-gradient(circle at 20% 20%, var(--bg2), var(--bg1));  
      overflow:hidden;  
    }  
    .card{  
      width:min(560px, 92vw);  
      background: rgba(255,255,255,.75);  
      border: 1px solid rgba(255,255,255,.6);  
      backdrop-filter: blur(10px);  
      border-radius: 18px;  
      padding: 28px 22px;  
      box-shadow: 0 18px 60px rgba(0,0,0,.12);  
      text-align:center;  
      position:relative;  
    }  
    .emoji{  
      width:76px; height:76px; margin:0 auto 10px;  
      display:grid; place-items:center;  
      border-radius: 999px;  
      background: rgba(255,255,255,.7);  
      box-shadow: 0 10px 30px rgba(0,0,0,.08);  
      font-size: 42px;  
      position:relative;  
    }  
    .emoji::after{  
      content:"💗";  
      position:absolute;  
      right:-8px; top:-10px;  
      font-size: 22px;  
      transform: rotate(10deg);  
    }  
    h1{  
      margin: 10px 0 18px;  
      font-size: clamp(22px, 4.6vw, 34px);  
      color: var(--text);  
      letter-spacing: -.02em;  
    }  
    .name{ font-weight: 800; text-transform: lowercase; }  
    .btns{  
      margin-top: 18px;  
      display:flex;  
      justify-content:center;  
      align-items:center;  
      gap: 14px;  
      position:relative;  
      height: 70px;  
    }  
    button{  
      border:0;  
      border-radius: 999px;  
      padding: 14px 22px;  
      font-size: 16px;  
      font-weight: 700;  
      cursor:pointer;  
      transition: transform .12s ease, box-shadow .12s ease;  
      user-select:none;  
    }  
    #yes{  
      background: var(--pink);  
      color: white;  
      box-shadow: 0 14px 30px rgba(255,59,122,.35);  
      min-width: 120px;  
    }  
    #yes:hover{ transform: translateY(-1px); box-shadow: 0 16px 34px rgba(255,59,122,.42); }  
    #no{  
      background: rgba(255,255,255,.9);  
      color: #333;  
      border: 1px solid rgba(0,0,0,.08);  
      min-width: 90px;  
      position:absolute;  
      left: calc(50% + 95px);  
      top: 50%;  
      transform: translate(-50%,-50%);  
    }  
    .sub{  
      margin-top: 12px;  
      color: rgba(0,0,0,.55);  
      font-size: 13px;  
    }  
    .footer{  
      margin-top: 12px;  
      font-size: 12px;  
      color: rgba(0,0,0,.45);  
    }  
    .hearts span{  
      position: fixed;  
      left: var(--x);  
      top: 110%;  
      font-size: var(--s);  
      animation: floatUp var(--d) linear infinite;  
      opacity: .75;  
      filter: drop-shadow(0 8px 10px rgba(0,0,0,.08));  
      pointer-events:none;  
    }  
    @keyframes floatUp{  
      0%{ transform: translateY(0) translateX(0) rotate(0deg); }  
      100%{ transform: translateY(-130vh) translateX(var(--dx)) rotate(20deg); }  
    }  
    .modal{  
      position:fixed; inset:0; display:none; place-items:center;  
      background: rgba(0,0,0,.35);  
      padding: 18px;  
    }  
    .modal .box{  
      width:min(520px, 92vw);  
      background:white;  
      border-radius: 18px;  
      padding: 22px;  
      text-align:center;  
      box-shadow: 0 18px 60px rgba(0,0,0,.22);  
    }  
    .box h2{ margin: 6px 0 10px; font-size: 26px; }  
    .box p{ margin: 0 0 14px; color:#333; line-height:1.35; }  
    .box .small{ font-size: 12px; color: rgba(0,0,0,.55); margin-top: 8px; }  
  </style>  
</head>  
<body>  
  <div class="hearts" aria-hidden="true"></div>  
  
  <main class="card">  
    <div class="emoji">🐣</div>  
    <h1><span class="name">aimen</span> will you be my valentine?</h1>  
  
    <div class="btns">  
      <button id="yes">Yes</button>  
      <button id="no">No</button>  
    </div>  
  
    <div class="sub">“No” seems a bit shy 😈</div>  
    <div class="footer">sent with dangerously cute intentions 💘</div>  
  </main>  
  
  <div class="modal" id="modal">  
    <div class="box">  
      <h2>Yessss! 🥺💘</h2>  
      <p>Aimen, you just made my whole day.<br/>Happy Valentine’s ❤️</p>  
      <button id="close" style="background:#111;color:#fff;padding:12px 18px;border-radius:999px;">Close</button>  
      <div class="small">Screenshot this and send it back 😌</div>  
    </div>  
  </div>  
  
  <script>  
    // Floating hearts background  
    const hearts = document.querySelector(".hearts");  
    const emojis = ["💗","💖","💘","💝","💕","💞","❤️"];  
    for (let i=0; i<18; i++){  
      const s = document.createElement("span");  
      s.textContent = emojis[Math.floor(Math.random()*emojis.length)];  
      s.style.setProperty("--x", Math.random()*100 + "vw");  
      s.style.setProperty("--dx", (Math.random()*120 - 60) + "px");  
      s.style.setProperty("--s", (14 + Math.random()*22) + "px");  
      s.style.setProperty("--d", (6 + Math.random()*10) + "s");  
      s.style.animationDelay = (-Math.random()*10) + "s";  
      hearts.appendChild(s);  
    }  
  
    const no = document.getElementById("no");  
    const yes = document.getElementById("yes");  
    const modal = document.getElementById("modal");  
    const close = document.getElementById("close");  
  
    function moveNo(){  
      const pad = 14;  
      const vw = window.innerWidth;  
      const vh = window.innerHeight;  
  
      // Keep it roughly near the card area, but unpredictable  
      const x = Math.max(pad, Math.min(vw - pad, (vw/2) + (Math.random()*420 - 210)));  
      const y = Math.max(pad, Math.min(vh - pad, (vh/2) + (Math.random()*240 - 120)));  
  
      no.style.left = x + "px";  
      no.style.top  = y + "px";  
    }  
  
    // Make "No" dodge  
    ["mouseenter","touchstart","pointerenter"].forEach(ev => {  
      no.addEventListener(ev, (e) => { e.preventDefault(); moveNo(); }, {passive:false});  
    });  
  
    // Yes opens sweet message  
    yes.addEventListener("click", () => { modal.style.display = "grid"; });  
    close.addEventListener("click", () => { modal.style.display = "none"; });  
  
    // Start with a small dodge to show the joke  
    setTimeout(moveNo, 700);  
  </script>  
</body>  
</html>  
