import {DATA_URL,number,jst,validate,series,summary,csv} from './model.mjs';
const $=id=>document.getElementById(id);
let data,products;
const text=(node,value)=>{node.textContent=value;return node};
const make=(tag,value)=>text(document.createElement(tag),value);
const svg=(tag,attrs)=>{const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value]of Object.entries(attrs))el.setAttribute(key,value);return el;};
const formatDelta=value=>value===null?'—':`+${number(value)}`;

function draw(rows,metric,color) {
  const container=$('chart');container.replaceChildren();
  const valid=rows.filter(r=>r[metric]!==null);
  if(!valid.length) {
    const box=make('div','');box.className='chart-empty';
    box.append(make('strong',rows.some(r=>r.status==='ok')?'次の記録から、増え方が見えてきます。':'この期間の計測データはありません。'),make('p',rows.some(r=>r.status==='ok')?'初回の累計は比較の基準として保存しました。':'期間を広げるか、記録処理の状態を確認してください。'));container.append(box);return;
  }
  const width=Math.max(240,Math.round(container.getBoundingClientRect().width)),height=240,pad={l:48,r:18,t:15,b:40},plotW=width-pad.l-pad.r,plotH=height-pad.t-pad.b;
  const chart=svg('svg',{viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':`${$('product').selectedOptions[0].textContent}の${metric==='total'?'累計':'観測間の増分'}。詳細は下の観測履歴に掲載。`});
  const ceiling=Math.max(4,Math.ceil(Math.max(...valid.map(r=>r[metric]))/4)*4);
  const first=Date.parse(rows[0].at),last=Date.parse(rows.at(-1).at);
  const x=row=>first===last?pad.l+plotW/2:pad.l+(Date.parse(row.at)-first)/(last-first)*plotW;
  const y=value=>pad.t+plotH-value/ceiling*plotH;
  for(let i=0;i<=4;i++) {const yy=pad.t+i*plotH/4;chart.append(svg('line',{x1:pad.l,x2:width-pad.r,y1:yy,y2:yy,stroke:'#e3eaf2'}));const label=svg('text',{x:pad.l-10,y:yy+4,'text-anchor':'end',fill:'#526070','font-size':12});label.textContent=number(Math.round(ceiling*(1-i/4)*100)/100);chart.append(label);}
  let previous=null;
  for(const row of rows) {
    const value=row[metric];if(value===null){previous=null;continue;}
    if(metric==='total'&&previous&&Date.parse(row.at)-Date.parse(previous.at)<=36*3600000)chart.append(svg('line',{x1:x(previous),y1:y(previous[metric]),x2:x(row),y2:y(value),stroke:color,'stroke-width':2}));
    const mark=metric==='delta'?svg('rect',{x:x(row)-Math.min(14,plotW/rows.length/3),y:y(value),width:Math.min(28,plotW/rows.length*2/3),height:Math.max(2,y(0)-y(value)),fill:color,rx:2}):svg('circle',{cx:x(row),cy:y(value),r:4,fill:color});
    const title=svg('title',{});title.textContent=`${jst(row.at)} / ${number(value)}回 / ${row.note}`;mark.append(title);chart.append(mark);previous=row;
  }
  for(const [row,anchor]of [[rows[0],'start'],[rows.at(-1),'end']]) {if(first===last&&anchor==='end')continue;const label=svg('text',{x:x(row),y:height-12,'text-anchor':first===last?'middle':anchor,fill:'#526070','font-size':12});label.textContent=jst(row.at).slice(0,10);chart.append(label);}
  container.append(chart);
}

function render() {
  const product=products.find(p=>p.id===$('product').value),period=$('period').value;
  const metric=$('metric').value==='total'?'total':'delta';
  const all=series(data,product.id),result=summary(all,period);
  const rows=result.shown;
  text($('chart-summary'),metric==='total'?`${product.name} · 累計の推移`:`期間内に比較できる増分：${result.intervals?formatDelta(result.increase)+'回':'まだありません'}`);
  text($('chart-note'),metric==='delta'?'各棒は前回の成功観測からの増分です。期間開始をまたぐ区間は、上の期間合計から除外します。':'各点は観測時点のGitHub累計です。欠測は線をつながず、空白にします。');
  draw(rows,metric,product.color);
  text($('insight'),result.intervals?`${result.intervals}区間を比較し、${number(result.increase)}回の増加を確認しました。${result.partial?'比較できない区間もあります。履歴の状態を確認してください。':'この件数だけで利用者数や増減の原因までは判断できません。'}`:'比較用の記録が揃ってから、増加数を表示します。初回の累計を、その日の増加数には数えません。');
  $('history-rows').replaceChildren();
  for(const row of rows.slice(-30).reverse()) {const tr=document.createElement('tr');[jst(row.at),number(row.total),formatDelta(row.delta),row.note].forEach(v=>tr.append(make('td',v)));$('history-rows').append(tr);}
  if(!rows.length){const tr=document.createElement('tr'),td=make('td','選択した期間の記録はありません。');td.colSpan=4;tr.append(td);$('history-rows').append(tr);}
}

async function init() {
  try {
    const config=await fetch('/stats/products.json',{credentials:'omit',referrerPolicy:'no-referrer'});if(!config.ok)throw Error('Catalog unavailable');products=(await config.json()).products;
    let fallback=false;
    try {const res=await fetch(DATA_URL,{cache:'no-cache',credentials:'omit',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(12000)});if(!res.ok)throw Error('History unavailable');data=validate(await res.json());}
    catch {fallback=true;const res=await fetch('/stats/initial.json',{credentials:'omit',referrerPolicy:'no-referrer'});if(!res.ok)throw Error('Initial observation unavailable');data=validate(await res.json());}
    const first=data.snapshots[0],latest=data.snapshots.at(-1),age=Date.now()-Date.parse(latest.observed_at);
    const measured=products.map(p=>latest.products[p.id]).filter(p=>p?.status==='ok');
    text($('total'),measured.length?number(measured.reduce((n,p)=>n+p.total,0)):'—');text($('coverage'),`${measured.length} / ${products.length}作品を計測。未取得分は合計に含みません。`);
    text($('started'),jst(first.observed_at).slice(0,10));text($('updated'),jst(latest.observed_at));
    const warning=fallback?'自動更新データに接続できないため、保存済みの初回記録を表示しています。':age>48*3600000?'2日以上更新されていません。記録処理の実行状況を確認してください。':'最新の記録を表示しています。';
    text($('load-status'),warning);$('load-status').classList.toggle('warning',fallback||age>48*3600000);text($('freshness'),age>48*3600000?'更新の確認が必要です':'取得時点の件数です');
    for(const p of products) {
      const option=make('option',p.name);option.value=p.id;$('product').append(option);
      const rows=series(data,p.id),last=rows.at(-1),tr=document.createElement('tr'),name=document.createElement('td'),link=make('a',p.name);link.href=p.page;name.append(link);tr.append(name,make('td',number(last.total)),make('td',formatDelta(last.delta)),make('td',last.note));$('product-rows').append(tr);
    }
    for(const id of ['overview','analysis','products-panel','history-panel'])$(id).hidden=false;
    for(const id of ['product','period','metric'])$(id).addEventListener('change',render);
    $('export').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([csv(data,products)],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='tokumaru-download-observations.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
    window.addEventListener('resize',()=>requestAnimationFrame(render));
    render();
  } catch {text($('load-status'),'記録を読み込めませんでした。時間をおいて再読み込みするか、下のJSONデータ・実行状況を確認してください。');$('load-status').classList.add('warning');}
}
init();
