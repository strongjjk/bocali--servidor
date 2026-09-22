/* Bocali v1.0 RC: servidor, contas, pedidos, Mercado Pago e ponte Android/Epson.
   Credenciais do provedor ficam somente no servidor. */
'use strict';
const Net={...window.PedeBootstrap,busy:false,online:true,lastSync:Date.now(),pending:null,authMode:'login',registerMode:'customer',baseline:null,lastSignature:'',saving:null};
const oldRender=render,oldShell=shell,oldCheckout=checkout,oldDashboard=dashboardView,oldOrdersView=ordersView,oldShowReceipt=showReceipt,oldPrinterHelp=printerHelp;
function cartKey(){return 'pede-v04-cart-'+(Net.user?.id||'guest');}
function rememberCart(){try{sessionStorage.setItem(cartKey(),JSON.stringify(state.cart));}catch{}}
function forgetPrivate(){state.cart={storeId:null,items:[]};draft=[];rawText='';Net.pending=null;geo.selection=null;geo.confirmed=null;}
function remoteSignature(data){return JSON.stringify([data.user,data.stores,data.products,data.favorites,data.customerOrders,data.merchantOrders,data.managedStores]);}
function applyRemote(data){
 const prior=Net.user?.id;Object.assign(Net,data);Net.lastSync=Date.now();Net.online=true;
 if(prior!==Net.user?.id){forgetPrivate();try{const x=JSON.parse(sessionStorage.getItem(cartKey()));if(x&&Array.isArray(x.items))state.cart=x;}catch{}}
 state.stores=data.stores;state.products=data.products;state.favorites=data.favorites;
 if(!data.managedStores.includes(state.adminStore))state.adminStore=data.managedStores[0]||'cantinho';
 Net.baseline=JSON.parse(JSON.stringify({stores:data.stores,products:data.products,favorites:data.favorites}));
 Net.lastSignature=remoteSignature(data);state.orders=isAdmin()?Net.merchantOrders:Net.customerOrders;
}
async function api(path,payload){
 const options={method:payload===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:{'X-Bocali-Request':'1'},signal:AbortSignal.timeout(20000)};
 if(payload!==undefined){options.headers['Content-Type']='application/json';options.headers['X-CSRF-Token']=Net.csrf||'';options.body=JSON.stringify(payload);}
 let response;
 try{response=await fetch(path,options);}catch{Net.online=false;updateConnection();throw new Error('Conex\u00e3o indispon\u00edvel. Confira o hist\u00f3rico antes de reenviar.');}
 const data=await response.json();
 if(data.gateRequired){Net.online=false;location.replace('/pilot'+location.hash);throw new Error('Acesso ao piloto expirado. Entre novamente.');}
 if(!response.ok){const err=new Error(data.error||'N\u00e3o foi poss\u00edvel concluir.');err.status=response.status;throw err;}
 Net.online=true;return data;
}
async function refresh(force=false){
 if(Net.busy&&!force)return;
 const seq=Net.refreshSeq=(Net.refreshSeq||0)+1;const data=await api('/api/bootstrap');if(seq!==Net.refreshSeq)return;const changed=remoteSignature(data)!==Net.lastSignature;
 const previousUser=Net.user?.id;const previousNew=(Net.merchantOrders||[]).filter(o=>o.status==='new').map(o=>o.id);applyRemote(data);
 const arrived=(Net.merchantOrders||[]).filter(o=>o.status==='new'&&!previousNew.includes(o.id));if(arrived.length&&typeof beep==='function')beep();
 if(previousUser&&!Net.user){closeModal();location.hash='#/conta';render();return;}
 if(changed&&!$('#modal').open&&!geo.edit&&!draft.length)render();else updateConnection();
}
function updateConnection(){
 const el=$('#sync-status');if(!el)return;
 el.classList.toggle('offline',!Net.online);
 el.textContent=Net.busy?'Salvando no servidor...':Net.online?'Bocali online':'Sem conexão - pedidos não confirmados';
}
async function run(task){
 if(Net.busy)throw new Error('Uma opera\u00e7\u00e3o est\u00e1 em andamento.');
 Net.busy=true;updateConnection();
 try{const result=await task();await refresh(true);return result;}
 catch(e){try{await refresh(true);}catch{}throw e;}
 finally{Net.busy=false;updateConnection();}
}
function requireUser(){if(Net.user)return true;toast('Entre na sua conta para guardar lojas e pedidos.');location.hash='#/conta';return false;}
function writable(){return Net.user&&Net.managedStores.includes(state.adminStore);}
function catalogPayload(){
 const store=adminShop(),baseline=Net.baseline.stores.find(s=>s.id===store.id);
 return {storeId:store.id,expectedVersion:baseline?.version,store:JSON.parse(JSON.stringify(store)),products:JSON.parse(JSON.stringify(state.products.filter(p=>p.storeId===store.id)))};
}
save=function(){
 rememberCart();if(!Net.baseline||Net.busy)return;
 const before=Net.baseline;const store=adminShop();const original=before.stores.find(s=>s.id===store.id);
 const changed=JSON.stringify(store)!==JSON.stringify(original)||JSON.stringify(state.products.filter(p=>p.storeId===store.id))!==JSON.stringify(before.products.filter(p=>p.storeId===store.id));
 if(changed){
  if(!writable()){applyRemote({...Net,stores:before.stores,products:before.products,favorites:before.favorites});render();return toast('Esta conta n\u00e3o pode alterar a loja.');}
  const payload=catalogPayload();
  Net.saving=run(()=>api('/api/catalog',payload)).then(()=>{render();toast('Altera\u00e7\u00e3o salva no servidor.');}).catch(e=>{render();toast(e.message);}).finally(()=>{Net.saving=null;});
 }
};
adminSelect=function(){return `<label><span class="only-screen-reader">Sua loja</span><select id="admin-select" class="admin-selector">${state.stores.filter(s=>Net.managedStores.includes(s.id)).map(s=>`<option value="${esc(s.id)}" ${s.id===state.adminStore?'selected':''}>${esc(s.name)}</option>`).join('')}</select></label>`;};
adminHeading=function(title,subtitle){return `<div class="page-heading"><div><div class="eyebrow muted" style="margin-bottom:10px">\u00c1REA DO LOJISTA \u00b7 ACESSO AUTORIZADO</div><h1>${title}</h1><p>${subtitle}</p></div>${adminSelect()}</div>`;};
shell=function(content){
 oldShell(content);
 document.title='Bocali | '+(view==='conta'?'Sua conta':view==='painel'?'Painel da loja':view==='piloto'?'Preparar operação':'Suas lojas favoritas');
 for(const notice of document.querySelectorAll('.notice.spaced')){if(notice.textContent.startsWith('Protótipo local:'))notice.textContent='Bocali conectado ao servidor. Pedidos confirmados aparecem nesta fila e podem ser enviados à Epson pelo Android.';}
 const note=$('.sidebar-note');if(note)note.innerHTML=ico('shield')+'<strong>Bocali conectado</strong>Contas, cardápios e pedidos sincronizados com o servidor.';
 const tag=$('.demo-tag');if(tag)tag.textContent='BETA 1.0';
 const footer=$('.page-footer span:last-child');if(footer)footer.textContent='Bocali 1.0 RC · acompanhe os pedidos pelo servidor.';
 const avatar=$('.avatar');if(avatar){avatar.href='#/conta';avatar.textContent=Net.user?Net.user.name.slice(0,1).toUpperCase():'Entrar';avatar.classList.add('account-avatar');avatar.setAttribute('aria-label','Minha conta');}
 const title=$('.topbar-title');if(view==='conta'&&title)title.textContent='Sua conta no Bocali';
 const main=$('#main');if(main){const strip=document.createElement('div');strip.className='connection-strip';strip.innerHTML=`<span id="sync-status" role="status"></span><span>${Net.user?esc(Net.user.name):'Visitante'} · ${Net.mode==='producao'?'online':'ambiente de desenvolvimento'}</span>`;main.prepend(strip);}
 updateConnection();
};
function accountView(){
 if(Net.user)return `<div class="page-heading"><div><div class="eyebrow muted">SUA CONTA</div><h1>Ol\u00e1, ${esc(Net.user.name.split(' ')[0])}.</h1><p>Seus favoritos e pedidos acompanham sua conta neste servidor.</p></div></div><div class="account-grid"><section class="panel"><h2>Seu acesso</h2><p class="muted">${esc(Net.user.email)}</p><div class="account-summary">${ico('shield')}<div><strong>${Net.managedStores.length?'Cliente e respons\u00e1vel por loja':'Conta de cliente'}</strong><p>Pedidos de outras pessoas n\u00e3o aparecem no seu hist\u00f3rico.</p></div></div><div class="toolbar"><a class="btn" href="#/${Net.managedStores.length?'painel':'explorar'}">${Net.managedStores.length?'Abrir painel da loja':'Escolher uma loja'}</a><button class="btn secondary" data-net="logout">Sair da conta</button></div></section><section class="panel"><h2>Segurança da conta</h2><p class="muted">Use uma senha exclusiva. Recuperação de senha por e-mail será a próxima camada antes da publicação ampla. Pagamentos online só aparecem quando o Mercado Pago estiver configurado no servidor.</p></section></div>`;
 const register=Net.authMode==='register',merchant=Net.registerMode==='merchant';
 return `<div class="account-grid auth-grid"><section class="account-story"><div class="eyebrow">UM ACESSO, SUAS LOJAS</div><h1>O pr\u00f3ximo pedido<br>come\u00e7a por aqui.</h1><p>Salve seus lugares favoritos. Pe\u00e7a novamente. Acompanhe o prazo confirmado pela loja.</p><div class="account-feature">${ico('heart')}<div><strong>Suas lojas, juntas.</strong><span>Favoritos guardados na sua conta.</span></div></div><div class="account-feature">${ico('order')}<div><strong>Do pedido ao balc\u00e3o.</strong><span>Cliente e atendente conectados ao mesmo servidor.</span></div></div><div class="account-feature">${ico('shield')}<div><strong>Cada loja, seu acesso.</strong><span>Controle de permiss\u00f5es verificado no servidor.</span></div></div><div class="story-label">BOCALI · SEUS SABORES, POR PERTO</div></section><section class="panel auth-panel"><div class="account-tabs"><button class="${!register?'active':''}" data-net="auth-mode" data-mode="login">Entrar</button><button class="${register?'active':''}" data-net="auth-mode" data-mode="register">Criar conta</button></div><h2>${register?'Seu primeiro acesso.':'Bem-vindo de volta.'}</h2><p class="muted small">${register?'Crie sua conta para pedir ou administrar seu estabelecimento.':'Acesse sua conta Bocali.'}</p><form id="account-form" class="spaced">${register?`<div class="account-role"><button type="button" class="chip ${!merchant?'active':''}" data-net="role" data-role="customer">Quero pedir</button><button type="button" class="chip ${merchant?'active':''}" data-net="role" data-role="merchant">Tenho uma loja</button></div><label class="field"><span>Seu nome</span><input name="name" maxlength="80" autocomplete="name" required></label>${merchant?'<label class="field"><span>Nome do estabelecimento</span><input name="storeName" maxlength="80" required></label><p class="small muted">Cria um estabelecimento separado, inicialmente pausado e pronto para receber seu cardápio.</p>':''}`:''}<label class="field"><span>E-mail</span><input name="email" type="email" autocomplete="username" maxlength="254" placeholder="voce@example.com" required></label><label class="field"><span>Senha ${register?'(pelo menos 12 caracteres)':''}</span><input name="password" type="password" autocomplete="${register?'new-password':'current-password'}" ${register?'minlength="12"':''} maxlength="128" required></label><div id="auth-error" class="auth-error" role="alert"></div><button class="btn full" type="submit">${register?'Criar conta':'Entrar no Bocali'} ${ico('arrow')}</button></form><p class="auth-footnote">${register?'N\u00e3o use senhas de bancos, e-mail ou outros aplicativos.':'A recupera\u00e7\u00e3o por e-mail ainda n\u00e3o foi implementada.'}</p><a class="text-link" href="#/explorar">Conhecer os card\u00e1pios sem entrar</a></section></div>`;
}
settingsView=function(){
 const native=nativePrinterAvailable();
 return `${adminHeading('Uma base conectada.','Configure sua loja e o aparelho que recebe os pedidos.')}<div class="settings-grid"><section class="panel"><h2>Dados da loja</h2><form id="store-settings-form"><label class="field"><span>Nome da loja</span><input name="name" value="${esc(adminShop().name)}" maxlength="80" required></label><label class="field"><span>Descrição</span><input name="description" value="${esc(adminShop().description)}" maxlength="240" required></label><label class="field"><span>Pedido mínimo (R$)</span><input name="minimum" value="${(adminShop().minimum/100).toFixed(2)}" inputmode="decimal" required></label><button class="btn" type="submit">Salvar no servidor</button></form></section><section class="panel"><h2>Aplicativo do balcão</h2><div class="info-box"><strong>${native?'Android conectado':'Navegador sem ponte nativa'}</strong><p>${native?'Este aparelho pode enviar comandas estruturadas para a Epson configurada no Bocali.':'No navegador comum, a impressão continua usando a janela do sistema. Para impressão direta, abra esta loja no aplicativo Android Bocali.'}</p></div>${native?'<button class="btn full" data-native-settings>Configurar Epson neste aparelho</button>':''}<div class="info-box"><strong>Pagamentos</strong><p>${Net.payments?.enabled?'Mercado Pago conectado: Pix por QR Code e cartão pelo checkout seguro disponíveis.':'Mercado Pago ainda não configurado no servidor. Dinheiro continua disponível.'}</p></div><div class="info-box"><strong>Mapa e cardápio</strong><p>O PDF pode montar um rascunho para revisão. Endereços reais dependem do provedor de geocodificação configurado.</p></div><a class="btn secondary" href="#/conta">Minha conta</a></section></div>`;
};
ordersView=function(){return oldOrdersView().replace('O prazo e o andamento s\u00e3o compartilhados apenas neste navegador. Nenhuma mensagem de WhatsApp ou notifica\u00e7\u00e3o real \u00e9 enviada.','Pedidos salvos na sua conta. Atualiza\u00e7\u00e3o a cada 4 segundos com esta p\u00e1gina aberta. Sem mensagens de WhatsApp.');};
render=function(){
 state.orders=isAdmin()?Net.merchantOrders:Net.customerOrders;
 if(view==='conta'){shell(accountView());return;}
 if((isAdmin()||view==='pedidos')&&!Net.user){shell(accountView());return;}
 if(isAdmin()&&!writable()){
  shell(`<div class="page-heading"><div><h1>Este acesso \u00e9 de cliente.</h1><p>O painel exige permiss\u00e3o para administrar uma loja.</p></div></div><div class="panel"><h2>As lojas permanecem separadas.</h2><p class="muted">Para administrar um estabelecimento, saia e crie uma conta do tipo "Tenho uma loja".</p><a href="#/conta" class="btn spaced">Abrir minha conta</a></div>`);return;
 }
 oldRender();
 if(view==='painel'){
  $$('[data-action="demo-order"]').forEach(el=>el.remove());
  const heading=$('.page-heading');if(heading){const p=document.createElement('div');p.className='notice green';p.style.marginBottom='20px';p.textContent='Pedidos confirmados pelos clientes chegam aqui automaticamente. Confira pagamento, itens e prazo antes de aceitar.';heading.after(p);}
 }
 if(view==='areas'){
  const notice=$('#main .notice');if(notice)notice.textContent='Desenhe as áreas reais de entrega da sua loja e defina a taxa de cada região. Pedidos fora da cobertura serão bloqueados pelo servidor.';
  if(!Net.demoAddresses)$$('[data-geo="sample"],[data-geo="checkout-sample"]').forEach(el=>el.remove());
 }
};
checkout=function(){
 if(!requireUser())return;oldCheckout();
 const firstNotice=$('#modal .notice');if(firstNotice)firstNotice.innerHTML='<strong>Confira entrega e pagamento</strong><p>O total final será recalculado pelo servidor antes do envio.</p>';
 const p=$('#modal .cart-caption');if(p)p.textContent='O servidor recalcula produtos, adicionais, taxa e total antes de criar o pedido.';
 const title=$('#modal h3.small.spaced:nth-of-type(2)');if(title)title.textContent='Pagamento';
 const card=$('input[name="payment"][value="card"]'),pix=$('input[name="payment"][value="pix"]'),cash=$('input[name="payment"][value="cash"]');
 if(card?.parentElement)card.parentElement.innerHTML='<input type="radio" name="payment" value="card">Cartão online <span class="option-detail">Checkout seguro Mercado Pago</span>';
 if(pix?.parentElement)pix.parentElement.innerHTML='<input type="radio" name="payment" value="pix">Pix online <span class="option-detail">QR Code / copia e cola</span>';
 const online=!!Net.payments?.enabled;
 $$('input[name="payment"]').forEach(input=>{if(input.value!=='cash')input.disabled=!online;});
 if(!online){checkoutPayment='cash';const c=$('input[name="payment"][value="cash"]');if(c)c.checked=true;const totals=$('#checkout-totals');if(totals){const n=document.createElement('div');n.className='notice';n.innerHTML='<strong>Pagamento online em configuração</strong><p>Pix e cartão serão liberados assim que a conta Mercado Pago do estabelecimento estiver conectada.</p>';totals.before(n);}}
 const note=$('#checkout-note')?.closest('label');if(note){const span=note.querySelector('span');if(span)span.textContent='Observação do pedido (opcional)';const ta=note.querySelector('textarea');if(ta)ta.placeholder='Ex.: sem cebola, molho separado.';}
 const button=$('#place-order');if(button)button.textContent='Continuar para conferir';
};
function orderPayload(){
 const payload={storeId:state.cart.storeId,items:state.cart.items.map(i=>({productId:i.productId,quantity:i.quantity,extraIds:i.extras.map(e=>e.id),note:i.note||''})),fulfillment:checkoutMode,payment:checkoutPayment,note:$('#checkout-note')?.value||''};
 if(checkoutMode==='delivery'){
  if(!geo.confirmed||D.addressKey(readAddress())!==geo.confirmed.addressKey)throw new Error('O endere\u00e7o mudou. Localize e confirme novamente.');
  const selected=geo.confirmed;payload.address=selected.address;
  if(selected.source==='demo'){
   const idx=[0,1,2,3].find(i=>D.addressKey({...selected.address,complement:''})===D.addressKey(D.sample(i).address));
   if(idx===undefined)throw new Error('Exemplo inv\u00e1lido. Localize novamente.');payload.sampleIndex=idx;
  }else payload.addressToken=selected.addressToken;
 }
 return payload;
}
placeOrder=async function(){
 if(!requireUser()||Net.busy)return;const b=$('#place-order');if(b)b.disabled=true;
 try{
  const payload=orderPayload(),result=await run(()=>api('/api/quote',payload));
  Net.pending={quoteId:result.quoteId,idempotencyKey:crypto.randomUUID?.()||C.uid()+C.uid()};const o=result.order;
  openModal('Confira antes de enviar',`<div class="notice green">Valores calculados pelo servidor. Nenhum pedido foi enviado ainda.</div><h3 class="spaced">${esc(o.storeName)}</h3><div class="order-body">${o.items.map(i=>`<div><span>${i.quantity}\u00d7 ${esc(i.name)}${i.extras.length?'<br><small>+ '+i.extras.map(e=>esc(e.name)).join(', ')+'</small>':''}</span><strong>${brl((i.unitPrice+i.extras.reduce((s,e)=>s+e.price,0))*i.quantity)}</strong></div>`).join('')}</div>${o.delivery?'<p class="small muted">'+esc(D.formatAddress(o.delivery.address))+'</p>':'<p class="small muted">Retirada no balc\u00e3o.</p>'}<div class="amount-row"><span>Produtos</span><strong>${brl(o.subtotal)}</strong></div><div class="amount-row"><span>Entrega</span><strong>${brl(o.fee)}</strong></div><div class="amount-row total"><span>Total</span><strong>${brl(o.total)}</strong></div><div id="confirm-order-error" role="alert" class="auth-error"></div><button class="btn full spaced" data-net="confirm-order">Confirmar pedido</button><p class="cart-caption">Resumo válido por até 10 minutos. Para Pix/cartão, o pedido só entra na fila da loja depois da aprovação do pagamento.</p>`);
 }catch(e){toast(e.message);if(b?.isConnected)b.disabled=false;}
};
async function submitServerOrder(button){
 if(!Net.pending||Net.busy)return;button.disabled=true;
 try{
  const result=await run(()=>api('/api/orders',Net.pending));const o=result.order;
  Net.pending=null;state.cart={storeId:null,items:[]};rememberCart();render();
  if(o.payment==='cash'){
   openModal('Pedido enviado',`<div class="success"><div class="success-mark">${ico('check')}</div><h2>${esc(o.id)}</h2><p>${esc(o.storeName)}<br>Total: <strong>${brl(o.total)}</strong></p><div class="notice green">Pedido enviado para a loja. Pagamento em dinheiro na entrega/retirada.</div><button class="btn full spaced" data-action="goto-orders">Acompanhar meu pedido</button></div>`);return;
  }
  await openOnlinePayment(o);
 }catch(e){const el=$('#confirm-order-error');if(el)el.textContent=e.message;if(e.status===409){Net.pending=null;button.textContent='Voltar para conferir';button.dataset.net='retry-checkout';}if(button.isConnected)button.disabled=false;}
}

