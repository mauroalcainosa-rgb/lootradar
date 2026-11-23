const { chromium } = require('playwright'); const fs=require('fs');
(async()=>{
 const b=await chromium.launch();
 const ctx=await b.newContext({viewport:{width:405,height:810},deviceScaleFactor:2.6667,isMobile:true,hasTouch:true});
 const deals=fs.readFileSync('../data/deals.json','utf8');
 await ctx.route(/deals\.json/, r=>r.fulfill({status:200,contentType:'application/json',body:deals}));
 await ctx.route(/steamstatic|epicgames\.com/, r=>r.continue());
 await ctx.addInitScript(()=>{ if(!localStorage.getItem('lootradar')) localStorage.setItem('lootradar', JSON.stringify({adult:true, prefs:{cats:['juegos'],budget:20000,size:'',name:'',weekly:5000}})); });
 const pg=await ctx.newPage(); const errs=[]; pg.on('pageerror',e=>errs.push(e.message));
 await pg.goto('http://localhost:8765/index.html'); await pg.waitForTimeout(3000);
 await pg.screenshot({path:'screen-1-hoy.png'});
 await pg.click('[data-tab=buscar]'); await pg.waitForTimeout(1500); await pg.screenshot({path:'screen-2-buscar.png'});
 await pg.click('[data-tab=hoy]'); await pg.waitForTimeout(1200);
 await pg.locator('.deal[data-open]').first().click(); await pg.waitForTimeout(1500); await pg.screenshot({path:'screen-3-detalle.png'});
 console.log(errs);
 await b.close();
})();
