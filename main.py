import streamlit as st
import pandas as pd
from vtop_client import VtopClient
from dataclasses import asdict

st.set_page_config(page_title="VTOP Client", layout="wide")

st.title("🎓 VTOP Streamlit Client")
st.caption("A simple and clean interface to view your VTOP data.") # <-- ADDED

if 'client' not in st.session_state:
    st.session_state.client = None
    st.session_state.semesters = []
    st.session_state.error = ""

def login():
    try:
        client = VtopClient(st.session_state.username, st.session_state.password)
        with st.spinner("Logging in... Please wait."):
            client.login()
        st.session_state.client = client
        st.session_state.error = ""
    except Exception as e:
        st.session_state.error = str(e)

def logout():
    st.session_state.client = None
    st.session_state.semesters = []
    st.session_state.error = ""

if not st.session_state.client:
    with st.form("login_form"):
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        submitted = st.form_submit_button("Login", on_click=login)
    
    if st.session_state.error:
        st.error(f"Login Failed: {st.session_state.error}")

else:
    client = st.session_state.client
    st.sidebar.success(f"Logged in as {client.reg_no}")
    st.sidebar.button("Logout", on_click=logout)

    if not st.session_state.semesters:
        with st.spinner("Fetching Semesters..."):
            st.session_state.semesters = client.get_semesters().semesters
    
    if not st.session_state.semesters:
        st.error("Could not fetch semester list.")
        st.stop()
    
    sem_options = {sem.name: sem.id for sem in st.session_state.semesters}
    selected_sem_name = st.sidebar.selectbox("Select Semester", options=sem_options.keys())
    selected_sem_id = sem_options[selected_sem_name]

    view_options = ["Attendance", "Timetable", "Marks", "Exam Schedule"]
    choice = st.sidebar.radio("Select View", view_options)

    st.header(f"{choice} for {selected_sem_name}")
    st.markdown("---")

    if choice == "Attendance":
        with st.spinner("Fetching Attendance..."):
            data = client.get_attendance(selected_sem_id)
        if data.records:
            df = pd.DataFrame([asdict(r) for r in data.records])
            df = df[['course_code', 'course_name', 'attendance_percentage', 'classes_attended', 'total_classes']]
            
            # <-- START: VISUAL ENHANCEMENTS -->
            st.subheader("Attendance Summary")
            avg_attendance = df['attendance_percentage'].mean()
            low_attendance_courses = df[df['attendance_percentage'] < 75].shape[0]

            col1, col2 = st.columns(2)
            col1.metric("Average Attendance", f"{avg_attendance:.2f}%")
            col2.metric("Courses Below 75%", f"{low_attendance_courses} 😟")
            st.markdown("---")
            
            st.subheader("Detailed View")
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "attendance_percentage": st.column_config.ProgressColumn(
                        "Attendance %",
                        format="%d%%",
                        min_value=0,
                        max_value=100,
                    ),
                },
                hide_index=True
            )
            # <-- END: VISUAL ENHANCEMENTS -->
        else:
            st.warning("No attendance data found.")

    elif choice == "Timetable":
        with st.spinner("Fetching Timetable..."):
            data = client.get_timetable(selected_sem_id)
        if data.slots:
            df = pd.DataFrame([asdict(s) for s in data.slots])
            df = df[['day', 'start_time', 'end_time', 'course_code', 'name', 'slot', 'room_no']]
            df.loc[df['slot'] == 'LUNCH', 'start_time'] = '14:00'

            day_order = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
            day_full_names = {
                "MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday",
                "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday"
            }

            for day_code in day_order:
                day_df = df[df['day'] == day_code]
                
                if not day_df.empty:
                    full_day_name = day_full_names.get(day_code, day_code)
                    
                    # <-- START: VISUAL ENHANCEMENT -->
                    with st.container(border=True):
                        st.subheader(f"{full_day_name}")
                        display_df = day_df.sort_values(by='start_time').drop(columns=['day'])
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                    # <-- END: VISUAL ENHANCEMENT -->
        else:
            st.warning("No timetable data found.")
            
    elif choice == "Marks":
        with st.spinner("Fetching Marks..."):
            data = client.get_marks(selected_sem_id)
        if data.records:
            for record in data.records:
                with st.expander(f"**{record.coursecode}** - {record.coursetitle}"):
                    st.write(f"**Faculty:** {record.faculity} | **Slot:** {record.slot}")
                    if record.marks:
                        marks_df = pd.DataFrame([asdict(m) for m in record.marks])
                        
                        # <-- START: VISUAL ENHANCEMENT -->
                        st.write("**Marks Distribution**")
                        marks_df['scored_mark'] = pd.to_numeric(marks_df['scored_mark'], errors='coerce')
                        chart_df = marks_df[['assessment_title', 'scored_mark', 'max_mark']].dropna()
                        
                        if not chart_df.empty:
                            st.bar_chart(chart_df.set_index('assessment_title')['scored_mark'])
                        
                        st.write("**Detailed Marks**")
                        # <-- END: VISUAL ENHANCEMENT -->
                        
                        st.dataframe(marks_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No marks uploaded yet for this course.")
        else:
            st.warning("No marks data found.")

    elif choice == "Exam Schedule":
        with st.spinner("Fetching Exam Schedule..."):
            data = client.get_exam_schedule(selected_sem_id)
        if data is None:
            st.warning("No exam schedule data found.")
        elif data.exams:
            def map_exam_name(long_name):
                name = long_name.lower()
                if "continuous assessment test - i" in name: return "CAT-1"
                if "continuous assessment test - ii" in name: return "CAT-2"
                if "final assessment test" in name: return "FAT"
                return long_name.title()
            
            # <-- START: VISUAL ENHANCEMENT (FIND NEXT EXAM) -->
            all_records = []
            for exam_group in data.exams:
                if exam_group.records:
                    all_records.extend(exam_group.records)

            if all_records:
                schedule_df = pd.DataFrame([asdict(r) for r in all_records])
                schedule_df['exam_datetime'] = pd.to_datetime(schedule_df['exam_date'] + ' ' + schedule_df['exam_time'], format='%d-%m-%Y %H:%M')
                
                future_exams = schedule_df[schedule_df['exam_datetime'] > pd.Timestamp.now()].sort_values('exam_datetime')
                
                if not future_exams.empty:
                    next_exam = future_exams.iloc[0]
                    st.info(f"**Next Exam:** {next_exam['course_name']} ({next_exam['course_code']}) on **{next_exam['exam_date']}** at **{next_exam['exam_time']}**")
                    st.markdown("---")
            # <-- END: VISUAL ENHANCEMENT -->

            exam_types = [map_exam_name(exam.exam_type) for exam in data.exams]
            tabs = st.tabs(exam_types)
            
            for i, exam_group in enumerate(data.exams):
                with tabs[i]:
                    if exam_group.records:
                        df = pd.DataFrame([asdict(r) for r in exam_group.records])
                        df = df[['course_code', 'course_name', 'exam_date', 'exam_time', 'venue', 'seat_location', 'seat_no']]
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"No schedule found for {exam_group.exam_type}")
        else:
            st.warning("No exam schedule data found.")