function paymentOrder(id){return Net.customerOrders.find(o=>o.id===id)||state.orders.find(o=>o.id===id);}
function showPixResult(order,payment){
 Net.lastPixCode=payment.qr_code||'';
 openModal('Pix gerado',`<div class="notice green"><strong>${esc(order.id)} · ${brl(order.total)}</strong><p>Após o pagamento, o Mercado Pago confirma automaticamente e só então o pedido entra na fila da loja.</p></div>${payment.qr_code_base64?`<img alt="QR Code Pix" style="display:block;max-width:260px;width:100%;margin:20px auto" src="data:image/png;base64,${payment.qr_code_base64}">`:''}<label class="field"><span>Pix copia e cola</span><textarea id="pix-code" readonly style="min-height:120px">${esc(payment.qr_code||'')}</textarea></label><button class="btn full" data-net="copy-pix">Copiar código Pix</button><a class="btn secondary full spaced" href="#/pedidos" data-action="close-modal">Acompanhar pedido</a>`);
}
function openPixForm(order){
 openModal('Pagar com Pix',`<div class="notice green"><strong>${esc(order.id)}</strong><p>${esc(order.storeName)} · ${brl(order.total)}</p></div><form id="pix-payment-form" data-order-id="${esc(order.id)}" class="spaced"><label class="field"><span>E-mail do pagador</span><input name="email" type="email" value="${esc(Net.user?.email||'')}" autocomplete="email" required></label><label class="field"><span>CPF do pagador</span><input name="cpf" inputmode="numeric" autocomplete="off" maxlength="14" placeholder="Somente números" required></label><div id="payment-error" class="auth-error" role="alert"></div><button class="btn full" type="submit">Gerar Pix seguro</button></form><p class="small muted spaced">O valor vem do pedido calculado pelo servidor. O Bocali não aceita um valor digitado pelo celular.</p>`);
}
async function submitPixPayment(form){
 const button=form.querySelector('[type="submit"]');if(button)button.disabled=true;
 const order=paymentOrder(form.dataset.orderId);const out=$('#payment-error');
 try{
  if(!order)throw new Error('Pedido não encontrado.');
  const data=Object.fromEntries(new FormData(form));const cpf=String(data.cpf||'').replace(/\D/g,'');
  if(cpf.length!==11)throw new Error('Informe um CPF com 11 dígitos.');
  const idem=crypto.randomUUID?.()||C.uid()+C.uid();
  const result=await api('/api/payment',{orderId:order.id,idempotencyKey:idem,formData:{payment_method_id:'pix',payer:{email:String(data.email||'').trim(),identification:{type:'CPF',number:cpf}}}});
  await refresh(true);const payment=result.payment||{};
  if(payment.status==='approved'){
   openModal('Pagamento aprovado',`<div class="success"><div class="success-mark">${ico('check')}</div><h2>${esc(order.id)}</h2><p>Pagamento aprovado. O pedido já foi enviado para a loja.</p><button class="btn full spaced" data-action="goto-orders">Acompanhar pedido</button></div>`);return;
  }
  if(payment.qr_code){showPixResult(order,payment);return;}
  if(payment.status==='rejected')throw new Error('Pagamento recusado. Gere um novo Pix ou escolha outro meio de pagamento.');
  openModal('Pagamento em processamento',`<div class="notice"><strong>${esc(order.id)}</strong><p>O Mercado Pago está processando o pagamento. O pedido será liberado para a loja somente após a confirmação.</p></div><button class="btn full spaced" data-action="goto-orders">Acompanhar pedido</button>`);
 }catch(err){if(out)out.textContent=err.message||'Não foi possível gerar o Pix.';if(button?.isConnected)button.disabled=false;}
}
async function openCardCheckout(order){
 if(!order)throw new Error('Pedido não encontrado.');
 openModal('Pagamento com cartão',`<div class="notice green"><strong>${esc(order.id)}</strong><p>${esc(order.storeName)} · ${brl(order.total)}</p></div><p>O cartão será preenchido no checkout oficial do Mercado Pago. No Android, ele abre em uma aba segura fora do WebView e retorna ao Bocali ao terminar.</p><div id="payment-error" class="auth-error" role="alert"></div><div class="loader"></div>`);
 try{
  const native=typeof window.__BOCALI_NATIVE_KEY==='string'&&window.__BOCALI_NATIVE_KEY&&window.BocaliPrinter&&typeof window.BocaliPrinter.openPayment==='function';
  const result=await api('/api/card-checkout',{orderId:order.id,returnMode:native?'android':'web'});
  const url=result.checkoutUrl;if(!url)throw new Error('Checkout do cartão indisponível.');
  if(native){nativeCall('openPayment',url);closeModal();toast('Pagamento aberto no Mercado Pago. Volte ao Bocali após concluir.');}
  else window.location.assign(url);
 }catch(err){const out=$('#payment-error');if(out)out.textContent=err.message||'Não foi possível abrir o pagamento com cartão.';else throw err;}
}
async function openOnlinePayment(order){
 if(!order)throw new Error('Pedido não encontrado.');
 if(order.paymentStatus==='approved'){location.hash='#/pedidos';render();return toast('Este pedido já está pago.');}
 if(order.payment==='pix')return openPixForm(order);
 if(order.payment==='card')return openCardCheckout(order);
 throw new Error('Este pedido não usa pagamento online.');
}

