import MiniSearch from 'minisearch';
import state from '../state.js';
import { COURT_ALIASES } from '../constants.js';

export function initSearch(){
  var tok=function(text){return text.toLowerCase().replace(/\./g,'').split(/[\s,;:–—\-\/]+/).filter(function(t){return t.length>0;});};
  state.judgeSearch=new MiniSearch({
    fields:['judge','court','courtNorm','state','name','summary','other'],
    storeFields:['idx'],
    tokenize:tok,
    searchOptions:{
      boost:{judge:3,court:2,courtNorm:2,state:2,name:2,summary:1,other:0.5},
      prefix:true,
      fuzzy:0.2,
      combineWith:'AND'
    }
  });
  var docs=state.data.map(function(d,i){
    var parts=[d.type,d.ai_type,d.applies_to];
    if(Array.isArray(d.applicableTo))parts.push(d.applicableTo.join(' '));
    return {id:i,idx:i,judge:d.judge||'',court:d.court||'',courtNorm:(d.court||'').replace(/\./g,''),state:d.state||'',name:d.name||'',summary:d.summary||'',other:parts.filter(Boolean).join(' ')};
  });
  state.judgeSearch.addAll(docs);
}

export function doSearch(q){
  if(!state.judgeSearch||!q)return state.data;
  var ql=q.toLowerCase().replace(/\./g,'').replace(/\s+/g,' ').trim();
  var aliasKey=Object.keys(COURT_ALIASES).find(function(k){return k===ql;});
  if(aliasKey){
    var target=COURT_ALIASES[aliasKey].toLowerCase();
    return state.data.filter(function(d){
      return (d.court||'').toLowerCase().indexOf(target)>=0 ||
             (d.state||'').toLowerCase()===target;
    });
  }
  var results=state.judgeSearch.search(q,{prefix:true,fuzzy:0.2,combineWith:'AND'});
  return results.map(function(r){return state.data[r.idx];});
}
