import state from '../state.js';
import { esc, fmtDate, sourceLabel } from '../utils/text.js';

export function renderBarList(){
  var list=document.getElementById('barList');
  list.innerHTML=state.barFiltered.map(function(d){
    var notes=d.rule_notes||{};
    var rulesHtml='';
    if(d.key_rules&&d.key_rules.length){
      rulesHtml='<div class="bar-detail-section"><h4>Key Rules</h4>'+d.key_rules.map(function(r){
        var note=notes[r];
        if(note){
          return '<div class="rule-card" onclick="event.stopPropagation();this.classList.toggle(\u0027open\u0027)">'+
            '<div class="rule-card-header has-note"><span class="rule-card-arrow">&#9654;</span><span class="rule-card-num">Rule '+esc(r)+'</span></div>'+
            '<div class="rule-card-note">'+esc(note)+'</div></div>';
        }
        return '<div class="rule-card"><div class="rule-card-header"><span class="rule-card-num">Rule '+esc(r)+'</span></div></div>';
      }).join('')+'</div>';
    }
    var srcHtml='';
    if(d.primary_source_urls&&d.primary_source_urls.length){
      var labelCounts={};
      var labeledUrls=d.primary_source_urls.map(function(u){
        var lbl=sourceLabel(u);
        labelCounts[lbl]=(labelCounts[lbl]||0)+1;
        return {url:u,label:lbl};
      });
      var labelSeen={};
      srcHtml='<div class="bar-detail-section"><h4>Sources</h4>'+labeledUrls.map(function(item){
        var display=item.label;
        if(labelCounts[display]>1){
          labelSeen[display]=(labelSeen[display]||0)+1;
          display=display+' ('+labelSeen[display]+')';
        }
        return '<div class="source-link"><span class="source-icon">&#128279;</span><a href="'+esc(item.url)+'" target="_blank" rel="noopener" onclick="event.stopPropagation()">'+esc(display)+'</a></div>';
      }).join('')+'</div>';
    }
    var hasOpinion=!!d.opinion_title;
    return '<div class="bar-item'+(hasOpinion?'':' no-opinion')+'" data-slug="'+esc(d.slug)+'"'+(hasOpinion?' onclick="this.classList.toggle(\u0027expanded\u0027)"':'')+'>'+
      '<div class="bar-item-header">'+
        '<div class="bar-item-state">'+esc(d.name)+'</div>'+
        '<span class="status-badge status-'+d.status+'">'+d.status+'</span>'+
        '<div class="bar-item-title">'+(hasOpinion?esc(d.opinion_title):'<span style="color:#c0c8d4;font-style:italic;">No opinion issued</span>')+'</div>'+
        '<div class="bar-item-date">'+(d.opinion_date?fmtDate(d.opinion_date):'')+'</div>'+
      '</div>'+
      '<div class="bar-item-detail">'+
        (d.citation?'<div style="font-size:12px;color:#64748b;margin-bottom:8px;">'+esc(d.citation)+'</div>':'')+
        (d.summary?'<div>'+esc(d.summary)+'</div>':'')+
        rulesHtml+
        (d.key_authority?'<div class="bar-detail-section"><h4>Key Authority</h4><div>'+esc(d.key_authority)+'</div></div>':'')+
        (d.carrier_implications?'<div class="bar-detail-section"><h4>Carrier Implications</h4><div>'+esc(d.carrier_implications)+'</div></div>':'')+
        srcHtml+
        '<div style="margin-top:8px;"><a href="'+esc(d.url)+'" target="_blank" rel="noopener" onclick="event.stopPropagation()" style="font-size:12px;color:#94a3b8;">via Legal AI Governance</a></div>'+
      '</div>'+
    '</div>';
  }).join('');
}
