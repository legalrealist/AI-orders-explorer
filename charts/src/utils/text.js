import { MONTHS } from '../constants.js';

export function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function parseDate(d){
  if(!d)return 0;
  var parts=d.split(/[-\/]/);
  if(parts.length===3) return new Date(parts[0],parts[1]-1,parts[2]).getTime();
  return new Date(d).getTime()||0;
}

export function fmtDate(d){
  if(!d)return 'No date';
  var m=d.match(/^(\d{4})-(\d{2})(?:-(\d{2}))?/);
  if(!m)return d;
  var mon=MONTHS[parseInt(m[2],10)-1]||m[2];
  return m[3]?mon+' '+parseInt(m[3],10)+', '+m[1]:mon+' '+m[1];
}

export function snippetSummary(s,len){
  if(!s)return '';
  s=s.replace(/<[^>]+>/g,'');
  if(s.length>len)s=s.substring(0,len)+'...';
  return s;
}

export function cleanJudgeName(raw){
  if(!raw)return 'Unknown';
  // Extract judge name from "Court Path|Court - Judge Name" patterns
  var parts=raw.split('|');
  // Try to find a part that looks like a judge name (contains "Judge" or "(Judge)")
  for(var i=parts.length-1;i>=0;i--){
    var p=parts[i].trim();
    var m=p.match(/[–\-]\s*\(?(?:Judge|Justice|Magistrate|Chief Judge|Presiding Justice)\)?\s+(.+)/i);
    if(m) return m[0].replace(/^[–\-]\s*/,'').trim();
    if(/^(?:Judge|Justice|Magistrate|Chief Judge|Presiding Justice)\s/i.test(p)) return p;
  }
  // If multiple pipe-separated parts, take the last one
  if(parts.length>1){
    var last=parts[parts.length-1].trim();
    // Remove leading court prefix like "N.D.N.Y. – "
    var cm=last.match(/[–\-]\s*(.+)/);
    if(cm) return cm[1].trim();
    return last;
  }
  return raw;
}

export function sourceLabel(url){
  try{var h=new URL(url).hostname.replace(/^www\./,'');} catch(e){return url;}
  var p=new URL(url).pathname.toLowerCase();
  if(/bar\.org|barass/.test(h)) return 'Bar Association';
  if(/ethics/.test(p)||/opinion/.test(p)) return 'Ethics Opinion';
  if(/governor/.test(h)||/executive.order/.test(p)||/\beo\b/i.test(p)) return 'Executive Order';
  if(/legislature|legis|akleg|alison/.test(h)||/bill|hcr|resolution/i.test(p)) return 'Legislation';
  if(/court/.test(h)||/uscourt/.test(h)) return 'Court Order';
  if(/supremecourt/.test(h)) return 'Supreme Court';
  if(/americanbar\.org/.test(h)) return 'ABA';
  if(/judiciary/.test(h)||/judicial/.test(h)||/jud/.test(h)) return 'Judiciary';
  var parts=h.split('.');
  return parts.length>2?parts.slice(-2).join('.'):h;
}