async function orderAction(id,values){
 const o=myOrder(id);if(!o)throw new Error('Pedido indispon\u00edvel. Atualize a fila.');
 return run(()=>api('/api/order-action',{orderId:id,expectedRevision:o.revision,...values}));
}
function nativePrinterAvailable(){return !!(window.__BOCALI_NATIVE_KEY&&window.BocaliPrinter&&typeof window.BocaliPrinter.submitTicket==='function');}
function nativeCall(method,...args){
 if(!nativePrinterAvailable())throw new Error('A impressão direta exige o aplicativo Android Bocali.');
 let raw;try{raw=window.BocaliPrinter[method](window.__BOCALI_NATIVE_KEY,...args);}catch(e){throw new Error(e?.message||'Falha na ponte Android.');}
 let parsed;try{parsed=JSON.parse(raw);}catch{throw new Error('Resposta inválida do módulo de impressão.');}
 if(!parsed.ok)throw new Error(parsed.error||'Não foi possível concluir na impressora.');return parsed.data;
}
function nativeTicket(o,kind,job){return BocaliNativeTicket.fromOrder(o,kind,job);}
function nativeJobFor(serverJobId){
 if(!nativePrinterAvailable())return null;const state=nativeCall('getState');return (state.jobs||[]).find(j=>j.serverJobId===serverJobId)||null;
}
window.BocaliNativeChanged=()=>window.dispatchEvent(new Event('bocali-native-change'));
acceptFromForm=async function(form){
 if(Net.busy)return;const button=$('#confirm-accept'),id=form.dataset.id,shouldPrint=$('#accept-print').checked;
 button.disabled=true;
 try{await orderAction(id,{action:'accept',min:Number($('#eta-min').value),max:Number($('#eta-max').value)});closeModal();render();if(shouldPrint)await printOrder(id,'kitchen');else toast('Pedido aceito no servidor. Comanda disponível para imprimir.');}
 catch(e){toast(e.message);if(button.isConnected)button.disabled=false;}
};
showReceipt=function(id,kind='kitchen',jobId=null){
 oldShowReceipt(id,kind,jobId);
 if(!nativePrinterAvailable()||!jobId)return;
 const controls=$('#modal .receipt-controls');if(!controls)return;
 let nativeJob=null;try{nativeJob=nativeJobFor(jobId);}catch{}
 const state=nativeJob?.state||'QUEUED';const labels={QUEUED:'Aguardando envio pelo Android',SENDING:'Enviando para a Epson',NOT_SENT:'Não enviada',UNCERTAIN:'Resultado incerto: confira o papel',SENT_UNCONFIRMED:'Dados enviados: confira o papel',CONFIRMED_BY_OPERATOR:'Saída confirmada',FAILED_BY_OPERATOR:'Marcada como não impressa'};
 const note=document.createElement('div');note.className='notice '+(['NOT_SENT','UNCERTAIN'].includes(state)?'':'green');note.innerHTML='<strong>Impressão direta pelo Android</strong><p>'+esc(labels[state]||state)+'. O servidor e o celular mantêm registros separados para reduzir duplicidade.</p>';
 controls.prepend(note);
 controls.querySelectorAll('p.small.muted').forEach(p=>p.textContent='Epson TM-T20X pela rede local. Confira fisicamente o papel antes de confirmar ou reimprimir.');
};
printOrder=async function(id,kind='kitchen'){
 try{
  const previous=myOrder(id)?.printJobs?.filter(j=>j.kind===kind)||[];
  if(previous.length&&!confirm('Reimprimir esta via? Confira para não duplicar o preparo.'))return;
  const result=await orderAction(id,{action:'print',kind,paper:printerPrefs().paper});const o=result.order,job=[...(o.printJobs||[])].reverse().find(j=>j.kind===kind&&j.status==='requested');
  if(!job)throw new Error('A tentativa de impressão não foi criada.');
  if(nativePrinterAvailable()){
   try{nativeCall('submitTicket',JSON.stringify(nativeTicket(o,kind,job)));render();showReceipt(id,kind,job.id);toast('Comanda enviada ao módulo Android. Confira a Epson antes de confirmar.');}
   catch(e){try{await orderAction(id,{action:'print-result',jobId:job.id,success:false});}catch{}render();throw e;}
   return;
  }
  render();showReceipt(id,kind,job.id);let root=$('#print-root');if(!root){root=document.createElement('div');root.id='print-root';document.body.append(root);}root.innerHTML=ticketHTML(o,kind,job.paper,job);root.style.width=job.paper+'mm';document.body.classList.add('receipt-print-active');window.print();
 }catch(e){toast(e.message);}
};
confirmPrint=async function(id,jobId,success){
 try{
  if(nativePrinterAvailable()){
   const nativeJob=nativeJobFor(jobId);if(nativeJob)nativeCall('confirmPaper',nativeJob.id,success);
  }
  const r=await orderAction(id,{action:'print-result',jobId,success});const j=r.order.printJobs.find(j=>j.id===jobId);render();showReceipt(id,j.kind,jobId);toast(success?'Saída confirmada no celular e no servidor.':'Tentativa marcada como não impressa.');
 }catch(e){toast(e.message);}
};
printerHelp=function(){
 if(nativePrinterAvailable())return openModal('Impressora da cozinha',`<div class="info-box"><strong>Epson conectada pelo aplicativo Android</strong><p>Use a tela nativa para conferir IP, estado e histórico local de impressão. O pedido continua salvo no servidor.</p></div><button class="btn full" data-native-settings>Configurar Epson neste aparelho</button><div class="notice spaced">Antes de reimprimir, confira a via anterior para não duplicar o preparo.</div>`);
 return oldPrinterHelp();
};
createDemoOrder=function(){toast('Use outra conta de cliente para testar a chegada do pedido pelo servidor.');};
publishDraft=async function(){
 if(!draft.length||!draft.every(C.validDraft)||Net.busy)return toast('Confira todas as linhas antes de publicar.');
 const p=catalogPayload();let added=0;
 for(const d of draft){if(p.products.some(x=>C.norm(x.name)===C.norm(d.name)))continue;p.products.push({id:C.uid(),storeId:p.storeId,name:d.name.trim(),description:d.description.trim(),category:d.category.trim(),price:d.price,available:true,art:'pastel',extras:[]});added++;}
 try{await run(()=>api('/api/catalog',p));draft=[];rawText='';render();toast(added+' produto(s) salvo(s) no servidor. Nomes j\u00e1 cadastrados foram preservados.');}catch(e){toast(e.message);}
};
// Attach authenticated headers to the two legacy fetch calls (PDF and geocoding).
const nativeFetch=window.fetch.bind(window);
window.fetch=function(input,options){
 const path=typeof input==='string'?input:'';
 if(['/api/import-pdf','/api/geocode'].includes(path)&&options?.method==='POST')options={...options,headers:{...options.headers,'X-Bocali-Request':'1','X-CSRF-Token':Net.csrf||''},credentials:'same-origin'};
 return nativeFetch(input,options);
};
document.addEventListener('click',e=>{
 const b=e.target.closest('[data-net]');if(b){e.preventDefault();e.stopImmediatePropagation();
  if(Net.busy)return;
  if(b.dataset.net==='auth-mode'){Net.authMode=b.dataset.mode;render();}
  else if(b.dataset.net==='role'){Net.registerMode=b.dataset.role;render();}
  else if(b.dataset.net==='confirm-order')submitServerOrder(b);
  else if(b.dataset.net==='retry-checkout'){closeModal();checkout();}
  else if(b.dataset.net==='pay-order'){const o=paymentOrder(b.dataset.id);openOnlinePayment(o).catch(err=>toast(err.message));}
  else if(b.dataset.net==='copy-pix'){const code=Net.lastPixCode||$('#pix-code')?.value||'';navigator.clipboard?.writeText(code).then(()=>toast('Código Pix copiado.')).catch(()=>toast('Selecione e copie o código Pix.'));}
  else if(b.dataset.net==='logout'){run(()=>api('/api/logout',{})).then(()=>{forgetPrivate();closeModal();location.hash='#/conta';render();}).catch(err=>toast(err.message));}
  return;
 }
 const geoButton=e.target.closest('[data-geo]');if(Net.busy&&geoButton){e.preventDefault();e.stopImmediatePropagation();return;}
 const action=e.target.closest('[data-action]');if(!action)return;
 const a=action.dataset.action;
 const mutating=['favorite','status','toggle-store','toggle-product','publish','reset','place-order','accept-order','print-order','print-result','demo-order'];
 if(Net.busy&&a!=='close-modal'){e.preventDefault();e.stopImmediatePropagation();return;}
 if(a==='favorite'){
  e.preventDefault();e.stopImmediatePropagation();if(!requireUser())return;
  run(()=>api('/api/favorites',{storeId:action.dataset.id,saved:!state.favorites.includes(action.dataset.id)})).then(()=>render()).catch(err=>toast(err.message));
 }else if(a==='status'){
  e.preventDefault();e.stopImmediatePropagation();const to=action.dataset.to,id=action.dataset.id;let reason='';
  if(to==='cancelled'){reason=prompt('Informe o motivo. Se o pedido foi pago online, o Bocali solicitará o estorno antes de concluir o cancelamento.');if(!reason?.trim())return;}
  orderAction(id,{action:'status',to,reason}).then(()=>{render();toast(to==='cancelled'?'Pedido cancelado. Avise a cozinha.':'Etapa atualizada no servidor.');}).catch(err=>toast(err.message));
 }else if(a==='reset'){e.preventDefault();e.stopImmediatePropagation();toast('O banco n\u00e3o pode ser apagado pelo navegador.');}
},true);
document.addEventListener('submit',async e=>{
 if(Net.busy){e.preventDefault();e.stopImmediatePropagation();return;}
 if(e.target.id==='account-form'){
  e.preventDefault();e.stopImmediatePropagation();const form=e.target,button=form.querySelector('[type="submit"]'),data=Object.fromEntries(new FormData(form));button.disabled=true;
  try{const creatingMerchant=Net.authMode==='register'&&Net.registerMode==='merchant';await run(()=>api(Net.authMode==='register'?'/api/register':'/api/login',{...data,mode:Net.registerMode}));closeModal();const ownedProducts=state.products.filter(p=>Net.managedStores.includes(p.storeId));location.hash='#/'+(creatingMerchant||Net.managedStores.length&&!ownedProducts.length?'importar':Net.managedStores.length?'painel':'minhas-lojas');render();}
  catch(err){const out=$('#auth-error');if(out)out.textContent=err.message;if(button.isConnected)button.disabled=false;}
 }else if(e.target.id==='pix-payment-form'){
  e.preventDefault();e.stopImmediatePropagation();await submitPixPayment(e.target);
 }else if(e.target.id==='store-settings-form'){
  e.preventDefault();e.stopImmediatePropagation();const data=Object.fromEntries(new FormData(e.target));const raw=data.minimum.trim(),minimum=/^0([,.]0{1,2})?$/.test(raw)?0:C.moneyToCents(raw);if(minimum===null)return toast('Confira o pedido m\u00ednimo.');Object.assign(adminShop(),{name:data.name,description:data.description,minimum});save();
 }
},true);
// Prevent concurrent local edits from being silently dropped by the save adapter.
document.addEventListener('change',e=>{if(Net.busy&&['printer-width','auto-print','admin-select'].includes(e.target.id)){e.preventDefault();e.stopImmediatePropagation();render();}},true);
document.addEventListener('click',e=>{const b=e.target.closest('[data-native-settings]');if(!b)return;e.preventDefault();if(nativePrinterAvailable()&&typeof window.BocaliPrinter.settings==='function')window.BocaliPrinter.settings(window.__BOCALI_NATIVE_KEY);});
window.addEventListener('bocali-native-change',()=>{if(currentReceipt?.jobId&&nativePrinterAvailable())showReceipt(currentReceipt.id,currentReceipt.kind,currentReceipt.jobId);});
applyRemote(window.PedeBootstrap);
try{const x=JSON.parse(sessionStorage.getItem(cartKey()));if(x&&Array.isArray(x.items))state.cart=x;}catch{}
render();
setInterval(()=>{if(!document.hidden&&!Net.busy&&!Net.saving&&!geo.edit&&!draft.length)refresh().catch(()=>updateConnection());},4000);
window.addEventListener('focus',()=>{if(!Net.busy&&!geo.edit&&!draft.length)refresh().catch(()=>updateConnection());});
