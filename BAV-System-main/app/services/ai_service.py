"""
app/services/ai_service.py — Ollama (primary) + OpenRouter (fallback) + rule-based (always)
"""
import sys, json, logging
from pathlib import Path
from typing import Optional
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import OPENROUTER_API_KEY, OPENROUTER_URL, AI_MODEL

log = logging.getLogger(__name__)
OLLAMA_URL   = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3:latest"

def _call_ollama(system_prompt: str, user_message: str) -> Optional[str]:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role":"system","content":system_prompt},{"role":"user","content":user_message}],
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 400},
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(60.0)) as c:
            r = c.post(OLLAMA_URL, json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
    except httpx.ConnectError:
        log.warning("Ollama not running — falling back to OpenRouter")
        return None
    except Exception as e:
        log.warning(f"Ollama error: {e}")
        return None

def _call_openrouter(system_prompt: str, user_message: str) -> Optional[str]:
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_key_here":
        return None
    headers = {"Authorization":f"Bearer {OPENROUTER_API_KEY}","Content-Type":"application/json","HTTP-Referer":"https://shikshasgaurd.gov.in","X-Title":"ShikshaGaurd"}
    payload = {"model":AI_MODEL,"messages":[{"role":"system","content":system_prompt},{"role":"user","content":user_message}],"max_tokens":500,"temperature":0.3}
    try:
        with httpx.Client(timeout=httpx.Timeout(30.0)) as c:
            r = c.post(OPENROUTER_URL, json=payload, headers=headers)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.warning(f"OpenRouter error: {e}")
        return None

def _call_ai(system_prompt: str, user_message: str) -> Optional[str]:
    return _call_ollama(system_prompt, user_message) or _call_openrouter(system_prompt, user_message)

def summarize_proposal(proposal_letter: str, structured_fields: dict) -> str:
    if not proposal_letter or len(proposal_letter.strip()) < 50:
        return _build_fallback_summary(structured_fields)
    sys_p = "You are an education ministry official reviewing school infrastructure proposals in India. Respond in exactly 3 bullet points:\n• Problem: [issue described]\n• Ask: [what is requested and amount]\n• Justification: [evidence provided]\nBe concise. No preamble."
    usr_p = f"School: {structured_fields.get('school_name','?')}\nIntervention: {structured_fields.get('intervention_type','?')}\nFunding: Rs{structured_fields.get('funding_requested',0):,.0f}\n\nLetter:\n{proposal_letter[:2000]}"
    return _call_ai(sys_p, usr_p) or _build_fallback_summary(structured_fields)

def explain_decision(verdict: str, confidence: float, violations: list, school_data: dict, proposal_data: dict) -> str:
    sys_p = "You are an AI assistant for the Samagra Shiksha validation system. Write a clear official explanation for a funding decision. Be direct. No sympathy. 3 sentences max. Third person. Reference Samagra Shiksha norms."
    critical = [v for v in violations if v.get("severity")=="critical"]
    warnings = [v for v in violations if v.get("severity")=="warning"]
    vtext = ""
    if critical: vtext += "Critical: "+"; ".join(v["message"] for v in critical[:3])+". "
    if warnings:  vtext += "Warnings: "+"; ".join(v["message"] for v in warnings[:3])+"."
    usr_p = f"Decision: {verdict} ({confidence*100:.0f}% confidence)\nSchool: {school_data.get('school_level','?')}, {school_data.get('total_students',0):.0f} students, PTR {school_data.get('ptr',0):.1f}\nRequest: {proposal_data.get('intervention_type','?')} Rs{proposal_data.get('funding_requested',0):,.0f}\n{vtext}\nWrite official explanation."
    result = _call_ai(sys_p, usr_p)
    if result and not result.startswith("AI service"):
        return result
    return generate_rule_based_explanation(verdict, confidence, violations, school_data, proposal_data)

def estimate_budget(proposal_data: dict, school_data: dict) -> dict:
    intervention = proposal_data.get("intervention_type","")
    dynamic      = proposal_data.get("dynamic_fields",{})
    sys_p = "You are a financial estimator for Indian government school infrastructure. Return ONLY valid JSON with keys: min_estimate, max_estimate, recommended (all integers in INR), reasoning (one sentence). No markdown."
    usr_p = f"Intervention: {intervention}\nFields: {json.dumps(dynamic)}\nSchool: {school_data.get('school_level','?')}, {school_data.get('total_students',0)} students, Delhi SOR 2024-25\nRequested: Rs{proposal_data.get('funding_requested',0):,.0f}\nEstimate realistic budget range."
    result = _call_ai(sys_p, usr_p)
    if result:
        try:
            clean = result.replace("```json","").replace("```","").strip()
            parsed = json.loads(clean)
            parsed["currency"] = "INR"
            parsed["source"]   = "AI"
            return parsed
        except Exception:
            pass
    return _sor_fallback_estimate(intervention, dynamic)

def _sor_fallback_estimate(intervention: str, dynamic: dict) -> dict:
    from config import INTERVENTION_COST_NORMS
    norm = INTERVENTION_COST_NORMS.get(intervention)
    if norm:
        units = max(int(dynamic.get("classrooms_requested",dynamic.get("rooms_to_repair",dynamic.get("toilet_seats_requested",dynamic.get("devices_requested",1))))),1)
        units = min(units, norm["max_units"])
        base  = norm["per_unit"] * units
        return {"min_estimate":int(base*0.75),"max_estimate":int(base*1.35),"recommended":int(base),"reasoning":f"SOR: Rs{norm['per_unit']:,}/unit x {units} units","currency":"INR","source":"SOR fallback"}
    return {"min_estimate":50000,"max_estimate":500000,"recommended":100000,"reasoning":"Default estimate","currency":"INR","source":"default"}

def generate_rule_based_explanation(verdict: str, confidence: float, violations: list, school_data: dict=None, proposal_data: dict=None) -> str:
    school_data   = school_data   or {}
    proposal_data = proposal_data or {}
    intervention  = proposal_data.get("intervention_type","")
    lines = []
    conf_pct = f"{confidence*100:.0f}%"

    # Opening verdict sentence
    if verdict=="Reject":   lines.append(f"The {intervention} proposal has been REJECTED ({conf_pct} confidence). Critical violations must be resolved before resubmission.")
    elif verdict=="Flag":   lines.append(f"The {intervention} proposal has been FLAGGED for review ({conf_pct} confidence). The following issues require clarification.")
    else:                   lines.append(f"The {intervention} proposal has been ACCEPTED ({conf_pct} confidence). All Samagra Shiksha criteria have been met.")

    # Supporting evidence (sanitation proposals)
    supporting = [v for v in violations if v.get("severity")=="supporting"]
    critical   = [v for v in violations if v.get("severity")=="critical"]
    warnings   = [v for v in violations if v.get("severity")=="warning"]

    if supporting:
        lines.append("Supporting evidence: "+" | ".join(v.get("message","") for v in supporting[:2])+".")
    if critical:
        lines.append("Critical issues: "+" | ".join(v.get("message","") for v in critical[:3])+".")
    if warnings and not critical:
        lines.append("Warnings: "+" | ".join(v.get("message","") for v in warnings[:3])+".")

    # Only add PTR context for non-sanitation proposals
    if intervention not in ("Sanitation", "Lab", "Digital"):
        ptr = school_data.get("ptr",0); thr = school_data.get("ptr_threshold",35)
        if ptr and thr: lines.append(f"PTR {ptr:.1f} — {'within norms' if ptr<=thr else f'exceeds norm {thr}'}.")

    return " ".join(lines)

def _build_fallback_summary(fields: dict) -> str:
    return f"• Problem: Infrastructure improvement needed at {fields.get('school_name','the school')}.\n• Ask: Rs{fields.get('funding_requested',0):,.0f} for {fields.get('intervention_type','infrastructure')} work.\n• Justification: Based on structured proposal fields submitted."