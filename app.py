
import streamlit as st
import pandas as pd
import json, uuid
from datetime import datetime, timezone

st.set_page_config(page_title="Revenue Recovery 0.4.9.1", layout="wide")
PROFILES=pd.read_csv("business_profiles.csv")
OPPS=pd.read_csv("baseline_opportunities.csv")
LK={"low":0.35,"medium":0.60,"high":0.82}
TRADE_RULES={
 "Plumbing":{"completed plumbing work","drain cleaning","service call","annual maintenance"},
 "HVAC":{"HVAC replacement","furnace replacement","annual maintenance","service call"},
 "Electrical":{"electrical panel upgrade","service call","annual maintenance"},
 "Roofing":{"roof replacement","service call"},
 "Multi-trade":set(OPPS["service_category"].tolist())
}

def urgency(o):
    if o["opportunity_type"]=="lead": return min(1,.75+.08*o["age_days"])
    if o["opportunity_type"]=="estimate": return min(1,.35+.035*o["age_days"]+.02*o["days_since_contact"])
    if o["opportunity_type"]=="invoice": return min(1,.35+.012*o["days_overdue"])
    if o["opportunity_type"]=="repeat_service": return min(1,.40+.02*o["age_days"])
    return .5

def customer_value(o):
    return min(1,(.70 if o["customer_type"]=="existing" else .35)+.04*o["prior_jobs"])

def seasonal_context(o,p):
    trade=p["trade"]; service=o["service_category"].lower(); event=o["weather_event_type"].lower(); season=o["current_season"].lower()
    mod=1.; reason="Neutral context"
    if trade=="HVAC":
        if "furnace" in service and season=="fall": mod+=.10; reason="Heating-season relevance"
        elif "hvac replacement" in service and season=="fall": mod+=.04; reason="Shoulder-season HVAC relevance"
        if "cold snap" in event and ("furnace" in service or "heating" in service): mod+=.06; reason="Heating-season + cold-weather relevance"
    elif trade=="Roofing":
        if "roof" in service and ("storm" in event or "wind" in event): mod+=.14; reason="Storm/wind event relevance"
        if season=="fall" and "roof" in service: mod+=.03; reason="Storm/wind + pre-winter timing"
    elif trade=="Plumbing" and ("cold" in event or "freeze" in event):
        mod+=.05; reason="Freeze-related plumbing relevance"
    elif trade=="Electrical" and ("power" in event or "storm" in event):
        mod+=.05; reason="Event-driven electrical relevance"
    elif trade=="Multi-trade":
        if "furnace" in service and ("cold" in event or season=="fall"): mod+=.06; reason="Heating context"
        if "roof" in service and ("storm" in event or "wind" in event): mod+=.08; reason="Roofing event context"
    return max(.90,min(1.18,mod)),reason

# Stable synthetic reference anchors. These are experimental engineering defaults,
# not universal industry thresholds. They avoid a score changing merely because an
# unrelated extreme-valued opportunity enters or leaves today's queue.
VALUE_ANCHORS={"cash":5000.0,"profit":5000.0,"growth":15000.0}

def anchored_scale(value,anchor):
    return max(0.0,min(1.0,float(value)/float(anchor)))

def value_vector(o,eligible):
    gp=float(o["amount"])*float(o["expected_margin"])
    collectible=float(o["unpaid_balance"]) if o["opportunity_type"]=="invoice" else 0.0
    return {
      "cash":anchored_scale(collectible,VALUE_ANCHORS["cash"]),
      "profit":anchored_scale(gp,VALUE_ANCHORS["profit"]),
      "growth":anchored_scale(float(o["amount"]),VALUE_ANCHORS["growth"])
    }

def objective_alignment(o):
    gp=float(o["amount"])*float(o["expected_margin"])
    return {
      "improve_cash_flow":min(1,(float(o["unpaid_balance"])/5000) if float(o["unpaid_balance"]) else .15),
      "recover_unsold_estimates":1. if o["opportunity_type"]=="estimate" else .10,
      "maximize_profitable_work":min(1,gp/4000),
      "fill_available_capacity":1. if o["scheduling_feasibility"]=="high" else .55 if o["scheduling_feasibility"]=="medium" else .20,
      "retain_valuable_customers":customer_value(o),
      "prevent_stale":urgency(o),
      "grow_revenue":min(1,float(o["amount"])/10000)*LK[o["responsiveness"]],
      "reduce_staff_time":min(1,(gp/max(1,float(o["estimated_staff_effort_minutes"])))/120)
    }

