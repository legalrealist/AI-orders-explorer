import state from '../state.js';
import { STATE_PATHS, LABEL_POS, STATE_POSTAL, POSTAL_STATE } from '../geo-data.js';
import { getColorForCount } from '../utils/data.js';
import { esc } from '../utils/text.js';
import { applyFilters } from '../filters/judge-filters.js';

export function buildMap(){
  var byState={};
  state.data.forEach(function(d){
    var s=d.state||'Unknown';
    if(!byState[s])byState[s]=0;
    byState[s]++;
  });
  var maxCount=0;
  for(var s in byState){if(byState[s]>maxCount)maxCount=byState[s];}

  var postalCounts={};
  for(var sn in STATE_POSTAL){
    var pc=STATE_POSTAL[sn];
    postalCounts[pc]=byState[sn]||0;
  }

  var svg='<svg viewBox="0 0 959 593" xmlns="http://www.w3.org/2000/svg">';
  for(var code in STATE_PATHS){
    var cnt=postalCounts[code]||0;
    var fill=getColorForCount(cnt, maxCount);
    var fullName=POSTAL_STATE[code]||code;
    svg+='<path d="'+STATE_PATHS[code]+'" fill="'+fill+'" data-state="'+esc(fullName)+'" data-code="'+code+'" data-count="'+cnt+'"/>';
  }
  for(var code in LABEL_POS){
    var pos=LABEL_POS[code];
    svg+='<text x="'+pos[0]+'" y="'+pos[1]+'">'+code+'</text>';
  }
  svg+='</svg>';
  document.getElementById('exMapContainer').insertAdjacentHTML('afterbegin', svg);

  var tooltip=document.getElementById('exMapTooltip');
  var container=document.getElementById('exMapContainer');

  container.addEventListener('mouseover',function(e){
    var path=e.target.closest('path[data-state]');
    if(!path)return;
    tooltip.textContent=path.dataset.state+': '+path.dataset.count+' order'+(path.dataset.count!=='1'?'s':'');
    tooltip.style.display='block';
  });
  container.addEventListener('mousemove',function(e){
    var rect=container.getBoundingClientRect();
    tooltip.style.left=(e.clientX-rect.left+12)+'px';
    tooltip.style.top=(e.clientY-rect.top-28)+'px';
  });
  container.addEventListener('mouseout',function(e){
    if(e.target.closest('path[data-state]'))tooltip.style.display='none';
  });
  container.addEventListener('click',function(e){
    var path=e.target.closest('path[data-state]');
    if(!path)return;
    document.getElementById('exHeroSearch').value='';
    document.getElementById('fState').value=path.dataset.state;
    applyFilters();
    document.getElementById('exFilters').scrollIntoView({behavior:'instant',block:'start'});
  });
}
