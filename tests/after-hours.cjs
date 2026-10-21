'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
const out=process.env.AFTER_HOURS_OUTPUT||path.join(root,'.dev-flow','qa');
fs.mkdirSync(out,{recursive:true});
const mime={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml','.png':'image/png','.webp':'image/webp'};
const server=http.createServer((req,res)=>{
 let file;
 try{file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));}catch{res.writeHead(400);res.end();return;}
 if(file!==root&&!file.startsWith(root+path.sep)){res.writeHead(403);res.end();return;}
 try{if(fs.statSync(file).isDirectory())file=path.join(file,'index.html');res.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));}catch{res.writeHead(404);res.end();}
});
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
 let browser,checks=0;
 const ok=(value,name)=>{assert.ok(value,name);checks++;console.log('PASS:',name)};
 try{
  browser=await chromium.launch({executablePath:process.env.AFTER_HOURS_CHROMIUM||undefined,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const page=await browser.newPage({viewport:{width:1280,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  if(process.env.AFTER_HOURS_FONT_CSS){const p=process.env.AFTER_HOURS_FONT_CSS;const css=fs.readFileSync(p,'utf8').replace(/url\(([^)]+)\)/g,(_,v)=>'url(data:font/woff2;base64,'+fs.readFileSync(path.resolve(path.dirname(p),v)).toString('base64')+')');await page.addInitScript(content=>document.addEventListener('DOMContentLoaded',()=>{const style=document.createElement('style');style.textContent=content+'h1,h2,.intro-copy,.tool-body p,.open{font-family:"Noto Sans JP",sans-serif!important}';document.head.append(style)}),css)}
  for(const route of ['/','/ja/']){
   await page.goto(base+route);
   const trigger=page.locator('[data-after-hours-trigger]'),door=page.locator('#after-hours-door');
   ok(await door.isHidden(),route+' entry starts hidden');
   ok(await page.locator('.pcard').count()===7,route+' seven public product cards retained');
   ok(await page.locator('#products a[href="/toku-chime/"]').count()===0,route+' Chime is absent from public products');
   for(let i=0;i<4;i++)await trigger.click();
   ok(await door.isHidden(),route+' four taps cannot open room');
   await page.waitForTimeout(2150);await trigger.click();
   ok(await door.isHidden(),route+' a long gap resets tap count');
   for(let i=0;i<4;i++)await trigger.click();
   ok(await door.isVisible()&&await trigger.getAttribute('aria-expanded')==='true',route+' five consecutive taps reveal moon');
   await door.click();ok(new URL(page.url()).pathname==='/after-hours/',route+' moon opens room');
  }
  ok(await page.locator('#nemumaru-link').getAttribute('href')==='https://nemumaru-pixel-worlds.bhpo.chatgpt.site/','Nemumaru links to existing private app');
  ok(await page.locator('#chime-link').getAttribute('href')==='/toku-chime/','Chime links to existing local tool');
  ok((await page.locator('meta[name="robots"]').getAttribute('content')).includes('noindex'),'room requests no indexing');
  ok(!fs.readFileSync(path.join(root,'sitemap.xml'),'utf8').includes('after-hours'),'room is absent from sitemap');
  ok(await page.locator('#tools .tool-card').count()===2,'room has exactly two tools');
  ok(await page.evaluate(()=>[...document.querySelectorAll('canvas')].every(c=>c.getContext('2d').getImageData(0,0,c.width,c.height).data.some((v,i)=>i%4===0&&v>25))),'all three pixel illustrations render');
  const liveA=await page.locator('#pixel-room').screenshot();await page.waitForTimeout(1800);const liveB=await page.locator('#pixel-room').screenshot();ok(!liveA.equals(liveB),'room screens and stars animate');
  await page.locator('#motion-toggle').click();const stillA=await page.locator('#pixel-room').screenshot();await page.waitForTimeout(400);ok(stillA.equals(await page.locator('#pixel-room').screenshot()),'motion off freezes pixel scene');
  await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>document.getElementById('motion-toggle').disabled);ok(await page.locator('#motion-toggle').isDisabled(),'OS reduced-motion preference overrides animation');
  ok(await page.locator('#motion-toggle').getAttribute('aria-pressed')==='false','reduced motion has accessible state');
  for(const width of [320,390,768,1280]){await page.setViewportSize({width,height:1000});ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),width+'px has no horizontal overflow')}
  await page.setViewportSize({width:1280,height:1060});await page.screenshot({path:path.join(out,'after-hours-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'after-hours-mobile.png'),fullPage:true});
  await page.locator('#chime-link').click();ok(await page.locator('#toggleButton').isVisible(),'Chime existing UI opens from launcher');
  await page.locator('[data-seconds="45"]').click();ok(await page.locator('#countdown').innerText()==='00:45','Chime presets work');
  await page.locator('#toggleButton').click();await page.waitForFunction(()=>document.getElementById('countdown').textContent!=='00:45',{},{timeout:5000});ok(await page.locator('#countdown').innerText()!=='00:45','Chime countdown still runs');await page.locator('#toggleButton').click();
  await page.goto(base+'/ja/');const trigger=page.locator('[data-after-hours-trigger]');await trigger.focus();for(let i=0;i<5;i++)await page.keyboard.press('Enter');
  ok(await page.locator('#after-hours-door').isVisible(),'keyboard can reveal entry');
  ok(await page.locator('#after-hours-door').evaluate(el=>el===document.activeElement),'keyboard focus moves to revealed door');
  ok(errors.length===0,'no page JavaScript errors: '+errors.join(';'));
  console.log(checks+' after-hours browser checks passed');
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r))}
})().catch(e=>{console.error(e);process.exit(1)});
