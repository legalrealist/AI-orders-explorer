import state from '../state.js';
import { countStats } from '../utils/data.js';
import { esc, fmtDate, parseDate, cleanJudgeName } from '../utils/text.js';
import { srcBadge } from './badges.js';
import { SANCTION_TYPE_LABELS, REQ_ACTIONS } from '../constants.js';

// Sources row for one timeline entry: self-hosted primary-source PDF (the
// archived order/opinion), the public source link, the R&G original as a
// fallback, and an `unverified` caveat when no open primary source confirms it.
function entrySources(d){
  var out='<div class="tl-links">';
  if(d.pdf) out+='<a class="tl-pdf" href="'+esc(d.pdf)+'" target="_blank" rel="noopener">&#128196; Primary-source PDF</a>';
  if(d.link) out+='<a class="jd-link" href="'+esc(d.link)+'" target="_blank" rel="noopener">View source &rarr;</a>';
  if(d.original_link && d.original_link!==d.link) out+='<a class="jd-link tl-orig" href="'+esc(d.original_link)+'" target="_blank" rel="noopener">Original (R&amp;G) &rarr;</a>';
  if(!d.pdf && !d.link) out+='<span class="tl-nolink">No primary source on file</span>';
  if(d.unverified) out+='<span class="tl-unverified" title="No openly accessible primary source independently confirms this entry">&#9888;&#65039; unverified</span>';
  return out+'</div>';
}

export function emptyDetailHtml(){
  var s=countStats(state.data);
  return '<div class="d-empty"><div style="font-size:32px;margin-bottom:12px;opacity:0.3">&#x2696;</div><div style="font-size:15px;margin-bottom:16px">Search for a judge or click from the list</div><div style="text-align:left;max-width:280px;margin:0 auto;font-size:13px;color:#94a3b8;line-height:1.8"><div><strong style="color:#2563eb">'+s.standing+'</strong> standing orders tracked</div><div><strong style="color:#dc2626">'+s.sanctions+'</strong> sanctions cases documented</div><div><strong style="color:#475569">'+s.jurisdictions+'</strong> jurisdictions covered</div><div style="margin-top:8px;font-size:12px;color:#cbd5e1">Search by judge, court, state, or case name</div></div></div>';
}

