const keyField=document.querySelector('#key'),notice=document.querySelector('#notice');
chrome.storage.local.get('key').then(({key})=>{keyField.value=key||''});
async function refresh(){try{const state=await chrome.runtime.sendMessage({type:'status'});document.querySelector('#status').textContent=state.message;document.querySelector('#status').dataset.state=state.state}catch{document.querySelector('#status').textContent='Reader needs a reload. Open Extensions, reload BoardLens Reader, then reload the chess tab.'}}
document.querySelector('#save').onclick=async()=>{await chrome.storage.local.set({key:keyField.value.trim()});await chrome.runtime.sendMessage({type:'reconnect'});await refresh()};
document.querySelector('#copy').onclick=async()=>{if(!keyField.value.trim()){notice.textContent='No key to copy yet.';return}try{await navigator.clipboard.writeText(keyField.value.trim());notice.textContent='Copied to clipboard.'}catch{keyField.select();const ok=document.execCommand('copy');notice.textContent=ok?'Copied to clipboard.':'Could not copy. Select and copy the key manually.'}};
refresh();setInterval(refresh,1000);
