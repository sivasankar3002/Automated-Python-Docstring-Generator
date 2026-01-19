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
    generate_compliance_report
)

# Page configuration
st.set_page_config(
    page_title="",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .reportview-container {
        background: #f5f7fa;
    }
    .sidebar .sidebar-content {
        background: #2c3e50;
        color: white;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .st-bb {
        background-color: #2c3e50;
        color: white;
    }
    .st-at {
        background-color: #3498db;
    }
    .css-1v3fvcr {
        background-color: #34495e;
    }
    .st-cx {
        background-color: #3498db;
    }
    .st-cy {
        background-color: #2980b9;
    }
    .css-1d90c0m {
        padding: 1rem 1rem 2rem;
    }
    .st-ag {
        font-weight: bold;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin: 10px 0;
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2c3e50;
    }
    .metric-label {
        font-size: 1.1rem;
        color: #7f8c8d;
        margin-top: 5px;
    }
    .compliance-good {
        color: #27ae60;
    }
    .compliance-bad {
        color: #e74c3c;
    }
    .comparison-container {
        background: white;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .before-section {
        background-color: #e8f4fd;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .after-section {
        background-color: #e8f5e9;
        padding: 15px;
        border-radius: 8px;
    }
    .improvement {
        color: #27ae60;
        font-weight: bold;
    }
    .decline {
        color: #e74c3c;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'results' not in st.session_state:
    st.session_state.results = None
if 'original_code' not in st.session_state:
    st.session_state.original_code = None
if 'instrumented_code' not in st.session_state:
    st.session_state.instrumented_code = None
if 'original_quality' not in st.session_state:
    st.session_state.original_quality = None
if 'instrumented_quality' not in st.session_state:
    st.session_state.instrumented_quality = None
if 'validation_results' not in st.session_state:
    st.session_state.validation_results = None
if 'original_violations' not in st.session_state:
    st.session_state.original_violations = None
if 'original_coverage_report' not in st.session_state:
    st.session_state.original_coverage_report = None
if 'instrumented_coverage_report' not in st.session_state:
    st.session_state.instrumented_coverage_report = None
if 'original_compliance_report' not in st.session_state:
    st.session_state.original_compliance_report = None
if 'instrumented_compliance_report' not in st.session_state:
    st.session_state.instrumented_compliance_report = None

# Helper functions
def create_zip_from_results(results):
    """Create ZIP file from processing results"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Add files for each processed file
        for file_path, data in results['file_results'].items():
            filename = os.path.basename(file_path)
            
            # Original code
            zip_file.writestr(f"original_{filename}", data['original_code'])
            
            # Instrumented code
            zip_file.writestr(f"instrumented_{filename}", data['instrumented_code'])
            
            # Reports for original code
            orig_cov_rpt = generate_before_coverage_report(data['original_quality'])
            orig_comp_rpt = generate_compliance_report(
                [{'line': v.line, 'code': v.code, 'message': v.message, 'source': v.source} 
                 for v in data['original_violations']],
                "PEP-257 Compliance Report (Before Instrumentation)"
            )
            
            # Reports for instrumented code
            inst_cov_rpt = generate_after_coverage_report(data['instrumented_quality'])
            inst_comp_rpt = generate_compliance_report(
                data['validation'],
                "PEP-257 Compliance Report (After Instrumentation)"
            )
            
            # Save reports
            zip_file.writestr(f"coverage_report_original_{filename}.txt", orig_cov_rpt)
            zip_file.writestr(f"compliance_report_original_{filename}.txt", orig_comp_rpt)
            zip_file.writestr(f"coverage_report_instrumented_{filename}.txt", inst_cov_rpt)
            zip_file.writestr(f"compliance_report_instrumented_{filename}.txt", inst_comp_rpt)
        
        # Add summary reports
        orig_summary = results['original_summary']
        inst_summary = results['instrumented_summary']
        
        summary_rpt = f"""
Docstring gen - Project Analysis Summary
==================================

BEFORE INSTRUMENTATION:
----------------------
Total Functions: {orig_summary['total_functions']}
Total Classes: {orig_summary['total_classes']}
Documented Items: {orig_summary['documented_items']}
Undocumented Items: {orig_summary['undocumented_items']}
Documentation Coverage: {orig_summary['coverage_percentage']}%
PEP-257 Compliance: {orig_summary['compliance_percentage']}%
PEP-257 Violations: {orig_summary['violation_count']}

AFTER INSTRUMENTATION:
---------------------
Total Functions: {inst_summary['total_functions']}
Total Classes: {inst_summary['total_classes']}
Documented Items: {inst_summary['documented_items']}
Undocumented Items: {inst_summary['undocumented_items']}
Documentation Coverage: {inst_summary['coverage_percentage']}%
PEP-257 Compliance: {inst_summary['compliance_percentage']}%
PEP-257 Violations: {inst_summary['violation_count']}

IMPROVEMENT:
-----------
Coverage Improvement: {round(inst_summary['coverage_percentage'] - orig_summary['coverage_percentage'], 1)}%
Compliance Improvement: {round(inst_summary['compliance_percentage'] - orig_summary['compliance_percentage'], 1)}%
"""
        zip_file.writestr("project_summary.txt", summary_rpt)
    
    zip_buffer.seek(0)
    return zip_buffer

def display_metrics_comparison(before, after):
    """Display metrics comparison between before and after instrumentation"""
    col1, col2, col3, col4 = st.columns(4)
    
    # Functions comparison
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{before['total_functions']}</div>
            <div class="metric-label">Functions (Before)</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{after['total_functions']}</div>
            <div class="metric-label">Functions (After)</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Classes comparison
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{before['total_classes']}</div>
            <div class="metric-label">Classes (Before)</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{after['total_classes']}</div>
            <div class="metric-label">Classes (After)</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Coverage comparison
    with col3:
        before_color = "compliance-good" if before['coverage_percentage'] > 80 else "compliance-bad"
        after_color = "compliance-good" if after['coverage_percentage'] > 80 else "compliance-bad"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value {before_color}">{before['coverage_percentage']}%</div>
            <div class="metric-label">Coverage % (Before)</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value {after_color}">{after['coverage_percentage']}%</div>
            <div class="metric-label">Coverage % (After)</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Compliance comparison
    with col4:
        before_color = "compliance-good" if before['compliance_percentage'] > 80 else "compliance-bad"
        after_color = "compliance-good" if after['compliance_percentage'] > 80 else "compliance-bad"
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value {before_color}">{before['compliance_percentage']}%</div>
            <div class="metric-label">Compliance % (Before)</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value {after_color}">{after['compliance_percentage']}%</div>
            <div class="metric-label">Compliance % (After)</div>
        </div>
        """, unsafe_allow_html=True)

def display_documentation_status(quality_report, title):
    """Display documented vs undocumented items"""
    st.subheader(title)
    
    # Functions status
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Functions:** {quality_report['total_functions']}")
        st.markdown(f"- **Documented:** {quality_report['documented_functions']}")
        st.markdown(f"- **Undocumented:** {quality_report['total_functions'] - quality_report['documented_functions']}")
        
        if quality_report['undocumented_functions']:
            st.markdown("##### Undocumented Functions:")
            for func in quality_report['undocumented_functions']:
                st.markdown(f"- `{func}`")
    
    # Classes status
    with col2:
        st.markdown(f"**Classes:** {quality_report['total_classes']}")
        st.markdown(f"- **Documented:** {quality_report['documented_classes']}")
        st.markdown(f"- **Undocumented:** {quality_report['total_classes'] - quality_report['documented_classes']}")
        
        if quality_report['undocumented_classes']:
            st.markdown("##### Undocumented Classes:")
            for cls in quality_report['undocumented_classes']:
                st.markdown(f"- `{cls}`")

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3764/3764812.png", width=100)
    st.title("Docstring Gen")
    st.markdown("### AI-Powered Docstring Generator")
    st.markdown("---")
    
    style = st.selectbox(
        "Documentation Style",
        ["Google Style", "NumPy Style", "reStructuredText"],
        index=0,
        help="Select the documentation style for generated docstrings"
    )
    
    style_map = {
        "Google Style": "google",
        "NumPy Style": "numpy",
        "reStructuredText": "reST"
    }
    selected_style = style_map[style]
    
    st.markdown("---")
    st.subheader("Features")
    st.markdown("""
    - ✨ Multi-style docstring generation
    - 🔍 Before/after comparison
    - 📊 Detailed coverage reporting
    - ⚡️ PEP-257 compliance analysis
    - 📥 One-click export
    """)
    
    st.markdown("---")
    st.markdown("### How to Use")
    st.markdown("""
    1. Upload a Python file or ZIP archive
    2. Select documentation style
    3. Click 'Process Files'
    4. Review before/after metrics
    5. Download results
    """)

# Main content
st.title("Milestone 2: Synthesis & Validation")
st.markdown("### Enhancing docstring generation with multi-style support and quality validation")

# File upload
uploaded_file = st.file_uploader(
    "Upload Python file or ZIP archive containing Python files", 
    type=["py", "zip"],
    accept_multiple_files=False
)

if uploaded_file:
    # Process button
    if st.button("🚀 Process Files", type="primary", use_container_width=True):
        with st.spinner("Processing your code..."):
            try:
                # Handle ZIP files
                if uploaded_file.name.endswith('.zip'):
                    with tempfile.TemporaryDirectory() as tmpdirname:
                        zip_path = os.path.join(tmpdirname, uploaded_file.name)
                        with open(zip_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(tmpdirname)
                        
                        # Process directory
                        results = CodeInstrumentor.process_directory(tmpdirname, selected_style)
                        st.session_state.results = results
                
                # Handle single Python file
                else:
                    content = uploaded_file.getvalue().decode("utf-8")
                    st.session_state.original_code = content
                    
                    # Analyze original code
                    original_quality = DocstringValidator.analyze_code_quality(content)
                    st.session_state.original_quality = original_quality
                    
                    # Generate original reports
                    st.session_state.original_coverage_report = generate_before_coverage_report(original_quality)
                    
                    original_violations = [
                        {'line': v.line, 'code': v.code, 'message': v.message, 'source': v.source}
                        for v in original_quality['violations']
                    ]
                    st.session_state.original_violations = original_violations
                    st.session_state.original_compliance_report = generate_compliance_report(
                        original_violations,
                        "PEP-257 Compliance Report (Before Instrumentation)"
                    )
                    
                    # Add docstrings
                    instrumented_code = CodeInstrumentor.add_docstrings(content, selected_style)
                    st.session_state.instrumented_code = instrumented_code
                    
                    # Analyze instrumented code
                    instrumented_quality = DocstringValidator.analyze_code_quality(instrumented_code)
                    st.session_state.instrumented_quality = instrumented_quality
                    
                    # Validate compliance
                    with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False) as tmp:
                        tmp.write(instrumented_code)
                        tmp_path = tmp.name
                    
                    validation_results = DocstringValidator.validate_file(tmp_path)
                    st.session_state.validation_results = validation_results
                    
                    # Generate instrumented reports
                    st.session_state.instrumented_coverage_report = generate_after_coverage_report(instrumented_quality)
                    st.session_state.instrumented_compliance_report = generate_compliance_report(
                        validation_results,
                        "PEP-257 Compliance Report (After Instrumentation)"
                    )
                    
                    os.unlink(tmp_path)
                
                st.success("✅ Processing complete!")
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.exception(e)

# Display results for single file
if st.session_state.original_quality and st.session_state.instrumented_quality and not st.session_state.results:
    st.markdown("---")
    st.subheader("Documentation Status Comparison")
    
    # Display metrics comparison
    display_metrics_comparison(st.session_state.original_quality, st.session_state.instrumented_quality)
    
    # Show improvement metrics
    coverage_improvement = round(
        st.session_state.instrumented_quality['coverage_percentage'] - 
        st.session_state.original_quality['coverage_percentage'], 
        1
    )
    compliance_improvement = round(
        st.session_state.instrumented_quality['compliance_percentage'] - 
        st.session_state.original_quality['compliance_percentage'], 
        1
    )
    
    st.markdown(f"### 📈 Improvements")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Documentation Coverage Improvement", 
            f"{coverage_improvement}%", 
            delta=f"from {st.session_state.original_quality['coverage_percentage']}% to {st.session_state.instrumented_quality['coverage_percentage']}%"
        )
    with col2:
        st.metric(
            "PEP-257 Compliance Improvement", 
            f"{compliance_improvement}%", 
            delta=f"from {st.session_state.original_quality['compliance_percentage']}% to {st.session_state.instrumented_quality['compliance_percentage']}%"
        )
    
    # Detailed documentation status
    st.markdown("---")
    st.subheader("Detailed Documentation Status")
    
    tab1, tab2 = st.tabs(["Before Instrumentation", "After Instrumentation"])
    
    with tab1:
        display_documentation_status(st.session_state.original_quality, "Before Instrumentation")
        
        st.markdown("---")
        st.subheader("PEP-257 Compliance Status (Before)")
        if st.session_state.original_violations:
            st.warning(f"Found {len(st.session_state.original_violations)} PEP-257 violations")
            for i, violation in enumerate(st.session_state.original_violations, 1):
                st.markdown(f"**Violation #{i}**")
                st.markdown(f"- **Line:** {violation['line']}")
                st.markdown(f"- **Code:** {violation['code']}")
                st.markdown(f"- **Message:** {violation['message']}")
                st.markdown(f"- **Source:** {violation['source']}")
                st.markdown("---")
        else:
            st.success("✅ No PEP-257 violations found before instrumentation!")
    
    with tab2:
        display_documentation_status(st.session_state.instrumented_quality, "After Instrumentation")
        
        st.markdown("---")
        st.subheader("PEP-257 Compliance Status (After)")
        if st.session_state.validation_results:
            st.warning(f"Found {len(st.session_state.validation_results)} PEP-257 violations")
            for i, violation in enumerate(st.session_state.validation_results, 1):
                st.markdown(f"**Violation #{i}**")
                st.markdown(f"- **Line:** {violation['line']}")
                st.markdown(f"- **Code:** {violation['code']}")
                st.markdown(f"- **Message:** {violation['message']}")
                st.markdown(f"- **Source:** {violation['source']}")
                st.markdown("---")
        else:
            st.success("✅ No PEP-257 violations found after instrumentation!")
    
    # Reports section
    st.markdown("---")
    st.subheader("Detailed Reports")
    
    tab1, tab2 = st.tabs(["Coverage Reports", "Compliance Reports"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Before Instrumentation")
            st.text_area("Coverage Report", st.session_state.original_coverage_report, height=300)
            st.download_button(
                "📥 Download Original Coverage Report",
                st.session_state.original_coverage_report,
                file_name="coverage_report_original.txt",
                mime="text/plain"
            )
        
        with col2:
            st.subheader("After Instrumentation")
            st.text_area("Coverage Report", st.session_state.instrumented_coverage_report, height=300)
            st.download_button(
                "📥 Download Instrumented Coverage Report",
                st.session_state.instrumented_coverage_report,
                file_name="coverage_report_instrumented.txt",
                mime="text/plain"
            )
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Before Instrumentation")
            st.text_area("Compliance Report", st.session_state.original_compliance_report, height=300)
            st.download_button(
                "📥 Download Original Compliance Report",
                st.session_state.original_compliance_report,
                file_name="compliance_report_original.txt",
                mime="text/plain"
            )
        
        with col2:
            st.subheader("After Instrumentation")
            st.text_area("Compliance Report", st.session_state.instrumented_compliance_report, height=300)
            st.download_button(
                "📥 Download Instrumented Compliance Report",
                st.session_state.instrumented_compliance_report,
                file_name="compliance_report_instrumented.txt",
                mime="text/plain"
            )
    
    # Code comparison
    st.markdown("---")
    st.subheader("Code Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Original Code")
        st.code(st.session_state.original_code, language="python")
    
    with col2:
        st.subheader("Instrumented Code")
        st.code(st.session_state.instrumented_code, language="python")
        
        st.download_button(
            "📥 Download Instrumented Code",
            st.session_state.instrumented_code,
            file_name=f"instrumented_{uploaded_file.name}",
            mime="text/plain"
        )

# Display results for directory/ZIP
if st.session_state.results:
    results = st.session_state.results
    original_summary = results['original_summary']
    instrumented_summary = results['instrumented_summary']
    
    st.markdown("---")
    st.subheader("Project-wide Analysis Summary")
    
    # Display metrics comparison
    display_metrics_comparison(original_summary, instrumented_summary)
    
    # Show improvement metrics
    coverage_improvement = round(instrumented_summary['coverage_percentage'] - original_summary['coverage_percentage'], 1)
    compliance_improvement = round(instrumented_summary['compliance_percentage'] - original_summary['compliance_percentage'], 1)
    
    st.markdown(f"### 📈 Project-wide Improvements")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Documentation Coverage Improvement", 
            f"{coverage_improvement}%", 
            delta=f"from {original_summary['coverage_percentage']}% to {instrumented_summary['coverage_percentage']}%"
        )
    with col2:
        st.metric(
            "PEP-257 Compliance Improvement", 
            f"{compliance_improvement}%", 
            delta=f"from {original_summary['compliance_percentage']}% to {instrumented_summary['compliance_percentage']}%"
        )
    
    # File selector
    st.markdown("---")
    st.subheader("File Details")
    
    file_options = list(results['file_results'].keys())
    selected_file = st.selectbox("Select file to view details:", file_options)
    
    if selected_file:
        file_data = results['file_results'][selected_file]
        original_quality = file_data['original_quality']
        instrumented_quality = file_data['instrumented_quality']
        
        st.subheader(f"File: {os.path.basename(selected_file)}")
        
        # File metrics comparison
        st.subheader("Metrics Comparison")
        display_metrics_comparison(original_quality, instrumented_quality)
        
        # Detailed documentation status
        st.markdown("---")
        st.subheader("Detailed Documentation Status")
        
        tab1, tab2 = st.tabs(["Before Instrumentation", "After Instrumentation"])
        
        with tab1:
            display_documentation_status(original_quality, "Before Instrumentation")
            
            st.markdown("---")
            st.subheader("PEP-257 Compliance Status (Before)")
            if file_data['original_violations']:
                st.warning(f"Found {len(file_data['original_violations'])} PEP-257 violations")
                for i, violation in enumerate(file_data['original_violations'], 1):
                    v_dict = {
                        'line': violation.line,
                        'code': violation.code,
                        'message': violation.message,
                        'source': violation.source
                    }
                    st.markdown(f"**Violation #{i}**")
                    st.markdown(f"- **Line:** {v_dict['line']}")
                    st.markdown(f"- **Code:** {v_dict['code']}")
                    st.markdown(f"- **Message:** {v_dict['message']}")
                    st.markdown(f"- **Source:** {v_dict['source']}")
                    st.markdown("---")
            else:
                st.success("✅ No PEP-257 violations found before instrumentation!")
        
        with tab2:
            display_documentation_status(instrumented_quality, "After Instrumentation")
            
            st.markdown("---")
            st.subheader("PEP-257 Compliance Status (After)")
            if file_data['validation']:
                st.warning(f"Found {len(file_data['validation'])} PEP-257 violations")
                for i, violation in enumerate(file_data['validation'], 1):
                    st.markdown(f"**Violation #{i}**")
                    st.markdown(f"- **Line:** {violation['line']}")
                    st.markdown(f"- **Code:** {violation['code']}")
                    st.markdown(f"- **Message:** {violation['message']}")
                    st.markdown(f"- **Source:** {violation['source']}")
                    st.markdown("---")
            else:
                st.success("✅ No PEP-257 violations found after instrumentation!")
        
        # Code comparison
        st.markdown("---")
        st.subheader("Code Comparison")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Original Code")
            st.code(file_data['original_code'], language="python")
        
        with col2:
            st.subheader("Instrumented Code")
            st.code(file_data['instrumented_code'], language="python")
    
    # Download all results
    st.markdown("---")
    st.subheader("Download Results")
    
    zip_buffer = create_zip_from_results(results)
    
    st.download_button(
        label="📥 Download All Results (ZIP)",
        data=zip_buffer,
        file_name="documind_results.zip",
        mime="application/zip"
    )
    
    # Show what's in the ZIP
    with st.expander("📁 ZIP Contents Preview"):
        st.markdown("""
        For each processed file:
        - `original_<filename>.py` - Original code
        - `instrumented_<filename>.py` - Code with added docstrings
        - `coverage_report_original_<filename>.txt` - Coverage metrics before instrumentation
        - `compliance_report_original_<filename>.txt` - PEP-257 compliance before instrumentation
        - `coverage_report_instrumented_<filename>.txt` - Coverage metrics after instrumentation
        - `compliance_report_instrumented_<filename>.txt` - PEP-257 compliance after instrumentation
        
        Additional files:
        - `project_summary.txt` - Overall project metrics and improvements
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #7f8c8d;'>
    <small>
        Docstring Gen v1.0 • Milestone 2 Implementation • 
        <a href="https://peps.python.org/pep-0257/" target="_blank">PEP 257</a> compliant
    </small>
</div>
""", unsafe_allow_html=True)