export function renderJudgeDetail(group){
  var p=document.getElementById('exDetail');
  var backBtn='<button class="d-back" onclick="document.getElementById(\u0027exList\u0027).scrollIntoView({block:\u0027start\u0027,behavior:\u0027instant\u0027});">← Back to list</button>';
  var html='<div class="d-title">'+esc(group.judge.replace(/\s*\|\s*/g,', '))+'</div>';
  html+='<div style="font-size:14px;color:#64748b;margin-bottom:16px;">'+esc(group.court)+(group.state?' &middot; '+esc(group.state):'')+(group.jurisdiction?' &middot; <span style="color:#2563eb;font-weight:500;">'+esc(group.jurisdiction)+'</span>':'')+'</div>';

  // Alerts
  if(group.sanctions>0){
    html+='<div class="d-alert sanctions">&#9888;&#65039; '+group.sanctions+' sanctions case'+(group.sanctions>1?'s':'')+' associated with this judge</div>';
  }
  if(group.warnings>0){
    html+='<div class="d-alert warning">&#9888;&#65039; '+group.warnings+' warning'+(group.warnings>1?'s':'')+' issued about AI use</div>';
  }

  // Requirements summary (compact)
  var reqKeys=Object.keys(group.reqs);
  if(reqKeys.length>0){
    html+='<div class="d-section"><h3>Requirements ('+reqKeys.length+')</h3>';
    reqKeys.forEach(function(k){
      var ra=REQ_ACTIONS[k];
      if(!ra)return;
      html+='<div class="jd-req">'+
        '<div class="jd-icon">'+ra.icon+'</div>'+
        '<div><div class="jd-label">'+ra.label+'</div>'+
        '<div class="jd-action">'+ra.action+'</div></div></div>';
    });
    html+='</div>';
  }

  // Timeline — entries sorted newest→oldest (most recent order first)
  var timeline=group.entries.slice().sort(function(a,b){ return parseDate(b.date)-parseDate(a.date); });
  html+='<div class="d-section"><h3>History ('+timeline.length+' entries, newest first)</h3>';
  html+='<div class="jd-timeline">';
  timeline.forEach(function(d){
    var name=d.judge?(d.court?d.court+' – '+d.judge:d.judge):cleanJudgeName(d.name||d.type||'Entry');
    if(name.length>120) name=name.substring(0,117)+'...';
    // Type badge
    var typeClass=d.type==='Standing Order'?'so':d.type==='Judicial Opinion'?'jo':d.type==='Administrative Order'?'ao':d.type==='Local Rules'?'lr':'pd';
    var typeLabel=d.type||'Order';
    // Consequence badge
    var consq='';
    if(d.consequence==='sanctions_attorney'||d.consequence==='sanctions_party') consq='<span class="tl-consq sn">SANCTIONS</span>';
    else if(d.consequence==='warning') consq='<span class="tl-consq wn">WARNING</span>';
    // Sanction type badges
    var stBadges='';
    if(d.sanction_types&&d.sanction_types.types){
      d.sanction_types.types.forEach(function(t){
        stBadges+=' <span class="sanction-type-badge st-'+t+'">'+(SANCTION_TYPE_LABELS[t]||t)+'</span>';
      });
    }
    // Summary snippet
    var summ=d.summary?d.summary.replace(/<[^>]+>/g,''):'';
    html+='<div class="tl-entry">'+
      '<div class="tl-date">'+fmtDate(d.date)+'</div>'+
      '<div class="tl-dot"></div>'+
      '<div class="tl-body">'+
        '<div class="tl-header"><span class="tl-badge '+typeClass+'">'+esc(typeLabel)+'</span>'+consq+stBadges+srcBadge(d.source)+'</div>'+
        '<div class="tl-name">'+esc(name)+'</div>'+
        (summ?'<div class="tl-summary">'+(summ.length>300?'<span class="tl-summ-short">'+esc(summ.slice(0,300))+'... <a href="#" class="tl-more" onclick="this.parentNode.style.display=\'none\';this.parentNode.nextElementSibling.style.display=\'\';return false;">Show more</a></span><span class="tl-summ-full" style="display:none">'+esc(summ)+'</span>':esc(summ))+'</div>':'')+
        entrySources(d)+
      '</div></div>';
  });
  html+='</div></div>';

  // Sanction types/amounts summary
  var stEntries=group.entries.filter(function(e){return e.sanction_types&&e.sanction_types.types&&e.sanction_types.types.length>0;});
  if(stEntries.length>0){
    html+='<div class="d-section d-sanction-types"><h3>Sanction Types</h3><div class="tag-pills">';
    var allTypes={};
    stEntries.forEach(function(e){e.sanction_types.types.forEach(function(t){allTypes[t]=1;});});
    Object.keys(allTypes).forEach(function(t){
      html+='<span class="sanction-type-badge st-'+t+'" style="font-size:12px;padding:3px 10px;">'+(SANCTION_TYPE_LABELS[t]||t)+'</span>';
    });
    html+='</div>';
    var amountEntries=stEntries.filter(function(e){return e.sanction_types.amount_sought||e.sanction_types.amount_awarded;});
    if(amountEntries.length>0){
      amountEntries.forEach(function(e){
        if(e.sanction_types.amount_sought) html+='<div style="margin-top:8px;font-size:13px;"><strong>Amount Sought:</strong> <span class="amount-tag">'+esc(e.sanction_types.amount_sought)+'</span></div>';
        if(e.sanction_types.amount_awarded) html+='<div style="margin-top:4px;font-size:13px;"><strong>Amount Awarded:</strong> <span class="amount-tag">'+esc(e.sanction_types.amount_awarded)+'</span></div>';
      });
    }
    html+='</div>';
  }

  p.innerHTML=backBtn+html;
}
