# Build Pipeline

Single source of truth: `../llm-market-research/docs/undercurrent.yaml`
Chapter descriptions: `../llm-market-research/docs/methodology/CHAPTER-ARCHITECTURE.md`

## When the YAML changes

```bash
# 1. Pull latest changes in the source repo
cd ../llm-market-research && git pull && cd ../nmq-narrative-intelligence-sales

# 2. Sync undercurrent.yaml to the site (framework.html loads it at runtime)
cp ../llm-market-research/docs/undercurrent.yaml ./undercurrent.yaml

# 3. Regenerate HTML fragments and inject into index.html + methodology.html
python3 build/generate.py --inject

# 4. Commit and push
git add -A && git commit -m "sync: update from undercurrent.yaml" && git push origin master
```

## What gets updated automatically

| File | How |
|------|-----|
| `framework.html` | Fetches `undercurrent.yaml` at runtime via js-yaml — always live |
| `index.html` (KPI flow diagrams) | `<!-- GEN:kpi-flow-a -->` and `<!-- GEN:kpi-flow-b -->` markers |
| `methodology.html` (product blocks) | `<!-- GEN:methodology-products -->` marker |

## Generated files

`_generated/` contains the raw HTML fragments for debugging.
`_generated/kpi-data.json` is a machine-readable dump of the full parsed structure.

## Dependencies

Python 3 + PyYAML (`pip install pyyaml` if not available — usually pre-installed).
