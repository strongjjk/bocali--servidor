/* Bocali 0.8 - Pure, integer-cent domain logic. No payment processing. */
(function(root){
'use strict';
const uid = () => 'i'+Date.now().toString(36)+Math.random().toString(36).slice(2,8);
const norm = s => String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().toLowerCase();
function moneyToCents(value){
 let s=String(value??'').trim().replace(/R\$\s*/gi,'').replace(/\s/g,'');
 if(!s) return null;
 if (/^\d{1,3}(\.\d{3})*,\d{2}$/.test(s)) s=s.replace(/\./g,'').replace(',','.');
 else if(/^\d+,\d{1,2}$/.test(s)) s=s.replace(',','.');
 else if(!/^\d+(\.\d{1,2})?$/.test(s)) return null;
 const n=Math.round(Number(s)*100);
 return Number.isSafeInteger(n)&&n>0&&n<=10000000?n:null;
}
function seed(){
 const stores=[
 {id:'cantinho',name:'Cantinho do Pastel',initials:'CP',type:'Pastelaria',tag:'Seu estabelecimento piloto',description:'Escolha seu sabor, personalize e acompanhe seu pedido.',tone:'peach',open:true,fee:500,eta:'35 a 50 min',minimum:1000},
 {id:'forno',name:'Forno da Vila',initials:'FV',type:'Pizzaria',tag:'Estabelecimento fict\u00edcio',description:'Pizzas e bons encontros, no mesmo lugar.',tone:'sage',open:true,fee:700,eta:'40 a 60 min',minimum:2000},
 {id:'acai',name:'A\u00e7a\u00ed da Pra\u00e7a',initials:'AP',type:'A\u00e7a\u00ed e sorvetes',tag:'Estabelecimento fict\u00edcio',description:'Uma pausa geladinha no seu dia.',tone:'lilac',open:true,fee:400,eta:'25 a 40 min',minimum:1200}
 ];
 const rows=[
 ['cantinho','Pastel de carne','Carne mo\u00edda e azeitona. Descri\u00e7\u00e3o de exemplo.','Cl\u00e1ssicos',1490,'pastel'],
 ['cantinho','Pastel de queijo','Queijo derretido. Descri\u00e7\u00e3o de exemplo.','Cl\u00e1ssicos',1490,'pastel'],
 ['cantinho','Pastel de pizza','Mu\u00e7arela, presunto, tomate e or\u00e9gano. Exemplo.','Cl\u00e1ssicos',1690,'pastel'],
 ['cantinho','Frango com requeij\u00e3o','Recheio de frango com requeij\u00e3o. Exemplo.','Especiais',1790,'pastel'],
 ['cantinho','Costela desfiada','Costela desfiada com queijo. Descri\u00e7\u00e3o de exemplo.','Especiais',2290,'pastel'],
 ['cantinho','Kinder Bueno','Pastel doce. Descri\u00e7\u00e3o de exemplo.','Doces',2090,'sweet'],
 ['cantinho','Refrigerante 600 ml','Bebida gelada. Marca a definir.','Bebidas',800,'drink'],
 ['cantinho','\u00c1gua mineral 500 ml','Sem g\u00e1s.','Bebidas',400,'drink'],
 ['forno','Pizza de mu\u00e7arela','Pizza grande. Produto fict\u00edcio.','Pizzas',4990,'pizza'],
 ['forno','Pizza de calabresa','Pizza grande. Produto fict\u00edcio.','Pizzas',5290,'pizza'],
 ['acai','A\u00e7a\u00ed 500 ml','Por\u00e7\u00e3o de a\u00e7a\u00ed. Produto fict\u00edcio.','A\u00e7a\u00ed',1990,'acai'],
 ['acai','A\u00e7a\u00ed 300 ml','Por\u00e7\u00e3o de a\u00e7a\u00ed. Produto fict\u00edcio.','A\u00e7a\u00ed',1490,'acai']
 ];
 return {version:1,stores,products:rows.map((r,i)=>({id:'p'+i,storeId:r[0],name:r[1],description:r[2],category:r[3],price:r[4],art:r[5],available:true,extras:r[5]==='pastel'?[{id:'cheese',name:'Queijo extra',price:300},{id:'bacon',name:'Bacon',price:400}]:[]})),favorites:['cantinho','forno'],orders:[],cart:{storeId:null,items:[]},nextOrder:1,adminStore:'cantinho'};
}
function totals(cart,fee=0){
 const subtotal=cart.items.reduce((sum,i)=>sum+(i.unitPrice+i.extras.reduce((s,e)=>s+e.price,0))*i.quantity,0);
 return {subtotal,fee:cart.items.length?fee:0,total:subtotal+(cart.items.length?fee:0),quantity:cart.items.reduce((s,i)=>s+i.quantity,0)};
}
function parseMenu(text){
 const lines=String(text||'').split(/\r?\n/).map(s=>s.replace(/\u00a0/g,' ').replace(/\s{2,}/g,' ').trim()).filter(Boolean);
 const items=[],warnings=[],categories=[];let category='Importados',categorySeen=false;
 const known=/^(past[eé]is|cl[aá]ssicos|especiais|bebidas|doces|salgados|pizzas|por[cç][oõ]es|a[cç]a[ií]|combos|lanches|sobremesas|sucos|caldos|massas|pratos|adicionais|extras|promo[cç][oõ]es|executivos|hamb[uú]rgueres|hot dog|cachorro quente|cervejas|refrigerantes|drinks|caf[eé]s)\b/i;
 const heading=line=>{if(line.length<2||line.length>48||/(?:R\$\s*)?\d+[,.]\d{1,2}/i.test(line))return false;if(known.test(line))return true;const letters=[...line].filter(c=>/[A-Za-zÀ-ÿ]/.test(c));if(letters.length<2)return false;return letters.filter(c=>c===c.toUpperCase()).length/letters.length>=.82&&line.split(/\s+/).length<=6;};
 for(let ix=0;ix<lines.length;ix++){
  const line=lines[ix];
  if(heading(line)){category=line.replace(/:$/,'').slice(0,50);categorySeen=true;if(!categories.includes(category))categories.push(category);continue;}
  const prices=[...line.matchAll(/(?:R\$\s*(?:\d{1,4}(?:\.\d{3})*(?:[,.]\d{1,2})?)|\d{1,4}(?:\.\d{3})*[,.]\d{2})(?!\d)/gi)].map(m=>({m,value:moneyToCents(m[0])})).filter(x=>x.value!==null);
  if(!prices.length)continue;
  let name=line.slice(0,prices[0].m.index).replace(/[.\s\-–—:|]+$/g,'').replace(/^[•\-–—\s]+/,'').trim();
  if(name.length<2){warnings.push('Linha '+(ix+1)+': havia preço, mas faltou um nome claro antes dele.');continue;}
  const multiple=prices.length>1;
  items.push({id:uid(),name:name.slice(0,100),description:'',category,price:multiple?null:prices[0].value,source:line.slice(0,300),reviewed:false,selected:true,ambiguous:multiple,confidence:multiple?'low':(categorySeen?'high':'medium'),priceOptions:prices.slice(0,8).map(x=>x.value),line:ix+1});
  if(multiple)warnings.push('Linha '+(ix+1)+': mais de um preço em "'+name+'". Escolha o tamanho/valor correto antes de publicar.');
  if(items.length>=250){warnings.push('Limite de 250 produtos por lote. Divida o cardápio em mais de uma importação.');break;}
 }
 if(!items.length)warnings.push('Nenhum produto com nome e preço reconhecido. Confira o texto ou cadastre manualmente.');
 else warnings.push('Rascunho montado pelo Bocali. Nada é publicado automaticamente: confira o PDF completo antes de salvar.');
 return {items,warnings,categories,summary:{items:items.length,highConfidence:items.filter(i=>i.confidence==='high').length,mediumConfidence:items.filter(i=>i.confidence==='medium').length,lowConfidence:items.filter(i=>i.confidence==='low').length,ambiguous:items.filter(i=>i.ambiguous).length}};
}
function validDraft(item){return !!item.name.trim()&&!!item.category.trim()&&Number.isInteger(item.price)&&item.price>0&&item.price<=10000000&&item.reviewed;}
const transitions={new:['accepted','cancelled'],accepted:['preparing','cancelled'],preparing:['ready','cancelled'],ready:['dispatched','completed','cancelled'],dispatched:['completed','cancelled'],completed:[],cancelled:[]};
function transition(order,to){
 if(to==='accepted'&&!order.eta)throw new Error('Defina o prazo antes de aceitar o pedido.');
 if(to==='dispatched'&&order.fulfillment!=='delivery')throw new Error('Retirada n\u00e3o sai para entrega.');
 if(order.status==='ready'&&to==='completed'&&order.fulfillment==='delivery')throw new Error('Marque a sa\u00edda para entrega antes de concluir.');
 if(!transitions[order.status]?.includes(to))throw new Error('Transi\u00e7\u00e3o de pedido inv\u00e1lida.');order.status=to;order.events.push({status:to,at:new Date().toISOString()});return order;}
function validateCart(state){
 const shop=state.stores.find(s=>s.id===state.cart.storeId);
 if(!shop||!shop.open)throw new Error('A loja est\u00e1 pausada.');
 if(!state.cart.items.length)throw new Error('Sua sacola est\u00e1 vazia.');
 for(const item of state.cart.items){
  const p=state.products.find(p=>p.id===item.productId&&p.storeId===shop.id);
  if(!p||!p.available)throw new Error(item.name+' n\u00e3o est\u00e1 dispon\u00edvel. Remova da sacola.');
  if(p.price!==item.unitPrice)throw new Error('O pre\u00e7o de '+p.name+' mudou. Remova e adicione novamente.');
  if(!Number.isInteger(item.quantity)||item.quantity<1||item.quantity>20)throw new Error('Quantidade inv\u00e1lida.');
  for(const e of item.extras){if(!p.extras.some(x=>x.id===e.id&&x.price===e.price))throw new Error('Um adicional mudou. Adicione o produto novamente.');}
 }
 if(totals(state.cart).subtotal<shop.minimum)throw new Error('O pedido est\u00e1 abaixo do m\u00ednimo da loja.');
 return shop;
}
function createOrder(state,{fulfillment,payment,note='',delivery=null}){
 const shop=validateCart(state);
 if(!['delivery','pickup'].includes(fulfillment)||!['cash','pix','card'].includes(payment))throw new Error('Op\u00e7\u00e3o inv\u00e1lida.');
 const engine=root.PedeDelivery||(typeof require==='function'?require('./delivery.js'):null);
 let checkedDelivery=null;
 if(fulfillment==='delivery'&&shop.deliveryConfig){if(!engine)throw new Error('Motor de entrega indisponivel.');checkedDelivery=engine.validateDelivery(shop,delivery);}
 const now=new Date().toISOString();const total=totals(state.cart,fulfillment==='delivery'?(checkedDelivery?checkedDelivery.quote.fee:shop.fee):0);
 const order={id:'PED-'+String(state.nextOrder++).padStart(4,'0'),storeId:shop.id,storeName:shop.name,items:JSON.parse(JSON.stringify(state.cart.items)),...total,delivery:checkedDelivery,fulfillment,payment,paymentStatus:'simulated',note:String(note).slice(0,200),status:'new',createdAt:now,events:[{status:'new',at:now}],demo:true};
 state.orders.unshift(order);state.cart={storeId:null,items:[]};return order;
}
const api={uid,norm,moneyToCents,seed,totals,parseMenu,validDraft,transition,transitions,createOrder,validateCart};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PedeCore=api;
})(typeof window!=='undefined'?window:globalThis);
