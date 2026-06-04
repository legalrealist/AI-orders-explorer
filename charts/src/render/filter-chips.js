import state from '../state.js';
import { esc } from '../utils/text.js';
import { applyFilters } from '../filters/judge-filters.js';

export function renderFilterChips(){
  var el=document.getElementById('exFilterChips');
  var parts=[];
  var typeF=document.getElementById('fType').value;
  var stateF=document.getElementById('fState').value;
  var judgeF=document.getElementById('fJudge').value;
  var outcomeF=document.getElementById('fOutcome').value;
  var tagF=document.getElementById('fTag').value;
  var dateFrom=document.getElementById('fDateFrom').value;
  var dateTo=document.getElementById('fDateTo').value;

  if(typeF)parts.push({label:'Type: '+typeF,clear:function(){document.getElementById('fType').value='';}});
  if(stateF)parts.push({label:'State: '+stateF,clear:function(){document.getElementById('fState').value='';}});
  if(judgeF)parts.push({label:'Judge: '+judgeF,clear:function(){document.getElementById('fJudge').value='';}});
  if(outcomeF){var outcomeLabels={sanctions_attorney:'Sanctions (Attorney)',sanctions_party:'Sanctions (Party)',warning:'Warning',none:'No Consequence'};parts.push({label:'Outcome: '+(outcomeLabels[outcomeF]||outcomeF),clear:function(){document.getElementById('fOutcome').value='';}});}
  if(tagF)parts.push({label:'Sector: '+tagF,clear:function(){document.getElementById('fTag').value='';}});
  if(dateFrom)parts.push({label:'From: '+dateFrom,clear:function(){document.getElementById('fDateFrom').value='';}});
  if(dateTo)parts.push({label:'To: '+dateTo,clear:function(){document.getElementById('fDateTo').value='';}});
  state.chips.forEach(function(c){
    var chipLabels={has_link:'Has Link',req_disclose:'Requires Disclosure',prohibited:'Prohibits AI',at_filings:'Filings/Drafting',at_research:'Research',at_consequences:'Consequences'};
    var lbl=chipLabels[c]||c;
    parts.push({label:lbl,chip:c,clear:function(){
      state.chips.delete(c);
      var chipEl=document.querySelector('.chip[data-f="'+c+'"]');
      if(chipEl)chipEl.classList.remove('on','on-red','on-orange');
    }});
  });

  if(parts.length===0){el.innerHTML='';return;}

  el.innerHTML=parts.map(function(p,i){
    return '<span class="filter-chip" data-idx="'+i+'">'+esc(p.label)+' <span class="fc-x">&times;</span></span>';
  }).join('')+'<span class="filter-chip clear-all" id="clearAllFilters">Clear All</span>';

  el.querySelectorAll('.filter-chip:not(.clear-all)').forEach(function(chip){
    chip.addEventListener('click',function(){
      var idx=parseInt(chip.dataset.idx);
      parts[idx].clear();
      applyFilters();
    });
  });
  document.getElementById('clearAllFilters').addEventListener('click',function(){
    document.getElementById('exHeroSearch').value='';
    parts.forEach(function(p){p.clear();});
    applyFilters();
  });
}
