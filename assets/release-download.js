/* Prefer the verified release copy; original links remain working fallbacks.
   Reads public aggregate data only. No click logging, cookies, or identifiers. */
(async()=>{
  const links=[...document.querySelectorAll('a[data-release-asset]')];
  if(!links.length)return;
  const repo='tokumaru-labs/tokumaru-labs.github.io';
  try {
    const response=await fetch(`https://raw.githubusercontent.com/${repo}/download-stats-data/downloads.json`,{credentials:'omit',referrerPolicy:'no-referrer',cache:'no-cache',signal:AbortSignal.timeout(5000)});
    if(!response.ok)return;
    const history=await response.json();
    if(history.schema!==1||!Array.isArray(history.snapshots))return;
    const latest=history.snapshots.at(-1);
    // Do not switch to a possibly removed release using stale data.
    if(!latest||!Number.isFinite(Date.parse(latest.observed_at))||Math.abs(Date.now()-Date.parse(latest.observed_at))>48*3600000)return;
    const product=latest.products?.['vscode-themes'];
    if(product?.status!=='ok'||!Array.isArray(product.assets))return;
    for(const link of links) {
      const asset=product.assets.find(a=>a.name===link.dataset.releaseAsset);
      const expected=`https://github.com/${repo}/releases/download/vscode-themes-v0.2.1/${link.dataset.releaseAsset}`;
      if(asset?.url!==expected||asset.digest!=='sha256:56a57076068c2244ec5ebd515f1b54043b89670fc118ff440db3aabfd387ffa5')continue;
      link.href=asset.url;link.removeAttribute('download');
    }
  } catch { /* Network failure leaves the original download unchanged. */ }
})();
