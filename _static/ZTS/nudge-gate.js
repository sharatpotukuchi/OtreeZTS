(function(){
  const qs = new URLSearchParams(location.search);
  const PID  = qs.get('pid');
  const COND = Number(qs.get('cond') || 0);

  window.NUDGE_STATE = { pid: PID, cond: COND };

  function enableNudges() {
    const p = window.NUDGE_STATE;
    // hook your existing event emitters here
    window.ZTS.on('orderFilled',  (e)=> maybeNudge('orderFilled', e));
    window.ZTS.on('drawdown',     (e)=> maybeNudge('drawdown', e));
    window.ZTS.on('heartbeat5s',  (e)=> maybeNudge('heartbeat', e));
    document.getElementById('nudge-chat')?.classList.remove('hidden');
  }
  function disableNudges() {
    document.getElementById('nudge-chat')?.classList.add('hidden');
    window.ZTS?.offAll?.(); // or remove the specific listeners
  }
  async function maybeNudge(eventType, payload){
    const p = window.NUDGE_STATE;
    if (p.cond !== 1) return; // hard gate
    try{
      const res = await fetch(`${window.NUDGE_API || ''}/nudges`, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          pid:p.pid, cond:p.cond, event_type:eventType,
          features:payload || {}
        })
      });
      if(!res.ok) return;
      const msg = await res.json();
      if(msg?.nudge_text){
        window.ChatPane?.push(msg.nudge_text, { badge: msg.bias_tag || 'Nudge' });
      }
    }catch(e){}
  }

  if (COND === 1) enableNudges(); else disableNudges();
})();
