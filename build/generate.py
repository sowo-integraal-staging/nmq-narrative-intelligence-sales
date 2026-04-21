#!/usr/bin/env python3
"""
UnderCurrent site generator
============================
Single source of truth:
  ../llm-market-research/docs/undercurrent.yaml
  ../llm-market-research/docs/methodology/CHAPTER-ARCHITECTURE.md

Outputs written to _generated/ and optionally injected into HTML files.

Usage:
  python3 build/generate.py            # generate fragments only
  python3 build/generate.py --inject   # generate + inject into HTML files

Injection markers in HTML files:
  <!-- GEN:kpi-flow-a -->      ... <!-- /GEN:kpi-flow-a -->
  <!-- GEN:kpi-flow-b -->      ... <!-- /GEN:kpi-flow-b -->
  <!-- GEN:framework-body -->  ... <!-- /GEN:framework-body -->
  <!-- GEN:methodology-products --> ... <!-- /GEN:methodology-products -->
"""

import os, re, sys, json
import yaml

HERE     = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.dirname(HERE)
YAML_PATH = os.path.normpath(os.path.join(HERE, '../../llm-market-research/docs/undercurrent.yaml'))
ARCH_PATH = os.path.normpath(os.path.join(HERE, '../../llm-market-research/docs/methodology/CHAPTER-ARCHITECTURE.md'))
OUT_DIR   = os.path.join(SITE_DIR, '_generated')

