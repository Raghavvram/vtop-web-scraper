import streamlit as st
import pandas as pd
from vtop_client import VtopClient  # Assuming you have this client library
from dataclasses import asdict
from datetime import datetime
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar

# --- Page Configuration ---
st.set_page_config(page_title="VTOP Client", layout="wide")

st.title("🎓 VTOP Streamlit Client")
st.caption("A modern dashboard to visualize your VTOP data.")

# --- State Initialization ---
if 'client' not in st.session_state:
    st.session_state.client = None
    st.session_state.semesters = []
    st.session_state.error = ""

# --- Helper Functions ---
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

def map_exam_name(long_name):
    name = long_name.lower()
    if "continuous assessment test - i" in name: return "CAT-1"
    if "continuous assessment test - ii" in name: return "CAT-2"
    if "final assessment test" in name: return "FAT"
    return long_name.title()

# --- Login UI ---
if not st.session_state.client:
    with st.form("login_form"):
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.form_submit_button("Login", on_click=login)

    if st.session_state.error:
        st.error(f"Login Failed: {st.session_state.error}")

# --- Main Application UI ---
else:
    client = st.session_state.client
    
    # --- Sidebar Navigation ---
    with st.sidebar:
        st.success(f"Logged in as {client.reg_no}")
        choice = option_menu(
            "VTOP Menu", 
            ["Attendance", "Timetable", "Marks", "Exam Schedule"],
            icons=['pie-chart-fill', 'calendar-week-fill', 'clipboard2-data-fill', 'pencil-square'],
            menu_icon="robot", 
            default_index=0
        )
        st.button("Logout", on_click=logout, use_container_width=True)

    # --- Semester Selection ---
    if not st.session_state.semesters:
        with st.spinner("Fetching Semesters..."):
            st.session_state.semesters = client.get_semesters().semesters
    
    if not st.session_state.semesters:
        st.error("Could not fetch semester list.")
        st.stop()
    
    sem_options = {sem.name: sem.id for sem in st.session_state.semesters}
    selected_sem_name = st.sidebar.selectbox("Select Semester", options=sem_options.keys())
    selected_sem_id = sem_options[selected_sem_name]

    st.header(f"{choice} for {selected_sem_name}")
    st.markdown("---")

    # --- Attendance Page ---
    if choice == "Attendance":
        with st.spinner("Fetching Attendance..."):
            data = client.get_attendance(selected_sem_id)
        if data.records:
            df = pd.DataFrame([asdict(r) for r in data.records])
            df = df[['course_code', 'course_name', 'attendance_percentage', 'classes_attended', 'total_classes']]
            
            # Summary Metrics
            st.subheader("Attendance Summary")
            avg_attendance = df['attendance_percentage'].mean()
            low_attendance_courses = df[df['attendance_percentage'] < 75].shape[0]

            col1, col2 = st.columns(2)
            col1.metric("Average Attendance", f"{avg_attendance:.2f}%")
            col2.metric("Courses Below 75%", f"{low_attendance_courses} 😟")
            
            # Donut Chart
            st.subheader("Attendance Status Overview")
            def get_status(p):
                if p >= 85: return 'Safe Zone (>= 85%)'
                if 75 <= p < 85: return 'Warning Zone (75-85%)'
                return 'Danger Zone (< 75%)'

            df['status'] = df['attendance_percentage'].apply(get_status)
            status_counts = df['status'].value_counts()
            colors = {'Safe Zone (>= 85%)': 'mediumseagreen', 'Warning Zone (75-85%)': 'orange', 'Danger Zone (< 75%)': 'tomato'}
            
            fig = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, hole=.5, marker_colors=[colors.get(key) for key in status_counts.index])])
            fig.update_layout(title_text='Course Status Distribution', legend_title_text='Attendance Zones')
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("---")

            # Detailed Dataframe
            st.subheader("Detailed View")
            st.dataframe(df, use_container_width=True, column_config={"attendance_percentage": st.column_config.ProgressColumn("Attendance %", format="%d%%", min_value=0, max_value=100)}, hide_index=True)
        else:
            st.warning("No attendance data found.")

    # --- Timetable Page ---
    elif choice == "Timetable":
        with st.spinner("Fetching Timetable..."):
            data = client.get_timetable(selected_sem_id)
        if data.slots:
            df = pd.DataFrame([asdict(s) for s in data.slots])
            df = df[['day', 'start_time', 'end_time', 'course_code', 'name', 'slot', 'room_no']]
            df.loc[df['slot'] == 'LUNCH', 'start_time'] = '14:00'

            # Live Status Box
            st.subheader("Live Class Status")
            now = datetime.now()
            today_code = now.strftime('%a').upper()
            today_df = df[df['day'] == today_code].copy()
            if not today_df.empty:
                today_df['start_dt'] = pd.to_datetime(today_df['start_time'], format='%H:%M').dt.time
                today_df['end_dt'] = pd.to_datetime(today_df['end_time'], format='%H:%M').dt.time
                now_time = now.time()
                current_class = today_df[(today_df['start_dt'] <= now_time) & (today_df['end_dt'] >= now_time)]
                if not current_class.empty:
                    course = current_class.iloc[0]
                    st.success(f"Ongoing Now: **{course['name']}** ({course['course_code']}) in **{course['room_no']}** until **{course['end_time']}**.")
                else:
                    next_class = today_df[today_df['start_dt'] > now_time].sort_values('start_dt')
                    if not next_class.empty:
                        course = next_class.iloc[0]
                        st.info(f"Up Next: **{course['name']}** ({course['course_code']}) at **{course['start_time']}** in **{course['room_no']}**.")
                    else:
                        st.success("🎉 No more classes for today!")
            else:
                st.info("No classes scheduled for today.")
            st.markdown("---")

            # Day-by-day schedule
            day_order = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
            day_full_names = {"MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday", "SUN": "Sunday"}
            for day_code in day_order:
                day_df = df[df['day'] == day_code]
                if not day_df.empty:
                    with st.container(border=True):
                        st.subheader(day_full_names.get(day_code, day_code))
                        display_df = day_df.sort_values(by='start_time').drop(columns=['day'])
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.warning("No timetable data found.")

    # --- Marks Page ---
    elif choice == "Marks":
        with st.spinner("Fetching Marks..."):
            data = client.get_marks(selected_sem_id)
        if data.records:
            for record in data.records:
                with st.expander(f"**{record.coursecode}** - {record.coursetitle}"):
                    st.write(f"**Faculty:** {record.faculity} | **Slot:** {record.slot}")
                    if record.marks:
                        marks_df = pd.DataFrame([asdict(m) for m in record.marks])
                        
                        # Gauge Chart
                        st.write("**Overall Performance**")
                        marks_df['scored_mark'] = pd.to_numeric(marks_df['scored_mark'], errors='coerce')
                        marks_df['max_mark'] = pd.to_numeric(marks_df['max_mark'], errors='coerce')
                        total_scored, total_max = marks_df['scored_mark'].sum(), marks_df['max_mark'].sum()
                        if total_max > 0:
                            percentage = (total_scored / total_max) * 100
                            fig = go.Figure(go.Indicator(
                                mode="gauge+number", value=percentage,
                                title={'text': f"Total Score ({total_scored}/{total_max})"},
                                gauge={'axis': {'range': [None, 100]}, 'bar': {'color': "cornflowerblue"},
                                       'steps': [{'range': [0, 50], 'color': "lightgray"}, {'range': [50, 75], 'color': "gray"}]}
                            ))
                            fig.update_layout(height=250)
                            st.plotly_chart(fig, use_container_width=True)

                        st.write("**Detailed Marks**")
                        st.dataframe(marks_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No marks uploaded yet for this course.")
        else:
            st.warning("No marks data found.")

    # --- Exam Schedule Page ---
    elif choice == "Exam Schedule":
        with st.spinner("Fetching Exam Schedule..."):
            data = client.get_exam_schedule(selected_sem_id)
        if data and data.exams:
            all_records = []
            for exam_group in data.exams:
                if exam_group.records:
                    for record in exam_group.records:
                        record_dict = asdict(record)
                        record_dict['exam_type_short'] = map_exam_name(exam_group.exam_type)
                        all_records.append(record_dict)

            if all_records:
                calendar_events = []
                for exam in all_records:
                    try:
                        start_datetime = datetime.strptime(f"{exam['exam_date']} {exam['exam_time']}", "%d-%m-%Y %H:%M")
                        calendar_events.append({
                            "title": f"{exam['exam_type_short']}: {exam['course_name']}",
                            "start": start_datetime.isoformat(),
                            "end": start_datetime.isoformat(),
                            "color": "tomato" if "FAT" in exam['exam_type_short'] else "cornflowerblue",
                        })
                    except (ValueError, KeyError):
                        continue # Skip records with bad date/time format
                
                calendar(events=calendar_events, options={"headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth,timeGridWeek"}})
            else:
                st.warning("No exam schedule data found.")
        else:
            st.warning("No exam schedule data found.")
