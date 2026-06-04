import state from '../state.js';
import { STATE_PATHS, LABEL_POS } from '../geo-data.js';
import { STATUS_COLORS } from '../constants.js';
import { applyBarFilters } from '../filters/bar-filters.js';

export function updateBarMapHighlights(){
  var activeAbbrs=new Set(state.barFiltered.map(function(d){return d.abbreviation;}));
  document.querySelectorAll('#barMapSvg path').forEach(function(p){
    var abbr=p.dataset.state;
    p.style.opacity=activeAbbrs.has(abbr)?'1':'0.3';
  });
}

export function renderBarMap(){
  var svg=document.getElementById('barMapSvg');
  if(!svg)return;
  var tooltip=document.getElementById('barTooltip');
  var statusByAbbr={};
  state.barData.forEach(function(d){statusByAbbr[d.abbreviation]=d;});

  for(var abbr in STATE_PATHS){
    var el=document.createElementNS('http://www.w3.org/2000/svg','path');
    el.setAttribute('d',STATE_PATHS[abbr]);
    var item=statusByAbbr[abbr];
    el.setAttribute('fill',item?(STATUS_COLORS[item.status]||'#e2e8f0'):'#e2e8f0');
    el.dataset.state=abbr;
    (function(abbr,item){
      el.addEventListener('mouseenter',function(e){
        var name=item?item.name:abbr;
        var status=item?item.status:'unknown';
        tooltip.textContent=name+': '+status;
        tooltip.style.display='block';
      });
      el.addEventListener('mousemove',function(e){
        tooltip.style.left=(e.clientX+12)+'px';
        tooltip.style.top=(e.clientY-20)+'px';
      });
      el.addEventListener('mouseleave',function(){tooltip.style.display='none';});
      el.addEventListener('click',function(){
        if(item){
          document.getElementById('barSearch').value='';
          document.getElementById('barStatusFilter').value='';
          applyBarFilters();
          var row=document.querySelector('.bar-item[data-slug="'+item.slug+'"]');
          if(row){document.querySelectorAll('.bar-item.expanded').forEach(function(el){el.classList.remove('expanded');});row.classList.add('expanded');setTimeout(function(){var y=row.getBoundingClientRect().top+window.pageYOffset-80;window.scrollTo({top:y,behavior:'instant'});},80);}
        }
      });
    })(abbr,item);
    svg.appendChild(el);
  }
  // Add state abbreviation labels
  if(typeof LABEL_POS!=='undefined'){
    for(var abbr in LABEL_POS){
      if(!STATE_PATHS[abbr])continue;
      var pos=LABEL_POS[abbr];
      var txt=document.createElementNS('http://www.w3.org/2000/svg','text');
      txt.setAttribute('x',pos[0]);
      txt.setAttribute('y',pos[1]);
      txt.setAttribute('font-size','14');
      txt.setAttribute('font-weight','700');
      txt.setAttribute('fill','#3a414e');
      txt.setAttribute('text-anchor','middle');
      txt.setAttribute('dominant-baseline','central');
      txt.setAttribute('pointer-events','none');
      txt.textContent=abbr;
      svg.appendChild(txt);
    }
  }
}
