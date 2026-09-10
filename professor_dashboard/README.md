# Professor results dashboard

The dashboard is a static, privacy-safe HTML file. It contains aggregate scored results but excludes prompts,
gold answers, and raw model responses so that held-out benchmark items are not leaked.

Generate it after scoring:

```powershell
python -m tajik_benchmark.cli dashboard --scores runs/real-pilot-scored.csv --output professor_dashboard/index.html
```

Open `index.html` locally to review it. To make it public, deploy this folder to GitHub Pages, Cloudflare Pages,
Netlify, or another static host only after the researcher confirms that the aggregated results may be public.
Do not deploy the `data/`, `runs/`, or `validation_evidence/` folders.
