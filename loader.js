/* No API responses are cached. Fail closed if the pilot server is offline. */
(async function(){
 'use strict';
 try{
  const r=await fetch('/api/bootstrap',{cache:'no-store',credentials:'same-origin',signal:AbortSignal.timeout(10000)});
  if(r.status===403){const problem=await r.json();if(problem.gateRequired){location.replace('/pilot'+location.hash);return;}}
  if(!r.ok)throw new Error();
  window.PedeBootstrap=await r.json();
  for(const src of ['delivery.js','domain.js','order-flow.js','app.js','delivery-ui.js','neighborhood-delivery.js','native-print.js','connected.js','operations.js']){
   await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=src;s.onload=resolve;s.onerror=reject;document.body.append(s);});
  }
 }catch{
  const app=document.getElementById('app');app.replaceChildren();
  const wrap=document.createElement('div');wrap.className='startup-error';
  const h=document.createElement('h1');h.textContent='N\u00e3o foi poss\u00edvel conectar ao Bocali.';
  const p=document.createElement('p');p.textContent='Execute o servidor do projeto e abra o endere\u00e7o local indicado. Nenhum pedido foi criado. Este aplicativo n\u00e3o funciona abrindo index.html diretamente.';
  const b=document.createElement('button');b.className='btn';b.textContent='Tentar novamente';b.addEventListener('click',()=>location.reload());
  wrap.append(h,p,b);app.append(wrap);
 }
})();
