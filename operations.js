/* Merchant-only preparation: configuration is not external validation. */
'use strict';
const Ops={data:null,user:null,busy:false,error:''};
const renderBeforeOps=render;
function statusItem(title,label,detail,kind='pending'){
 return `<article class="ops-status"><div><h3>${title}</h3><p>${detail}</p></div><span class="ops-badge ${kind}">${label}</span></article>`;
}
function pilotView(){
 const d=Ops.data,store=d?.stores.find(s=>s.id===state.adminStore),hosted=Boolean(d?.httpsConfigured);
 const storeUrl=d?d.origin+'/#/loja/'+encodeURIComponent(state.adminStore):'';
 return `${adminHeading('Preparar o teste.','Um pedido no celular. O mesmo pedido no balc&atilde;o. Ainda sem vendas reais.')}
 <section class="ops-hero"><div><div class="eyebrow">PR&Oacute;XIMO MARCO DO BOCALI</div><h2>Conectar os dois lados <br>sem arriscar o atendimento.</h2><p>Este painel mostra o que est&aacute; configurado. Ele n&atilde;o certifica impressoras, pagamentos ou servi&ccedil;os externos.</p></div><span class="ops-hero-label">PILOTO 0.6<br><strong>SEM COBRAN&Ccedil;AS</strong></span></section>
 <div class="ops-grid"><section class="panel"><div class="ops-panel-heading"><h2>Conex&otilde;es do piloto</h2><button class="btn secondary small" data-ops="refresh" ${Ops.busy?'disabled':''}>${Ops.busy?'Conferindo...':'Conferir agora'}</button></div>
 ${Ops.error?`<p class="auth-error" role="alert">${esc(Ops.error)}</p>`:''}
 ${!d?'<p class="muted spaced">Consultando as configura&ccedil;&otilde;es do servidor...</p>':
 statusItem('Acesso ao teste',d.gateEnabled?'Protegido':'Local',d.gateEnabled?'C&oacute;digo de entrada separado da conta de cada pessoa.':'Acesso restrito ao ambiente local de desenvolvimento.',d.gateEnabled?'ready':'pending')+
 statusItem('Contas e pedidos','No servidor','Cliente e lojista consultam o mesmo banco.','ready')+
 statusItem('Endere&ccedil;o do aplicativo',hosted?'HTTPS configurado':'N&atilde;o publicado',hosted?'Conferir o endere&ccedil;o nos aparelhos do piloto.':'Este endere&ccedil;o local n&atilde;o abre no celular de outra pessoa.',hosted?'configured':'pending')+
 statusItem('Entrega por bairro','Configur&aacute;vel','Cadastre bairro, apelidos e taxa. O CEP apenas ajuda a preencher o endere&ccedil;o.','ready')+
 statusItem('Impress&atilde;o',typeof nativePrinterAvailable==='function'&&nativePrinterAvailable()?'Android conectado':'Navegador',typeof nativePrinterAvailable==='function'&&nativePrinterAvailable()?'Ponte de impress&atilde;o direta dispon&iacute;vel neste aparelho; confirme fisicamente o papel.':'No navegador comum, usa a janela de impress&atilde;o.')+
 statusItem('Pagamentos',d.payments==='mercadopago'?'Online + balc&atilde;o':'Balc&atilde;o',d.payments==='mercadopago'?'Pix/cart&atilde;o online conectados; dinheiro e maquininha tamb&eacute;m dispon&iacute;veis.':'Dinheiro e cart&atilde;o na maquininha dispon&iacute;veis. Pix/cart&atilde;o online aguardam Mercado Pago.',d.payments==='mercadopago'?'configured':'ready')+
 statusItem('C&oacute;pias de seguran&ccedil;a','Ferramenta preparada','Backup e restaura&ccedil;&atilde;o por comando. Agendamento externo ainda n&atilde;o configurado.')+
 statusItem('Leitura de PDF',d.pdfEnabled?'Ativada para teste':'Desativada',d.pdfEnabled?'A confer&ecirc;ncia dos produtos continua obrigat&oacute;ria.':'Texto colado continua dispon&iacute;vel. Liberar PDF s&oacute; ap&oacute;s revisar as depend&ecirc;ncias.')}
 </section><div class="ops-side"><section class="panel"><div class="eyebrow muted">LINK DA SUA LOJA</div><h2>${esc(store?.name||adminShop().name)}</h2><p class="muted small">O link abre diretamente o card&aacute;pio desta loja. N&atilde;o inclui senha nem c&oacute;digo de acesso.</p><label class="field"><span>Endere&ccedil;o deste ambiente</span><input id="pilot-store-link" readonly value="${esc(storeUrl)}"></label><div class="toolbar"><button class="btn" data-ops="copy" ${!hosted?'disabled':''}>${hosted?'Copiar link da loja':'Dispon&iacute;vel ap&oacute;s hospedar'}</button><a class="btn secondary" href="#/loja/${esc(state.adminStore)}">Ver card&aacute;pio</a></div>${!hosted?'<p class="ops-note">N&atilde;o envie um endere&ccedil;o 127.0.0.1 aos clientes. Ele funciona somente no computador em que o servidor est&aacute; rodando.</p>':''}<div class="ops-counts"><span><b>${store?.products??'--'}</b>produtos de teste</span><span><b>${store?.deliveryAreas??'--'}</b>configura&ccedil;&otilde;es de entrega</span></div></section>
 <section class="panel"><div class="eyebrow muted">ROTEIRO DO PRIMEIRO PEDIDO</div><h2>Teste acompanhado.</h2><div class="ops-steps"><p><b>1</b><span>Abra a loja com uma conta de cliente em outra sess&atilde;o.</span></p><p><b>2</b><span>Escolha um produto e confira a taxa de entrega ou a retirada.</span></p><p><b>3</b><span>No balc&atilde;o, aceite o pedido e informe o prazo.</span></p><p><b>4</b><span>Confira a atualiza&ccedil;&atilde;o no cliente e teste a comanda.</span></p></div><div class="info-box"><strong>N&atilde;o preparar os pedidos.</strong><p>O GloriaFood segue sendo o sistema de atendimento real.</p></div></section></div></div>`;
}
async function loadOps(){
 if(Ops.busy||!Net.user||!writable())return;Ops.busy=true;Ops.error='';const userId=Net.user.id;
 try{const data=await api('/api/pilot-status');if(Net.user?.id===userId){Ops.data=data;Ops.user=userId;}}
 catch(e){Ops.error=e.message;}
 finally{Ops.busy=false;if(view==='piloto')render();}
}
render=function(){
 if(Ops.user!==Net.user?.id){Ops.data=null;Ops.user=Net.user?.id||null;}
 if(view==='piloto'&&Net.user&&writable()){
  shell(pilotView());const t=$('.topbar-title');if(t)t.textContent='Preparação do piloto';
  if(!Ops.data&&!Ops.busy&&!Ops.error)loadOps();return;
 }
 renderBeforeOps();
 if(view==='configuracoes'&&Net.user&&writable()){
  const p=$('.page-heading');if(p){const a=document.createElement('a');a.href='#/piloto';a.className='btn secondary ops-entry';a.textContent='Preparar o teste e conferir conexões';p.after(a);}
 }
};
document.addEventListener('click',async e=>{
 const b=e.target.closest('[data-ops]');if(!b)return;e.preventDefault();
 if(b.dataset.ops==='refresh'){loadOps();render();return;}
 if(b.dataset.ops==='copy'){
  const input=$('#pilot-store-link');if(!Ops.data?.httpsConfigured||!input)return;
  try{await navigator.clipboard.writeText(input.value);toast('Link da loja copiado. Envie o código do piloto separadamente.');}
  catch{input.focus();input.select();toast('Selecione e copie o link exibido.');}
 }
});
window.addEventListener('offline',()=>{Net.online=false;updateConnection();});
window.addEventListener('online',()=>refresh().catch(()=>updateConnection()));
render();
