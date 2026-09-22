/* Bocali v1.0 RC5 - production connectivity hooks. */
'use strict';
window.addEventListener('offline',()=>{if(window.Net){Net.online=false;if(typeof updateConnection==='function')updateConnection();}});
window.addEventListener('online',()=>{if(typeof refresh==='function')refresh().catch(()=>{if(typeof updateConnection==='function')updateConnection();});});
