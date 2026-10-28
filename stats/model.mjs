export const DATA_URL = 'https://raw.githubusercontent.com/tokumaru-labs/tokumaru-labs.github.io/download-stats-data/downloads.json';
export const number = value => value === null || value === undefined ? '—' : new Intl.NumberFormat('ja-JP').format(value);
export const jst = value => new Intl.DateTimeFormat('ja-JP', {timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(value));

export function validate(data) {
  if(data?.schema!==1 || !Array.isArray(data.snapshots) || !data.snapshots.length) throw Error('No observations');
  let previous=-Infinity;
  for(const s of data.snapshots) {
    const time=Date.parse(s.observed_at);
    if(!Number.isFinite(time)||time<=previous||!s.products||typeof s.products!=='object')throw Error('Invalid observation');
    previous=time;
    for(const p of Object.values(s.products)) {
      if(!['ok','no_assets','unavailable'].includes(p.status))throw Error('Invalid status');
      if(p.status==='ok') {
        if(!Array.isArray(p.assets)||!p.assets.length||!Number.isSafeInteger(p.total)||p.total<0)throw Error('Invalid counter');
        const ids=new Set();let sum=0;
        for(const a of p.assets) {
          if(!Number.isSafeInteger(a.id)||ids.has(a.id)||!Number.isSafeInteger(a.count)||a.count<0||!Number.isFinite(Date.parse(a.created_at)))throw Error('Invalid asset');
          ids.add(a.id);sum+=a.count;
        }
        if(sum!==p.total)throw Error('Counter mismatch');
      } else if(p.total!==null)throw Error('Missing value is not zero');
    }
  }
  return data;
}

export function series(data,id) {
  let previous=null,missed=false;
  return data.snapshots.map(sample=>{
    const product=sample.products[id]||{status:'not_recorded',total:null,assets:[]};
    const item={at:sample.observed_at,total:product.total,status:product.status,delta:null,note:'',from:null};
    if(product.status!=='ok') { missed=true;item.note=product.status==='not_recorded'?'未記録（この指標の観測なし）':product.status==='no_assets'?'GitHub配布の開始待ち':'取得失敗・欠測';return item; }
    if(!previous) { item.note='初回記録（比較の基準）'; }
    else {
      item.from=previous.at;
      const before=new Map(previous.product.assets.map(a=>[a.id,a]));
      const after=new Map(product.assets.map(a=>[a.id,a]));
      const removed=[...before.keys()].some(id=>!after.has(id));
      let invalid=removed,delta=0;
      for(const asset of product.assets) {
        const old=before.get(asset.id);
        if(old) { if(asset.count<old.count)invalid=true; else delta+=asset.count-old.count; }
        else if(Date.parse(asset.created_at)>Date.parse(previous.at)) { delta+=asset.count; }
        else invalid=true;
      }
      if(invalid)item.note='比較不可（ファイル変更・カウンター減少）';
      else { item.delta=delta;item.note=missed||Date.parse(item.at)-Date.parse(previous.at)>36*3600000?'複数日・欠測を含む区間':'前回観測からの増分'; }
    }
    previous={at:sample.observed_at,product};missed=false;
    return item;
  });
}

export function filterPeriod(rows,days,now=Date.now()) {
  const start=days==='all'?-Infinity:now-Number(days)*86400000;
  return rows.filter(r=>Date.parse(r.at)>=start);
}

export function summary(rows,days,now=Date.now()) {
  const start=days==='all'?-Infinity:now-Number(days)*86400000;
  const shown=filterPeriod(rows,days,now);
  // A crossing interval cannot be attributed entirely to the chosen period.
  const complete=shown.filter(r=>r.delta!==null&&Date.parse(r.from)>=start);
  const partial=shown.some(r=>r.status!=='ok'||(r.from&&r.delta===null)||(r.delta!==null&&Date.parse(r.from)<start));
  return {shown,intervals:complete.length,increase:complete.reduce((n,r)=>n+r.delta,0),partial};
}

export function csv(data,products) {
  const cell=value=>'"'+String(value??'').replaceAll('"','""').replace(/^[=+@\-]/,"'$&")+'"';
  // Keep the original columns and product names; append metric semantics.
  const rows=[['product','observed_at_utc','observed_at_jst','cumulative','increase','interval_start_utc','status','note','metric_id','metric_role','measurement_note']];
  for(const p of products) for(const r of series(data,p.id))rows.push([p.name,r.at,jst(r.at),r.total,r.delta,r.from,r.status,r.note,p.id,p.reference?'reference':'distribution',p.description||'公開配布ファイルの取得回数。利用者数・インストール数ではありません。']);
  return '\uFEFF'+rows.map(r=>r.map(cell).join(',')).join('\r\n')+'\r\n';
}
