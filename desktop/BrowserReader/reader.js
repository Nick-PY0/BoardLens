// Main-world read only access to the board interface; never calls game input methods.
(()=>{
 const names={pawn:'p',knight:'n',bishop:'b',rook:'r',queen:'q',king:'k'};
 function fenOf(map,turn='w'){
  let rows=[];for(let rank=8;rank;rank--){let row='',empty=0;for(let f=0;f<8;f++){const p=map[String.fromCharCode(97+f)+rank];if(!p)empty++;else{if(empty)row+=empty;empty=0;row+=p}}if(empty)row+=empty;rows.push(row)}return rows.join('/')+' '+turn+' - - 0 1';
 }
 function read(){
  if(document.visibilityState!=='visible')return [];
  return [...document.querySelectorAll('wc-chess-board,cg-board')].filter(e=>{let r=e.getBoundingClientRect();return r.width>=150&&r.height>=150&&r.left>=0&&r.top>=0&&r.right<=innerWidth+1&&r.bottom<=innerHeight+1}).slice(0,3).map((e,index)=>{
   const rect=e.getBoundingClientRect(),g=e.game;let fen,turnHint=null,bottom=true,points={},is3d=!!e.querySelector('canvas');
   if(g&&typeof g.getFEN==='function'){
    fen=g.getFEN();bottom=!g.getOptions().flipped;
    const renderer=g.getRenderer(),canvas=e.querySelector('canvas');
    if(is3d&&renderer?.getCoordsFromSquare&&canvas){
     for(let rank=1;rank<=8;rank++)for(let f=0;f<8;f++){const square=String.fromCharCode(97+f)+rank,p=renderer.getCoordsFromSquare(square);points[square]=[p.x/canvas.width,p.y/canvas.height]}
     bottom=points.a1[1]>points.a8[1];
    }
   }else{
    let map={};bottom=!e.closest('.orientation-black');
    for(const piece of e.querySelectorAll('piece')){
     const classes=[...piece.classList],name=Object.keys(names).find(n=>classes.includes(n));if(!name||classes.includes('ghost'))continue;
     const r=piece.getBoundingClientRect();let f=Math.round((r.left-rect.left)/(rect.width/8)),row=Math.round((r.top-rect.top)/(rect.height/8));if(f<0||f>7||row<0||row>7)continue;
     const square=String.fromCharCode(97+(bottom?f:7-f))+(bottom?8-row:row+1),p=names[name];map[square]=classes.includes('white')?p.toUpperCase():p;
    }
    const wrap=e.closest('.cg-wrap')?.parentElement?.parentElement;
    const runningTop=wrap?.querySelector('.rclock-top.running'),runningBottom=wrap?.querySelector('.rclock-bottom.running');
    if(runningTop)turnHint=!bottom;else if(runningBottom)turnHint=bottom;
    fen=fenOf(map,turnHint===false?'b':'w');
   }
   if(!fen)return null;
   if(!Object.keys(points).length)for(let rank=1;rank<=8;rank++)for(let f=0;f<8;f++)points[String.fromCharCode(97+f)+rank]=[(bottom?f+.5:7.5-f)/8,(bottom?8.5-rank:rank-.5)/8];
   return {fen,exact:!!g,turn_hint:turnHint,white_bottom:bottom,index,points,rect:{x:rect.x,y:rect.y,width:rect.width,height:rect.height}};
  }).filter(Boolean);
 }
 setInterval(()=>{try{window.postMessage({boardlensRead:true,boards:read()},location.origin)}catch{}},75);
})();
