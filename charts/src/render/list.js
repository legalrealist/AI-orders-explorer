import state from '../state.js';
import { esc, snippetSummary } from '../utils/text.js';
import { renderJudgeDetail } from './detail.js';

export function renderList(groups, intlData){
  state.lastGroups=groups; state.lastIntlData=intlData||[];
  var el=document.getElementById('exList');
  var start=state.listPage*state.pageSize;
  var show=groups.slice(start,start+state.pageSize);
  var totalEntries=0;groups.forEach(function(g){totalEntries+=g.entries.length;});
  var totalPages=Math.ceil(groups.length/state.pageSize);
  var header='<div class="list-header"><strong>'+groups.length+'</strong> judges &middot; <strong>'+totalEntries+'</strong> entries <span style="float:right;color:#94a3b8;font-weight:400;">sorted by most recent</span></div>';
  if(totalPages>1){
    var pgNums='';
    for(var pi=0;pi<totalPages;pi++){
      if(pi===state.listPage) pgNums+='<span style="display:inline-block;padding:2px 8px;border-radius:4px;background:#2563eb;color:#fff;font-size:12px;font-weight:600;margin:0 2px;">'+(pi+1)+'</span>';
      else pgNums+='<button class="pg-btn pg-num" data-page="'+pi+'" style="background:#e2e8f0;color:#334155;margin:0 2px;">'+(pi+1)+'</button>';
    }
    header+='<div style="padding:6px 20px;background:#f0f4ff;border-bottom:1px solid #cbd5e1;font-size:13px;color:#334155;display:flex;align-items:center;justify-content:space-between;">'
      +'<span>Page '+(state.listPage+1)+' of '+totalPages+' (showing '+(start+1)+'–'+Math.min(start+state.pageSize,groups.length)+' of '+groups.length+')</span>'
      +'<span>'
      +(state.listPage>0?'<button class="pg-btn" id="pgPrev">&laquo; Prev</button>':'')
      +pgNums
      +(state.listPage<totalPages-1?'<button class="pg-btn" id="pgNext">Next &raquo;</button>':'')
      +'</span></div>';
  }
  el.innerHTML=header+show.map(function(g){
    var counts=[];
    if(g.orders) counts.push('<span style="color:#2563eb">'+g.orders+' order'+(g.orders>1?'s':'')+'</span>');
    if(g.opinions) counts.push(g.opinions+' opinion'+(g.opinions>1?'s':''));
    if(g.sanctions) counts.push('<span style="color:#dc2626;font-weight:600">'+g.sanctions+' sanction'+(g.sanctions>1?'s':'')+'</span>');
    if(g.warnings) counts.push('<span style="color:#ea580c">'+g.warnings+' warning'+(g.warnings>1?'s':'')+'</span>');
    var countStr=counts.join(' · ');var hasStandingOrder=g.entries.some(function(e){return e.type==='Standing Order'||e.type==='Local Rules'||e.type==='Administrative Order';});
    var rp='';
    var rr=g.reqs;
    if(rr.disclose)rp+='<span class="rq rq-disclose">Disclose</span>';
    if(rr.tool)rp+='<span class="rq rq-tool">Name Tool</span>';
    if(rr.sections)rp+='<span class="rq rq-sections">ID Sections</span>';
    if(rr.certify_all||rr.certify_if_ai)rp+='<span class="rq rq-certify">Certify</span>';
    if(rr.verify)rp+='<span class="rq rq-verify">Verify</span>';
    if(rr.prompts)rp+='<span class="rq rq-prompts">Retain Prompts</span>';
    if(rr.prohibited)rp+='<span class="rq rq-prohibit">Prohibited</span>';
    if(rr.evidence)rp+='<span class="rq rq-disclose">AI Evidence</span>';
    var preview=snippetSummary(g.entries[0].summary||g.entries[0].name||'',90);
    var rowCls='ex-row'+(g.judge===state.selectedJudge?' sel':'')+(g.sanctions?' has-sanctions':(hasStandingOrder?' has-order':''));
    return '<div class="'+rowCls+'" data-judge="'+esc(g.judge)+'">'+
      '<div class="r-top">'+
      '<span class="r-judge">'+esc(g.judge.replace(/\s*\|\s*/g,', '))+'</span>'+
      '<span class="r-counts">'+countStr+'</span>'+
      '</div>'+
      '<div class="r-meta"><span>'+esc(g.court)+'</span><span>'+esc(g.state)+'</span></div>'+
      (preview?'<div class="r-preview">'+esc(preview)+'</div>':'')+
      (rp?'<div class="r-reqs">'+rp+'</div>':'')+
    '</div>';
  }).join('');

  // International section
  if(intlData&&intlData.length>0){
    var intlGroups={};
    intlData.forEach(function(d){
      var key=d.judge||d.name||'Unknown';
      if(!intlGroups[key])intlGroups[key]={judge:key,court:d.court||'',state:d.state||'',jurisdiction:d.jurisdiction||'',entries:[],reqs:{},sanctions:0,warnings:0,orders:0,opinions:0};
      intlGroups[key].entries.push(d);
      if(d.court)intlGroups[key].court=d.court;
      if(d.state)intlGroups[key].state=d.state;
      if(d.jurisdiction)intlGroups[key].jurisdiction=d.jurisdiction;
    });
    var intlGroupsList=Object.values(intlGroups);
    el.innerHTML+=
      '<div class="intl-header" id="intlToggle"><span class="arrow">&#9654;</span> International ('+intlData.length+')</div>'+
      '<div class="intl-section" id="intlSection">'+
      intlGroupsList.map(function(g){
        var iPreview=snippetSummary(g.entries[0].summary||g.entries[0].name||'',90);
        return '<div class="ex-row" data-judge="'+esc(g.judge)+'">'+
          '<div class="r-top"><span class="r-judge">'+esc(g.judge)+'</span><span class="r-counts">'+g.entries.length+' entr'+(g.entries.length>1?'ies':'y')+'</span></div>'+
          '<div class="r-meta"><span>'+esc(g.court)+'</span>'+(g.state?'<span>'+esc(g.state)+'</span>':'')+(g.jurisdiction?'<span style="color:#2563eb;font-weight:500;">'+esc(g.jurisdiction)+'</span>':'')+'</div>'+
          (iPreview?'<div class="r-preview">'+esc(iPreview)+'</div>':'')+
        '</div>';
      }).join('')+
      '</div>';
    var intlToggle=document.getElementById('intlToggle');
    if(intlToggle){
      intlToggle.addEventListener('click',function(){
        intlToggle.classList.toggle('open');
        document.getElementById('intlSection').classList.toggle('open');
      });
    }
    // Wire click handlers for international rows too
    document.getElementById('intlSection').querySelectorAll('.ex-row').forEach(function(r){
      r.addEventListener('click',function(){
        var judgeName=r.dataset.judge;
        state.selectedJudge=judgeName;
        var group=intlGroupsList.find(function(g){return g.judge===judgeName;});
        if(group)renderJudgeDetail(group);
        el.querySelectorAll('.ex-row').forEach(function(x){x.classList.remove('sel');});
        r.classList.add('sel');
      });
    });
  }

  // Bind click handlers for main (non-international) rows
  Array.from(el.querySelectorAll('.ex-row')).forEach(function(r){
    if(r.closest('#intlSection')) return; // skip intl rows, handled above
    r.addEventListener('click',function(){
      var judgeName=r.dataset.judge;
      state.selectedJudge=judgeName;
      var group=show.find(function(g){return g.judge===judgeName;});
      if(group) renderJudgeDetail(group);
      el.querySelectorAll('.ex-row').forEach(function(x){x.classList.remove('sel');});
      r.classList.add('sel');
      if(window.innerWidth<=900){document.getElementById('exDetail').scrollIntoView({behavior:'instant',block:'start'});}
    });
  });

  // Pagination buttons
  var prevBtn=document.getElementById('pgPrev');
  var nextBtn=document.getElementById('pgNext');
  function onPageChange(){ state.selectedJudge=null; document.getElementById('exDetail').innerHTML='<div class="d-empty">Select a judge from the list to view details</div>'; }
  if(prevBtn) prevBtn.addEventListener('click',function(){ state.listPage--; onPageChange(); renderList(state.lastGroups,state.lastIntlData); el.scrollTop=0; });
  if(nextBtn) nextBtn.addEventListener('click',function(){ state.listPage++; onPageChange(); renderList(state.lastGroups,state.lastIntlData); el.scrollTop=0; });
  el.querySelectorAll('.pg-num').forEach(function(btn){
    btn.addEventListener('click',function(){ state.listPage=parseInt(btn.dataset.page); onPageChange(); renderList(state.lastGroups,state.lastIntlData); el.scrollTop=0; });
  });
}
