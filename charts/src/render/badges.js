export function reqPills(d){
  var r=d.reqs||{}, pills=[];
  if(r.disclose)pills.push('<span class="rq rq-disclose">Disclose</span>');
  if(r.tool)pills.push('<span class="rq rq-tool">Name Tool</span>');
  if(r.sections)pills.push('<span class="rq rq-sections">ID Sections</span>');
  if(r.certify_all||r.certify_if_ai)pills.push('<span class="rq rq-certify">Certify</span>');
  if(r.verify)pills.push('<span class="rq rq-verify">Verify</span>');
  if(r.prompts)pills.push('<span class="rq rq-prompts">Retain Prompts</span>');
  if(r.prohibited)pills.push('<span class="rq rq-prohibit">Prohibited</span>');
  if(r.evidence)pills.push('<span class="rq rq-disclose">AI Evidence</span>');
  return pills.join('');
}

export function typeBadge(t){
  if(t==='Standing Order')return '<span class="r-badge so">STANDING ORDER</span>';
  if(t==='Judicial Opinion')return '<span class="r-badge jo">OPINION</span>';
  if(t==='Administrative Order')return '<span class="r-badge ao">ADMIN ORDER</span>';
  if(t==='Local Rules')return '<span class="r-badge lr">LOCAL RULE</span>';
  return '<span class="r-badge pd">PRACTICE DIR</span>';
}

export function srcBadge(s){
  return '';
}

export function consqBadge(c){
  if(c==='sanctions_attorney'||c==='sanctions_party')return '<span class="r-consequence sn">SANCTIONS</span>';
  if(c==='warning')return '<span class="r-consequence wn">WARNING</span>';
  return '';
}
