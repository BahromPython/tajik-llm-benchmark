from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path


def build_dashboard(scores_path: str, output_path: str, title: str = "Tajik LLM Benchmark") -> None:
    with Path(scores_path).open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    public_rows = []
    for row in rows:
        correct = row.get("objective_correct", "")
        public_rows.append({
            "provider": row.get("provider", ""), "model": row.get("model", ""),
            "condition": row.get("condition", ""), "category": row.get("category", ""),
            "correct": None if correct == "" else float(correct),
            "tokens": float(row["total_tokens"]) if row.get("total_tokens") else None,
            "cost": float(row["estimated_cost_usd"]) if row.get("estimated_cost_usd") else None,
            "latency": float(row["latency_ms"]) if row.get("latency_ms") else None,
            "failed": row.get("request_status", "ok") != "ok",
        })
    data = json.dumps(public_rows, ensure_ascii=False).replace("</", "<\\/")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = DASHBOARD_TEMPLATE.replace("__TITLE__", html.escape(title)).replace("__DATA__", data).replace("__GENERATED__", generated)
    target = Path(output_path); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")


DASHBOARD_TEMPLATE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{--ink:#12221b;--muted:#68766f;--bg:#f3f5f0;--card:#fff;--accent:#1f6b4f;--line:#dce3dc}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,Segoe UI,sans-serif}.wrap{max-width:1280px;margin:auto;padding:28px}header{display:flex;justify-content:space-between;gap:20px;align-items:end;margin-bottom:20px}h1{margin:0;font-size:28px}.sub{color:var(--muted)}.filters{display:flex;gap:10px;flex-wrap:wrap}select{padding:9px 30px 9px 10px;border:1px solid var(--line);border-radius:8px;background:white}.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}.card,.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px}.label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.05em}.value{font-size:26px;font-weight:700;margin-top:5px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.panel h2{font-size:16px;margin:0 0 15px}.barrow{display:grid;grid-template-columns:minmax(150px,1fr) 3fr 62px;gap:10px;align-items:center;margin:10px 0}.track{height:12px;background:#edf1ed;border-radius:20px;overflow:hidden}.bar{height:100%;background:var(--accent);border-radius:20px}.tablebox{margin-top:12px;overflow:auto}table{width:100%;border-collapse:collapse;background:white}th,td{padding:10px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}th{color:var(--muted);font-size:12px}footer{color:var(--muted);margin-top:14px}@media(max-width:850px){.kpis{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}header{display:block}.filters{margin-top:14px}}@media print{.filters{display:none}.wrap{max-width:none}}
</style></head><body><main class="wrap"><header><div><h1>__TITLE__</h1><div class="sub">Professor review dashboard · aggregate results only</div></div><div class="filters"><select id="provider"><option value="">All providers</option></select><select id="model"><option value="">All models</option></select><select id="condition"><option value="">All conditions</option></select><select id="category"><option value="">All categories</option></select></div></header>
<section class="kpis"><div class="card"><div class="label">Responses</div><div class="value" id="n">0</div></div><div class="card"><div class="label">Objective accuracy</div><div class="value" id="accuracy">—</div></div><div class="card"><div class="label">Total tokens</div><div class="value" id="tokens">—</div></div><div class="card"><div class="label">Estimated cost</div><div class="value" id="cost">—</div></div><div class="card"><div class="label">Failures</div><div class="value" id="failures">0</div></div></section>
<section class="grid"><div class="panel"><h2>Accuracy by model</h2><div id="modelbars"></div></div><div class="panel"><h2>Accuracy by prompt condition</h2><div id="conditionbars"></div></div></section><section class="panel tablebox"><h2>Model summary</h2><table><thead><tr><th>Provider</th><th>Model</th><th>Responses</th><th>Scored</th><th>Accuracy</th><th>Tokens</th><th>Cost</th><th>Median latency</th></tr></thead><tbody id="tbody"></tbody></table></section><footer>Generated __GENERATED__. This dashboard excludes prompts, gold answers, and raw responses to protect held-out benchmark content.</footer></main>
<script>const DATA=__DATA__;const fields=['provider','model','condition','category'];for(const f of fields){const s=document.getElementById(f);[...new Set(DATA.map(x=>x[f]).filter(Boolean))].sort().forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;s.appendChild(o)});s.onchange=render}const fmt=n=>n==null?'—':Math.round(n).toLocaleString();const pct=n=>n==null?'—':(100*n).toFixed(1)+'%';function filtered(){return DATA.filter(x=>fields.every(f=>!document.getElementById(f).value||x[f]===document.getElementById(f).value))}function groups(rows,key){const m={};for(const r of rows)(m[r[key]]??=[]).push(r);return m}function accuracy(rows){const v=rows.filter(r=>r.correct!=null);return v.length?v.reduce((a,r)=>a+r.correct,0)/v.length:null}function bars(id,obj){const el=document.getElementById(id);el.innerHTML=Object.entries(obj).sort((a,b)=>(accuracy(b[1])??-1)-(accuracy(a[1])??-1)).map(([k,v])=>{const a=accuracy(v);return `<div class="barrow"><span>${k}</span><div class="track"><div class="bar" style="width:${a==null?0:a*100}%"></div></div><strong>${pct(a)}</strong></div>`}).join('')||'<span class="sub">No scored results yet.</span>'}function median(a){a=a.filter(x=>x!=null).sort((x,y)=>x-y);return a.length?a[Math.floor(a.length/2)]:null}function render(){const r=filtered(),sc=r.filter(x=>x.correct!=null);document.getElementById('n').textContent=fmt(r.length);document.getElementById('accuracy').textContent=pct(accuracy(r));document.getElementById('tokens').textContent=fmt(r.some(x=>x.tokens!=null)?r.reduce((a,x)=>a+(x.tokens||0),0):null);const c=r.some(x=>x.cost!=null)?r.reduce((a,x)=>a+(x.cost||0),0):null;document.getElementById('cost').textContent=c==null?'—':'$'+c.toFixed(3);document.getElementById('failures').textContent=fmt(r.filter(x=>x.failed).length);bars('modelbars',groups(r,'model'));bars('conditionbars',groups(r,'condition'));document.getElementById('tbody').innerHTML=Object.entries(groups(r,'model')).map(([m,v])=>{const c=v.some(x=>x.cost!=null)?v.reduce((a,x)=>a+(x.cost||0),0):null;return `<tr><td>${v[0].provider}</td><td>${m}</td><td>${fmt(v.length)}</td><td>${fmt(v.filter(x=>x.correct!=null).length)}</td><td>${pct(accuracy(v))}</td><td>${fmt(v.some(x=>x.tokens!=null)?v.reduce((a,x)=>a+(x.tokens||0),0):null)}</td><td>${c==null?'—':'$'+c.toFixed(3)}</td><td>${fmt(median(v.map(x=>x.latency)))} ms</td></tr>`}).join('')||'<tr><td colspan="8">No results yet.</td></tr>'}render();</script></body></html>'''
