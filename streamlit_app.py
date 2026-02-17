import streamlit as st
import os
import tempfile
import zipfile
import io
from m2_core import (
    DocstringGenerator,
    DocstringValidator,
    CodeInstrumentor,
    generate_before_coverage_report,
    generate_after_coverage_report,
    generate_compliance_report,
)

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Auto-DocstringGen · Milestone 4",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Global ── */
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }

    /* ── Metric cards ── */
    .metric-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        text-align: center;
        margin: 6px 0;
        border-left: 5px solid #7c3aed;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.12);
    }
    .metric-value { font-size: 2.2rem; font-weight: 700; color: #1e1b4b; }
    .metric-label { font-size: 0.9rem; color: #6b7280; margin-top: 4px; }
    .compliance-good { color: #16a34a; }
    .compliance-bad  { color: #dc2626; }

    /* ── Section header pills ── */
    .section-pill {
        display: inline-block;
        background: #ede9fe;
        color: #5b21b6;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-bottom: 10px;
    }

    /* ── Violation card ── */
    .violation-card {
        background: #fff7ed;
        border-left: 4px solid #f97316;
        border-radius: 8px;
        padding: 10px 14px;
        margin: 6px 0;
        font-size: 0.88rem;
    }

    /* ── Search bar styling ── */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1px solid #d1d5db;
        padding: 8px 12px;
    }

    /* ── Progress bar colour ── */
    .stProgress > div > div > div > div { background-color: #7c3aed; }

    /* ── Download button ── */
    .stDownloadButton > button {
        background: #7c3aed;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: 600;
    }
    .stDownloadButton > button:hover { background: #6d28d9; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] { background: #1e1b4b; }
    section[data-testid="stSidebar"] * { color: #e5e7eb !important; }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TOOLTIP HELPER
# ─────────────────────────────────────────────
TOOLTIPS = {
    "style":         "Choose the docstring format. Google Style is the most popular; NumPy is preferred in scientific code; reST is used in Sphinx docs.",
    "coverage":      "Percentage of functions and classes that have a docstring. Higher is better — aim for 100%.",
    "compliance":    "How well existing docstrings follow PEP 257 conventions. Violations are style/format issues found by pydocstyle.",
    "file_search":   "Type part of a filename to narrow the list below.",
    "file_filter":   "Restrict the file list to only files that still have problems.",
    "sym_search":    "Filter undocumented function/class names by keyword.",
    "sym_section":   "Show functions, classes, or both in the documentation status panel.",
    "process":       "Reads every .py file, measures current docstring coverage, then auto-generates missing docstrings.",
    "download_zip":  "Download a ZIP with original + instrumented code and all reports for every file.",
}


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
_STATE_KEYS = [
    "results", "original_code", "instrumented_code",
    "original_quality", "instrumented_quality",
    "validation_results", "original_violations",
    "original_coverage_report", "instrumented_coverage_report",
    "original_compliance_report", "instrumented_compliance_report",
]
for _k in _STATE_KEYS:
    if _k not in st.session_state:
        st.session_state[_k] = None


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def coverage_color(pct: float) -> str:
    if pct >= 80:
        return "compliance-good"
    if pct >= 50:
        return "#d97706"
    return "compliance-bad"


def progress_bar(pct: float, label: str):
    """Render a labelled progress bar with colour coding."""
    color = "#16a34a" if pct >= 80 else ("#f59e0b" if pct >= 50 else "#dc2626")
    st.markdown(f"""
    <div style="margin:6px 0">
      <div style="display:flex;justify-content:space-between;font-size:0.82rem;color:#374151;margin-bottom:3px">
        <span>{label}</span><span style="font-weight:700;color:{color}">{pct}%</span>
      </div>
      <div style="background:#e5e7eb;border-radius:6px;height:10px">
        <div style="width:{min(pct,100)}%;background:{color};border-radius:6px;height:10px"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def metric_card(value, label, color_class=""):
    return f"""
    <div class="metric-card">
      <div class="metric-value {color_class}">{value}</div>
      <div class="metric-label">{label}</div>
    </div>
    """


def create_zip_from_results(results):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, data in results["file_results"].items():
            fname = os.path.basename(file_path)
            zf.writestr(f"original_{fname}", data["original_code"])
            zf.writestr(f"instrumented_{fname}", data["instrumented_code"])

            orig_cov = generate_before_coverage_report(data["original_quality"])
            orig_comp = generate_compliance_report(
                [{"line": v.line, "code": v.code, "message": v.message, "source": v.source}
                 for v in data["original_violations"]],
                "PEP-257 Compliance Report (Before Instrumentation)",
            )
            inst_cov  = generate_after_coverage_report(data["instrumented_quality"])
            inst_comp = generate_compliance_report(
                data["validation"],
                "PEP-257 Compliance Report (After Instrumentation)",
            )
            zf.writestr(f"coverage_original_{fname}.txt",   orig_cov)
            zf.writestr(f"compliance_original_{fname}.txt", orig_comp)
            zf.writestr(f"coverage_instrumented_{fname}.txt",   inst_cov)
            zf.writestr(f"compliance_instrumented_{fname}.txt", inst_comp)

        os_ = results["original_summary"]
        is_ = results["instrumented_summary"]
        summary = f"""
Auto-DocstringGen · Project Analysis Summary
=========================================

BEFORE INSTRUMENTATION
-----------------------
Functions  : {os_['total_functions']}
Classes    : {os_['total_classes']}
Documented : {os_['documented_items']}
Undocumented: {os_['undocumented_items']}
Coverage   : {os_['coverage_percentage']}%
PEP-257    : {os_['compliance_percentage']}%
Violations : {os_['violation_count']}

AFTER INSTRUMENTATION
----------------------
Functions  : {is_['total_functions']}
Classes    : {is_['total_classes']}
Documented : {is_['documented_items']}
Undocumented: {is_['undocumented_items']}
Coverage   : {is_['coverage_percentage']}%
PEP-257    : {is_['compliance_percentage']}%
Violations : {is_['violation_count']}

IMPROVEMENT
-----------
Coverage   : +{round(is_['coverage_percentage']   - os_['coverage_percentage'],   1)}%
Compliance : +{round(is_['compliance_percentage'] - os_['compliance_percentage'], 1)}%
"""
        zf.writestr("project_summary.txt", summary)
    zip_buffer.seek(0)
    return zip_buffer


# ─────────────────────────────────────────────
# UI COMPONENTS
# ─────────────────────────────────────────────
def display_metrics_comparison(before: dict, after: dict):
    """Four-column metrics card grid comparing before vs after."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(metric_card(before["total_functions"], "Functions (Before)"), unsafe_allow_html=True)
        st.markdown(metric_card(after["total_functions"],  "Functions (After)"),  unsafe_allow_html=True)

    with col2:
        st.markdown(metric_card(before["total_classes"], "Classes (Before)"), unsafe_allow_html=True)
        st.markdown(metric_card(after["total_classes"],  "Classes (After)"),  unsafe_allow_html=True)

    with col3:
        st.markdown(
            metric_card(f"{before['coverage_percentage']}%", "Coverage (Before)",
                        coverage_color(before["coverage_percentage"])),
            unsafe_allow_html=True,
        )
        st.markdown(
            metric_card(f"{after['coverage_percentage']}%", "Coverage (After)",
                        coverage_color(after["coverage_percentage"])),
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            metric_card(f"{before['compliance_percentage']}%", "PEP-257 (Before)",
                        coverage_color(before["compliance_percentage"])),
            unsafe_allow_html=True,
        )
        st.markdown(
            metric_card(f"{after['compliance_percentage']}%", "PEP-257 (After)",
                        coverage_color(after["compliance_percentage"])),
            unsafe_allow_html=True,
        )


def display_improvement_banner(before: dict, after: dict):
    """Show coverage and compliance delta as st.metric widgets."""
    cov_delta  = round(after["coverage_percentage"]   - before["coverage_percentage"],   1)
    comp_delta = round(after["compliance_percentage"] - before["compliance_percentage"], 1)

    st.markdown("#### 📈 Improvements at a Glance")
    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            label="Documentation Coverage",
            value=f"{after['coverage_percentage']}%",
            delta=f"{cov_delta:+.1f}% vs before",
            help=TOOLTIPS["coverage"],
        )
        progress_bar(after["coverage_percentage"], "Coverage after instrumentation")
    with c2:
        st.metric(
            label="PEP-257 Compliance",
            value=f"{after['compliance_percentage']}%",
            delta=f"{comp_delta:+.1f}% vs before",
            help=TOOLTIPS["compliance"],
        )
        progress_bar(after["compliance_percentage"], "Compliance after instrumentation")


def display_violations(violations: list, label: str = ""):
    """Render violations as styled cards with an optional expander."""
    if not violations:
        st.success(f"✅ No PEP-257 violations {label}")
        return

    st.warning(f"⚠️ {len(violations)} PEP-257 violation(s) found {label}")

    # Search inside violations
    v_search = st.text_input(
        "🔍 Search violations",
        key=f"vsearch_{label}",
        placeholder="Filter by message or code…",
        help="Narrow violations by typing a keyword from the message or PEP code.",
    )
    filtered = violations
    if v_search:
        q = v_search.lower()
        filtered = [v for v in violations
                    if q in str(v.get("message","")).lower()
                    or q in str(v.get("code","")).lower()]

    st.caption(f"Showing {len(filtered)} of {len(violations)} violations")

    for i, v in enumerate(filtered, 1):
        with st.expander(f"Violation #{i} — {v.get('code','?')} · Line {v.get('line','?')}"):
            st.markdown(f"""
            <div class="violation-card">
              <b>Line:</b> {v.get('line','–')}<br>
              <b>Code:</b> <code>{v.get('code','–')}</code><br>
              <b>Message:</b> {v.get('message','–')}<br>
              <b>Source:</b> <code>{v.get('source','–')}</code>
            </div>
            """, unsafe_allow_html=True)


def display_documentation_status(
    quality_report: dict,
    title: str,
    search_query: str = "",
    show_functions: bool = True,
    show_classes: bool = True,
):
    """Documented vs undocumented breakdown with search + section filter."""
    st.markdown(f'<span class="section-pill">{title}</span>', unsafe_allow_html=True)
    search = search_query.lower().strip()
    col1, col2 = st.columns(2)

    if show_functions:
        with col1:
            total  = quality_report["total_functions"]
            docd   = quality_report["documented_functions"]
            undocd = total - docd
            st.markdown(f"**🔧 Functions** — {total} total")
            progress_bar(round(docd / total * 100, 1) if total else 0, "Documented")
            st.caption(f"✅ Documented: {docd}   ❌ Undocumented: {undocd}")

            funcs = quality_report.get("undocumented_functions") or []
            if search:
                funcs = [f for f in funcs if search in f.lower()]
            if funcs:
                st.markdown("**Undocumented functions:**")
                for f in funcs:
                    st.markdown(f"- `{f}`")
            elif undocd == 0:
                st.success("All functions are documented!")
            else:
                st.info("No matches for current search.")

    if show_classes:
        with col2:
            total  = quality_report["total_classes"]
            docd   = quality_report["documented_classes"]
            undocd = total - docd
            st.markdown(f"**🏗️ Classes** — {total} total")
            progress_bar(round(docd / total * 100, 1) if total else 0, "Documented")
            st.caption(f"✅ Documented: {docd}   ❌ Undocumented: {undocd}")

            classes = quality_report.get("undocumented_classes") or []
            if search:
                classes = [c for c in classes if search in c.lower()]
            if classes:
                st.markdown("**Undocumented classes:**")
                for c in classes:
                    st.markdown(f"- `{c}`")
            elif undocd == 0:
                st.success("All classes are documented!")
            else:
                st.info("No matches for current search.")


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📝 Auto-DocstringGen")
    st.markdown("*Automatically generates, validates, and reports PEP-257 compliant docstrings for Python code*")
    st.markdown("---")

    style = st.selectbox(
        "📐 Documentation Style",
        ["Google Style", "NumPy Style", "reStructuredText"],
        index=0,
        help=TOOLTIPS["style"],
    )
    style_map = {"Google Style": "google", "NumPy Style": "numpy", "reStructuredText": "reST"}
    selected_style = style_map[style]

    st.markdown("---")
    st.markdown("### ℹ️ How It Works")
    with st.expander("Click to expand", expanded=False):
        st.markdown("""
        1. **Upload** a `.py` file or `.zip` archive
        2. **Choose** a docstring style
        3. **Click** Process Files
        4. **Review** before/after metrics
        5. **Download** results
        """)

    st.markdown("---")
    st.markdown("### 🔑 Style Guide")
    with st.expander("Docstring formats", expanded=False):
        st.markdown("""
        **Google Style**
        ```python
        def fn(x):
            \"\"\"Summary.

            Args:
                x (int): Description.

            Returns:
                int: Description.
            \"\"\"
        ```
        **NumPy Style**
        ```python
        def fn(x):
            \"\"\"Summary.

            Parameters
            ----------
            x : int
                Description.
            \"\"\"
        ```
        """)

    st.markdown("---")
    st.markdown("### 📊 Legend")
    st.markdown("""
    🟢 ≥ 80% — Good  
    🟡 50–79% — Fair  
    🔴 < 50% — Needs work  
    """)

    st.markdown("---")
    st.caption("Auto-DocstringGen v1.0.0 · [PEP 257](https://peps.python.org/pep-0257/)")


# ─────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────
st.title("📝 Auto-DocstringGen")
st.markdown(
    "**Automated docstring generation & PEP-257 validation** · "
    "Upload a Python file or ZIP, generate missing docstrings, and review quality metrics."
)
st.markdown("---")

# ─────────────────────────────────────────────
# FILE UPLOAD
# ─────────────────────────────────────────────
col_up, col_info = st.columns([2, 1])

with col_up:
    uploaded_file = st.file_uploader(
        "📂 Upload Python file or ZIP archive",
        type=["py", "zip"],
        accept_multiple_files=False,
        help="Upload a single .py file for analysis, or a .zip archive containing multiple .py files.",
    )

with col_info:
    st.info(
        "**Supported inputs**\n\n"
        "• Single `.py` file\n"
        "• `.zip` archive with multiple Python files\n\n"
        "Results include before/after metrics and downloadable reports.",
        icon="💡",
    )

if uploaded_file:
    if st.button(
        "🚀 Process Files",
        type="primary",
        use_container_width=True,
        help=TOOLTIPS["process"],
    ):
        with st.spinner("⏳ Analysing and generating docstrings…"):
            try:
                if uploaded_file.name.endswith(".zip"):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        zip_path = os.path.join(tmpdir, uploaded_file.name)
                        with open(zip_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        with zipfile.ZipFile(zip_path, "r") as zr:
                            zr.extractall(tmpdir)
                        results = CodeInstrumentor.process_directory(tmpdir, selected_style)
                        st.session_state.results = results
                        # Clear single-file state
                        for k in ["original_code", "instrumented_code", "original_quality",
                                  "instrumented_quality", "validation_results",
                                  "original_violations", "original_coverage_report",
                                  "instrumented_coverage_report", "original_compliance_report",
                                  "instrumented_compliance_report"]:
                            st.session_state[k] = None
                else:
                    content = uploaded_file.getvalue().decode("utf-8")
                    st.session_state.original_code    = content
                    st.session_state.results          = None

                    oq = DocstringValidator.analyze_code_quality(content)
                    st.session_state.original_quality         = oq
                    st.session_state.original_coverage_report = generate_before_coverage_report(oq)

                    orig_v = [
                        {"line": v.line, "code": v.code, "message": v.message, "source": v.source}
                        for v in oq["violations"]
                    ]
                    st.session_state.original_violations      = orig_v
                    st.session_state.original_compliance_report = generate_compliance_report(
                        orig_v, "PEP-257 Compliance Report (Before Instrumentation)"
                    )

                    inst = CodeInstrumentor.add_docstrings(content, selected_style)
                    st.session_state.instrumented_code = inst

                    iq = DocstringValidator.analyze_code_quality(inst)
                    st.session_state.instrumented_quality           = iq
                    st.session_state.instrumented_coverage_report   = generate_after_coverage_report(iq)

                    import tempfile as _tf, os as _os
                    fd, tmp_path = _tf.mkstemp(suffix=".py", text=True)
                    try:
                        with _os.fdopen(fd, "w", encoding="utf-8") as tmp:
                            tmp.write(inst)
                        val = DocstringValidator.validate_file(tmp_path)
                    finally:
                        try:
                            _os.unlink(tmp_path)
                        except OSError:
                            pass

                    st.session_state.validation_results = val
                    st.session_state.instrumented_compliance_report = generate_compliance_report(
                        val, "PEP-257 Compliance Report (After Instrumentation)"
                    )

                st.success("✅ Processing complete!")

            except Exception as e:
                st.error(f"❌ An error occurred: {e}")
                st.exception(e)


# ─────────────────────────────────────────────
# RESULTS — SINGLE FILE
# ─────────────────────────────────────────────
if (
    st.session_state.original_quality
    and st.session_state.instrumented_quality
    and not st.session_state.results
):
    oq = st.session_state.original_quality
    iq = st.session_state.instrumented_quality

    st.markdown("---")
    st.subheader("📊 Metrics Overview")
    display_metrics_comparison(oq, iq)

    st.markdown("---")
    display_improvement_banner(oq, iq)

    # ── Filters ──────────────────────────────
    st.markdown("---")
    st.subheader("🔍 Documentation Status")
    fc1, fc2 = st.columns(2)
    with fc1:
        sq = st.text_input(
            "Search functions / classes",
            placeholder="e.g. validate, parse…",
            help=TOOLTIPS["sym_search"],
        )
    with fc2:
        sections = st.multiselect(
            "Show sections",
            ["Functions", "Classes"],
            default=["Functions", "Classes"],
            help=TOOLTIPS["sym_section"],
        )
    show_f = "Functions" in sections
    show_c = "Classes"   in sections

    tab_before, tab_after = st.tabs(["Before Instrumentation", "After Instrumentation"])

    with tab_before:
        display_documentation_status(oq, "Before Instrumentation", sq, show_f, show_c)
        st.markdown("---")
        st.markdown("#### PEP-257 Violations (Before)")
        display_violations(st.session_state.original_violations or [], "before instrumentation")

    with tab_after:
        display_documentation_status(iq, "After Instrumentation", sq, show_f, show_c)
        st.markdown("---")
        st.markdown("#### PEP-257 Violations (After)")
        display_violations(st.session_state.validation_results or [], "after instrumentation")

    # ── Reports ───────────────────────────────
    st.markdown("---")
    st.subheader("📄 Detailed Reports")
    rt1, rt2 = st.tabs(["Coverage Reports", "Compliance Reports"])

    with rt1:
        rc1, rc2 = st.columns(2)
        with rc1:
            st.caption("Before Instrumentation")
            st.text_area("Coverage", st.session_state.original_coverage_report, height=250, label_visibility="collapsed")
            st.download_button("📥 Download", st.session_state.original_coverage_report,
                               file_name="coverage_before.txt", mime="text/plain")
        with rc2:
            st.caption("After Instrumentation")
            st.text_area("Coverage", st.session_state.instrumented_coverage_report, height=250, label_visibility="collapsed")
            st.download_button("📥 Download", st.session_state.instrumented_coverage_report,
                               file_name="coverage_after.txt", mime="text/plain")

    with rt2:
        cc1, cc2 = st.columns(2)
        with cc1:
            st.caption("Before Instrumentation")
            st.text_area("Compliance", st.session_state.original_compliance_report, height=250, label_visibility="collapsed")
            st.download_button("📥 Download", st.session_state.original_compliance_report,
                               file_name="compliance_before.txt", mime="text/plain")
        with cc2:
            st.caption("After Instrumentation")
            st.text_area("Compliance", st.session_state.instrumented_compliance_report, height=250, label_visibility="collapsed")
            st.download_button("📥 Download", st.session_state.instrumented_compliance_report,
                               file_name="compliance_after.txt", mime="text/plain")

    # ── Code comparison ───────────────────────
    st.markdown("---")
    st.subheader("🔀 Code Comparison")
    code_c1, code_c2 = st.columns(2)
    with code_c1:
        st.caption("Original Code")
        st.code(st.session_state.original_code, language="python")
    with code_c2:
        st.caption("Instrumented Code")
        st.code(st.session_state.instrumented_code, language="python")
        st.download_button(
            "📥 Download Instrumented Code",
            st.session_state.instrumented_code,
            file_name=f"instrumented_{uploaded_file.name if uploaded_file else 'code.py'}",
            mime="text/plain",
        )


# ─────────────────────────────────────────────
# RESULTS — ZIP / DIRECTORY
# ─────────────────────────────────────────────
if st.session_state.results:
    results   = st.session_state.results
    orig_sum  = results["original_summary"]
    inst_sum  = results["instrumented_summary"]

    st.markdown("---")
    st.subheader("📊 Project-wide Analysis")
    display_metrics_comparison(orig_sum, inst_sum)

    st.markdown("---")
    display_improvement_banner(orig_sum, inst_sum)

    # ── File search & filter ──────────────────
    st.markdown("---")
    st.subheader("📁 File Explorer")

    ff1, ff2 = st.columns(2)
    with ff1:
        file_search = st.text_input(
            "🔍 Search files",
            placeholder="Type filename…",
            help=TOOLTIPS["file_search"],
        )
    with ff2:
        file_filter = st.selectbox(
            "Filter files",
            ["All files", "Only files with undocumented items", "Only files with PEP-257 violations"],
            help=TOOLTIPS["file_filter"],
        )

    file_options = list(results["file_results"].keys())

    if file_search:
        file_options = [f for f in file_options if file_search.lower() in os.path.basename(f).lower()]

    if file_filter != "All files":
        filtered = []
        for path in file_options:
            d = results["file_results"][path]
            if file_filter == "Only files with undocumented items" and d["instrumented_quality"]["undocumented_items"] > 0:
                filtered.append(path)
            elif file_filter == "Only files with PEP-257 violations" and len(d["validation"]) > 0:
                filtered.append(path)
        file_options = filtered

    if not file_options:
        st.info("ℹ️ No files match the current search/filter settings.")
    else:
        # Show file summary table
        st.caption(f"{len(file_options)} file(s) shown")
        summary_rows = []
        for p in file_options:
            d = results["file_results"][p]
            iq = d["instrumented_quality"]
            summary_rows.append({
                "File": os.path.basename(p),
                "Functions": iq["total_functions"],
                "Classes": iq["total_classes"],
                "Coverage %": iq["coverage_percentage"],
                "Compliance %": iq["compliance_percentage"],
                "Violations": len(d["validation"]),
            })
        import pandas as pd
        st.dataframe(
            pd.DataFrame(summary_rows).set_index("File"),
            use_container_width=True,
        )

        selected_file = st.selectbox(
            "Select a file to inspect:",
            file_options,
            format_func=os.path.basename,
            help="Choose a file to see detailed before/after documentation status.",
        )

        if selected_file:
            fd = results["file_results"][selected_file]
            oq = fd["original_quality"]
            iq = fd["instrumented_quality"]

            st.subheader(f"📄 {os.path.basename(selected_file)}")
            display_metrics_comparison(oq, iq)
            display_improvement_banner(oq, iq)

            st.markdown("---")
            st.markdown("#### 🔍 Symbol Search & Filters")
            sc1, sc2 = st.columns(2)
            with sc1:
                sym_q = st.text_input(
                    "Search functions/classes",
                    key=f"sq_{selected_file}",
                    placeholder="e.g. parse, load…",
                    help=TOOLTIPS["sym_search"],
                )
            with sc2:
                sym_sec = st.multiselect(
                    "Show sections",
                    ["Functions", "Classes"],
                    default=["Functions", "Classes"],
                    key=f"ss_{selected_file}",
                    help=TOOLTIPS["sym_section"],
                )
            show_f = "Functions" in sym_sec
            show_c = "Classes"   in sym_sec

            tb1, tb2 = st.tabs(["Before Instrumentation", "After Instrumentation"])
            with tb1:
                display_documentation_status(oq, "Before", sym_q, show_f, show_c)
                st.markdown("---")
                before_v = [
                    {"line": v.line, "code": v.code, "message": v.message, "source": v.source}
                    for v in fd["original_violations"]
                ]
                display_violations(before_v, "before instrumentation")

            with tb2:
                display_documentation_status(iq, "After", sym_q, show_f, show_c)
                st.markdown("---")
                display_violations(fd["validation"], "after instrumentation")

            st.markdown("---")
            st.subheader("🔀 Code Comparison")
            cc1, cc2 = st.columns(2)
            with cc1:
                st.caption("Original")
                st.code(fd["original_code"], language="python")
            with cc2:
                st.caption("Instrumented")
                st.code(fd["instrumented_code"], language="python")

    # ── Download all ──────────────────────────
    st.markdown("---")
    st.subheader("📦 Download All Results")
    zip_buf = create_zip_from_results(results)
    st.download_button(
        label="📥 Download Full ZIP",
        data=zip_buf,
        file_name="docstringsiva_results.zip",
        mime="application/zip",
        help=TOOLTIPS["download_zip"],
        use_container_width=True,
    )
    with st.expander("📁 What's inside the ZIP?"):
        st.markdown("""
        For each processed `.py` file:
        - `original_<file>.py` — original source
        - `instrumented_<file>.py` — source with generated docstrings
        - `coverage_original_<file>.txt` — coverage report before
        - `coverage_instrumented_<file>.txt` — coverage report after
        - `compliance_original_<file>.txt` — PEP-257 report before
        - `compliance_instrumented_<file>.txt` — PEP-257 report after

        Plus a `project_summary.txt` with overall metrics.
        """)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#9ca3af;font-size:0.82rem'>
  Auto-DocstringGen v1.0.0 &nbsp;·&nbsp; Milestone 4 &nbsp;·&nbsp;
  <a href="https://peps.python.org/pep-0257/" target="_blank" style="color:#7c3aed">PEP 257</a> &nbsp;·&nbsp;
  <a href="https://pypi.org/project/docstringsiva/" target="_blank" style="color:#7c3aed">PyPI</a>
</div>
""", unsafe_allow_html=True)