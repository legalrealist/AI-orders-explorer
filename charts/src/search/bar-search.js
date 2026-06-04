import MiniSearch from 'minisearch';
import state from '../state.js';

export function initBarSearch(){
  state.barSearch=new MiniSearch({
    fields:['name','opinion_title','summary','_rules','key_authority'],
    storeFields:['slug'],
    idField:'slug',
    searchOptions:{boost:{name:2,opinion_title:2},fuzzy:0.2,prefix:true}
  });
  state.barSearch.addAll(state.barData.map(function(d){
    return Object.assign({},d,{_rules:Array.isArray(d.key_rules)?d.key_rules.join(' '):''});
  }));
}
