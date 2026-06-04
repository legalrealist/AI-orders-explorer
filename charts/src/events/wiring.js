import state from '../state.js';

export function wireEvents(deps){
  var applyFilters=deps.applyFilters;
  var applyBarFilters=deps.applyBarFilters;
  var clearAllFilters=deps.clearAllFilters;

  function scrollToResults(){
    document.getElementById('exFilters').scrollIntoView({behavior:'instant',block:'start'});
  }

  // Hero search clear button
  document.getElementById('heroSearchClear').addEventListener('click',function(){
    document.getElementById('exHeroSearch').value='';
    document.getElementById('heroSearchClear').style.display='none';
    clearAllFilters();applyFilters();
  });

  // Hero search input
  document.getElementById('exHeroSearch').addEventListener('input',function(){
    document.getElementById('heroSearchClear').style.display=this.value?'block':'none';
    clearTimeout(state.searchTimer);
    state.searchTimer=setTimeout(function(){
      var isBar=document.getElementById('barOpinionsView').classList.contains('active');
      if(isBar){
        document.getElementById('barSearch').value=document.getElementById('exHeroSearch').value;
        applyBarFilters();
      } else {
        if(document.getElementById('exHeroSearch').value.trim()) clearAllFilters();
        applyFilters();
        scrollToResults();
      }
    },300);
  });

  // Hero search keydown (Enter)
  document.getElementById('exHeroSearch').addEventListener('keydown',function(e){
    if(e.key==='Enter'){
      e.preventDefault();
      clearTimeout(state.searchTimer);
      var isBar=document.getElementById('barOpinionsView').classList.contains('active');
      if(isBar){
        document.getElementById('barSearch').value=document.getElementById('exHeroSearch').value;
        applyBarFilters();
      } else {
        if(document.getElementById('exHeroSearch').value.trim()) clearAllFilters();
        applyFilters();
        scrollToResults();
      }
    }
  });

  // Filter chips click
  document.getElementById('exFilters').addEventListener('click',function(e){
    var chip=e.target.closest('.chip');
    if(!chip)return;
    var f=chip.dataset.f;
    if(state.chips.has(f)){state.chips.delete(f);chip.classList.remove('on','on-red','on-orange');}
    else{state.chips.add(f);chip.classList.add(f==='prohibited'?'on-red':'on');}
    applyFilters();
  });

  // Map toggle
  (function(){
    var toggle=document.getElementById('mapToggle');
    var map=document.getElementById('exMapWrap');
    var arrow=document.getElementById('toggleArrow');
    if(toggle&&map){
      toggle.addEventListener('click',function(){
        var collapsed=map.classList.toggle('collapsed');
        arrow.classList.toggle('collapsed',collapsed);
        try{sessionStorage.setItem('mapCollapsed',collapsed?'1':'0');}catch(e){}
      });
      try{var mc=sessionStorage.getItem('mapCollapsed');if(mc!=='0'){map.classList.add('collapsed');arrow.classList.add('collapsed');}}catch(e){}
    }
  })();

  // Tab switching
  document.querySelectorAll('.tab-btn').forEach(function(btn){
    btn.addEventListener('click',function(){
      document.querySelectorAll('.tab-btn').forEach(function(b){b.classList.remove('active');});
      btn.classList.add('active');
      var tab=btn.dataset.tab;
      document.getElementById('judgesView').classList.toggle('active',tab==='judges');
      document.getElementById('barOpinionsView').classList.toggle('active',tab==='bar-opinions');
    });
  });

  // Bar search/filter/hide listeners
  document.getElementById('barSearch').addEventListener('input',function(){applyBarFilters();});
  document.getElementById('barStatusFilter').addEventListener('change',function(){applyBarFilters();});
  document.getElementById('barHideNone').addEventListener('change',function(){applyBarFilters();});

  // Sticky filter bar shadow
  (function(){
    var filters=document.getElementById('exFilters');
    if(filters){
      var parent=filters.parentElement;
      function checkScroll(){
        var rect=filters.getBoundingClientRect();
        if(rect.top<=0&&parent.scrollTop>0){filters.classList.add('scrolled');}
        else{filters.classList.remove('scrolled');}
      }
      window.addEventListener('scroll',checkScroll,{passive:true});
      if(parent!==document.body)parent.addEventListener('scroll',checkScroll,{passive:true});
    }
  })();
}
