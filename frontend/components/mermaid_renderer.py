# frontend/components/mermaid_renderer.py
import streamlit as st
import streamlit.components.v1 as components
from utils.helpers import generate_key
import re

def validate_and_fix_mermaid_syntax(mermaid_code: str) -> tuple:
    """Validate and fix common Mermaid syntax errors"""
    errors = []
    fixed_code = mermaid_code.strip()

    # Remove markdown code blocks
    if fixed_code.startswith("```mermaid"):
        fixed_code = fixed_code.replace("```mermaid", "").replace("```", "").strip()
    elif fixed_code.startswith("```"):
        fixed_code = fixed_code.replace("```", "").strip()

    # Remove diagram markers if present
    fixed_code = fixed_code.replace("[DIAGRAM_START]", "").replace("[DIAGRAM_END]", "").strip()

    lines = fixed_code.split('\n')
    fixed_lines = []

    for line in lines:
        original_line = line
        line = line.strip()

        if not line or line.startswith('%%'):
            fixed_lines.append(line)
            continue

        if line.startswith('subgraph') or line == 'end':
            fixed_lines.append(line)
            continue

        # Fix arrow syntax
        line = re.sub(r'-{3,}>', '-->', line)
        line = re.sub(r'\.{3,}>', '-..->', line)

        # Fix node IDs with spaces
        if '-->' in line or '-..->' in line or '==>' in line:
            parts = line.split('[', 1)
            if len(parts) > 1:
                before_bracket = parts[0]
                before_bracket = re.sub(r'(\w+)\s+(\w+)(?=\s*$)', r'\1_\2', before_bracket)
                line = before_bracket + '[' + parts[1]

        if line != original_line.strip():
            errors.append(f"Fixed: {original_line.strip()[:50]}...")

        fixed_lines.append(line)

    fixed_code = '\n'.join(fixed_lines)
    return fixed_code, errors