def value_for(vv,obj):
    if obj=="improve_cash_flow": return vv["cash"]
    if obj=="maximize_profitable_work": return vv["profit"]
    if obj in ("grow_revenue","recover_unsold_estimates","fill_available_capacity"): return vv["growth"]
    return (vv["profit"]+vv["growth"])/2

def feasibility(o,p):
    office=o["opportunity_type"]=="invoice" or o["required_skill"]=="office"
    cap=.95 if office else {"plenty":1.,"some_availability":.85,"limited":.55,"none":.20}.get(p["capacity_status"],.70)
    sched={"high":1.,"medium":.70,"low":.35}.get(o["scheduling_feasibility"],.5)
    geo={"high":1.,"medium":.75}.get(o["geographic_fit"],.6)
    x=.5*cap+.3*sched+.2*geo
    if p["workload"]=="busy" and not office: x*=.8
    if x>=.8: b="Ready now"
    elif x>=.55: b="Pursue now; execution may need scheduling"
    elif x>=.35: b="Preserve opportunity; delay execution"
    else: b="Do not promise immediate execution"
    return x,b

def queue(p):
    eligible=OPPS[OPPS["service_category"].isin(TRADE_RULES[p["trade"]])].copy()
    rows=[]
    for _,o in eligible.iterrows():
        vv=value_vector(o,eligible)
        al=objective_alignment(o)
        ba=.5*al[p["priority_1"]]+.3*al[p["priority_2"]]+.2*al[p["priority_3"]]
        ov=.5*value_for(vv,p["priority_1"])+.3*value_for(vv,p["priority_2"])+.2*value_for(vv,p["priority_3"])
        lk=LK[o["responsiveness"]]; ur=urgency(o); cv=customer_value(o); sm,sr=seasonal_context(o,p)
        contrib={"Objective-specific economic value":.35*ov,"Likelihood":.20*lk,"Urgency":.20*ur,"Customer value":.10*cv,"Business alignment":.15*ba}
        score=sum(contrib.values())*sm
        if p["cash_flow_pressure"]=="high" and o["opportunity_type"]=="invoice": score*=1.05
        elif p["cash_flow_pressure"]=="low" and o["opportunity_type"]=="invoice": score*=.98
        fs,fb=feasibility(o,p)
        top=sorted(contrib.items(),key=lambda x:x[1],reverse=True)
        rows.append({"opportunity_id":o["opportunity_id"],"title":o["title"],"amount":o["amount"],"score":score,
                     "confidence":"Moderate","action_band":fb,"seasonal_reason":sr,
                     "top_contributor":top[0][0],"second_contributor":top[1][0],"contrib_json":json.dumps(contrib)})
    q=pd.DataFrame(rows).sort_values("score",ascending=False).reset_index(drop=True)
    q["rank"]=range(1,len(q)+1)
    if len(q)>1:
        gap=(q.iloc[0]["score"]-q.iloc[1]["score"])/max(q.iloc[0]["score"],1e-9)
        q.loc[0,"confidence"]="Low" if gap<.03 else ("High" if gap>=.08 else "Moderate")
    return q,eligible

def persist(payload):
    st.session_state.setdefault("local_submissions",[]).append(payload)
    try:
        from supabase import create_client
        c=create_client(st.secrets["supabase"]["url"],st.secrets["supabase"]["anon_key"])
        c.table("validation_submissions").insert(payload, returning="minimal").execute()
        return True,"Saved to validation database."
    except Exception:
        return False,"Saved in this session only. Persistent database is not configured yet."

st.title("Revenue Recovery 0.4.9.1")
st.caption("Validation-ready candidate — fictional data only")

if "review_id" not in st.session_state:
    st.session_state.review_id=str(uuid.uuid4())

with st.sidebar:
    selected=st.selectbox("Controlled business profile",PROFILES["label"].tolist())
    p=PROFILES.loc[PROFILES["label"]==selected].iloc[0].to_dict()
    role=st.selectbox("Your role",["Owner","General manager","Office/dispatch manager","Estimator/sales","Bookkeeping/accounting","Operations","Other"])
    experience=st.selectbox("Industry experience",["<1 year","1–3 years","4–7 years","8+ years","Prefer not to say"])
    st.write(f"Trade: **{p['trade']}**")
    st.write(f"Capacity: **{p['capacity_status']}**")
    st.write(f"Cash pressure: **{p['cash_flow_pressure']}**")

