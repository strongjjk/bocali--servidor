/* Bocali 0.2. Pure acceptance/receipt logic; no network or printer connection. */
(function(root){
'use strict';
const Core=typeof module!=='undefined'&&module.exports?require('./domain.js'):root.PedeCore;
function validTime(now){const t=new Date(now);if(!Number.isFinite(t.getTime()))throw new Error('Data inv\u00e1lida.');return t;}
function accept(order,minMinutes,maxMinutes,now=new Date().toISOString()){
 if(order.status!=='new')throw new Error('Este pedido j\u00e1 foi atendido. Atualize a fila.');
 if(!['delivery','pickup'].includes(order.fulfillment))throw new Error('Modalidade inv\u00e1lida.');
 const min=Number(minMinutes),max=Number(maxMinutes);
 if(!Number.isInteger(min)||!Number.isInteger(max)||min<1||max>240||min>max)throw new Error('Informe um prazo entre 1 e 240 minutos, com m\u00ednimo menor ou igual ao m\u00e1ximo.');
 const at=validTime(now),eta={minMinutes:min,maxMinutes:max,from:new Date(+at+min*60000).toISOString(),to:new Date(+at+max*60000).toISOString(),basis:at.toISOString(),fulfillment:order.fulfillment};
 order.eta=eta;order.acceptedAt=at.toISOString();Core.transition(order,'accepted');
 const event=order.events[order.events.length-1];event.at=at.toISOString();event.eta={...eta};
 return order;
}
function jobs(order,kind='kitchen'){return (order.printJobs||[]).filter(j=>j.kind===kind);}
function canPrint(order,kind){
 if(!['kitchen','counter','cancellation'].includes(kind))return false;
 if(kind==='cancellation')return order.status==='cancelled'&&(!!order.acceptedAt||order.events?.some(e=>e.status==='accepted'));
 return ['accepted','preparing','ready','dispatched','completed'].includes(order.status);
}
function requestPrint(order,{kind='kitchen',paper=80,now=new Date().toISOString()}={}){
 if(!canPrint(order,kind))throw new Error('Aceite o pedido antes de imprimir. Para cancelados, use apenas o aviso de cancelamento.');
 if(jobs(order,kind).some(j=>j.status==='requested'))throw new Error('Confira se a tentativa anterior saiu antes de solicitar outra via.');
 if(![58,80].includes(Number(paper)))throw new Error('Selecione papel de 58 ou 80 mm.');
 const at=validTime(now).toISOString(),job={id:Core.uid(),kind,paper:Number(paper),sequence:jobs(order,kind).length+1,status:'requested',requestedAt:at};
 (order.printJobs||(order.printJobs=[])).push(job);return job;
}
function resolvePrint(order,id,success,now=new Date().toISOString()){
 const job=(order.printJobs||[]).find(j=>j.id===id);
 if(!job||job.status!=='requested')throw new Error('Esta tentativa j\u00e1 foi resolvida ou n\u00e3o existe.');
 if(typeof success!=='boolean')throw new Error('Confirma\u00e7\u00e3o inv\u00e1lida.');
 const at=validTime(now).toISOString();job.status=success?'confirmed_by_operator':'failed_by_operator';job.resolvedAt=at;return job;
}
function printState(order,kind='kitchen'){
 const all=jobs(order,kind),pending=all.filter(j=>j.status==='requested');
 if(pending.length)return 'pending';
 if(all.some(j=>j.status==='confirmed_by_operator'))return 'confirmed';
 if(all.length)return 'failed';return 'not_requested';
}
const api={accept,jobs,canPrint,requestPrint,resolvePrint,printState};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PedeOrders=api;
})(typeof window!=='undefined'?window:globalThis);
