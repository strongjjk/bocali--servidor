'use strict';
document.querySelector('#setup-form').addEventListener('submit',async e=>{
 e.preventDefault();const form=e.target,out=document.querySelector('#entry-error'),button=form.querySelector('button');out.textContent='';
 const data=Object.fromEntries(new FormData(form));if(data.password!==data.repeat){out.textContent='As senhas nao conferem.';return;}delete data.repeat;button.disabled=true;
 try{const r=await fetch('/api/setup-owner',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','X-Pede-Request':'1'},body:JSON.stringify(data),signal:AbortSignal.timeout(20000)});const result=await r.json();if(!r.ok)throw Error(result.error||'Nao foi possivel configurar.');form.reset();location.replace('/#/painel');}
 catch(err){out.textContent=err.message;button.disabled=false;}
});
