import state from '../state.js';
import { countStats } from '../utils/data.js';
import { fmtDate } from '../utils/text.js';

export function renderStats(){
  var s=countStats(state.data);
  document.getElementById('judgesTabBtn').textContent='Judges ('+s.total+')';
  document.getElementById('exStats').style.display='flex';
  var latestDate='';state.data.forEach(function(d){if(d.date&&d.date>latestDate)latestDate=d.date;});
  if(latestDate){var ud=document.getElementById('exLastUpdated');if(ud)ud.textContent='Data current through '+fmtDate(latestDate);}
  document.getElementById('exStats').innerHTML=
    '<div class="ex-stat info"><div class="num">'+s.standing+'</div><div class="label">Standing Orders</div></div>'+
    '<div class="ex-stat"><div class="num">'+s.jurisdictions+'</div><div class="label">Jurisdictions</div></div>'+
    '<div class="ex-stat warn"><div class="num">'+s.warnings+'</div><div class="label">Warnings Issued</div></div>'+
    '<div class="ex-stat danger"><div class="num">'+s.sanctions+'</div><div class="label">Sanctions Cases</div></div>'+
    '<div class="ex-stat"><div class="num">'+s.total+'</div><div class="label">Total Orders</div></div>';
  var es=document.getElementById('emptyStanding');if(es)es.textContent=s.standing;
  var esn=document.getElementById('emptySanctions');if(esn)esn.textContent=s.sanctions;
  var ej=document.getElementById('emptyJurisdictions');if(ej)ej.textContent=s.jurisdictions;
}
