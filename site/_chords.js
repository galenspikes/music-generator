
(function(){
  "use strict";
  var DATA=JSON.parse(document.getElementById("chd-data").textContent);
  var RECIPES=DATA.recipes, CATS=DATA.categories;
  var ROOTS=[{n:"C",pc:0,l:"C"},{n:"D\u266d",pc:1,l:"D"},{n:"D",pc:2,l:"D"},
    {n:"E\u266d",pc:3,l:"E"},{n:"E",pc:4,l:"E"},{n:"F",pc:5,l:"F"},
    {n:"F\u266f",pc:6,l:"F"},{n:"G",pc:7,l:"G"},{n:"A\u266d",pc:8,l:"A"},
    {n:"A",pc:9,l:"A"},{n:"B\u266d",pc:10,l:"B"},{n:"B",pc:11,l:"B"}];
  var LETTERS=["C","D","E","F","G","A","B"], LPC={C:0,D:2,E:4,F:5,G:7,A:9,B:11};
  function spell(pc,step,rootPc,rootLetter){
    var letter=LETTERS[(LETTERS.indexOf(rootLetter)+step)%7];
    var acc=((pc-LPC[letter]+6)%12)-6; if(acc<=-3)acc+=12; if(acc>=3)acc-=12;
    var m=acc===-2?"\ud834\udd2b":acc===-1?"\u266d":acc===1?"\u266f":acc===2?"\ud834\udd2a":"";
    return letter+m;
  }
  var $=function(id){return document.getElementById(id);};
  function esc(s){return String(s).replace(/[&<>]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;"}[c];});}
  var state={name:null,root:0};

  var AC=null,master=null,active=[],loopTimer=null,mode=null;
  function ensureAudio(){
    if(!AC){ AC=new (window.AudioContext||window.webkitAudioContext)();
      master=AC.createGain(); master.gain.value=0.9; master.connect(AC.destination); }
    if(AC.state!=="running")AC.resume(); return AC;
  }
  function voice(midi,t0,sustain,dur,mul){
    var o=AC.createOscillator(); o.type="triangle";
    o.frequency.value=440*Math.pow(2,(midi-69)/12);
    var g=AC.createGain(), peak=0.13*(mul||1);
    g.gain.setValueAtTime(0.0001,t0);
    g.gain.exponentialRampToValueAtTime(peak,t0+0.014);
    o.connect(g); g.connect(master); o.start(t0);
    if(sustain){ g.gain.exponentialRampToValueAtTime(peak*0.72,t0+0.5); active.push({o:o,g:g}); }
    else { g.gain.exponentialRampToValueAtTime(0.0001,t0+dur); o.stop(t0+dur+0.06); }
  }
  function setMode(m){ mode=m;
    document.querySelectorAll(".pbtn[data-mode]").forEach(function(b){
      b.classList.toggle("on",b.dataset.mode===m); }); }
  function stopAll(){
    if(loopTimer){clearInterval(loopTimer);loopTimer=null;}
    if(AC){ var now=AC.currentTime;
      active.forEach(function(v){ try{ v.g.gain.cancelScheduledValues(now);
        v.g.gain.setValueAtTime(Math.max(0.0001,v.g.gain.value),now);
        v.g.gain.exponentialRampToValueAtTime(0.0001,now+0.2); v.o.stop(now+0.24);}catch(e){} }); }
    active=[]; setMode(null);
  }
  function voiced(){ var r=RECIPES[state.name], base=48+ROOTS[state.root].pc;
    return r.offsets.map(function(o){return base+o;}); }
  function doStrike(){ ensureAudio(); stopAll(); var t0=AC.currentTime+0.02;
    voiced().forEach(function(m){voice(m,t0,false,0.55,0.85);}); }
  function doSustain(){ ensureAudio(); stopAll(); var t0=AC.currentTime+0.02;
    voiced().forEach(function(m){voice(m,t0,true,0,0.68);}); setMode("sustain"); }
  function doArp(loop){ ensureAudio(); stopAll(); var ns=voiced(), i=0;
    function step(){ voice(ns[i%ns.length],AC.currentTime+0.01,false,0.42,0.95); i++;
      if(!loop && i>=ns.length && loopTimer){clearInterval(loopTimer);loopTimer=null;} }
    step(); loopTimer=setInterval(step,175); if(loop)setMode("loop"); }

  var LOW=48,HIGH=84,WHITE=[0,2,4,5,7,9,11];
  function drawKeyboard(container,voicedMidis,degByMidi){
    container.innerHTML="";
    var whites=[],blacks=[],wi=0;
    for(var m=LOW;m<=HIGH;m++){ var pc=m%12;
      if(WHITE.indexOf(pc)>=0){whites.push({m:m,i:wi});wi++;}
      else blacks.push({m:m,after:wi-1}); }
    var nW=wi;
    whites.forEach(function(k){
      var el=document.createElement("div"); el.className="kbd-white";
      el.style.left=(k.i/nW*100)+"%"; el.style.width=(100/nW)+"%";
      if(voicedMidis.indexOf(k.m)>=0){ el.className+=" on";
        var d=document.createElement("span"); d.className="kbd-deg";
        d.textContent=degByMidi[k.m]||""; el.appendChild(d); }
      container.appendChild(el);
    });
    blacks.forEach(function(k){
      var el=document.createElement("div"); el.className="kbd-black";
      var bw=100/nW*0.62;
      el.style.left=((k.after+1)/nW*100)+"%"; el.style.width=bw+"%";
      el.style.marginLeft=(-bw/2)+"%";
      if(voicedMidis.indexOf(k.m)>=0){ el.className+=" on";
        var d=document.createElement("span"); d.className="kbd-deg kbd-deg-b";
        d.textContent=degByMidi[k.m]||""; el.appendChild(d); }
      container.appendChild(el);
    });
  }

  var IC=["ic1 (m2/M7)","ic2 (M2/m7)","ic3 (m3/M6)","ic4 (M3/m6)","ic5 (P4/P5)","ic6 (tritone)"];
  function renderDetail(){
    var r=RECIPES[state.name]; if(!r)return;
    var root=ROOTS[state.root], base=48+root.pc;
    var vm=r.offsets.map(function(o){return base+o;});
    var degByMidi={}; r.notes.forEach(function(n){degByMidi[base+n.offset]=n.degree;});
    var chips=r.notes.map(function(n){
      var nm=spell(n.pc,n.step,root.pc,root.l);
      return '<span class="note-chip"><b>'+esc(nm)+'</b><i>'+esc(n.degree)+'</i></span>';
    }).join("");
    var icv=r.icv.map(function(v,i){return '<span class="icv-cell" title="'+IC[i]+'"><b>'+v+'</b><i>'+(i+1)+'</i></span>';}).join("");
    var flags=r.flags.map(function(f){return '<span class="flag">'+esc(f)+'</span>';}).join("");
    var aliases=r.aliases.length?'<div class="d-alias">identical set to '+r.aliases.map(function(a){return '<code>'+esc(a)+'</code>';}).join(", ")+'</div>':"";
    var pcs=r.notes.map(function(n){return n.pc;}).filter(function(v,i,a){return a.indexOf(v)===i;}).sort(function(x,y){return x-y;});
    var c=r.consonance;
    var hf='<sup class="fn"><a href="#ref-'+DATA.huron_ref+'">'+DATA.huron_ref+'</a></sup>';
    var N=24, lit=Math.max(1,Math.round(c.index*N)), segs="";
    var bandCls={consonant:"g",mild:"g",tense:"a",dissonant:"r",harsh:"r"}[c.band]||"a";
    for(var s=0;s<N;s++){ segs+='<div class="led-seg'+(s<lit?" on "+bandCls:"")+'"></div>'; }
    var meter='<div class="cons">'+
      '<div class="cons-head"><span>Consonance / dissonance'+hf+'</span>'+
        '<span class="cons-band">'+esc(c.band)+'</span></div>'+
      '<div class="led-meter">'+segs+'</div>'+
      '<div class="cons-ends"><span>consonant</span><span>dissonant</span></div>'+
      '<div class="cons-read">'+esc(c.reading)+' \u00b7 Huron '+(c.score>=0?"+":"")+c.score.toFixed(2)+'/dyad</div>'+
      '</div>';
    $("detail").innerHTML=
      '<div class="d-head"><div><h2 class="d-name">'+esc(r.name)+'</h2>'+
        '<div class="d-sub">'+esc(r.category)+'</div>'+aliases+'</div>'+
        '<div class="d-badges"><span class="badge">prime '+esc(r.prime)+'</span>'+
        '<span class="badge">Forte '+esc(r.forte)+'</span></div></div>'+
      '<div class="sub">Keyboard</div>'+
      '<div class="kbd" id="kbd"></div>'+
      '<div class="note-row">'+chips+'</div>'+
      '<div class="sub">Transport</div>'+
      '<div class="transport">'+
        '<button class="pbtn" id="p-strike" title="One short chord">\u25b7 Short</button>'+
        '<button class="pbtn" data-mode="sustain" id="p-sustain" title="Hold the chord">\u25b7 Sustain</button>'+
        '<button class="pbtn" id="p-arp" title="Arpeggiate once">\u25b7 Arpeggio</button>'+
        '<button class="pbtn" data-mode="loop" id="p-loop" title="Repeat the arpeggio">\u21bb Loop</button>'+
        '<button class="pbtn stop" id="p-stop" title="Stop">\u25a0</button>'+
        '<span class="play-hint">root '+esc(root.n)+'</span></div>'+
      (r.description?'<div class="d-desc">'+r.description+'</div>':"")+
      meter+
      '<div class="sub">Set-class analysis</div>'+
      '<dl class="d-analysis">'+
        '<dt>Pitch-class set</dt><dd>{'+pcs.join(", ")+'}</dd>'+
        '<dt>Prime form</dt><dd>'+esc(r.prime)+'</dd>'+
        '<dt>Forte number</dt><dd>'+esc(r.forte)+'</dd>'+
        '<dt>Interval-class vector</dt><dd class="icv-row">'+icv+'</dd>'+
        '<dt>Stacked intervals</dt><dd>'+esc(r.intervals.join(" \u00b7 "))+'</dd>'+
        (flags?'<dt>Character</dt><dd class="flag-row">'+flags+'</dd>':"")+
      '</dl>';
    drawKeyboard($("kbd"),vm,degByMidi);
    $("p-strike").onclick=doStrike;
    $("p-sustain").onclick=doSustain;
    $("p-arp").onclick=function(){doArp(false);};
    $("p-loop").onclick=function(){ if(mode==="loop")stopAll(); else doArp(true); };
    $("p-stop").onclick=stopAll;
    var btns=document.querySelectorAll(".idx-item");
    for(var i=0;i<btns.length;i++)btns[i].classList.toggle("active",btns[i].dataset.name===state.name);
  }

  function buildIndex(){
    var idx=$("index");
    CATS.forEach(function(cat){
      var h=document.createElement("div"); h.className="idx-cat"; h.textContent=cat.title; idx.appendChild(h);
      cat.names.forEach(function(name){
        var b=document.createElement("button"); b.className="idx-item"; b.type="button";
        b.dataset.name=name; b.textContent=name;
        b.addEventListener("click",function(){select(name);});
        idx.appendChild(b);
      });
    });
  }
  function select(name){ if(!RECIPES[name])return; stopAll(); state.name=name; renderDetail();
    var el=document.querySelector('.idx-item[data-name="'+name+'"]');
    if(el&&el.scrollIntoView)el.scrollIntoView({block:"nearest"});
    if(history.replaceState)history.replaceState(null,"","#"+name);
  }
  function knobRot(i){ return -150 + i*(300/11); }   // degrees for root index 0..11
  function updateRootUI(){
    var d=$("rootdial"); if(d)d.style.transform="rotate("+knobRot(state.root)+"deg)";
    var led=$("rootled"); if(led)led.textContent=ROOTS[state.root].n;
    var k=$("rootknob"); if(k)k.setAttribute("aria-valuenow",state.root);
  }
  function setRoot(i){ state.root=((i%12)+12)%12; stopAll(); updateRootUI(); renderDetail(); }
  function buildKnob(){
    var k=$("rootknob"); if(!k)return;
    k.addEventListener("click",function(){setRoot(state.root+1);});
    k.addEventListener("contextmenu",function(e){e.preventDefault();setRoot(state.root-1);});
    k.addEventListener("wheel",function(e){e.preventDefault();setRoot(state.root+(e.deltaY<0?1:-1));},{passive:false});
    k.addEventListener("keydown",function(e){
      if(e.key==="ArrowUp"||e.key==="ArrowRight"){e.preventDefault();setRoot(state.root+1);}
      else if(e.key==="ArrowDown"||e.key==="ArrowLeft"){e.preventDefault();setRoot(state.root-1);}});
    updateRootUI();
  }
  function wireFilter(){
    $("filter").addEventListener("input",function(){
      var q=this.value.toLowerCase().trim();
      document.querySelectorAll(".idx-item").forEach(function(b){
        var r=RECIPES[b.dataset.name];
        var hay=(b.dataset.name+" "+r.forte+" "+r.prime+" "+r.flags.join(" ")+" "+r.category).toLowerCase();
        b.style.display=(!q||hay.indexOf(q)>=0)?"":"none";
      });
    });
  }
  function init(){
    buildKnob(); buildIndex(); wireFilter();
    var start=decodeURIComponent((location.hash||"").slice(1));
    if(!RECIPES[start])start=CATS[0].names[0];
    select(start);
    ["pointerdown","keydown"].forEach(function(ev){
      window.addEventListener(ev,function(){if(AC&&AC.state!=="running")AC.resume();},{passive:true});});
    window.__chords=function(){return {recipe:state.name,root:ROOTS[state.root].n,
      voiced:voiced(),audio:AC?AC.state:null,count:Object.keys(RECIPES).length};};
  }
  init();
})();