def render_mermaid(mermaid_code, height=800, unique_id=None, theme='dark'):
    """
    Render mermaid diagram with zoom, pan, and fullscreen.
    
    ✅ FIX: The original code mixed ES module (mermaid) with a classic <script> tag
    (panzoom). ES modules run in their own scope, so `window.Panzoom` was undefined
    when the mermaid module tried to use it → silent failure → white box.
    
    Now both are loaded via dynamic import() inside the same ES module scope,
    ensuring they're both available before rendering starts.
    """
    if not unique_id:
        unique_id = generate_key(mermaid_code)

    fixed_code, syntax_fixes = validate_and_fix_mermaid_syntax(mermaid_code)

    if syntax_fixes:
        with st.expander("🔧 Auto-fixed Syntax Issues", expanded=False):
            for fix in syntax_fixes:
                st.info(fix)

    # Escape for safe JS embedding
    safe_mermaid_code = (
        fixed_code
        .replace('\\', '\\\\')
        .replace('`', '\\`')
        .replace('${', '\\${')
        .replace('</script>', '<\\/script>')
    )

    if theme == 'dark':
        bg = '#1a1a1a'
        node_bg = '#2d2d2d'
        node_bg2 = '#3d3d3d'
        text_color = '#ffffff'
        primary = '#8b5cf6'
        primary_border = '#6d28d9'
        line_color = '#a78bfa'
        cluster_bg = '#2d2d2d'
        edge_label_bg = '#2d2d2d'
        note_bg = '#3d3d3d'
        activation_bg = '#4c1d95'
        secondary = '#4c1d95'
        tertiary = '#2e1065'
        seq_num_color = '#1a1a1a'
    else:
        bg = '#ffffff'
        node_bg = '#f7f7f8'
        node_bg2 = '#ffffff'
        text_color = '#111111'
        primary = '#7c3aed'
        primary_border = '#6d28d9'
        line_color = '#8b5cf6'
        cluster_bg = '#f7f7f8'
        edge_label_bg = '#ffffff'
        note_bg = '#ffffff'
        activation_bg = '#ede9fe'
        secondary = '#ede9fe'
        tertiary = '#f5f3ff'
        seq_num_color = '#ffffff'

    mermaid_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: {bg};
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            overflow: hidden;
        }}
        #diagram-wrapper {{
            position: relative;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
            background: {bg};
        }}
        #diagram-container {{
            width: 100%;
            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            cursor: grab;
            overflow: visible;
        }}
        #diagram-container:active {{ cursor: grabbing; }}
        .zoom-controls {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            border-radius: 12px;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            z-index: 1000;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .zoom-btn {{
            background: rgba(139,92,246,0.9);
            color: white;
            border: none;
            padding: 10px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
            white-space: nowrap;
        }}
        .zoom-btn:hover {{
            background: rgba(124,58,237,1);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(139,92,246,0.4);
        }}
        .fullscreen-btn {{ background: rgba(34,197,94,0.9); margin-top: 8px; }}
        .fullscreen-btn:hover {{
            background: rgba(22,163,74,1);
            box-shadow: 0 4px 8px rgba(34,197,94,0.4);
        }}
        .instructions {{
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            font-size: 13px;
            z-index: 1000;
        }}
        .instructions strong {{ display: block; margin-bottom: 8px; color: #8b5cf6; }}
        .instructions p {{ margin: 4px 0; opacity: 0.9; }}
        .error-container {{
            background: linear-gradient(135deg,#fee2e2,#fecaca);
            border: 3px solid #ef4444;
            border-radius: 16px;
            padding: 40px;
            max-width: 700px;
            margin: 40px auto;
            text-align: center;
        }}
        .error-icon {{ font-size: 3rem; margin-bottom: 1rem; }}
        .error-title {{ font-size: 1.8rem; font-weight: 800; color: #991b1b; margin-bottom: 1rem; }}
        .error-message {{ color: #7f1d1d; font-size: 1rem; line-height: 1.6; }}
        .error-details {{
            background: rgba(255,255,255,0.5);
            border-radius: 8px;
            padding: 12px;
            margin: 12px 0;
            text-align: left;
            font-family: monospace;
            font-size: 0.85rem;
            word-break: break-all;
        }}
        .suggestions {{ background: rgba(255,255,255,0.6); border-radius: 10px; padding: 20px; margin: 15px 0; text-align: left; }}
        .suggestions ul {{ list-style: none; padding: 0; }}
        .suggestions li {{ margin: 10px 0; padding-left: 20px; position: relative; }}
        .suggestions li:before {{ content: "→"; position: absolute; left: 0; color: #dc2626; font-weight: bold; }}
        svg {{ filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1)); min-width: 600px; min-height: 400px; }}
        svg text {{ fill: {text_color} !important; }}
        .loading {{ color: {text_color}; font-size: 1.1rem; }}
    </style>
</head>
<body>
    <div id="diagram-wrapper">
        <div class="zoom-controls">
            <button id="zoom-in"  class="zoom-btn">🔍+ Zoom In</button>
            <button id="zoom-out" class="zoom-btn">🔍− Zoom Out</button>
            <button id="zoom-reset" class="zoom-btn">↺ Reset</button>
            <button id="zoom-fit"  class="zoom-btn">⛶ Fit</button>
            <button id="fullscreen-btn" class="zoom-btn fullscreen-btn">⛶ Fullscreen</button>
        </div>
        <div class="instructions">
            <strong>💡 Controls:</strong>
            <p>🖱️ Drag to pan</p>
            <p>🖱️ Scroll to zoom</p>
        </div>
        <div id="diagram-container">
            <div id="status">⏳ Loading libraries…</div>
        </div>
    </div>

    <!-- ✅ FIX: UMD builds via unpkg - classic scripts, no ES module scope issues -->
    <script src="https://unpkg.com/mermaid@10.9.1/dist/mermaid.min.js"></script>
    <script src="https://unpkg.com/@panzoom/panzoom@4.5.1/dist/panzoom.min.js"></script>
    <script>

        mermaid.initialize({{
            startOnLoad: false,
            theme: 'base',
            themeVariables: {{
                primaryColor: '{primary}',
                primaryTextColor: '#ffffff',
                primaryBorderColor: '{primary_border}',
                lineColor: '{line_color}',
                secondaryColor: '{secondary}',
                tertiaryColor: '{tertiary}',
                background: '{bg}',
                mainBkg: '{node_bg}',
                secondBkg: '{node_bg2}',
                textColor: '{text_color}',
                nodeBorder: '{primary_border}',
                clusterBkg: '{cluster_bg}',
                clusterBorder: '{primary_border}',
                defaultLinkColor: '{line_color}',
                titleColor: '{text_color}',
                edgeLabelBackground: '{edge_label_bg}',
                actorBorder: '{primary_border}',
                actorBkg: '{node_bg2}',
                actorTextColor: '{text_color}',
                actorLineColor: '{line_color}',
                signalColor: '{text_color}',
                signalTextColor: '{text_color}',
                labelBoxBkgColor: '{node_bg}',
                labelBoxBorderColor: '{primary_border}',
                labelTextColor: '{text_color}',
                loopTextColor: '{text_color}',
                noteBorderColor: '{primary_border}',
                noteBkgColor: '{note_bg}',
                noteTextColor: '{text_color}',
                activationBorderColor: '{primary_border}',
                activationBkgColor: '{activation_bg}',
                sequenceNumberColor: '{seq_num_color}',
                fontSize: '14px',
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            }},
            securityLevel: 'loose',
            logLevel: 'error',
            flowchart: {{ useMaxWidth: false, htmlLabels: true, curve: 'basis', padding: 30, nodeSpacing: 80, rankSpacing: 80 }},
            sequence: {{ useMaxWidth: false, diagramMarginX: 30, diagramMarginY: 30, actorMargin: 80, width: 180, height: 80, mirrorActors: true, wrap: true }},
            er: {{ useMaxWidth: false, padding: 30, layoutDirection: 'TB', minEntityWidth: 150, minEntityHeight: 100 }},
            gantt: {{ useMaxWidth: false, barHeight: 30, barGap: 8, topPadding: 50, leftPadding: 100, fontSize: 14 }}
        }});

        function showError(msg) {{
            const container = document.getElementById('diagram-wrapper');
            if (container) {{
                container.innerHTML = `
                    <div class="error-container">
                        <div class="error-icon">⚠️</div>
                        <div class="error-title">Diagram Rendering Error</div>
                        <div class="error-message">
                            <p><strong>The AI generated invalid Mermaid syntax</strong></p>
                            <div class="error-details">${{msg}}</div>
                            <div class="suggestions">
                                <p>💡 <strong>How to fix:</strong></p>
                                <ul>
                                    <li>Ask: <em>"Regenerate the diagram with correct syntax"</em></li>
                                    <li>Try: <em>"Show me a simple architecture diagram"</em></li>
                                </ul>
                            </div>
                        </div>
                    </div>`;
            }}
        }}

        function initZoom() {{
            const container = document.getElementById('diagram-container');
            if (!container) return;

            try {{
                const pz = Panzoom(container, {{ maxScale: 5, minScale: 0.2, startScale: 1, canvas: true }});
                container.parentElement.addEventListener('wheel', pz.zoomWithWheel);

                document.getElementById('zoom-in')?.addEventListener('click',    () => pz.zoomIn());
                document.getElementById('zoom-out')?.addEventListener('click',   () => pz.zoomOut());
                document.getElementById('zoom-reset')?.addEventListener('click', () => pz.reset());
                document.getElementById('zoom-fit')?.addEventListener('click',   () => {{ pz.reset(); pz.zoom(0.8, {{ animate: true }}); }});

                const fsBtn = document.getElementById('fullscreen-btn');
                fsBtn?.addEventListener('click', () => {{
                    if (!document.fullscreenElement) {{
                        document.getElementById('diagram-wrapper').requestFullscreen().catch(console.error);
                    }} else {{
                        document.exitFullscreen();
                    }}
                }});
                document.addEventListener('fullscreenchange', () => {{
                    if (fsBtn) fsBtn.textContent = document.fullscreenElement ? '🗙 Exit Fullscreen' : '⛶ Fullscreen';
                }});
            }} catch(e) {{
                console.warn('Zoom init failed:', e);
            }}
        }}

        function render() {{
            const code = `{safe_mermaid_code}`;
            const container = document.getElementById('diagram-container');

            if (!code || code.trim().length < 5) {{
                showError('Empty diagram code received.');
                return;
            }}

            mermaid.render('mermaid-svg-{unique_id}', code).then(function(result) {{
                var svg = result.svg;
                container.innerHTML = svg;

                // Fix SVG sizing
                const svgEl = container.querySelector('svg');
                if (svgEl) {{
                    svgEl.style.maxWidth = 'none';
                    svgEl.style.height = 'auto';
                    try {{
                        const bb = svgEl.getBBox();
                        if (bb && bb.width > 0) {{
                            const pad = 40;
                            svgEl.setAttribute('viewBox', `${{bb.x - pad}} ${{bb.y - pad}} ${{bb.width + pad*2}} ${{bb.height + pad*2}}`);
                        }}
                    }} catch(_) {{}}
                    svgEl.setAttribute('preserveAspectRatio', 'xMidYMid meet');
                }}

                setTimeout(initZoom, 100);

            }}).catch(function(err) {{
                console.error('Mermaid error:', err);
                showError(err.message || String(err));
            }});
        }}

        window.addEventListener('load', function() {{
            setTimeout(render, 200);
        }});
    </script>
</body>
</html>"""

    try:
        components.html(mermaid_html, height=height, scrolling=False)
        return True
    except Exception as e:
        st.error(f"⚠️ Render Error: {str(e)}")
        with st.expander("🔍 View Diagram Code"):
            st.code(fixed_code, language="mermaid")
        return False