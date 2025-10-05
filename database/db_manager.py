import streamlit as st
import pandas as pd
from datetime import datetime
import tempfile
import os
from pathlib import Path

# Import utilities
# from database.db_manager import DatabaseManager
# from utils.cad_evaluator import CADEvaluator
# from utils.pdf_generator import PDFReportGenerator
# from utils.file_manager import FileManager

# Page configuration
st.set_page_config(
    page_title="CAD Evaluation System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize managers
@st.cache_resource
def init_managers():
    return {
        'db': DatabaseManager(),
        'evaluator': CADEvaluator(),
        'pdf': PDFReportGenerator(),
        'files': FileManager()
    }

managers = init_managers()

# Session state initialization
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        color: #721c24;
    }
    .info-box {
        padding: 1rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 5px;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)

# ============== AUTHENTICATION FUNCTIONS ==============

def login_page():
    """Login page"""
    st.markdown("<h1 class='main-header'>🎓 CAD Evaluation System</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("🔐 Login")
        
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        col_login, col_register = st.columns(2)
        
        with col_login:
            if st.button("Login", use_container_width=True):
                if username and password:
                    success, user_data = managers['db'].authenticate_user(username, password)
                    if success:
                        st.session_state.user = user_data
                        st.session_state.page = 'student_dashboard' if user_data['role'] == 'student' else 'faculty_dashboard'
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                else:
                    st.warning("Please enter username and password")
        
        with col_register:
            if st.button("Register", use_container_width=True):
                st.session_state.page = 'register'
                st.rerun()

def register_page():
    """Registration page"""
    st.markdown("<h1 class='main-header'>📝 Student Registration</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("registration_form"):
            username = st.text_input("Username*")
            password = st.text_input("Password*", type="password")
            confirm_password = st.text_input("Confirm Password*", type="password")
            full_name = st.text_input("Full Name*")
            email = st.text_input("Email*")
            department = st.selectbox("Department", [
                "Mechanical Engineering",
                "Civil Engineering",
                "Electrical Engineering",
                "Computer Science",
                "Other"
            ])
            
            col_submit, col_back = st.columns(2)
            
            with col_submit:
                submit = st.form_submit_button("Register", use_container_width=True)
            
            with col_back:
                back = st.form_submit_button("Back to Login", use_container_width=True)
            
            if submit:
                if not all([username, password, full_name, email]):
                    st.error("Please fill all required fields")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    success, result = managers['db'].register_user(
                        username, password, full_name, email, 'student', department
                    )
                    if success:
                        st.success("Registration successful! Please login.")
                        st.session_state.page = 'login'
                        st.rerun()
                    else:
                        st.error(f"Registration failed: {result}")
            
            if back:
                st.session_state.page = 'login'
                st.rerun()

# ============== STUDENT PAGES ==============

def student_dashboard():
    """Student dashboard"""
    user = st.session_state.user
    
    st.markdown(f"<h1 class='main-header'>👨‍🎓 Student Dashboard</h1>", unsafe_allow_html=True)
    st.markdown(f"### Welcome, {user['full_name']}!")
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"**Logged in as:** {user['username']}")
        st.markdown(f"**Role:** {user['role'].title()}")
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = 'login'
            st.rerun()
    
    # Tabs
    tab1, tab2 = st.tabs(["📤 Submit Experiment", "📊 My Results"])
    
    with tab1:
        submit_experiment_tab(user)
    
    with tab2:
        view_results_tab(user)

def submit_experiment_tab(user):
    """Submit experiment tab for students"""
    st.subheader("📤 Submit Your CAD Model")
    
    # Get active experiments
    experiments = managers['db'].get_active_experiments()
    
    if not experiments:
        st.info("No active experiments available at the moment.")
        return
    
    # Experiment selection
    experiment_options = {f"{exp['experiment_code']} - {exp['experiment_name']}": exp 
                         for exp in experiments}
    
    selected_exp_name = st.selectbox(
        "Select Experiment",
        options=list(experiment_options.keys())
    )
    
    if selected_exp_name:
        selected_exp = experiment_options[selected_exp_name]
        
        # Display experiment details
        with st.expander("📋 Experiment Details", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Code:** {selected_exp['experiment_code']}")
                st.write(f"**Name:** {selected_exp['experiment_name']}")
            with col2:
                st.write(f"**Created by:** {selected_exp['creator_name']}")
                if selected_exp['deadline']:
                    st.write(f"**Deadline:** {selected_exp['deadline']}")
            
            if selected_exp['description']:
                st.write(f"**Description:** {selected_exp['description']}")
        
        # File upload
        st.markdown("---")
        uploaded_file = st.file_uploader(
            "Upload Your CAD Model",
            type=['obj', 'stl', 'ply', 'off', 'step', 'stp', 'STEP', 'STP'],
            help="Supported formats: OBJ, STL, PLY, OFF, STEP (Max 200MB)"
        )
        
        if uploaded_file:
            # Show file info
            file_size = uploaded_file.size / (1024 * 1024)  # MB
            st.info(f"📁 **File:** {uploaded_file.name} ({file_size:.2f} MB)")
            
            if st.button("🚀 Submit for Evaluation", type="primary", use_container_width=True):
                with st.spinner("Processing your submission..."):
                    try:
                        # Save student submission
                        submission_path, filename = managers['files'].save_student_submission(
                            uploaded_file,
                            selected_exp['experiment_code'],
                            user['username']
                        )
                        
                        # Create submission record
                        success, submission_id = managers['db'].create_submission(
                            selected_exp['experiment_id'],
                            user['user_id'],
                            submission_path
                        )
                        
                        if not success:
                            st.error(f"Database error: {submission_id}")
                            return
                        
                        # Evaluate the model
                        st.info("🔍 Evaluating your CAD model...")
                        
                        reference_path = selected_exp['reference_model_path']
                        
                        eval_results = managers['evaluator'].evaluate(
                            reference_path,
                            submission_path,
                            num_points=2048
                        )
                        
                        if eval_results['success']:
                            # Generate PDF report
                            st.info("📄 Generating PDF report...")
                            
                            temp_pdf = tempfile.NamedTemporaryFile(
                                delete=False, suffix='.pdf'
                            )
                            
                            managers['pdf'].generate_evaluation_report(
                                temp_pdf.name,
                                {'full_name': user['full_name'], 
                                 'username': user['username'],
                                 'email': user.get('email', 'N/A')},
                                selected_exp,
                                eval_results
                            )
                            
                            # Save PDF to permanent storage
                            pdf_path = managers['files'].save_pdf_report(
                                temp_pdf.name,
                                selected_exp['experiment_code'],
                                user['username']
                            )
                            
                            # Save evaluation results
                            managers['db'].save_evaluation_result(
                                submission_id,
                                eval_results['grade'],
                                eval_results['feedback'],
                                pdf_path
                            )
                            
                            # Delete student submission file
                            success, message = managers['files'].delete_student_submission(submission_path)
                            
                            # If STEP file, also delete converted OBJ
                            if submission_path.lower().endswith(('.step', '.stp')):
                                converted_path = submission_path.replace('.step', '.obj').replace('.stp', '.obj').replace('.STEP', '.obj').replace('.STP', '.obj')
                                if os.path.exists(converted_path):
                                    try:
                                        os.remove(converted_path)
                                    except Exception as e:
                                        st.warning(f"Could not delete converted file: {str(e)}")
                            
                            # Clean up temp PDF
                            os.unlink(temp_pdf.name)
                            
                            # Show results
                            st.success("✅ Evaluation Complete!")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                grade = eval_results['grade']['letter_grade']
                                score = eval_results['grade']['numerical_score']
                                st.metric("Grade", f"{grade} ({score}%)")
                            with col2:
                                mean_dev = eval_results['grade']['mean_deviation']
                                st.metric("Mean Deviation", f"{mean_dev:.4f}")
                            with col3:
                                max_dev = eval_results['grade']['max_deviation']
                                st.metric("Max Deviation", f"{max_dev:.4f}")
                            
                            # Download PDF
                            with open(pdf_path, 'rb') as f:
                                st.download_button(
                                    "📥 Download Full Report (PDF)",
                                    f.read(),
                                    file_name=f"{user['username']}_evaluation_report.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                            
                            # Show feedback
                            with st.expander("📝 Detailed Feedback", expanded=True):
                                st.text(eval_results['feedback'])
                            
                            # Show 3D visualization heatmap
                            if 'heatmap' in eval_results:
                                st.markdown("---")
                                st.subheader("🎨 3D Accuracy Visualization")
                                st.plotly_chart(eval_results['heatmap'], use_container_width=True)
                                st.info("🔍 Red areas = higher deviation, Green areas = better accuracy. Rotate and zoom with mouse.")
                        
                        else:
                            st.error(f"Evaluation failed: {eval_results.get('error', 'Unknown error')}")
                            managers['db'].update_submission_status(submission_id, 'failed')
                    
                    except Exception as e:
                        st.error(f"Error during submission: {str(e)}")

def view_results_tab(user):
    """View previous results tab"""
    st.subheader("📊 Your Evaluation Results")
    
    submissions = managers['db'].get_student_submissions(user['user_id'])
    
    if not submissions:
        st.info("You haven't submitted any experiments yet.")
        return
    
    # Create dataframe
    df_data = []
    for sub in submissions:
        df_data.append({
            'Experiment': sub['experiment_code'],
            'Name': sub['experiment_name'],
            'Submitted': sub['submission_date'],
            'Grade': sub['letter_grade'] if sub['letter_grade'] else 'Pending',
            'Score': f"{sub['numerical_score']}%" if sub['numerical_score'] else 'N/A',
            'Status': sub['evaluation_status'].title()
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Download reports
    st.markdown("---")
    st.subheader("📥 Download Reports")
    
    for sub in submissions:
        if sub['pdf_report_path'] and os.path.exists(sub['pdf_report_path']):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{sub['experiment_code']}** - Grade: {sub['letter_grade']} ({sub['numerical_score']}%)")
            with col2:
                with open(sub['pdf_report_path'], 'rb') as f:
                    st.download_button(
                        "📄 PDF",
                        f.read(),
                        file_name=f"{sub['experiment_code']}_report.pdf",
                        key=f"download_{sub['submission_id']}"
                    )

# ============== FACULTY PAGES ==============

def faculty_dashboard():
    """Faculty dashboard"""
    user = st.session_state.user
    
    st.markdown(f"<h1 class='main-header'>👨‍🏫 Faculty Dashboard</h1>", unsafe_allow_html=True)
    st.markdown(f"### Welcome, {user['full_name']}!")
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"**Logged in as:** {user['username']}")
        st.markdown(f"**Role:** {user['role'].title()}")
        
        # Storage stats
        stats = managers['files'].get_storage_stats()
        st.markdown("---")
        st.markdown("**💾 Storage Usage**")
        st.write(f"Experiments: {stats['experiments']} MB")
        st.write(f"Submissions: {stats['submissions']} MB")
        st.write(f"Reports: {stats['reports']} MB")
        st.write(f"**Total: {stats['total']} MB**")
        
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = 'login'
            st.rerun()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "📤 Create Experiment",
        "📊 View All Results",
        "⚙️ Manage Experiments"
    ])
    
    with tab1:
        create_experiment_tab(user)
    
    with tab2:
        view_all_results_tab(user)
    
    with tab3:
        manage_experiments_tab(user)

def create_experiment_tab(user):
    """Create new experiment tab"""
    st.subheader("📤 Create New Experiment")
    
    with st.form("create_experiment_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            exp_code = st.text_input("Experiment Code*", placeholder="EXP001")
            exp_name = st.text_input("Experiment Name*", placeholder="Flange Design")
            deadline = st.date_input("Deadline (Optional)")
        
        with col2:
            description = st.text_area("Description", height=100)
            
        reference_file = st.file_uploader(
            "Upload Reference CAD Model*",
            type=['obj', 'stl', 'ply', 'off', 'step', 'stp', 'STEP', 'STP'],
            help="This is the correct model that students will be evaluated against"
        )
        
        # Custom grading thresholds (optional)
        with st.expander("⚙️ Custom Grading Thresholds (Optional)"):
            st.info("Leave blank to use default thresholds")
            col1, col2, col3 = st.columns(3)
            with col1:
                thresh_a = st.number_input("A Grade (≤)", value=0.1, step=0.01)
                thresh_b = st.number_input("B Grade (≤)", value=0.5, step=0.1)
            with col2:
                thresh_c = st.number_input("C Grade (≤)", value=1.0, step=0.1)
                thresh_d = st.number_input("D Grade (≤)", value=2.0, step=0.1)
        
        submit = st.form_submit_button("🚀 Create Experiment", use_container_width=True)
        
        if submit:
            if not all([exp_code, exp_name, reference_file]):
                st.error("Please fill all required fields and upload reference model")
            else:
                try:
                    with st.spinner("Creating experiment..."):
                        # Save reference file
                        ref_path, ref_filename = managers['files'].save_experiment_file(
                            reference_file,
                            exp_code
                        )
                        
                        # Prepare grading thresholds
                        custom_thresholds = {
                            'A': thresh_a,
                            'B': thresh_b,
                            'C': thresh_c,
                            'D': thresh_d,
                            'F': float('inf')
                        }
                        
                        # Create experiment in database
                        success, exp_id = managers['db'].create_experiment(
                            exp_code,
                            exp_name,
                            description,
                            ref_path,
                            user['user_id'],
                            deadline.isoformat() if deadline else None,
                            custom_thresholds
                        )
                        
                        if success:
                            st.success(f"✅ Experiment '{exp_code}' created successfully!")
                            st.balloons()
                        else:
                            st.error(f"Failed to create experiment: {exp_id}")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")

def view_all_results_tab(user):
    """View all student results"""
    st.subheader("📊 All Student Results")
    
    results = managers['db'].get_all_results_for_faculty(user['user_id'])
    
    if not results:
        st.info("No submissions yet.")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    experiments = list(set([r['experiment_code'] for r in results]))
    
    with col1:
        filter_exp = st.selectbox("Filter by Experiment", ['All'] + experiments)
    
    with col2:
        filter_grade = st.selectbox("Filter by Grade", ['All', 'A', 'B', 'C', 'D', 'F'])
    
    # Apply filters
    filtered_results = results
    if filter_exp != 'All':
        filtered_results = [r for r in filtered_results if r['experiment_code'] == filter_exp]
    if filter_grade != 'All':
        filtered_results = [r for r in filtered_results if r['letter_grade'] == filter_grade]
    
    # Create DataFrame
    df_data = []
    for r in filtered_results:
        df_data.append({
            'Student': r['full_name'],
            'Username': r['username'],
            'Experiment': r['experiment_code'],
            'Submitted': r['submission_date'],
            'Grade': r['letter_grade'] if r['letter_grade'] else 'Pending',
            'Score': f"{r['numerical_score']}%" if r['numerical_score'] else 'N/A',
            'Mean Dev': f"{r['mean_deviation']:.4f}" if r['mean_deviation'] else 'N/A'
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Statistics
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    evaluated = [r for r in filtered_results if r['numerical_score'] is not None]
    
    with col1:
        st.metric("Total Submissions", len(filtered_results))
    with col2:
        st.metric("Evaluated", len(evaluated))
    with col3:
        if evaluated:
            avg_score = sum([r['numerical_score'] for r in evaluated]) / len(evaluated)
            st.metric("Average Score", f"{avg_score:.1f}%")
    with col4:
        if evaluated:
            grade_dist = {}
            for r in evaluated:
                grade_dist[r['letter_grade']] = grade_dist.get(r['letter_grade'], 0) + 1
            most_common = max(grade_dist, key=grade_dist.get)
            st.metric("Most Common Grade", most_common)
    
    # Export to CSV
    if df_data:
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Export to CSV",
            csv,
            "evaluation_results.csv",
            "text/csv"
        )

def manage_experiments_tab(user):
    """Manage experiments tab"""
    st.subheader("⚙️ Manage Experiments")
    
    experiments = managers['db'].get_active_experiments()
    
    if not experiments:
        st.info("No experiments created yet.")
        return
    
    for exp in experiments:
        with st.expander(f"📁 {exp['experiment_code']} - {exp['experiment_name']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Code:** {exp['experiment_code']}")
                st.write(f"**Name:** {exp['experiment_name']}")
                st.write(f"**Created:** {exp['created_at']}")
            
            with col2:
                st.write(f"**Creator:** {exp['creator_name']}")
                if exp['deadline']:
                    st.write(f"**Deadline:** {exp['deadline']}")
                st.write(f"**Status:** {'Active' if exp['is_active'] else 'Inactive'}")
            
            if exp['description']:
                st.write(f"**Description:** {exp['description']}")

# ============== MAIN APP ROUTING ==============

def main():
    """Main application router"""
    
    if st.session_state.page == 'login':
        login_page()
    elif st.session_state.page == 'register':
        register_page()
    elif st.session_state.page == 'student_dashboard':
        student_dashboard()
    elif st.session_state.page == 'faculty_dashboard':
        faculty_dashboard()
    else:
        st.session_state.page = 'login'
        st.rerun()

if __name__ == "__main__":
    main()
