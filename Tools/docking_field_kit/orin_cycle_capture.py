"""1사이클 take(4s)->release 를 양 버스 전체 캡처·health·steer·Seer 알람과 함께 기록한다 (debt-129/130 검증용)."""
import sys, time, json, collections
sys.path.insert(0,"/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Tools/docking_field_kit")
sys.path.insert(0,"/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/src/Comm/TCP_IP/seer_api")
from orin_home_experiment import Rig
from seer_api.api import SeerApi
seer=SeerApi("192.168.44.82",timeout=3.0)
def steer():
    try: return seer.get_speed().get('steer_angles')
    except Exception as e: return None
def alarms():
    try:
        a=seer.get_alarms(); out=[]
        for k in ("fatals","errors","warnings"):
            for e in (a.get(k) or []):
                out.append((k[0].upper(),e.get('code'),(e.get('desc') or e.get('info') or '')[-70:]))
        return out
    except Exception as ex: return [("X",-1,str(ex)[:40])]
stamp=time.strftime("%y%m%d_%H%M%S")
LOG="/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Log/e1_all_%s.jsonl"%stamp
rig=Rig("/home/nvidia/Project/Ford-CATL-AMR/Big-AMR/Log/e1_rig_%s.jsonl"%stamp)
p=rig.p; out=open(LOG,"w"); T0=time.time()
def cap(dur, phase):
    t_end=time.time()+dur; n=collections.Counter()
    while time.time()<t_end:
        with rig._io: rx=p.can_recv()
        t=round(time.time()-T0,4)
        for a,_,d,b in rx:
            out.write(json.dumps({"t":t,"ph":phase,"b":b,"id":a,"d":bytes(d).hex()})+"\n")
            n[b]+=1
        time.sleep(0.002)
    return dict(n)
h=p.health(); print("HEALTH0 harness=%s safety=%s"%(h.get("car_harness_status"),h.get("safety_mode")),flush=True)
base_al=alarms(); print("ALARMS0",base_al,flush=True)
print("STEER0",steer(),flush=True)
print("pre-capture 2s:",cap(2.0,"idle"),flush=True)
rig.take(settle=0.2)          # 0.2 s settle (drain inside), then our own capture
t_take=time.time()-T0
h=p.health(); print("HEALTH_ENG harness=%s safety=%s hb_lost=%s"%(h.get("car_harness_status"),h.get("safety_mode"),h.get("heartbeat_lost")),flush=True)
print("engage capture 4s:",cap(4.0,"eng"),flush=True)
h=p.health(); print("HEALTH_ENG2 safety=%s hb_lost=%s"%(h.get("safety_mode"),h.get("heartbeat_lost")),flush=True)
t_rel=time.time()-T0
rig.release()
print("t_take=%.3f t_rel=%.3f"%(t_take,t_rel),flush=True)
# post-release: capture + steer polling for up to 45 s (homing takes ~35 s if it starts)
mx=0.0; started=False; t_end=time.time()+45
while time.time()<t_end:
    cap(0.5,"post")
    sa=steer()
    try:
        m=max(abs(x) for x in sa); mx=max(mx,m)
        if m>0.2 and not started: started=True; print("  >>> steer moved %.3f rad at t=%.2f (release+%.2f)"%(m,time.time()-T0,time.time()-T0-t_rel),flush=True)
        if started and m<0.05 and time.time()-T0-t_rel>5: print("  steer back to %.3f at release+%.2f"%(m,time.time()-T0-t_rel),flush=True); break
        if not started and time.time()-T0-t_rel>12: break
    except Exception: pass
out.close()
print("RESULT max|steer|=%.3f rad -> %s"%(mx,"재호밍" if mx>0.2 else "PASS"),flush=True)
new_al=[a for a in alarms() if a not in base_al]; print("NEW_ALARMS",new_al,flush=True)
h=p.health(); print("HEALTH_END harness=%s safety=%s"%(h.get("car_harness_status"),h.get("safety_mode")),flush=True)
rig.close()
# quick signature summary
rows=[json.loads(l) for l in open(LOG)]
for ph in ("idle","eng","post"):
    c=collections.Counter()
    for r in rows:
        if r["ph"]!=ph: continue
        i=r["id"]; b=r["b"]
        k="req" if 0x601<=i<=0x604 else "resp" if 0x581<=i<=0x584 else "guard" if 0x701<=i<=0x704 else "emcy" if 0x81<=i<=0x84 else "other"
        c[(b,k)]+=1
    print("SIG",ph,dict(sorted(c.items())),flush=True)
print("LOG",LOG)
