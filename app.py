
import streamlit as st
import pandas as pd
import json, uuid
from datetime import datetime, timezone

st.set_page_config(page_title="Revenue Recovery", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root{--bg:#f6f8fb;--card:#fff;--text:#172033;--muted:#667085;--border:#e6eaf0;--accent:#2457d6;--soft:#eef3ff;--good:#137a5b;--warn:#a15c00}
.stApp{background:var(--bg);color:var(--text)}
.block-container{max-width:1180px;padding-top:2rem;padding-bottom:4rem}
[data-testid="stSidebar"]{background:#fff;border-right:1px solid var(--border)}
h1,h2,h3{letter-spacing:-.02em}
.rr-hero{background:linear-gradient(135deg,#fff 0%,#f3f6ff 100%);border:1px solid var(--border);border-radius:22px;padding:28px 30px;margin-bottom:20px;box-shadow:0 8px 28px rgba(23,32,51,.05)}
.rr-eyebrow{display:inline-block;font-size:.75rem;font-weight:800;color:var(--accent);background:var(--soft);border-radius:999px;padding:5px 10px;margin-bottom:10px;text-transform:uppercase;letter-spacing:.05em}
.rr-title{font-size:2.05rem;font-weight:850;margin:0 0 8px;color:var(--text)}
.rr-sub{color:var(--muted);max-width:760px;font-size:1rem;line-height:1.55;margin:0}
.rr-stepbar{display:flex;gap:10px;margin:12px 0 22px;flex-wrap:wrap}
.rr-step{flex:1;min-width:180px;background:#fff;border:1px solid var(--border);border-radius:14px;padding:11px 14px;color:var(--muted);font-size:.9rem}
.rr-step.active{border-color:#b8c8ff;background:#f7f9ff;color:var(--accent);font-weight:750}
.rr-step.done{color:var(--good);background:#f4fbf8;border-color:#ccebdd;font-weight:700}
.rr-section{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:21px 23px;margin-bottom:16px;box-shadow:0 4px 16px rgba(23,32,51,.035)}
.rr-section-title{font-size:1.16rem;font-weight:800;margin-bottom:4px}
.rr-section-sub{color:var(--muted);font-size:.92rem}
.rr-scenario{border:1px solid var(--border);border-radius:16px;padding:16px 17px;background:#fff;min-height:165px;box-shadow:0 2px 8px rgba(23,32,51,.025)}
.rr-scenario h4{margin:4px 0 8px;font-size:1rem}
.rr-amount{font-size:1.28rem;font-weight:850;margin:3px 0 10px}
.rr-meta{color:var(--muted);font-size:.84rem;line-height:1.6}
.rr-pill{display:inline-block;border-radius:999px;padding:4px 8px;font-size:.72rem;font-weight:750;background:#f1f4f8;color:#44516a;margin-right:5px;margin-bottom:5px}
.rr-pill.blue{background:var(--soft);color:var(--accent)} .rr-pill.green{background:#eaf8f2;color:var(--good)} .rr-pill.amber{background:#fff5e8;color:var(--warn)}
.rr-queue{background:#fff;border:1px solid var(--border);border-radius:16px;padding:16px 18px;margin-bottom:10px}
.rr-queue.top{border:1.5px solid #9fb5ff;box-shadow:0 4px 18px rgba(36,87,214,.08)}
.rr-rank{font-size:1.5rem;font-weight:850;color:var(--accent)}
.rr-qtitle{font-size:1.02rem;font-weight:800}
.rr-muted{color:var(--muted)}
.rr-note{border-left:4px solid #b8c8ff;background:#f7f9ff;border-radius:10px;padding:12px 14px;color:#34415a;margin:12px 0}
.rr-warning{border-left:4px solid #e3a13b;background:#fff8ee;border-radius:10px;padding:12px 14px;color:#68420e;margin:12px 0}
.rr-context-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.rr-context-item{background:#f7f8fb;border:1px solid #edf0f4;border-radius:10px;padding:9px 10px}
.rr-context-label{color:var(--muted);font-size:.7rem;text-transform:uppercase;letter-spacing:.04em}
.rr-context-value{font-weight:750;margin-top:2px}
div[data-testid="stButton"] button{border-radius:12px;font-weight:750;padding:.55rem 1rem}
div[data-testid="stSelectbox"] label,div[data-testid="stTextArea"] label{font-weight:650;color:#39445a}
@media(max-width:760px){.block-container{padding:1rem .75rem 3rem}.rr-hero{padding:20px 18px;border-radius:16px}.rr-title{font-size:1.55rem}.rr-context-grid{grid-template-columns:1fr}}
</style>
""", unsafe_allow_html=True)

PROFILES=pd.read_csv("business_profiles.csv")
OPPS=pd.read_csv("baseline_opportunities.csv")
LK={"low":.35,"medium":.60,"high":.82}
TRADE_RULES={"Plumbing":{"completed plumbing work","drain cleaning","service call","annual maintenance"},"HVAC":{"HVAC replacement","furnace replacement","annual maintenance","service call"},"Electrical":{"electrical panel upgrade","service call","annual maintenance"},"Roofing":{"roof replacement","service call"},"Multi-trade":set(OPPS["service_category"].tolist())}

def urgency(o):
    if o["opportunity_type"]=="lead": return min(1,.75+.08*o["age_days"])
    if o["opportunity_type"]=="estimate": return min(1,.35+.035*o["age_days"]+.02*o["days_since_contact"])
    if o["opportunity_type"]=="invoice": return min(1,.35+.012*o["days_overdue"])
    if o["opportunity_type"]=="repeat_service": return min(1,.40+.02*o["age_days"])
    return .5

def customer_value(o): return min(1,(.70 if o["customer_type"]=="existing" else .35)+.04*o["prior_jobs"])

def seasonal_context(o,p):
    trade=p["trade"];service=o["service_category"].lower();event=o["weather_event_type"].lower();season=o["current_season"].lower()
    mod=1.;reason="Neutral context"
    if trade=="HVAC":
        if "furnace" in service and season=="fall": mod+=.10;reason="Heating-season relevance"
        elif "hvac replacement" in service and season=="fall": mod+=.04;reason="Shoulder-season HVAC relevance"
        if "cold snap" in event and ("furnace" in service or "heating" in service): mod+=.06;reason="Heating-season + cold-weather relevance"
    elif trade=="Roofing":
        if "roof" in service and ("storm" in event or "wind" in event): mod+=.14;reason="Storm/wind event relevance"
        if season=="fall" and "roof" in service: mod+=.03;reason="Storm/wind + pre-winter timing"
    elif trade=="Plumbing" and ("cold" in event or "freeze" in event): mod+=.05;reason="Freeze-related plumbing relevance"
    elif trade=="Electrical" and ("power" in event or "storm" in event): mod+=.05;reason="Event-driven electrical relevance"
    elif trade=="Multi-trade":
        if "furnace" in service and ("cold" in event or season=="fall"): mod+=.06;reason="Heating context"
        if "roof" in service and ("storm" in event or "wind" in event): mod+=.08;reason="Roofing event context"
    return max(.90,min(1.18,mod)),reason

VALUE_ANCHORS={"cash":5000.,"profit":5000.,"growth":15000.}
def scale(v,a): return max(0.,min(1.,float(v)/float(a)))
def value_vector(o):
    gp=float(o["amount"])*float(o["expected_margin"]);cash=float(o["unpaid_balance"]) if o["opportunity_type"]=="invoice" else 0.
    return {"cash":scale(cash,VALUE_ANCHORS["cash"]),"profit":scale(gp,VALUE_ANCHORS["profit"]),"growth":scale(o["amount"],VALUE_ANCHORS["growth"])}

def objective_alignment(o):
    gp=float(o["amount"])*float(o["expected_margin"])
    return {"improve_cash_flow":min(1,(float(o["unpaid_balance"])/5000) if float(o["unpaid_balance"]) else .15),"recover_unsold_estimates":1. if o["opportunity_type"]=="estimate" else .10,"maximize_profitable_work":min(1,gp/4000),"fill_available_capacity":1. if o["scheduling_feasibility"]=="high" else .55 if o["scheduling_feasibility"]=="medium" else .20,"retain_valuable_customers":customer_value(o),"prevent_stale":urgency(o),"grow_revenue":min(1,float(o["amount"])/10000)*LK[o["responsiveness"]],"reduce_staff_time":min(1,(gp/max(1,float(o["estimated_staff_effort_minutes"])))/120)}

def vfor(vv,obj):
    if obj=="improve_cash_flow": return vv["cash"]
    if obj=="maximize_profitable_work": return vv["profit"]
    if obj in ("grow_revenue","recover_unsold_estimates","fill_available_capacity"): return vv["growth"]
    return (vv["profit"]+vv["growth"])/2

def feasibility(o,p):
    office=o["opportunity_type"]=="invoice" or o["required_skill"]=="office"
    cap=.95 if office else {"plenty":1.,"some_availability":.85,"limited":.55,"none":.20}.get(p["capacity_status"],.70)
    sched={"high":1.,"medium":.70,"low":.35}.get(o["scheduling_feasibility"],.5);geo={"high":1.,"medium":.75}.get(o["geographic_fit"],.6)
    x=.5*cap+.3*sched+.2*geo
    if p["workload"]=="busy" and not office:x*=.8
    if x>=.8:b="Ready now"
    elif x>=.55:b="Pursue now · scheduling needed"
    elif x>=.35:b="Preserve · delay execution"
    else:b="Do not promise immediate execution"
    return x,b

def make_queue(p):
    eligible=OPPS[OPPS["service_category"].isin(TRADE_RULES[p["trade"]])].copy();rows=[]
    for _,o in eligible.iterrows():
        vv=value_vector(o);al=objective_alignment(o);ba=.5*al[p["priority_1"]]+.3*al[p["priority_2"]]+.2*al[p["priority_3"]]
        ov=.5*vfor(vv,p["priority_1"])+.3*vfor(vv,p["priority_2"])+.2*vfor(vv,p["priority_3"])
        lk=LK[o["responsiveness"]];ur=urgency(o);cv=customer_value(o);sm,sr=seasonal_context(o,p)
        contrib={"Objective-specific economic value":.35*ov,"Likelihood":.20*lk,"Urgency":.20*ur,"Customer value":.10*cv,"Business alignment":.15*ba}
        score=sum(contrib.values())*sm
        if p["cash_flow_pressure"]=="high" and o["opportunity_type"]=="invoice":score*=1.05
        elif p["cash_flow_pressure"]=="low" and o["opportunity_type"]=="invoice":score*=.98
        fs,fb=feasibility(o,p);top=sorted(contrib.items(),key=lambda x:x[1],reverse=True)
        rows.append({"opportunity_id":o["opportunity_id"],"title":o["title"],"amount":o["amount"],"score":score,"confidence":"Moderate","action_band":fb,"seasonal_reason":sr,"top1":top[0][0],"top2":top[1][0],"contrib":json.dumps(contrib)})
    q=pd.DataFrame(rows).sort_values("score",ascending=False).reset_index(drop=True);q["rank"]=range(1,len(q)+1)
    if len(q)>1:
        gap=(q.iloc[0]["score"]-q.iloc[1]["score"])/max(q.iloc[0]["score"],1e-9)
        q.loc[0,"confidence"]="Low" if gap<.03 else ("High" if gap>=.08 else "Moderate")
    return q,eligible

def persist(payload):
    st.session_state.setdefault("local_submissions",[]).append(payload)
    try:
        from supabase import create_client
        c=create_client(st.secrets["supabase"]["url"],st.secrets["supabase"]["anon_key"])
        c.table("validation_submissions").insert(payload,returning="minimal").execute()
        return "Review saved securely."
    except Exception:
        return "Review retained in this session only; database connection is not configured."

def pretty(x): return str(x).replace("_"," ").title()

def card(o):
    overdue=f"<span class='rr-pill amber'>{int(o['days_overdue'])} days overdue</span>" if int(o["days_overdue"])>0 else ""
    age=f"{int(o['age_days'])} days old" if int(o["age_days"])>0 else "New today"
    return f"""<div class='rr-scenario'><span class='rr-pill blue'>{pretty(o['opportunity_type'])}</span>{overdue}<h4>{o['title']}</h4><div class='rr-amount'>${float(o['amount']):,.0f}</div><div class='rr-meta'>{age}<br>Responsiveness: <b>{pretty(o['responsiveness'])}</b><br>Scheduling fit: <b>{pretty(o['scheduling_feasibility'])}</b></div></div>"""

if "review_id" not in st.session_state: st.session_state.review_id=str(uuid.uuid4())

st.markdown("<div class='rr-hero'><div class='rr-eyebrow'>Research prototype · Synthetic data</div><div class='rr-title'>Revenue Recovery</div><p class='rr-sub'>Compare your real-world judgment with an explainable revenue-prioritization model. You rank the opportunities first; the model stays hidden until your answer is locked.</p></div>",unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Reviewer setup")
    selected=st.selectbox("Business profile",PROFILES["label"].tolist());p=PROFILES.loc[PROFILES["label"]==selected].iloc[0].to_dict()
    role=st.selectbox("Your role",["Owner","General manager","Office/dispatch manager","Estimator/sales","Bookkeeping/accounting","Operations","Other"])
    exp=st.selectbox("Industry experience",["<1 year","1–3 years","4–7 years","8+ years","Prefer not to say"])
    st.markdown("---");st.markdown("#### Current context")
    st.markdown(f"<div class='rr-context-grid'><div class='rr-context-item'><div class='rr-context-label'>Trade</div><div class='rr-context-value'>{p['trade']}</div></div><div class='rr-context-item'><div class='rr-context-label'>Capacity</div><div class='rr-context-value'>{pretty(p['capacity_status'])}</div></div><div class='rr-context-item'><div class='rr-context-label'>Cash pressure</div><div class='rr-context-value'>{pretty(p['cash_flow_pressure'])}</div></div><div class='rr-context-item'><div class='rr-context-label'>Workload</div><div class='rr-context-value'>{pretty(p['workload'])}</div></div></div>",unsafe_allow_html=True)

q,eligible=make_queue(p);seed=abs(hash((st.session_state.review_id,p["business_id"])))%(2**32);shuffled=eligible.sample(frac=1,random_state=seed).reset_index(drop=True)
locked=st.session_state.get(f"locked_{p['business_id']}",False)
st.markdown(f"<div class='rr-stepbar'><div class='rr-step {'done' if locked else 'active'}'>1 · Rank independently</div><div class='rr-step {'active' if locked else ''}'>2 · Reveal the model</div><div class='rr-step'>3 · Explain disagreement</div></div>",unsafe_allow_html=True)

st.markdown("<div class='rr-section'><div class='rr-section-title'>Step 1 — What would you handle first?</div><div class='rr-section-sub'>Rank these fictional opportunities using your own business judgment. Revenue Recovery's answer is hidden until you lock yours.</div></div>",unsafe_allow_html=True)
for i in range(0,len(shuffled),2):
    cols=st.columns(2,gap="medium")
    for j,c in enumerate(cols):
        if i+j<len(shuffled):
            with c:st.markdown(card(shuffled.iloc[i+j]),unsafe_allow_html=True)

st.markdown("#### Your ranking")
labels=shuffled["title"].tolist();chosen=[];remaining=labels[:]
for i in range(len(labels)):
    pick=st.selectbox(f"#{i+1}",remaining,key=f"{p['business_id']}_rank_{i}",disabled=locked);chosen.append(pick);remaining=[x for x in remaining if x!=pick]
blind=st.text_area("What mattered most in your ranking? (optional)",key=f"{p['business_id']}_blind",placeholder="Cash flow, urgency, customer relationship, crew availability...",disabled=locked)
if not locked and st.button("Lock my ranking and reveal the model",type="primary",use_container_width=True):
    st.session_state[f"locked_{p['business_id']}"]=True;st.session_state[f"human_{p['business_id']}"]=chosen;st.session_state[f"blind_saved_{p['business_id']}"]=blind;st.rerun()

if locked:
    st.markdown("<div class='rr-section'><div class='rr-section-title'>Step 2 — Revenue Recovery's Revenue Queue</div><div class='rr-section-sub'>Compare your independent judgment with the model. Commercial priority and immediate action feasibility are separated.</div></div>",unsafe_allow_html=True)
    for _,r in q.iterrows():
        tc=" top" if int(r["rank"])==1 else "";pc="green" if r["confidence"]=="High" else ("amber" if r["confidence"]=="Low" else "blue")
        st.markdown(f"<div class='rr-queue{tc}'><div style='display:flex;gap:14px'><div class='rr-rank'>#{int(r['rank'])}</div><div><div class='rr-qtitle'>{r['title']}</div><div class='rr-muted' style='margin:4px 0 8px'>${float(r['amount']):,.0f}</div><span class='rr-pill {pc}'>Confidence: {r['confidence']}</span><span class='rr-pill'>{r['action_band']}</span></div></div></div>",unsafe_allow_html=True)
    top=q.iloc[0]
    if top["confidence"]=="Low":st.markdown("<div class='rr-warning'><b>Near tie:</b> the leading opportunities are close. The model should not be treated as having a strong winner.</div>",unsafe_allow_html=True)
    st.markdown(f"<div class='rr-note'><b>Why #1:</b> the strongest weighted contributors are <b>{top['top1']}</b> and <b>{top['top2']}</b>. Context: <b>{top['seasonal_reason']}</b>.</div>",unsafe_allow_html=True)
    with st.expander("See how the top recommendation was calculated"):
        for factor,value in json.loads(top["contrib"]).items():
            st.write(f"**{factor}**");st.progress(min(1.,max(0.,float(value)/.35)));st.caption(f"Weighted contribution: {float(value):.3f}")
    human=st.session_state[f"human_{p['business_id']}"];model=q["title"].tolist();exact=sum(1 for i,x in enumerate(human) if model[i]==x)
    c1,c2=st.columns(2);c1.metric("Position agreement",f"{exact}/{len(model)}");c2.metric("Top confidence",top["confidence"])
    st.markdown("<div class='rr-section'><div class='rr-section-title'>Step 3 — Where does the model differ from you?</div><div class='rr-section-sub'>Disagreement is useful evidence. It does not automatically mean either side is wrong.</div></div>",unsafe_allow_html=True)
    agreement=st.selectbox("How well does the model reflect your judgment?",["Very well","Mostly well","Mixed","Mostly poorly","Very poorly"])
    override=st.selectbox("Would you change the model's top recommendation?",["No","Yes"])
    reason=st.selectbox("Main reason",["No override reason","Cash flow","Customer relationship","Crew availability","Higher margin","Seasonal consideration","Strategic customer","Missing information","Owner judgment","Other"])
    post=st.text_area("What is the model missing or getting wrong? (optional)")
    if st.button("Submit review",type="primary",use_container_width=True):
        payload={"review_id":st.session_state.review_id,"submitted_at":datetime.now(timezone.utc).isoformat(),"prototype_version":"0.4.9.1","business_profile_id":p["business_id"],"reviewer_role":role,"experience_band":exp,"randomized_order":shuffled["opportunity_id"].tolist(),"human_ranking_titles":human,"human_ranking_ids":[eligible.loc[eligible["title"]==t,"opportunity_id"].iloc[0] for t in human],"model_ranking_ids":q["opportunity_id"].tolist(),"model_confidence_top":top["confidence"],"agreement_response":agreement,"override_top":override,"override_reason":reason,"blind_comment":st.session_state[f"blind_saved_{p['business_id']}"],"post_model_comment":post,"synthetic_data_only":True}
        st.success(persist(payload));st.caption("Agreement is evidence, not proof of correctness.")

st.markdown("<div style='height:24px'></div>",unsafe_allow_html=True)
st.caption("Experimental validation build · No real customer data · No autonomous actions · No causal revenue claims")
