const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage();
await p.goto('http://127.0.0.1:8768/index.html');await p.waitForFunction(()=>window.ready===true);
const d=await p.evaluate(()=>({A:window.DROPS_A,B:window.DROPS_B}));require('fs').writeFileSync('drops.json',JSON.stringify(d));console.log(d.A.length,d.B.length);await b.close();})();
