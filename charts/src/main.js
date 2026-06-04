import state from './state.js';
import { initSearch } from './search/judges-search.js';
import { initBarSearch } from './search/bar-search.js';
import { applyFilters, clearAllFilters } from './filters/judge-filters.js';
import { applyBarFilters } from './filters/bar-filters.js';
import { renderStats } from './render/stats.js';
import { buildMap } from './render/map.js';
import { renderBarMap } from './render/bar-map.js';
import { wireEvents } from './events/wiring.js';
import { esc } from './utils/text.js';
import { SANCTION_TYPE_LABELS } from './constants.js';
import { encodeHashState, applyHashState } from './utils/url-hash.js';

// Loading state
document.getElementById('exStats').style.display='flex';
document.getElementById('exStats').innerHTML='<div style="padding:20px;color:#94a3b8;text-align:center;">Loading court orders...</div>';

// Wire DOM events
wireEvents({ applyFilters: function(){ applyFilters(); encodeHashState(); }, applyBarFilters: function(){ applyBarFilters(); encodeHashState(); }, clearAllFilters: clearAllFilters });

// Init
fetch(state.dataBase + '/explorer_data.json')
  .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
  .then(function(data){
    state.data=data;
    initSearch();
    renderStats();
    buildMap();

    // Populate filters
    var stateSet={},tagSet={},judgeSet={};
    var nStanding=0,nSanctions=0,nDisclose=0,nOpinions=0;
    data.forEach(function(d){
      if(d.state)stateSet[d.state]=1;
      if(d.judge)judgeSet[d.judge]=1;
      if(Array.isArray(d.applicableTo))d.applicableTo.forEach(function(t){tagSet[t]=1;});
      if(d.type==='Standing Order'||d.type==='Local Rules'||d.type==='Administrative Order')nStanding++;
      if(d.type==='Judicial Opinion')nOpinions++;
      if(d.consequence==='sanctions_attorney'||d.consequence==='sanctions_party')nSanctions++;
      if(d.reqs&&d.reqs.disclose)nDisclose++;
    });
    var sel=document.getElementById('fState');
    Object.keys(stateSet).sort().forEach(function(s){
      var o=document.createElement('option');o.value=s;o.textContent=s;sel.appendChild(o);
    });
    var jsel=document.getElementById('fJudge');
    Object.keys(judgeSet).sort().forEach(function(j){
      var o=document.createElement('option');o.value=j;o.textContent=j;jsel.appendChild(o);
    });
    var tsel=document.getElementById('fTag');
    Object.keys(tagSet).sort().forEach(function(t){
      var o=document.createElement('option');o.value=t;o.textContent=t;tsel.appendChild(o);
    });

    // Populate sanction type filter
    var stSet={};
    data.forEach(function(d){if(d.sanction_types&&d.sanction_types.types)d.sanction_types.types.forEach(function(t){stSet[t]=1;});});
    var stsel=document.getElementById('fSanctionType');
    Object.keys(stSet).sort().forEach(function(t){
      var o=document.createElement('option');o.value=t;o.textContent=SANCTION_TYPE_LABELS[t]||t;stsel.appendChild(o);
    });

    // Category quick-filter buttons
    var cats=[
      {label:'All Orders',count:data.length,filter:function(){resetFilters();}},
      {label:'Standing Orders',count:nStanding,filter:function(){resetFilters();document.getElementById('fType').value='Standing Order';}},
      {label:'Opinions',count:nOpinions,filter:function(){resetFilters();document.getElementById('fType').value='Judicial Opinion';}},
      {label:'Sanctions',count:nSanctions,filter:function(){resetFilters();document.getElementById('fOutcome').value='sanctions_attorney';}},
      {label:'Requires Disclosure',count:nDisclose,filter:function(){resetFilters();state.chips.add('req_disclose');var c=document.querySelector('.chip[data-f="req_disclose"]');if(c)c.classList.add('on');}}
    ];
    var catEl=document.getElementById('exCategories');
    catEl.innerHTML=cats.map(function(c,i){
      return '<button class="cat-btn'+(i===0?' active':'')+'" data-cat="'+i+'">'+esc(c.label)+' <span class="cat-count">'+c.count+'</span></button>';
    }).join('');
    catEl.querySelectorAll('.cat-btn').forEach(function(btn){
      btn.addEventListener('click',function(){
        catEl.querySelectorAll('.cat-btn').forEach(function(b){b.classList.remove('active');});
        btn.classList.add('active');
        cats[parseInt(btn.dataset.cat)].filter();
        applyFilters();
        encodeHashState();
      });
    });

    function resetFilters(){
      ['fType','fState','fJudge','fOutcome','fTag','fSanctionType'].forEach(function(id){document.getElementById(id).value='';});
      document.getElementById('fDateFrom').value='';
      document.getElementById('fDateTo').value='';
      state.chips.clear();
      document.querySelectorAll('.chip').forEach(function(c){c.classList.remove('on','on-red','on-orange');});
    }

    // Wire up filters
    ['fType','fState','fJudge','fOutcome','fTag','fSanctionType'].forEach(function(id){
      document.getElementById(id).addEventListener('change',function(){
        catEl.querySelectorAll('.cat-btn').forEach(function(b){b.classList.remove('active');});
        applyFilters();
        encodeHashState();
      });
    });
    document.getElementById('fDateFrom').addEventListener('change',function(){ applyFilters(); encodeHashState(); });
    document.getElementById('fDateTo').addEventListener('change',function(){ applyFilters(); encodeHashState(); });

    // Initial render
    applyFilters();
    encodeHashState();

    // Load bar opinions
    fetch(state.dataBase + '/bar_opinions.json')
      .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
      .then(function(barData){
        state.barData=barData.items||barData;
        document.getElementById('barTabBtn').textContent='Bar Opinions ('+state.barData.length+')';
        initBarSearch();
        renderBarMap();
        applyBarFilters();
        encodeHashState();
      })
      .catch(function(err){console.error('Bar data load error:',err);});
  })
  .catch(function(err){
    document.getElementById('judgesTabBtn').textContent='Judges ('+state.data.length+')';
    document.getElementById('exStats').style.display='flex';
    document.getElementById('exStats').innerHTML='<div style="padding:20px;color:#dc2626;text-align:center;">Failed to load data. Please refresh the page.</div>';
    console.error('Data load error:',err);
  });

// Apply hash state on load
setTimeout(applyHashState,300);
