import { parseDate } from './text.js';

export function sortNewestFirst(arr){
  return arr.slice().sort(function(a,b){ return parseDate(b.date)-parseDate(a.date); });
}

export function reqCount(d){var c=0;var r=d.reqs||{};for(var k in r){if(r[k])c++;}return c;}

export function getColorForCount(count, maxCount){
  if(count===0) return '#E8E8E8';
  var t = Math.min(count / maxCount, 1);
  t = Math.pow(t, 0.5);
  var r = Math.round(232 - t * (232 - 21));
  var g = Math.round(232 - t * (232 - 128));
  var b = Math.round(232 - t * (232 - 61));
  return 'rgb('+r+','+g+','+b+')';
}

export function countStats(data){
  var so=0,sn=0,wn=0,states=new Set();
  data.forEach(function(d){
    if(d.type==='Standing Order'||d.type==='Local Rules'||d.type==='Administrative Order')so++;
    if(d.consequence==='sanctions_attorney'||d.consequence==='sanctions_party')sn++;
    if(d.consequence==='warning')wn++;
    if(d.state)states.add(d.state);
  });
  return {standing:so,sanctions:sn,warnings:wn,jurisdictions:states.size,total:data.length};
}

export function consqLabel(c){
  if(c==='sanctions_attorney')return 'Sanctions (Attorney)';
  if(c==='sanctions_party')return 'Sanctions (Party)';
  if(c==='warning')return 'Warning';
  return '';
}
