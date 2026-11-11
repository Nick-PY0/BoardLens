const base='http://127.0.0.1:8788';
let connection={state:'idle',message:'Checking connection…',updated:0},retryAt=0,retryDelay=250;
function status(state,message){connection={state,message,updated:Date.now()};chrome.action.setBadgeText({text:state==='connected'?'ON':state==='repair'?'!':state==='pair'?'?':'…'});chrome.action.setBadgeBackgroundColor({color:state==='connected'?'#397955':state==='repair'||state==='pair'?'#b97a24':'#56665c'});chrome.action.setTitle({title:'BoardLens · '+message})}
async function desktop(path,body){
 const {key}=await chrome.storage.local.get('key');
 if(!key){status('pair','Pairing needed · paste the desktop reader key.');return {error:connection.message,repair:true}}
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),1500);
 try{
  const headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},options={headers,signal:controller.signal};if(body){options.method='POST';options.body=JSON.stringify(body)}
  const response=await fetch(base+path,options),data=await response.json();
  if(response.status===401){status('repair','Key does not match · copy the current desktop reader key and reconnect.');return {error:connection.message,repair:true}}
  if(!response.ok){status('waiting','Waiting for a stable board.');return {error:data.error||connection.message}}
  status('connected','Connected to BoardLens');retryAt=0;retryDelay=250;return data;
 }catch{
  status('disconnected','Desktop unavailable · enable Browser themes / 3D. Retrying automatically.');retryAt=Date.now()+retryDelay;retryDelay=Math.min(3000,retryDelay*2);return {error:connection.message};
 }finally{clearTimeout(timer)}
}
chrome.runtime.onMessage.addListener((m,sender,respond)=>{
 if(m.type==='status'||m.type==='reconnect'){
  if(m.type==='reconnect')retryAt=0;
  (async()=>{if(Date.now()>=retryAt)await desktop('/hints');return connection})().then(respond);return true;
 }
 if(m.type!=='boards'||!sender.tab||!/^https:\/\/(www\.chess\.com|lichess\.org)\//.test(sender.url||''))return;
 (async()=>{
  if(Date.now()<retryAt)return {error:connection.message};
  const posted=await desktop('/boards',{source:String(sender.tab.id),boards:m.boards});if(posted.error)return posted;
  const hints=await desktop('/hints');if(hints.error)return hints;
  return Object.fromEntries(Object.entries(hints).filter(([key])=>key.startsWith('browser:'+sender.tab.id+':')));
 })().then(respond,e=>respond({error:e.message}));return true;
});
