import state from '../state.js';
import { renderBarList } from '../render/bar-list.js';
import { updateBarMapHighlights } from '../render/bar-map.js';

export function applyBarFilters(){
  var q=document.getElementById('barSearch').value.trim();
  var statusF=document.getElementById('barStatusFilter').value;
  var searchIds=null;
  if(q&&state.barSearch){
    searchIds=new Set(state.barSearch.search(q).map(function(r){return r.id;}));
  }
  var hideNone=document.getElementById('barHideNone').checked;
  state.barFiltered=state.barData.filter(function(d){
    if(searchIds&&!searchIds.has(d.slug))return false;
    if(statusF&&d.status!==statusF)return false;
    if(hideNone&&!d.opinion_title)return false;
    return true;
  });
  state.barFiltered.sort(function(a,b){ return (b.date||'').localeCompare(a.date||''); });
  document.getElementById('barCount').textContent=state.barFiltered.length+' of '+state.barData.length;
  renderBarList();
  updateBarMapHighlights();
}
