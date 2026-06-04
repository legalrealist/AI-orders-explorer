export var STATUS_COLORS = { formal: '#1e40af', informal: '#60a5fa', pending: '#bfdbfe', none: '#e2e8f0' };
export var SANCTION_TYPE_LABELS = {
  monetary: '$ Monetary', dismissal: 'Dismissal', striking: 'Striking',
  bar_referral: 'Bar Referral', cle: 'CLE Required', show_cause: 'Show Cause',
  admonishment: 'Admonishment', contempt: 'Contempt'
};

export var REQ_ACTIONS = {
  disclose: {icon:'&#128221;', label:'Disclose AI Use', action:'Include a statement in your filing disclosing that AI tools were used.'},
  tool: {icon:'&#128295;', label:'Name the Tool', action:'Identify the specific AI tool(s) used by name (e.g., ChatGPT, CoCounsel).'},
  how: {icon:'&#128196;', label:'Describe How Used', action:'Explain how AI assisted in preparing the filing.'},
  sections: {icon:'&#128204;', label:'ID AI-Assisted Sections', action:'Mark which sections were drafted or assisted by AI.'},
  verify: {icon:'&#9989;', label:'Verify Accuracy', action:'Independently verify all AI-generated content and citations.'},
  certify_all: {icon:'&#9997;&#65039;', label:'Certify All Filings', action:'Sign a certification on ALL filings attesting to accuracy.'},
  certify_if_ai: {icon:'&#9997;&#65039;', label:'Certify If AI Used', action:'Sign a certification that AI-generated content has been verified.'},
  prompts: {icon:'&#128190;', label:'Retain Prompts', action:'Preserve all AI prompts and outputs; produce on request.'},
  proprietary: {icon:'&#128274;', label:'Protect Proprietary Info', action:'Do not input confidential or privileged information into AI tools.'},
  prohibited: {icon:'&#128683;', label:'AI Prohibited', action:'AI tools are prohibited for filings in this court.'},
  warning: {icon:'&#9888;&#65039;', label:'Warning Issued', action:'The court has warned about AI use; exercise heightened caution.'},
  rules: {icon:'&#128214;', label:'Cites Existing Rules', action:'References existing professional conduct rules as governing AI use.'},
  evidence: {icon:'&#128269;', label:'Disclose AI Evidence', action:'Disclose when AI-generated content is submitted as evidence.'}
};

export var COURT_ALIASES={
'sdny':'S.D.N.Y.','edny':'E.D.N.Y.','ndny':'N.D.N.Y.','wdny':'W.D.N.Y.',
'cdcal':'C.D. Cal.','ndcal':'N.D. Cal.','edcal':'E.D. Cal.','sdcal':'S.D. Cal.',
'ndill':'N.D. Ill.','cdill':'C.D. Ill.','sdill':'S.D. Ill.',
'edtex':'E.D. Tex.','sdtex':'S.D. Tex.','ndtex':'N.D. Tex.','wdtex':'W.D. Tex.',
'edpa':'E.D. Pa.','wdpa':'W.D. Pa.','mdpa':'M.D. Pa.',
'sdfl':'S.D. Fla.','mdfl':'M.D. Fla.','ndfl':'N.D. Fla.',
'edva':'E.D. Va.','wdva':'W.D. Va.',
'edmi':'E.D. Mich.','wdmi':'W.D. Mich.',
'ddc':'D.D.C.','dnj':'D.N.J.','dmd':'D. Md.','dmass':'D. Mass.',
'dco':'D. Colo.','daz':'D. Ariz.','dor':'D. Or.','dct':'D. Conn.',
'southern district of new york':'S.D.N.Y.','eastern district of new york':'E.D.N.Y.',
'northern district of new york':'N.D.N.Y.','western district of new york':'W.D.N.Y.',
'central district of california':'C.D. Cal.','northern district of california':'N.D. Cal.',
'southern district of florida':'S.D. Fla.','middle district of florida':'M.D. Fla.',
'northern district of illinois':'N.D. Ill.','eastern district of texas':'E.D. Tex.',
'southern district of texas':'S.D. Tex.','northern district of texas':'N.D. Tex.',
'western district of texas':'W.D. Tex.','district of columbia':'District of Columbia',
'dc':'District of Columbia','d.c.':'District of Columbia'
};

export var REQ_LABELS = {
  disclose:'Disclose AI Use', tool:'Disclose Tool', how:'Disclose How Used',
  sections:'ID Sections', verify:'Verify Accuracy', certify_all:'Certify All Filings',
  certify_if_ai:'Certify If AI Used', prompts:'Retain Prompts', proprietary:'Protect Proprietary',
  prohibited:'Prohibits AI', warning:'Warning Only', rules:'Cites Rules', evidence:'Disclose AI Evidence'
};

export var MONTHS=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
