'use strict';
document.querySelector('#pilot-form').addEventListener('submit',async e=>{
 e.preventDefault();const button=e.target.querySelector('button'),out=document.querySelector('#entry-error');button.disabled=true;out.textContent='';
 try{const r=await fetch('/api/pilot-unlock',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','X-Pede-Request':'1'},body:JSON.stringify({code:e.target.code.value}),signal:AbortSignal.timeout(15000)});const data=await r.json();if(!r.ok)throw Error(data.error||'Nao foi possivel entrar.');e.target.reset();location.replace('/'+location.hash);}
 catch(err){out.textContent=err.message||'Conexao indisponivel. Tente novamente.';button.disabled=false;}
});