q,eligible=queue(p)
seed=abs(hash((st.session_state.review_id,p["business_id"])))%(2**32)
shuffled=eligible.sample(frac=1,random_state=seed).reset_index(drop=True)

st.subheader("Step 1 — Rank independently")
st.info("Rank these fictional opportunities before seeing Revenue Recovery's ranking.")
st.dataframe(shuffled[["title","opportunity_type","amount","age_days","days_overdue","responsiveness","scheduling_feasibility"]],hide_index=True,use_container_width=True)

labels=shuffled["title"].tolist()
chosen=[]
remaining=labels[:]
for i in range(len(labels)):
    pick=st.selectbox(f"Your rank #{i+1}",remaining,key=f"{p['business_id']}_rank_{i}")
    chosen.append(pick)
    remaining=[x for x in remaining if x!=pick]
blind_comment=st.text_area("What mattered most in your ranking? (optional)",key=f"{p['business_id']}_blind_comment")

if st.button("Lock my independent ranking"):
    st.session_state[f"locked_{p['business_id']}"]=True
    st.session_state[f"human_{p['business_id']}"]=chosen
    st.session_state[f"blind_{p['business_id']}"]=blind_comment
    st.success("Independent ranking locked.")

if st.session_state.get(f"locked_{p['business_id']}"):
    st.divider()
    st.subheader("Step 2 — Revenue Recovery's ranking")
    show=q[["rank","title","amount","action_band","confidence"]].copy()
    show["amount"]=show["amount"].map(lambda x:f"${x:,.0f}")
    st.dataframe(show,hide_index=True,use_container_width=True)

    top=q.iloc[0]
    if top["confidence"]=="Low":
        st.warning("Top opportunities are effectively close; treat the ranking as uncertain.")

    st.write(f"**Why #1:** largest weighted contributors are **{top['top_contributor']}** and **{top['second_contributor']}**.")
    st.write(f"**Context:** {top['seasonal_reason']}. **Action feasibility:** {top['action_band']}.")

    with st.expander("Weighted contribution details"):
        d=json.loads(top["contrib_json"])
        st.dataframe(pd.DataFrame({"Factor":d.keys(),"Weighted contribution":[round(v,3) for v in d.values()]}),hide_index=True,use_container_width=True)

    human=st.session_state[f"human_{p['business_id']}"]
    model=q["title"].tolist()
    exact=sum(1 for i,x in enumerate(human) if model[i]==x)
    st.write(f"Position-by-position agreement: **{exact}/{len(model)}**")

    st.subheader("Step 3 — Review the disagreement/agreement")
    agreement=st.selectbox("How well does the model reflect your judgment?",["Very well","Mostly well","Mixed","Mostly poorly","Very poorly"])
    override=st.selectbox("Would you change the model's top recommendation?",["No","Yes"])
    reason=st.selectbox("Main reason",["No override reason","Cash flow","Customer relationship","Crew availability","Higher margin","Seasonal consideration","Strategic customer","Missing information","Owner judgment","Other"])
    post_comment=st.text_area("What is the model missing or getting wrong? (optional)")

    if st.button("Submit review"):
        payload={
          "review_id":st.session_state.review_id,
          "submitted_at":datetime.now(timezone.utc).isoformat(),
          "prototype_version":"0.4.9.1",
          "business_profile_id":p["business_id"],
          "reviewer_role":role,
          "experience_band":experience,
          "randomized_order":shuffled["opportunity_id"].tolist(),
          "human_ranking_titles":human,
          "human_ranking_ids":[eligible.loc[eligible["title"]==t,"opportunity_id"].iloc[0] for t in human],
          "model_ranking_ids":q["opportunity_id"].tolist(),
          "model_confidence_top":top["confidence"],
          "agreement_response":agreement,
          "override_top":override,
          "override_reason":reason,
          "blind_comment":st.session_state[f"blind_{p['business_id']}"],
          "post_model_comment":post_comment,
          "synthetic_data_only":True
        }
        _,msg=persist(payload)
        st.success(msg)
        st.caption("Agreement is evidence, not proof of correctness.")

st.divider()
st.caption("No real customer data. No autonomous actions. No causal revenue claims.")
