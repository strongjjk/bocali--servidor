(function(root){
'use strict';
const line=x=>String(x??'').replace(/\r?\n/g,' / ').replace(/\t/g,' ');
function fromOrder(o,kind,job){
 if(!o||!job||!['kitchen','counter','cancellation'].includes(kind))throw new Error('Pedido ou via inválidos.');
 const accepted=Date.parse(o.acceptedAt),created=Date.parse(o.createdAt);
 if(!Number.isFinite(accepted)||!Number.isFinite(created))throw new Error('Datas do pedido inválidas para a comanda.');
 const a=o.delivery?.address,address=typeof a==='string'?a:a?[a.street,a.number,a.neighborhood,a.city,a.state,a.complement].filter(Boolean).join(', '):'';
 const items=(o.items||[]).map(i=>({name:line(i.name),quantity:i.quantity,extras:(i.extras||[]).map(e=>line(e.name)),note:line(i.note),lineTotalCents:(i.unitPrice+(i.extras||[]).reduce((sum,e)=>sum+e.price,0))*i.quantity}));
 return {schemaVersion:1,testMode:false,printJobId:job.id,sequence:job.sequence,storeId:o.storeId,orderId:o.id,storeName:line(o.storeName),customer:line(o.customerName||'Cliente'),kind,fulfillment:o.fulfillment,acceptedAt:accepted,createdAt:created,minMinutes:o.eta?.minMinutes||15,maxMinutes:o.eta?.maxMinutes||25,items,note:line(o.note),address:line(address),subtotalCents:o.subtotal,feeCents:o.fee,totalCents:o.total,payment:o.payment,paymentStatus:o.paymentStatus,paymentProviderMethod:line(o.paymentProviderMethod),cashChangeNeeded:!!o.paymentDetails?.changeNeeded,changeForCents:Number(o.paymentDetails?.changeFor||0)};
}
const api={fromOrder};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.BocaliNativeTicket=api;
})(typeof window!=='undefined'?window:globalThis);
