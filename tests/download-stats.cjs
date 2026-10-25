'use strict';
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=process.env.STATS_QA_OUTPUT||path.resolve(root,'.dev-flow/stats-qa');
fs.mkdirSync(out,{recursive:true});
const types={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.png':'image/png','.svg':'image/svg+xml','.webp':'image/webp'};
const server=http.createServer((req,res)=>{
 let file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
 if(!file.startsWith(root+path.sep)&&file!==root){res.writeHead(403).end();return;}
 try{if(fs.statSync(file).isDirectory())file=path.join(file,'index.html');res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));}catch{res.writeHead(404).end();}
});
const initial=JSON.parse(fs.readFileSync(path.join(root,'stats/initial.json'),'utf8'));
const DATA='https://raw.githubusercontent.com/tokumaru-labs/tokumaru-labs.github.io/download-stats-data/downloads.json';
// Keep both fixture timestamps and browser Date independent of the host date.
const TEST_NOW=Date.parse('2026-10-25T03:00:00Z');
const latest=structuredClone(initial.snapshots[0]);
const fixture=()=>{const first=structuredClone(latest),last=structuredClone(latest);first.observed_at=new Date(TEST_NOW-86400000).toISOString();last.observed_at=new Date(TEST_NOW).toISOString();last.products['toku-control'].total+=3;last.products['toku-control'].assets[0].count+=3;return {schema:1,snapshots:[first,last]};};
(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
 let browser,checks=0;const errors=[];
 const check=(value,message)=>{assert.ok(value,message);checks++;console.log('PASS',message)};
 try{
  browser=await chromium.launch({executablePath:process.env.STATS_CHROMIUM||undefined,headless:true,args:['--no-sandbox','--single-process','--disable-dev-shm-usage']});
  const page=await browser.newPage({viewport:{width:1280,height:900},acceptDownloads:true});page.on('pageerror',e=>errors.push(e.message));
  await page.clock.setFixedTime(new Date(TEST_NOW));
  let payload=initial,rawFailure=false;
  await page.route(DATA,route=>rawFailure?route.fulfill({status:503,body:'Unavailable'}):route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(payload)}));
  const open=async()=>{await page.goto(base+'/stats/');await page.locator('#analysis').waitFor({state:'visible'});};
  await open();
  check(await page.locator('#total').innerText()==='6','real initial cumulative value displayed');
  check((await page.locator('#chart').innerText()).includes('次の記録'),'first sample is not graphed as six new downloads');
  check((await page.locator('#product-rows').innerText()).includes('GitHub配布の開始待ち'),'untracked VSIX is not presented as zero');
  check((await page.locator('meta[name="robots"]').getAttribute('content'))==='noindex,nofollow,noarchive','unlisted page requests no indexing');
  for(const width of [320,390,768,1280]){
   await page.setViewportSize({width,height:900});
   check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),width+'px no horizontal overflow');
   check(await page.locator('select,button').evaluateAll(els=>els.every(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1})),width+'px controls fit');
   if(width<720)check((await page.locator('#product').boundingBox()).width>=220,width+'px full product name fits');
  }
  for(const [name,width]of [['initial-desktop',1280],['initial-mobile',390]]){
   await page.setViewportSize({width,height:900});await page.screenshot({path:path.join(out,name+'.png'),fullPage:true});
  }
  payload=fixture();await open();
  check((await page.locator('#chart-summary').innerText()).includes('+3回'),'period growth uses sample difference');
  check(await page.locator('#chart rect').count()===1,'one measurable interval rendered');
  await page.locator('#metric').selectOption('total');check(await page.locator('#chart circle').count()===2,'cumulative mode has two observations');
  await page.locator('#product').selectOption('vscode-themes');check((await page.locator('#chart').innerText()).includes('計測データはありません'),'product selector displays honest empty state');
  await page.locator('#product').selectOption('toku-control');
  const downloadPromise=page.waitForEvent('download');await page.locator('#export').click();const download=await downloadPromise;const saved=path.join(out,'observations.csv');await download.saveAs(saved);
  const csv=fs.readFileSync(saved,'utf8');check(csv.includes('TOKU CONTROL')&&csv.includes('"3"')&&csv.includes('observed_at_jst'),'CSV contains observations and growth');
  await page.setViewportSize({width:1280,height:900});await page.screenshot({path:path.join(out,'fixture-history-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'fixture-history-mobile.png'),fullPage:true});
  rawFailure=true;await open();check((await page.locator('#load-status').innerText()).includes('初回記録'),'network failure shows labeled initial fallback');
  rawFailure=false;payload=fixture();payload.snapshots.at(-1).products['toku-control'].total=999;await open();check((await page.locator('#load-status').innerText()).includes('初回記録'),'invalid counters fall back without inventing totals');
  payload=fixture();payload.snapshots=payload.snapshots.slice(0,1);payload.snapshots[0].observed_at=new Date(TEST_NOW-4*86400000).toISOString();await open();check((await page.locator('#load-status').innerText()).includes('2日以上'),'stale history is clearly labeled');
  rawFailure=true;await page.route('**/stats/initial.json',route=>route.fulfill({status:503,body:'Unavailable'}));await page.goto(base+'/stats/');await page.waitForFunction(()=>document.getElementById('load-status').textContent.includes('読み込めません'));check(await page.locator('#overview').isHidden(),'complete failure shows no fabricated metrics');await page.unroute('**/stats/initial.json');rawFailure=false;
  const name='tokumaru-vscode-themes-0.2.1.vsix';
  const url='https://github.com/tokumaru-labs/tokumaru-labs.github.io/releases/download/vscode-themes-v0.2.1/'+name;
  payload=fixture();payload.snapshots.at(-1).products['vscode-themes']={status:'ok',total:0,assets:[{id:9,name,url,count:0,created_at:new Date(TEST_NOW).toISOString(),digest:'sha256:56a57076068c2244ec5ebd515f1b54043b89670fc118ff440db3aabfd387ffa5'}]};
  for(const route of ['/','/ja/','/vscode-themes/','/ja/vscode-themes/']){
   await page.goto(base+route);await page.waitForFunction(url=>document.querySelector('a[data-release-asset]')?.href===url,url);
   check(await page.locator('a[data-release-asset]').first().getAttribute('href')===url,route+' verified mirror preferred');
   check(await page.locator('a[data-release-asset]').first().getAttribute('download')===null,route+' cross-origin download attribute removed');
  }
  payload.snapshots.at(-1).products['vscode-themes'].assets[0].digest='wrong';await page.goto(base+'/ja/');await page.waitForTimeout(100);
  check((await page.locator('a[data-release-asset]').getAttribute('href')).startsWith('/downloads/'),'unverified mirror leaves original fallback');
  rawFailure=true;await page.goto(base+'/ja/vscode-themes/');await page.waitForTimeout(100);const fallback=await page.locator('a[data-release-asset]').getAttribute('href');check(fallback==='/downloads/'+name,'network failure preserves direct download');
  check((await page.request.get(base+fallback)).status()===200,'local fallback binary remains available');
  payload=initial;rawFailure=false;await page.goto(base+'/stats/');await page.keyboard.press('Tab');check(await page.evaluate(()=>document.activeElement.classList.contains('skip-link')),'keyboard skip link accessible');await page.keyboard.press('Enter');check(new URL(page.url()).hash==='#main','keyboard skip link opens main');
  check(errors.length===0,'no page JavaScript errors: '+errors.join(';'));
  console.log(checks+' browser checks passed; '+out);
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exit(1)});
