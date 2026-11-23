const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch(); const pg=await b.newPage({viewport:{width:1024,height:500}});
await pg.goto('file://'+process.cwd()+'/feature.html'); await pg.waitForTimeout(500);
await pg.screenshot({path:'feature-1024x500.png'}); await b.close();})();
