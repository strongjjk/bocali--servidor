/* Bocali 0.3: independent delivery-area engine. Coordinates use [longitude, latitude]. */
(function(root){
'use strict';
const clone=x=>JSON.parse(JSON.stringify(x));
const normalize=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim().toLowerCase().replace(/\s+/g,' ');
const fields=['street','number','neighborhood','city','state','postcode','complement'];
function addressKey(a){return fields.map(k=>normalize(a?.[k])).join('|');}
function formatAddress(a){if(!a)return '';return [a.street+', '+a.number,a.complement,a.neighborhood,a.city+' / '+a.state,a.postcode].filter(Boolean).join(' - ');}
function validPoint(p){return !!p&&typeof p.lng==='number'&&typeof p.lat==='number'&&Number.isFinite(p.lng)&&Number.isFinite(p.lat)&&Math.abs(p.lng)<=180&&Math.abs(p.lat)<=85;}
function validAddress(a){return !!a&&['street','number','neighborhood','city','state'].every(k=>typeof a[k]==='string'&&a[k].trim().length>0&&a[k].length<=120)&&/^[A-Za-z]{2}$/.test(a.state)&&(!a.postcode||/^\d{5}-?\d{3}$/.test(a.postcode));}
function onSegment(p,a,b){const cross=(p[0]-a[0])*(b[1]-a[1])-(p[1]-a[1])*(b[0]-a[0]);return Math.abs(cross)<1e-12&&p[0]>=Math.min(a[0],b[0])-1e-10&&p[0]<=Math.max(a[0],b[0])+1e-10&&p[1]>=Math.min(a[1],b[1])-1e-10&&p[1]<=Math.max(a[1],b[1])+1e-10;}
function inRing(point,ring){if(!validPoint(point)||!Array.isArray(ring)||ring.length<3)return false;const p=[point.lng,point.lat];let inside=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){const a=ring[i],b=ring[j];if(onSegment(p,a,b))return true;if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])inside=!inside;}return inside;}
function orientation(a,b,c){return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);}
function intersects(a,b,c,d){const u=orientation(a,b,c),v=orientation(a,b,d),w=orientation(c,d,a),x=orientation(c,d,b);if(u*v<0&&w*x<0)return true;return Math.abs(u)<1e-12&&onSegment(c,a,b)||Math.abs(v)<1e-12&&onSegment(d,a,b)||Math.abs(w)<1e-12&&onSegment(a,c,d)||Math.abs(x)<1e-12&&onSegment(b,c,d);}
function validateZone(z,storeId){
 if(!z||z.storeId!==storeId)throw new Error('A \u00e1rea deve pertencer a esta loja.');
 if(typeof z.name!=='string'||!z.name.trim()||z.name.length>60)throw new Error('Informe um nome de at\u00e9 60 caracteres.');
 if(!['delivery','blocked'].includes(z.kind))throw new Error('Tipo de \u00e1rea inv\u00e1lido.');
 if(!Number.isInteger(z.fee)||z.fee<0||z.fee>100000)throw new Error('Taxa inv\u00e1lida. Use de R$ 0 a R$ 1.000.');
 if(!Number.isInteger(z.priority)||z.priority<0||z.priority>999)throw new Error('Prioridade deve ser um inteiro entre 0 e 999.');
 if(!Array.isArray(z.ring)||z.ring.length<3||z.ring.length>100||!z.ring.every(p=>Array.isArray(p)&&p.length===2&&validPoint({lng:p[0],lat:p[1]})))throw new Error('Desenhe uma \u00e1rea com 3 a 100 pontos v\u00e1lidos.');
 const r=z.ring,n=r.length;let area=0;
 for(let i=0;i<n;i++){const j=(i+1)%n;area+=r[i][0]*r[j][1]-r[j][0]*r[i][1];if(r[i][0]===r[j][0]&&r[i][1]===r[j][1])throw new Error('Remova pontos repetidos.');for(let k=i+1;k<n;k++){const l=(k+1)%n;if(i===k||j===k||l===i)continue;if(intersects(r[i],r[j],r[k],r[l]))throw new Error('O desenho cruza a si mesmo. Redesenhe o contorno.');}}
 if(Math.abs(area)<1e-10)throw new Error('A \u00e1rea precisa ter superf\u00edcie; os pontos n\u00e3o podem ficar em uma linha.');return true;
}
function defaultConfig(storeId,index=0){
 const make=(id,name,fee,priority,ring)=>({id:storeId+'-'+id,storeId,name,fee:fee+index*100,priority,ring,kind:'delivery',active:true});
 return {schema:1,revision:1,city:'Pindamonhangaba',state:'SP',reference:{lng:-45.461,lat:-22.925},zones:[
 make('a','\u00c1rea A - exemplo',500,30,[[-45.471,-22.921],[-45.463,-22.917],[-45.453,-22.923],[-45.457,-22.932],[-45.469,-22.932]]),
 make('b','\u00c1rea B - exemplo',800,20,[[-45.483,-22.921],[-45.479,-22.909],[-45.458,-22.908],[-45.439,-22.916],[-45.441,-22.937],[-45.465,-22.943],[-45.482,-22.934]]),
 make('c','\u00c1rea C - exemplo',1200,10,[[-45.497,-22.921],[-45.489,-22.900],[-45.46,-22.898],[-45.425,-22.912],[-45.427,-22.941],[-45.449,-22.952],[-45.479,-22.950],[-45.495,-22.938]])]};
}
function migrate(state){state.stores.forEach((s,i)=>{if(!s.deliveryConfig)s.deliveryConfig=defaultConfig(s.id,i);});return state;}
function sample(i=0){const pts=[[-45.462,-22.925],[-45.476,-22.918],[-45.488,-22.914],[-45.516,-22.921]];const point={lng:pts[i][0],lat:pts[i][1]};return {point,address:{street:'Rua Exemplo '+String.fromCharCode(65+i),number:'100',neighborhood:'Setor fict\u00edcio '+String.fromCharCode(65+i),city:'Pindamonhangaba',state:'SP',postcode:'',complement:''},source:'demo',precise:true};}
function quote(store,point){
 if(!validPoint(point))return {ok:false,code:'invalid_point',message:'Localize e confirme o endere\u00e7o para calcular a entrega.'};
 const cfg=store?.deliveryConfig;if(!cfg)return {ok:false,code:'unconfigured',message:'Esta loja ainda n\u00e3o configurou \u00e1reas de entrega.'};
 const active=cfg.zones.filter(z=>z.active&&z.storeId===store.id);try{active.forEach(z=>validateZone(z,store.id));}catch{return {ok:false,code:'invalid_config',message:'Configura\u00e7\u00e3o de entrega inv\u00e1lida. Fale com a loja.'};}
 const matches=active.filter(z=>inRing(point,z.ring));
 if(matches.some(z=>z.kind==='blocked'))return {ok:false,code:'blocked',message:'Este ponto est\u00e1 em uma \u00e1rea sem entrega.'};
 if(!matches.length)return {ok:false,code:'outside',message:'A loja n\u00e3o atende este endere\u00e7o. Escolha retirada ou outro endere\u00e7o.'};
 matches.sort((a,b)=>b.priority-a.priority||a.id.localeCompare(b.id));
 if(matches.length>1&&matches[0].priority===matches[1].priority)return {ok:false,code:'conflict',message:'Duas \u00e1reas com a mesma prioridade se encontram aqui. A loja precisa corrigir a configura\u00e7\u00e3o.'};
 const z=matches[0];return {ok:true,storeId:store.id,zoneId:z.id,zoneName:z.name,fee:z.fee,revision:cfg.revision,overlap:matches.length>1,priority:z.priority};
}
function validateDelivery(store,delivery,now=Date.now()){
 if(!delivery||!validAddress(delivery.address)||!delivery.confirmed||delivery.addressKey!==addressKey(delivery.address))throw new Error('Confira o endere\u00e7o completo e confirme o ponto no mapa.');
 if(!['demo','geoapify'].includes(delivery.source)||!delivery.precise)throw new Error('A localiza\u00e7\u00e3o est\u00e1 imprecisa. Corrija o endere\u00e7o antes de continuar.');
 const q=quote(store,delivery.point);if(!q.ok)throw new Error(q.message);
 if(!delivery.quote||['storeId','zoneId','fee','revision'].some(k=>q[k]!==delivery.quote[k]))throw new Error('A taxa ou a \u00e1rea mudou. Recalcule e confirme o novo total antes de pedir.');
 const age=now-Date.parse(delivery.confirmedAt);if(!Number.isFinite(age)||age<0||age>10*60*1000)throw new Error('A confer\u00eancia do endere\u00e7o expirou. Confirme novamente.');
 return {...clone(delivery),quote:q,quotedAt:new Date(now).toISOString()};
}
function confirmSelection(store,selection){if(!validAddress(selection.address)||!selection.precise)throw new Error('Corrija o endere\u00e7o e localize um ponto preciso.');const q=quote(store,selection.point);if(!q.ok)throw new Error(q.message);return {...clone(selection),confirmed:true,addressKey:addressKey(selection.address),confirmedAt:new Date().toISOString(),quote:q};}
function saveZone(store,zone){validateZone(zone,store.id);const z=clone(zone),cfg=store.deliveryConfig,index=cfg.zones.findIndex(a=>a.id===z.id);if(index<0)cfg.zones.push(z);else cfg.zones[index]=z;cfg.revision++;return z;}
const api={clone,addressKey,formatAddress,validAddress,validPoint,inRing,validateZone,defaultConfig,migrate,sample,quote,validateDelivery,confirmSelection,saveZone};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PedeDelivery=api;
})(typeof window!=='undefined'?window:globalThis);