os.makedirs(OUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Load YAML
# ─────────────────────────────────────────────────────────────────────────────

def load_products():
    with open(YAML_PATH) as f:
        data = yaml.safe_load(f)
    products_raw = data['platform']['products']
    products = []
    for p in products_raw:
        prod = {
            'id':           p.get('id', ''),
            'name':         p.get('name', ''),
            'tagline':      p.get('tagline', ''),
            'role':         (p.get('role') or '').strip(),
            'chapter_arc':  (p.get('chapter_arc') or '').strip(),
            'chapters': [],
        }
        for ch in (p.get('chapters') or []):
            chapter = {
                'id':             ch.get('id', ''),
                'number':         ch.get('number', ''),
                'name':           ch.get('name', ''),
                'client_question':(ch.get('client_question') or '').strip(),
                'illuminates':    (ch.get('illuminates') or '').strip(),
                'unique_insight': (ch.get('unique_insight') or '').strip(),
                'enables':        (ch.get('enables') or '').strip(),
                'improves':       (ch.get('improves') or '').strip(),
                'kpis': [],
            }
            for kpi in (ch.get('kpis') or []):
                chapter['kpis'].append({
                    'name':       (kpi.get('name') or '').strip(),
                    'short_name': (kpi.get('short_name') or '').strip(),
                    'motivation': (kpi.get('motivation') or '').strip(),
                    'definition': (kpi.get('definition') or '').strip(),
                    'how_to_read':(kpi.get('how_to_read') or '').strip(),
                    'prompt_type':(kpi.get('prompt_type') or '').strip(),
                    'direction':  (kpi.get('direction') or '').strip(),
                })
            prod['chapters'].append(chapter)
        products.append(prod)
    return products

# ─────────────────────────────────────────────────────────────────────────────
# 2. Parse CHAPTER-ARCHITECTURE.md for rich prose descriptions
# ─────────────────────────────────────────────────────────────────────────────

def load_chapter_arch():
    with open(ARCH_PATH) as f:
        lines = f.readlines()

    arch = {}
    current_product = None
    current_ch_name = None
    current_block = []

    def flush_chapter():
        if not current_product or not current_ch_name or not current_block:
            return
        text = ''.join(current_block)
        arc_m = re.search(r'\*"(.+?)"\*', text)
        arc = arc_m.group(1) if arc_m else ''

        def extract(label):
            m = re.search(
                rf'\*\*{re.escape(label)}\*\*\n(.*?)(?=\n\*\*|\Z)',
                text, re.DOTALL
            )
            return ' '.join(m.group(1).strip().split()) if m else ''

        arch[current_product][current_ch_name] = {
            'arc':         arc,
            'illuminates': extract('What does this chapter illuminate?'),
            'enables':     extract('How does it allow data-based calls?'),
            'improves':    extract('What do we expect to improve'),
        }

    for line in lines:
        stripped = line.rstrip()
        # Product-level header
        pm = re.match(r'^## (AI Brand Monitor|AI Market Research) — Chapters', stripped)
        if pm:
            flush_chapter()
            current_ch_name = None
            current_block = []
            current_product = 'ai_brand_monitor' if 'Brand' in pm.group(1) else 'ai_market_research'
            arch.setdefault(current_product, {})
            continue
        # Chapter header
        sm = re.match(r'^### Ch\. \d+ — (.+)$', stripped)
        if sm and current_product:
            flush_chapter()
            current_ch_name = sm.group(1).strip()
            current_block = [line]
            continue
        # New top-level section (## but not a product header) — stop collecting
        if re.match(r'^## ', stripped) and current_ch_name:
            flush_chapter()
            current_ch_name = None
            current_block = []
            continue
        if current_ch_name is not None:
            current_block.append(line)

    flush_chapter()
    return arch

# ─────────────────────────────────────────────────────────────────────────────
# 3. HTML helpers
# ─────────────────────────────────────────────────────────────────────────────

def esc(s):
    return (s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&#34;').replace("'",'&#39;')

CH_CLASSES = ['ch1', 'ch2', 'ch3', 'ch4', 'ch5']

def kpi_tooltip(kpi):
    name = esc(kpi['name'])
    body = esc(kpi['motivation'] or kpi['definition'])
    return (f'<span class="kpi-tip">'
            f'<span class="kpi-tip-name">{name}</span>'
            f'<span class="kpi-tip-why">{body}</span>'
            f'</span>')

def chapter_popover(ch, arch_ch):
    num   = ch['number']
    name  = ch['name']
    title = esc(f'Chapter {num} \u00b7 {name}')

    # prefer arch prose (richer) over YAML fields
    arc      = esc(arch_ch.get('arc', '') or ch.get('client_question', ''))
    illum    = esc(arch_ch.get('illuminates', '') or ch.get('illuminates', ''))
    enables  = esc(arch_ch.get('enables', '')    or ch.get('enables', ''))
    improves = esc(arch_ch.get('improves', '')   or ch.get('improves', ''))

    return (f'<div class="ch-popover">'
            f'<div class="ch-popover-title">{title}</div>'
            f'<div class="ch-popover-arc">&#8220;{arc}&#8221;</div>'
            f'<div class="ch-popover-q">What it illuminates</div>'
            f'<div class="ch-popover-body">{illum}</div>'
            f'<div class="ch-popover-q">What it enables</div>'
            f'<div class="ch-popover-body">{enables}</div>'
            f'<div class="ch-popover-q">What improves</div>'
            f'<div class="ch-popover-body">{improves}</div>'
            f'</div>')

# ─────────────────────────────────────────────────────────────────────────────
# 4. Fragment builders
# ─────────────────────────────────────────────────────────────────────────────

def build_kpi_flow(product, arch_prod):
    chapters = product['chapters']
    lines = ['<div class="kpi-flow">',
             '  <div class="flow-row-wrap"><div class="flow-row">']

    for i, ch in enumerate(chapters):
        cls   = CH_CLASSES[min(i, 4)]
        label = esc(f"Ch. {ch['number']} \u00b7 {ch['name']}")
        arch_ch = arch_prod.get(ch['name'], {})
        popover = chapter_popover(ch, arch_ch)

        lines.append(f'    <div class="flow-chapter">')
        lines.append(f'      <div class="flow-header {cls}">{label}</div>')
        lines.append(f'      {popover}')
        lines.append(f'      <div class="flow-body">')
        for kpi in ch['kpis']:
            tip = kpi_tooltip(kpi)
            lines.append(f'        <div class="flow-kpi" tabindex="0">{esc(kpi["name"])}{tip}</div>')
        lines.append(f'      </div>')
        lines.append(f'    </div>')
        if i < len(chapters) - 1:
            lines.append(f'    <div class="flow-arrow">&#8594;</div>')

    lines.append('  </div></div><!-- /flow-row-wrap -->')
    lines.append('</div>')
    return '\n'.join(lines)


def build_framework_body(products, arch):
    lines = []
    for prod in products:
        is_a   = 'brand' in prod['id']
        panel  = 'A' if is_a else 'B'
        active = ' active' if is_a else ''
        arch_prod = arch.get(prod['id'], {})

        lines.append(f'  <div id="ppanel-{panel}" class="ppanel{active}">')

        for i, ch in enumerate(prod['chapters']):
            cls    = CH_CLASSES[min(i, 4)]
            arch_ch = arch_prod.get(ch['name'], {})
            client_q = esc(arch_ch.get('arc', '') or ch.get('client_question', ''))

            lines.append(f'    <div class="chapter">')
            lines.append(f'      <div class="chapter-header">')
            lines.append(f'        <span class="chapter-num {cls}">Ch. {ch["number"]}</span>')
            lines.append(f'        <div>')
            lines.append(f'          <div class="chapter-title">{esc(ch["name"])}</div>')
            lines.append(f'          <div class="chapter-desc">&#8220;{client_q}&#8221;</div>')
            lines.append(f'        </div>')
            lines.append(f'      </div>')
            lines.append(f'      <div class="kpi-list">')
            for kpi in ch['kpis']:
                body = esc(kpi['definition'] or kpi['motivation'])
                lines.append(f'        <div class="kpi-item">')
                lines.append(f'          <div class="kpi-item-name">{esc(kpi["name"])}</div>')
                lines.append(f'          <div class="kpi-item-body">{body}</div>')
                lines.append(f'        </div>')
            lines.append(f'      </div>')
            lines.append(f'    </div>')

        lines.append(f'  </div><!-- /ppanel-{panel} -->')
        lines.append('')
    return '\n'.join(lines)


def build_methodology_products(products, arch):
    lines = []
    for prod in products:
        is_a  = 'brand'     in prod['id']
        is_c  = 'publisher' in prod['id']
        cls   = 'a' if is_a else ('c' if is_c else 'b')
        role  = esc(prod['role'])
        name  = esc(prod['name'])
        kpi_n = sum(len(ch['kpis']) for ch in prod['chapters'])
        if is_a:
            subj = 'The AI system is the subject.'
        elif is_c:
            subj = 'The AI system is the reader.'
        else:
            subj = 'The AI system is the instrument.'

        lines.append(f'  <div class="product-block">')
        lines.append(f'    <span class="product-block-label {cls}">{name}</span>')
        lines.append(f'    <h4>{subj}</h4>')
        lines.append(f'    <p>{role}</p>')
        lines.append(f'    <p style="margin-bottom:0.5rem;">{kpi_n} KPIs across five chapters:</p>')
        lines.append(f'    <div class="chapter-list">')
        for ch in prod['chapters']:
            lines.append(f'      <span class="chapter-pill"><strong>Ch.{ch["number"]}</strong> {esc(ch["name"])}</span>')
        lines.append(f'    </div>')
        lines.append(f'  </div>')
        lines.append('')
    return '\n'.join(lines)

# ─────────────────────────────────────────────────────────────────────────────
# 5. Injection
# ─────────────────────────────────────────────────────────────────────────────

def inject(html_path, marker, content):
    with open(html_path) as f:
        src = f.read()
    open_tag  = f'<!-- GEN:{marker} -->'
    close_tag = f'<!-- /GEN:{marker} -->'
    if open_tag not in src:
        print(f'  [SKIP] {os.path.basename(html_path)}: marker GEN:{marker} not found — add it first')
        return
    replaced = re.sub(
        re.escape(open_tag) + r'.*?' + re.escape(close_tag),
        f'{open_tag}\n{content}\n{close_tag}',
        src, flags=re.DOTALL
    )
    with open(html_path, 'w') as f:
        f.write(replaced)
    print(f'  [OK]   {os.path.basename(html_path)}: GEN:{marker}')

# ─────────────────────────────────────────────────────────────────────────────
# 6. Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print(f'Loading YAML...')
    products = load_products()
    for p in products:
        n = sum(len(c['kpis']) for c in p['chapters'])
        print(f'  {p["name"]}: {len(p["chapters"])} chapters, {n} KPIs')

    print('Loading chapter architecture...')
    arch = load_chapter_arch()
    for k, v in arch.items():
        print(f'  {k}: {len(v)} chapters')

    prod_a = next((p for p in products if 'brand'     in p['id']), None)
    prod_b = next((p for p in products if 'market'    in p['id'] or 'research' in p['id']), None)
    prod_c = next((p for p in products if 'publisher' in p['id']), None)
    arch_a = arch.get('ai_brand_monitor', {})
    arch_b = arch.get('ai_market_research', {})
    arch_c = {}  # no CHAPTER-ARCHITECTURE.md entry for C yet; uses YAML fields directly

    print('\nBuilding fragments...')
    flow_a     = build_kpi_flow(prod_a, arch_a) if prod_a else ''
    flow_b     = build_kpi_flow(prod_b, arch_b) if prod_b else ''
    flow_c     = build_kpi_flow(prod_c, arch_c) if prod_c else ''
    fw_body    = build_framework_body(products, arch)
    meth_prods = build_methodology_products(products, arch)

    fragments = {
        'kpi-flow-a.html':            flow_a,
        'kpi-flow-b.html':            flow_b,
        'kpi-flow-c.html':            flow_c,
        'framework-body.html':        fw_body,
        'methodology-products.html':  meth_prods,
    }
    for fname, content in fragments.items():
        path = os.path.join(OUT_DIR, fname)
        with open(path, 'w') as f:
            f.write(content)
        print(f'  Wrote _generated/{fname}')

    with open(os.path.join(OUT_DIR, 'kpi-data.json'), 'w') as f:
        json.dump({'products': products}, f, indent=2, ensure_ascii=False)
    print(f'  Wrote _generated/kpi-data.json')

    if '--inject' in sys.argv:
        print('\nInjecting into HTML...')
        inject(os.path.join(SITE_DIR, 'index.html'),       'kpi-flow-a',           flow_a)
        inject(os.path.join(SITE_DIR, 'index.html'),       'kpi-flow-b',           flow_b)
        inject(os.path.join(SITE_DIR, 'publishers.html'),  'kpi-flow-c',           flow_c)
        inject(os.path.join(SITE_DIR, 'framework.html'),   'framework-body',       fw_body)
        inject(os.path.join(SITE_DIR, 'methodology.html'), 'methodology-products', meth_prods)

    print('\nDone.')

if __name__ == '__main__':
    main()
