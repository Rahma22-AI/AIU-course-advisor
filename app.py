import streamlit as st
import pandas as pd
from engine import CourseRecommender, Student
from utils import load_courses, save_courses
from datetime import datetime

# Config and style
st.set_page_config(page_title="AIU AIE Course Advisor", layout="wide", page_icon="📚")
st.markdown("""
    <style>
        .block-container {padding: 2rem 3rem;}
        .recommendation-card {
            background-color: #1f77b4;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
            margin: 0.5rem 0;
        }
        .explanation-text {
            background-color: #f8f9fa;
            color: #2c3e50;
            padding: 0.8rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
            border-left: 4px solid #28a745;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# Load course data
df = load_courses()
if df.empty:
    st.error("No courses available in the database. Please contact the admin.")
    st.stop()
course_codes = df["Course Code"].tolist()
course_dict = df.set_index("Course Code").to_dict("index")

# Logging
def log_action(action, detail):
    with open("logs.txt", "a") as f:
        f.write(f"[{datetime.now()}] {action}: {detail}\n")

# Helper function to display recommendations with explanations
def display_recommendations_with_explanations(recommendations, positive_explanations, total_credits, max_credits):
    if recommendations:
        st.success(f"🎯 **{len(recommendations)} Courses Recommended** – Total Credits: **{total_credits}/{max_credits}**")
        
        # Display summary table
        rec_df = pd.DataFrame(recommendations, columns=["Course Code", "Course Name", "Credit Hours"])
        st.dataframe(rec_df, use_container_width=True)
        
        # Display detailed explanations
        st.markdown("### 📋 **Why These Courses Were Recommended**")
        
        for i, explanation in enumerate(positive_explanations):
            with st.container():
                st.markdown(f'<div class="explanation-text">{explanation}</div>', unsafe_allow_html=True)
        
        # Credit utilization info
        credit_usage = (total_credits / max_credits) * 100
        if credit_usage > 90:
            st.warning(f"⚠️ You're using {credit_usage:.1f}% of your credit limit. Consider your workload carefully.")
        elif credit_usage > 75:
            st.info(f"📊 You're using {credit_usage:.1f}% of your credit limit. Good course load!")
        else:
            st.success(f"✅ You're using {credit_usage:.1f}% of your credit limit. You could add more courses if needed.")
            
    else:
        st.warning("⚠️ No eligible courses found based on your current academic status.")

# Tabs
student_tab, gpa_tab, admin_tab, help_tab = st.tabs(["📅 Student Panel", "📊 GPA Calculator", "🔧 Admin Panel", "❓ Help & Guide"])

# Student Panel
with student_tab:
    st.markdown("## 🎓 AIU Course Registration Advisor – AIE Track")
    st.markdown("Built with 🔍 intelligent course matching, prerequisites, and CGPA logic")
    st.divider()

    # Add helpful information section
    with st.expander("ℹ️ How to Use This System", expanded=False):
        st.markdown("""
        **Step 1:** Select your current semester (Fall or Spring)
        
        **Step 2:** Enter your CGPA (0.0 to 4.0) - this determines your maximum credit limit:
        - CGPA < 2.0: Maximum 12 credits
        - CGPA 2.0-2.99: Maximum 15 credits  
        - CGPA ≥ 3.0: Maximum 18 credits
        
        **Step 3:** Select all courses you have **passed** from the dropdown
        
        **Step 4:** Select any courses you have **failed** and need to retake
        
        **Step 5:** Click "Get Recommendations" to see your personalized course list!
        
        💡 **Tip:** Failed courses will be prioritized in your recommendations if prerequisites are met.
        """)

    with st.container():
        col1, col2 = st.columns(2)

        with col1:
            semester = st.radio("📅 Select Current Semester", ["Fall", "Spring"], horizontal=True)
            cgpa_input = st.text_input("🎯 Enter Your CGPA (0.0 – 4.0)", placeholder="e.g., 3.25")
            cgpa = None
            try:
                if cgpa_input:
                    cgpa = float(cgpa_input)
                    if not (0.0 <= cgpa <= 4.0):
                        st.error("⚠️ CGPA must be between 0.0 and 4.0")
                        cgpa = None
                    else:
                        # Show credit limit preview
                        max_credits = 12 if cgpa < 2.0 else 15 if cgpa < 3.0 else 18
                        st.info(f"📊 Your credit limit: **{max_credits} credits** (based on CGPA {cgpa})")
            except ValueError:
                if cgpa_input:
                    st.error("❌ Invalid input. Please enter a number like 2.75")
                cgpa = None

        with col2:
            passed = st.multiselect(
                "✅ Select Courses You Have **Passed**", 
                options=course_codes,
                format_func=lambda x: f"{x} – {course_dict[x]['Course Name']}",
                help="Select all courses you have successfully completed"
            )
            # Normalize course codes by removing spaces
            passed = [code.replace(" ", "") for code in passed]
            
            available_failed = [c for c in course_codes if c not in passed]
            failed = st.multiselect(
                "❌ Select Courses You Have **Failed**", 
                options=available_failed,
                format_func=lambda x: f"{x} – {course_dict[x]['Course Name']}",
                help="Select courses you need to retake (these will be prioritized)"
            )
            failed = [code.replace(" ", "") for code in failed]

    if st.button("📋 Get My Course Recommendations", type="primary", use_container_width=True):
        if cgpa is None:
            st.error("⚠️ Please enter a valid CGPA between 0.0 and 4.0")
        elif not semester:
            st.error("⚠️ Please select a semester")
        else:
            with st.spinner("🔍 Analyzing your academic record and generating recommendations..."):
                engine = CourseRecommender(df)
                engine.reset()
                student_fact = Student(cgpa=cgpa, semester=semester, passed=passed, failed=failed)
                engine.declare(student_fact)
                engine.run()
                recommendations, debug_log = engine.get_recommendations()
                positive_explanations = engine.get_positive_explanations()

            # Display results
            display_recommendations_with_explanations(
                recommendations, positive_explanations, engine.total_credits, engine.max_credits
            )

            # If no recommendations, show detailed help
            if not recommendations:
                # Categorize and display rejection reasons
                rejection_reasons = {
                    "🗓️ Semester Mismatch": [],
                    "📚 Prerequisites Missing": [],
                    "🔗 Co-requisites Missing": [],
                    "💳 Credit Limit Exceeded": [],
                    "✅ Already Passed": [],
                    "🎯 Track Mismatch": [],
                    "❓ Other": []
                }
                
                for log in debug_log:
                    if "Not offered in" in log:
                        rejection_reasons["🗓️ Semester Mismatch"].append(log)
                    elif "Missing prerequisites" in log:
                        rejection_reasons["📚 Prerequisites Missing"].append(log)
                    elif "Missing co-requisites" in log:
                        rejection_reasons["🔗 Co-requisites Missing"].append(log)
                    elif "Credit limit exceeded" in log:
                        rejection_reasons["💳 Credit Limit Exceeded"].append(log)
                    elif "Already passed" in log:
                        rejection_reasons["✅ Already Passed"].append(log)
                    elif "Not in AIE track" in log:
                        rejection_reasons["🎯 Track Mismatch"].append(log)
                    else:
                        rejection_reasons["❓ Other"].append(log)

                with st.expander("🔍 Why No Courses Were Recommended?", expanded=True):
                    for category, logs in rejection_reasons.items():
                        if logs:
                            st.subheader(category)
                            for log in logs:
                                st.text(f"• {log}")
                            
                            # Provide specific guidance
                            if "Semester Mismatch" in category:
                                st.info("💡 **Solution:** Try selecting the other semester, or contact your advisor about course availability.")
                            elif "Prerequisites Missing" in category:
                                st.info("💡 **Solution:** Focus on completing prerequisite courses first, then return for these courses.")
                            elif "Co-requisites Missing" in category:
                                st.info("💡 **Solution:** Co-requisite courses must be taken together. Consider taking them in a future semester.")
                            elif "Credit Limit Exceeded" in category:
                                st.info(f"💡 **Solution:** Your CGPA ({cgpa}) limits you to {engine.max_credits} credits. Focus on improving your GPA or take fewer courses.")
                            elif "Already Passed" in category:
                                st.info("💡 **Info:** These courses are excluded because you've already completed them successfully.")

            # Debug information (collapsed by default)
            with st.expander("🔧 Technical Debug Information", expanded=False):
                st.write("**Input Parameters:**")
                st.json({
                    "CGPA": cgpa,
                    "Semester": semester,
                    "Passed Courses": passed,
                    "Failed Courses": failed,
                    "Credit Limit": engine.max_credits
                })
                
                st.write("**System Processing Log:**")
                for log in debug_log:
                    st.text(f"• {log}")
# GPA Calculator Tab 
with gpa_tab:
    st.markdown("## 📊 GPA Calculator")
    st.markdown("Calculate your current CGPA and see how it affects your course registration limits")
    st.divider()

    # Instructions
    with st.expander("ℹ️ How to Use the GPA Calculator", expanded=False):
        st.markdown("""
        **Step 1:** Add your completed courses one by one using the form below
        
        **Step 2:** For each course, enter:
        - Course name or code
        - Credit hours (1-6)
        - Grade received (A+, A, A-, B+, B, B-, C+, C, C-, D+, D, F)
        
        **Step 3:** Click "Add Course" to include it in your calculation
        
        **Step 4:** View your calculated CGPA and corresponding credit limit
        
        **Grade Point Scale:**
        - A+ = 4.0, A = 4.0, A- = 3.7
        - B+ = 3.3, B = 3.0, B- = 2.7
        - C+ = 2.3, C = 2.0, C- = 1.7
        - D+ = 1.3, D = 1.0, F = 0.0
        """)

    # Initialize session state for courses
    if 'gpa_courses' not in st.session_state:
        st.session_state.gpa_courses = []

    # Grade point mapping
    grade_points = {
        'A+': 4.0, 'A': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0, 'C-': 1.7,
        'D+': 1.3, 'D': 1.0, 'F': 0.0
    }

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### ➕ Add Course")
        with st.form("add_gpa_course", clear_on_submit=True):
            course_name = st.text_input("Course Name/Code", placeholder="e.g., CSE015 or Math I")
            credit_hours = st.number_input("Credit Hours", min_value=1, max_value=6, value=3)
            grade = st.selectbox("Grade Received", options=list(grade_points.keys()))
            
            if st.form_submit_button("➕ Add Course", type="primary"):
                if course_name.strip():
                    course_data = {
                        'name': course_name.strip(),
                        'credits': credit_hours,
                        'grade': grade,
                        'points': grade_points[grade]
                    }
                    st.session_state.gpa_courses.append(course_data)
                    st.success(f"✅ Added {course_name} ({grade}) - {credit_hours} credits")
                    st.rerun()
                else:
                    st.error("❌ Please enter a course name")

    with col2:
        st.markdown("### 🚀 Quick Add Common Courses")
        
        # Common courses from the database
        common_courses = [
            ("MAT111", "Mathematics I", 3),
            ("CSE014", "Structured Programming", 3),
            ("CSE015", "Object Oriented Programming", 3),
            ("MAT112", "Mathematics II", 3),
            ("CSE111", "Data Structures", 3)
        ]
        
        st.markdown("Select a course and grade to quickly add it:")
        
        # Course selection
        selected_course_idx = st.selectbox(
            "Choose Course",
            range(len(common_courses)),
            format_func=lambda x: f"{common_courses[x][0]} - {common_courses[x][1]} ({common_courses[x][2]} cr)",
            key="quick_course_select"
        )
        
        # Get the selected course info
        selected_course = common_courses[selected_course_idx]
        
        st.markdown(f"**Grade for {selected_course[0]} - {selected_course[1]}:**")
        
        # Create grade buttons in a grid
        col1_grades, col2_grades = st.columns(2)
        
        with col1_grades:
            for grade in ['A+', 'A', 'A-', 'B+', 'B', 'B-']:
                if st.button(grade, key=f"grade_{grade}_{selected_course[0]}", use_container_width=True):
                    course_data = {
                        'name': f"{selected_course[0]} - {selected_course[1]}",
                        'credits': selected_course[2],
                        'grade': grade,
                        'points': grade_points[grade]
                    }
                    st.session_state.gpa_courses.append(course_data)
                    st.success(f"✅ Added {selected_course[0]} ({grade})")
                    st.rerun()
        
        with col2_grades:
            for grade in ['C+', 'C', 'C-', 'D+', 'D', 'F']:
                if st.button(grade, key=f"grade_{grade}_{selected_course[0]}", use_container_width=True):
                    course_data = {
                        'name': f"{selected_course[0]} - {selected_course[1]}",
                        'credits': selected_course[2],
                        'grade': grade,
                        'points': grade_points[grade]
                    }
                    st.session_state.gpa_courses.append(course_data)
                    st.success(f"✅ Added {selected_course[0]} ({grade})")
                    st.rerun()

    st.divider()

    # Display current courses and calculate GPA
    if st.session_state.gpa_courses:
        st.markdown("### 📚 Your Courses")
        
        # Create DataFrame for display
        gpa_df = pd.DataFrame(st.session_state.gpa_courses)
        
        # Add a column for grade points calculation
        gpa_df['Grade Points'] = gpa_df['credits'] * gpa_df['points']
        
        # Create a nice table header
        col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])
        with col1:
            st.markdown("**Course**")
        with col2:
            st.markdown("**Credits**")
        with col3:
            st.markdown("**Grade**")
        with col4:
            st.markdown("**Points**")
        with col5:
            st.markdown("**Total**")
        with col6:
            st.markdown("**Action**")
        
        st.divider()
        
        # Display each course with remove option
        for i, row in gpa_df.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])
            with col1:
                st.write(row['name'])
            with col2:
                st.write(f"{row['credits']} cr")
            with col3:
                st.write(row['grade'])
            with col4:
                st.write(f"{row['points']:.1f}")
            with col5:
                st.write(f"{row['Grade Points']:.1f}")
            with col6:
                if st.button("🗑️", key=f"remove_{i}", help="Remove this course"):
                    st.session_state.gpa_courses.pop(i)
                    st.rerun()
        
        # Calculate totals
        total_credits = gpa_df['credits'].sum()
        total_grade_points = gpa_df['Grade Points'].sum()
        cgpa = total_grade_points / total_credits if total_credits > 0 else 0.0
        
        # Determine credit limit
        if cgpa < 2.0:
            credit_limit = 12
            limit_color = "🔴"
        elif cgpa < 3.0:
            credit_limit = 15
            limit_color = "🟡"
        else:
            credit_limit = 18
            limit_color = "🟢"
        
        st.divider()
        
        # Display results
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Credits", f"{total_credits}")
        with col2:
            st.metric("🎯 Current CGPA", f"{cgpa:.3f}")
        with col3:
            st.metric(f"{limit_color} Credit Limit", f"{credit_limit}")
        
        # GPA Analysis
        st.markdown("### 📈 GPA Analysis")
        
        if cgpa >= 3.7:
            st.success("🌟 **Excellent Performance!** You're in the top tier with maximum credit privileges.")
        elif cgpa >= 3.0:
            st.success("✅ **Good Performance!** You can register for the maximum 18 credits per semester.")
        elif cgpa >= 2.5:
            st.warning("⚠️ **Average Performance.** You can register for up to 15 credits. Consider focusing on improving grades.")
        elif cgpa >= 2.0:
            st.warning("⚠️ **Below Average Performance.** Limited to 15 credits. Focus on improving your study habits.")
        else:
            st.error("🚨 **Poor Performance.** Limited to 12 credits per semester. Consider seeking academic support.")
        
        # Improvement suggestions
        if cgpa < 3.0:
            st.markdown("### 💡 Improvement Suggestions")
            
            # Calculate what GPA needed for next tier
            if cgpa < 2.0:
                target_gpa = 2.0
                target_credits = 15
            else:
                target_gpa = 3.0
                target_credits = 18
            
            # Simple calculation for next semester improvement
            future_credits = 15
            required_total_points = target_gpa * (total_credits + future_credits)
            required_next_semester_points = required_total_points - total_grade_points
            required_avg_grade = required_next_semester_points / future_credits
            
            if required_avg_grade <= 4.0:
                # Find the closest grade
                closest_grade = min(grade_points.keys(), key=lambda x: abs(grade_points[x] - required_avg_grade))
                
                st.info(f"""
                **To reach {target_gpa:.1f} CGPA and unlock {target_credits} credit limit:**
                
                If you take {future_credits} credits next semester, you would need an average grade of approximately:
                - **{required_avg_grade:.1f}** grade points per credit
                - This roughly corresponds to **{closest_grade}** average grades
                """)
            else:
                st.warning(f"To reach {target_gpa:.1f} CGPA, you'll need multiple semesters of excellent performance or consider retaking some courses.")
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear All Courses", type="secondary", use_container_width=True):
                st.session_state.gpa_courses = []
                st.success("✅ All courses cleared!")
                st.rerun()
        
        with col2:
            # Export functionality
            if st.button("📥 Export Report", type="primary", use_container_width=True):
                csv_data = gpa_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV Report",
                    data=csv_data,
                    file_name=f"gpa_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
    else:
        st.info("📝 No courses added yet. Use the form above to add your completed courses and calculate your CGPA.")
        
        # Sample calculation example
        st.markdown("### 📖 Example Calculation")
        example_df = pd.DataFrame([
            {"Course": "MAT111 - Mathematics I", "Credits": 3, "Grade": "A", "Points": 4.0, "Grade Points": 12.0},
            {"Course": "CSE014 - Programming", "Credits": 3, "Grade": "B+", "Points": 3.3, "Grade Points": 9.9},
            {"Course": "PHY212 - Physics", "Credits": 2, "Grade": "A-", "Points": 3.7, "Grade Points": 7.4},
        ])
        st.dataframe(example_df, use_container_width=True)
        st.markdown("**CGPA = Total Grade Points ÷ Total Credits = 29.3 ÷ 8 = 3.66**")
        st.markdown("**Credit Limit: 18 credits** (CGPA ≥ 3.0)")
        
        # Quick start with example data
        if st.button("🚀 Try with Example Data", type="secondary"):
            st.session_state.gpa_courses = [
                {'name': 'MAT111 - Mathematics I', 'credits': 3, 'grade': 'A', 'points': 4.0},
                {'name': 'CSE014 - Programming', 'credits': 3, 'grade': 'B+', 'points': 3.3},
                {'name': 'PHY212 - Physics', 'credits': 2, 'grade': 'A-', 'points': 3.7}
            ]
            st.rerun()
# Admin Panel section


with admin_tab:
    st.title("🔧 Admin Panel")

    password = st.text_input("🔑 Enter admin password", type="password", placeholder="Enter admin password")
    if password != "admin123":
        st.info("🔒 Access restricted. Please enter the correct admin password to continue.")
        st.stop()

    st.success("✅ Admin authenticated successfully!")

    # Add new course
    with st.expander("➕ Add New Course"):
        with st.form("add_course"):
            col1, col2 = st.columns(2)
            with col1:
                code = st.text_input("Course Code*", placeholder="e.g., CSE101")
                name = st.text_input("Course Name*", placeholder="e.g., Introduction to Programming")
                credit = st.number_input("Credit Hours*", min_value=1, max_value=6, value=3)
                semester = st.selectbox("Semester Offered*", ["Fall", "Spring", "Both"])

            with col2:
                pre = st.text_input("Prerequisites", placeholder="e.g., MAT111,CSE014")
                co = st.text_input("Co-requisites", placeholder="e.g., MAT112")
                track = st.text_input("Track*", value="Artificial Intelligence Engineering")

            desc = st.text_area("Description", placeholder="Brief description of the course")
            submitted = st.form_submit_button("➕ Add Course", type="primary")

            if submitted:
                if not code or not name:
                    st.error("❌ Course Code and Course Name are required!")
                elif code in df["Course Code"].values:
                    st.error(f"❌ Course {code} already exists!")
                else:
                    new_row = {
                        "Course Code": code,
                        "Course Name": name,
                        "Description": desc,
                        "Prerequisites": pre,
                        "Co-requisites": co,
                        "Credit Hours": credit,
                        "Semester Offered": semester,
                        "Track": track
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_courses(df)
                    log_action("ADD", f"{code} ({name}) added by admin")
                    st.success(f"✅ Course {code} added!")
                    st.rerun()

    # Edit course
    with st.expander("🖊 Edit Existing Course"):
        if df.empty:
            st.warning("No courses available.")
        else:
            edit_code = st.selectbox("Select Course to Edit", df["Course Code"].unique())
            course = df[df["Course Code"] == edit_code].iloc[0]

            with st.form("edit_course"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Course Name", value=course["Course Name"])
                    credit = st.number_input("Credit Hours", min_value=1, max_value=6, value=int(course["Credit Hours"]))
                    semester = st.selectbox("Semester Offered", ["Fall", "Spring", "Both"], index=["Fall", "Spring", "Both"].index(course["Semester Offered"]))

                with col2:
                    pre = st.text_input("Prerequisites", value=str(course["Prerequisites"]) if pd.notna(course["Prerequisites"]) else "")
                    co = st.text_input("Co-requisites", value=str(course["Co-requisites"]) if pd.notna(course["Co-requisites"]) else "")
                    track = st.text_input("Track", value=course["Track"])

                desc = st.text_area("Description", value=str(course["Description"]) if pd.notna(course["Description"]) else "")

                confirm_edit = st.checkbox("✅ Confirm changes before saving")
                submitted = st.form_submit_button("💾 Save Changes", type="primary")

            if submitted:
                if confirm_edit:
                    updated_row = {
                        "Course Code": edit_code,
                        "Course Name": name,
                        "Description": desc,
                        "Prerequisites": pre,
                        "Co-requisites": co,
                        "Credit Hours": credit,
                        "Semester Offered": semester,
                        "Track": track
                    }
                    df.loc[df["Course Code"] == edit_code, :] = pd.DataFrame([updated_row]).values
        
                    save_courses(df)
                    log_action("EDIT", f"{edit_code} updated by admin")
                    st.success(f"✅ Course {edit_code} updated!")
                    st.rerun()
                else:
                    st.error("❌ Please confirm changes before saving.")

    # Delete course
    with st.expander("🗑️ View and Delete Courses"):
        if df.empty:
            st.warning("No courses available.")
        else:
            st.dataframe(df, use_container_width=True)
            to_delete = st.selectbox("Select Course to Delete", df["Course Code"].unique())
            if to_delete:
                course_info = df[df["Course Code"] == to_delete].iloc[0]
                st.warning(f"⚠️ About to delete: {to_delete} - {course_info['Course Name']}")
                confirm_delete = st.checkbox("✅ Confirm deletion")
                if st.button("🗑️ Delete Course", disabled=not confirm_delete):
                    df = df[df["Course Code"] != to_delete]
                    save_courses(df)
                    log_action("DELETE", f"{to_delete} deleted by admin")
                    st.success(f"✅ Deleted {to_delete}")
                    st.rerun()

    # Backup / Restore
    with st.expander("📂 Backup & Restore Course Database"):
        st.download_button(
            label="📥 Download Course Database (CSV)",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=f"aiu_courses_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime='text/csv'
        )

        uploaded_file = st.file_uploader("Upload New CSV")
        if uploaded_file:
            try:
                new_df = pd.read_csv(uploaded_file)
                preview_cols = ["Course Code", "Course Name", "Credit Hours"]
                st.dataframe(new_df[preview_cols] if all(c in new_df for c in preview_cols) else new_df)

                if all(col in new_df.columns for col in df.columns):
                    if st.checkbox("✅ Confirm overwrite database"):
                        save_courses(new_df)
                        log_action("UPLOAD", f"Database replaced using {uploaded_file.name}")
                        st.success(f"✅ Database replaced with {len(new_df)} courses.")
                        st.rerun()
                else:
                    st.error("❌ Uploaded CSV is missing required columns.")
            except Exception as e:
                st.error(f"❌ Failed to load CSV: {e}")

    # Logs
    with st.expander("📋 System Audit Log"):
        try:
            with open("logs.txt", "r") as f:
                logs = f.readlines()[-50:]
                for line in reversed(logs):
                    st.text(line.strip())
        except:
            st.info("No logs found.")

        if st.button("🗑️ Clear Audit Log"):
            open("logs.txt", "w").close()
            st.success("✅ Audit log cleared.")
            st.rerun()

# Help & Guide Tab
with help_tab:
    st.title("❓ Help & User Guide")
    
    st.markdown("## 🎯 System Overview")
    st.info("""
    The AIU Course Registration Advisor is an intelligent system designed to help Artificial Intelligence Engineering 
    students select appropriate courses based on their academic progress, CGPA, and university requirements.
    """)
    
    st.markdown("## 📚 How It Works")
    
    with st.expander("🔍 Course Recommendation Logic", expanded=True):
        st.markdown("""
        The system uses the following rules to recommend courses:
        
        **1. Credit Limit Based on CGPA:**
        - CGPA < 2.0: Maximum 12 credits per semester
        - CGPA 2.0-2.99: Maximum 15 credits per semester  
        - CGPA ≥ 3.0: Maximum 18 credits per semester
        
        **2. Prerequisites Check:**
        - You must have passed all prerequisite courses before enrolling
        
        **3. Co-requisites Validation:**
        - Co-requisite courses must be taken together or already completed
        
        **4. Failed Course Priority:**
        - Previously failed courses are prioritized if prerequisites are met
        
        **5. Semester Availability:**
        - Only courses offered in your selected semester are recommended
        
        **6. Track Alignment:**
        - All courses must belong to the Artificial Intelligence Engineering track
        """)
    
    with st.expander("📝 Step-by-Step Usage Guide"):
        st.markdown("""
        **Step 1: Select Semester**
        - Choose whether you're planning for Fall or Spring semester
        
        **Step 2: Enter CGPA**
        - Input your current CGPA (0.0 to 4.0)
        - This determines your maximum credit limit
        
        **Step 3: Select Passed Courses**
        - Choose all courses you have successfully completed
        - These will be used to check prerequisites
        
        **Step 4: Select Failed Courses**
        - Choose any courses you need to retake
        - These will be prioritized in recommendations
        
        **Step 5: Get Recommendations**
        - Click the recommendation button to see your personalized course list
        - Review the explanations to understand why each course was recommended
        """)
    
    with st.expander("⚠️ Common Issues & Solutions"):
        st.markdown("""
        **Problem: No courses recommended**
        - Check if you've completed necessary prerequisites
        - Verify your CGPA allows for additional credits
        - Try selecting the other semester
        
        **Problem: Course not appearing**
        - Ensure you haven't already passed the course
        - Check if prerequisites are completed
        - Verify the course is offered in your selected semester
        
        **Problem: Credit limit reached**
        - Focus on improving your CGPA for higher credit limits
        - Consider taking fewer courses per semester
        - Prioritize required courses over electives
        """)
    
    st.markdown("## 🏫 University Policies")
    st.markdown("""
    **Credit Limits:**
    - Students with CGPA below 2.0 are limited to 12 credits per semester
    - Students with CGPA 2.0-2.99 can take up to 15 credits per semester
    - Students with CGPA 3.0 and above can take up to 18 credits per semester
    
    **Prerequisites:**
    - All prerequisite courses must be passed before enrolling in dependent courses
    - Prerequisites are strictly enforced by the system
    
    **Failed Courses:**
    - Students must retake failed courses to graduate
    - Failed courses are automatically prioritized in recommendations
    """)
    
    st.markdown("## 📞 Support")
    st.success("""
    **Need Help?**
    - Contact your academic advisor for course planning assistance
    - Visit the Computer Science & Engineering department office
    - Email: cse@aiu.edu.eg
    - Phone: +20 xxx xxx xxxx
    """)
    
    st.markdown("## ℹ️ System Information")
    st.markdown(f"""
    **Version:** 1.0
    **Last Updated:** {datetime.now().strftime('%B %Y')}
    **Total Courses in Database:** {len(df)}
    **Track:** Artificial Intelligence Engineering
    """)