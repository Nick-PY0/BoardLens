(()=>{
 const ns='http://www.w3.org/2000/svg',layer=document.createElementNS(ns,'svg');layer.setAttribute('data-boardlens','arrows');
 Object.assign(layer.style,{position:'fixed',inset:'0',width:'100vw',height:'100vh',pointerEvents:'none',zIndex:'2147483646'});document.documentElement.append(layer);
 const notice=document.createElement('div');notice.hidden=true;Object.assign(notice.style,{position:'fixed',bottom:'12px',left:'12px',zIndex:'2147483647',padding:'9px 12px',borderRadius:'8px',background:'#2d392d',color:'#fff',font:'13px system-ui',pointerEvents:'none',maxWidth:'320px'});document.documentElement.append(notice);
 let busy=false,last=0;
 window.addEventListener('message',async event=>{
  if(event.source!==window||event.origin!==location.origin||!event.data?.boardlensRead)return;
  const boards=event.data.boards;if(!Array.isArray(boards)||boards.length>3)return;
  if(document.visibilityState!=='visible'){layer.replaceChildren();return}
  if(busy)return;busy=true;
  try{
   const response=await chrome.runtime.sendMessage({type:'boards',boards:boards.map(b=>({fen:b.fen,exact:b.exact,turn_hint:b.turn_hint,white_bottom:b.white_bottom}))});
   if(!response||response.error){if(response?.repair){notice.textContent='BoardLens: '+response.error;notice.hidden=false}if(Date.now()-last>1500)layer.replaceChildren();return}notice.hidden=true;last=Date.now();
   const fragments=[];
   for(let i=0;i<boards.length;i++){
    const b=boards[i],hint=Object.entries(response).find(([k,v])=>k.endsWith(':'+i)&&v.fen===b.fen);if(!hint)continue;
    for(const m of hint[1].marks||[]){
     const point=b.points[m.square];if(!point)continue;
     const circle=document.createElementNS(ns,'circle'),r=b.rect;
     circle.setAttribute('cx',r.x+point[0]*r.width);circle.setAttribute('cy',r.y+point[1]*r.height);circle.setAttribute('r',r.width/8*(m.kind==='attack'?.12:.36));circle.setAttribute('fill',m.color);circle.setAttribute('fill-opacity',m.kind==='attack'?'.25':'.4');
     if(m.kind!=='attack'){circle.setAttribute('stroke',m.color);circle.setAttribute('stroke-width','2')}
     fragments.push(circle);
    }
    for(const a of hint[1].arrows){
     const from=b.points[a.move.slice(0,2)],to=b.points[a.move.slice(2,4)];if(!from||!to)continue;
     const r=b.rect,start=[r.x+from[0]*r.width,r.y+from[1]*r.height],end=[r.x+to[0]*r.width,r.y+to[1]*r.height],angle=Math.atan2(end[1]-start[1],end[0]-start[0]),head=Math.max(10,r.width/28),width=Math.max(4,r.width/85);
     let line=document.createElementNS(ns,'path');line.setAttribute('d',`M ${start.join(' ')} L ${end.join(' ')}`);line.setAttribute('stroke',a.color);line.setAttribute('stroke-width',width);line.setAttribute('stroke-linecap','round');line.setAttribute('fill','none');line.setAttribute('opacity','.85');fragments.push(line);
     let triangle=document.createElementNS(ns,'path');triangle.setAttribute('d',`M ${end.join(' ')} L ${end[0]-head*Math.cos(angle-.5)} ${end[1]-head*Math.sin(angle-.5)} L ${end[0]-head*Math.cos(angle+.5)} ${end[1]-head*Math.sin(angle+.5)} Z`);triangle.setAttribute('fill',a.color);fragments.push(triangle);
    }
   }
   layer.replaceChildren(...fragments);
  }catch(error){if(String(error).includes('context invalidated')){notice.textContent='BoardLens: reload this chess tab to reconnect the reader.';notice.hidden=false}if(Date.now()-last>1500)layer.replaceChildren()}finally{busy=false}
 });
 document.addEventListener('visibilitychange',()=>layer.replaceChildren());
})();
