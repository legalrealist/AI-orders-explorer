import state from '../state.js';
import { renderJudgeDetail } from '../render/detail.js';
import { applyFilters } from '../filters/judge-filters.js';

export function encodeHashState(){
  var h={};
  var q=document.getElementById('exHeroSearch').value.trim();
  if(q)h.q=q;
  var tab=document.getElementById('barOpinionsView').classList.contains('active')?'bar':'judges';
  if(tab==='bar')h.tab='bar';
  var cat=document.querySelector('.cat-btn.active');
  if(cat&&cat.dataset.cat!=='all')h.cat=cat.dataset.cat;
  var fType=document.getElementById('fType').value;if(fType)h.type=fType;
  var fState=document.getElementById('fState').value;if(fState)h.state=fState;
  var fOutcome=document.getElementById('fOutcome').value;if(fOutcome)h.outcome=fOutcome;
  if(state.selectedJudge)h.judge=state.selectedJudge;
  var keys=Object.keys(h);
  if(keys.length===0){history.replaceState(null,'',location.pathname);return;}
  var parts=keys.map(function(k){return encodeURIComponent(k)+'='+encodeURIComponent(h[k]);});
  history.replaceState(null,'','#'+parts.join('&'));
}

export function decodeHashState(){
  var hash=location.hash.replace(/^#/,'');
  if(!hash)return null;
  var h={};
  hash.split('&').forEach(function(p){var kv=p.split('=');if(kv.length===2)h[decodeURIComponent(kv[0])]=decodeURIComponent(kv[1]);});
  return h;
}

export function applyHashState(){
  var h=decodeHashState();
  if(!h)return;
  if(h.tab==='bar'){
    document.getElementById('barTabBtn').click();
  }
  if(h.q){document.getElementById('exHeroSearch').value=h.q;}
  if(h.cat){var cb=document.querySelector('.cat-btn[data-cat="'+h.cat+'"]');if(cb)cb.click();return;}
  if(h.type)document.getElementById('fType').value=h.type;
  if(h.state)document.getElementById('fState').value=h.state;
  if(h.outcome)document.getElementById('fOutcome').value=h.outcome;
  applyFilters();
  if(h.judge){
    setTimeout(function(){
      state.selectedJudge=h.judge;
      var groups=state.lastGroups;
      for(var i=0;i<groups.length;i++){if(groups[i].key===h.judge){renderJudgeDetail(groups[i]);break;}}
    },200);
  }
}
