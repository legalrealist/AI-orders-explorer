import state from '../state.js';
import { doSearch } from '../search/judges-search.js';
import { renderFilterChips } from '../render/filter-chips.js';
import { renderList } from '../render/list.js';
import { renderJudgeDetail, emptyDetailHtml } from '../render/detail.js';
import { cleanJudgeName, parseDate } from '../utils/text.js';

export function applyFilters(){
  var mfBtn=document.getElementById('moreFiltersBtn'),mfRow=document.getElementById('moreFiltersRow');
  if(mfBtn&&mfRow){var hasMore=document.getElementById('fOutcome').value||document.getElementById('fTag').value||document.getElementById('fSanctionType').value;if(hasMore){mfBtn.classList.add('open');mfRow.classList.add('open');}}
  var typeF=document.getElementById('fType').value;
  var stateF=document.getElementById('fState').value;
  var judgeF=document.getElementById('fJudge').value;
  var outcomeF=document.getElementById('fOutcome').value;
  var tagF=document.getElementById('fTag').value;
  var dateFrom=document.getElementById('fDateFrom').value;
  var dateTo=document.getElementById('fDateTo').value;
  var q=document.getElementById('exHeroSearch').value.toLowerCase();

  var searchMatches=q?new Set(doSearch(q).map(function(d){return d.id;})):null;
  state.filtered=state.data.filter(function(d){
    if(searchMatches&&!searchMatches.has(d.id))return false;
    if(typeF&&d.type!==typeF)return false;
    if(stateF&&d.state!==stateF)return false;
    if(judgeF&&(d.judge||'')!==judgeF)return false;
    if(outcomeF==='none'&&d.consequence)return false;
    if(outcomeF&&outcomeF!=='none'&&d.consequence!==outcomeF)return false;
    if(tagF&&!(Array.isArray(d.applicableTo)&&d.applicableTo.indexOf(tagF)>=0))return false;
    var stF=document.getElementById('fSanctionType').value;
    if(stF&&!(d.sanction_types&&d.sanction_types.types&&d.sanction_types.types.indexOf(stF)>=0))return false;
    if(dateFrom&&d.date&&d.date.substring(0,7)<dateFrom)return false;
    if(dateTo&&d.date&&d.date.substring(0,7)>dateTo)return false;
    for(var c of state.chips){
      if(c==='has_link'&&!d.link)return false;
      if(c==='req_disclose'&&!d.reqs.disclose)return false;
      if(c==='prohibited'&&!d.reqs.prohibited)return false;
      if(c==='at_filings'&&!(Array.isArray(d.applicableTo)&&d.applicableTo.some(function(a){return a.indexOf('Filings')>=0;})))return false;
      if(c==='at_research'&&!(Array.isArray(d.applicableTo)&&d.applicableTo.some(function(a){return a.indexOf('Research')>=0;})))return false;
      if(c==='at_consequences'&&!(Array.isArray(d.applicableTo)&&d.applicableTo.some(function(a){return a.indexOf('Consequences')>=0;})))return false;
    }
    return true;
  });

  // Separate international entries
  var intlFiltered = state.filtered.filter(function(d){ return (d.jurisdiction||'US')!=='US'; });
  state.filtered = state.filtered.filter(function(d){ return (d.jurisdiction||'US')==='US'; });

  // Sort newest first
  state.filtered.sort(function(a,b){ return parseDate(b.date)-parseDate(a.date); });

  // Group by judge — use court-qualified key for generic names like "All Judges", "District Wide"
  var judgeGroups = {};
  state.filtered.forEach(function(d){
    var jname = d.judge || d.name || 'Unknown';
    var jl = jname.toLowerCase();
    var isGeneric = jl==='all judges'||jl==='district wide'||jl==='unknown'||/^local\s/.test(jl)||/^lcr/i.test(jl);
    var normName = isGeneric ? jname : jname.replace(/^(Chief |Magistrate |Senior |Presiding )/i,'');
    var key = isGeneric ? jname + ' — ' + (d.court||d.state||'') : normName;
    var displayName = isGeneric ? (d.court||jname) : (d.judge ? jname : cleanJudgeName(jname));
    if(!judgeGroups[key]) judgeGroups[key] = {judge:displayName, court:'', state:'', entries:[], reqs:{}, sanctions:0, warnings:0, orders:0, opinions:0};
    var g = judgeGroups[key];
    g.entries.push(d);
    if(d.court) g.court = d.court;
    if(d.state) g.state = d.state;
    var r = d.reqs || {};
    for(var k in r){ if(r[k]) g.reqs[k] = true; }
    if(d.type==='Standing Order'||d.type==='Local Rules'||d.type==='Administrative Order') g.orders++;
    if(d.type==='Judicial Opinion') g.opinions++;
    if(d.consequence==='sanctions_attorney'||d.consequence==='sanctions_party') g.sanctions++;
    if(d.consequence==='warning') g.warnings++;
  });
  var groups = Object.values(judgeGroups);
  // Sort: judges with standing orders first, then those with sanctions/warnings, then by name
  groups.sort(function(a,b){
    return parseDate(b.entries[0].date) - parseDate(a.entries[0].date);
  });

  var usOnly=state.data.filter(function(d){return (d.jurisdiction||'US')==='US';}).length;document.getElementById('exCount').textContent=state.filtered.length+' of '+usOnly+(intlFiltered.length?' + '+intlFiltered.length+' intl':'');

  // Update judge dropdown to show only judges matching current filters (excluding judge filter itself)
  var jsel=document.getElementById('fJudge');
  var curJudge=jsel.value;
  var filteredJudges={};
  state.data.filter(function(d){
    if(typeF&&d.type!==typeF)return false;
    if(stateF&&d.state!==stateF)return false;
    if(outcomeF==='none'&&d.consequence)return false;
    if(outcomeF&&outcomeF!=='none'&&d.consequence!==outcomeF)return false;
    if(tagF&&!(Array.isArray(d.applicableTo)&&d.applicableTo.indexOf(tagF)>=0))return false;
    var stF=document.getElementById('fSanctionType').value;
    if(stF&&!(d.sanction_types&&d.sanction_types.types&&d.sanction_types.types.indexOf(stF)>=0))return false;
    if(dateFrom&&d.date&&d.date.substring(0,7)<dateFrom)return false;
    if(dateTo&&d.date&&d.date.substring(0,7)>dateTo)return false;
    return true;
  }).forEach(function(d){if(d.judge)filteredJudges[d.judge]=1;});
  while(jsel.options.length>1)jsel.remove(1);
  Object.keys(filteredJudges).sort().forEach(function(j){
    var o=document.createElement('option');o.value=j;o.textContent=j;jsel.appendChild(o);
  });
  jsel.value=curJudge;

  renderFilterChips();
  state.listPage=0;
  renderList(groups, intlFiltered);
  if(groups.length>0){
    var found=false;
    if(state.selectedJudge){
      for(var i=0;i<groups.length;i++){
        if(groups[i].judge===state.selectedJudge){renderJudgeDetail(groups[i]);found=true;break;}
      }
    }
    if(!found){document.getElementById('exDetail').innerHTML=emptyDetailHtml();state.selectedJudge=null;}
  } else {
    state.selectedJudge=null;
    document.getElementById('exDetail').innerHTML='<div class="d-empty">No results match your filters</div>';
  }
}

export function clearAllFilters(){
  document.getElementById('fType').value='';
  document.getElementById('fState').value='';
  document.getElementById('fJudge').value='';
  document.getElementById('fOutcome').value='';
  document.getElementById('fTag').value='';
  document.getElementById('fDateFrom').value='';
  document.getElementById('fDateTo').value='';
  state.chips.clear();
  document.querySelectorAll('.chip.on,.chip.on-red,.chip.on-orange').forEach(function(c){c.classList.remove('on','on-red','on-orange');});
}
