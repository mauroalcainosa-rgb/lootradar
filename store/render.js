const { chromium } = require('playwright'); const fs=require('fs');
(async()=>{
 const b=await chromium.launch(); const pg=await b.newPage();
 const svg=fs.readFileSync('icon.svg','utf8');
 async function shot(html,w,h,out){ await pg.setViewportSize({width:w,height:h}); await pg.setContent(`<html><body style="margin:0;background:transparent">${html}</body></html>`); await pg.screenshot({path:out,omitBackground:true,clip:{x:0,y:0,width:w,height:h}}); }
 const inner=svg.match(/<g id="fg">[\s\S]*?<\/g>/)[0], defs=svg.match(/<defs>[\s\S]*?<\/defs>/)[0];
 const full=(s,round)=>`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="${s}" height="${s}">${defs}${round?'<circle cx="256" cy="256" r="256" fill="#0B0B0F"/>':'<rect width="512" height="512" fill="#0B0B0F"/>'}${inner}</svg>`;
 // foreground for adaptive: 108dp canvas, logo within ~66dp safe zone -> scale content 0.62 centered
 const fgsvg=s=>`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="${s}" height="${s}">${defs}<g transform="translate(256 256) scale(0.62) translate(-256 -256)">${inner}</g></svg>`;
 await shot(full(512),512,512,'icon-512.png');
 const res='../app/android/app/src/main/res/';
 const L={mdpi:48,hdpi:72,xhdpi:96,xxhdpi:144,xxxhdpi:192}, F={mdpi:108,hdpi:162,xhdpi:216,xxhdpi:324,xxxhdpi:432};
 for(const d in L){ await shot(full(L[d]),L[d],L[d],res+`mipmap-${d}/ic_launcher.png`); await shot(full(L[d],true),L[d],L[d],res+`mipmap-${d}/ic_launcher_round.png`); await shot(fgsvg(F[d]),F[d],F[d],res+`mipmap-${d}/ic_launcher_foreground.png`); }
 await b.close();
})();
