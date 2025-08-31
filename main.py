import streamlit as st
import pandas as pd
from dataclasses import asdict
from datetime import datetime
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
import requests

# --- (Assuming you have a 'vtop_client.py' file with VtopClient) ---
from vtop_client import VtopClient 
# --------------------------------------------------------------------


# --- Page Configuration ---
st.set_page_config(page_title="VTOP Client", layout="wide")

st.title("🎓 VTOP Streamlit Client")
st.caption("A modern dashboard to visualize your VTOP data.")

# --- Helper Functions ---
def login():
    try:
        client = VtopClient(st.session_state.username, st.session_state.password)
        with st.spinner("Logging in..."):
            client.login()
        st.session_state.client = client
        st.session_state.error = ""
    except Exception as e:
        st.session_state.error = str(e)

def logout():
    st.session_state.client = None
    st.session_state.semesters = []
    st.session_state.error = ""

# --- State Initialization ---
if 'client' not in st.session_state:
    st.session_state.client = None
    st.session_state.semesters = []
    st.session_state.error = ""

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
    
    with st.sidebar:
        st.success(f"Logged in as {client.reg_no}")
        choice = option_menu("VTOP Menu", ["Attendance", "Timetable", "Marks", "Exam Schedule"],
                             icons=['pie-chart-fill', 'calendar-week-fill', 'clipboard2-data-fill', 'pencil-square'],
                             menu_icon="robot", default_index=0)
        st.button("Logout", on_click=logout, use_container_width=True)

    if not st.session_state.semesters:
        st.session_state.semesters = client.get_semesters().semesters
    sem_options = {sem.name: sem.id for sem in st.session_state.semesters}
    selected_sem_name = st.sidebar.selectbox("Select Semester", options=sem_options.keys())
    selected_sem_id = sem_options[selected_sem_name]

    st.header(f"{choice} for {selected_sem_name}")
    st.markdown("---")

    # --- Attendance Page ---
    if choice == "Attendance":
        with st.spinner("Fetching Attendance..."):
            data = client.get_attendance(selected_sem_id)
        if data and data.records:
            df = pd.DataFrame([asdict(r) for r in data.records])
            
            if 'attendance_percentage' in df.columns:
                df['attendance_percentage'] = pd.to_numeric(df['attendance_percentage'].astype(str).str.replace('%', ''), errors='coerce')
                df.dropna(subset=['attendance_percentage'], inplace=True)
                if not df.empty:
                    df['attendance_percentage'] = df['attendance_percentage'].astype(int)

                if df.empty:
                    st.warning("Could not parse any valid attendance data.")
                    st.stop()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Attendance Summary")
                    avg_attendance = df['attendance_percentage'].mean()
                    low_attendance_courses = df[df['attendance_percentage'] < 75].shape[0]
                    mcol1, mcol2 = st.columns(2)
                    mcol1.metric("Average", f"{avg_attendance:.2f}%")
                    mcol2.metric("Courses < 75%", f"{low_attendance_courses} 😟")
                with col2:
                    def get_status(p):
                        if p >= 85: return 'Safe'
                        if 75 <= p < 85: return 'Warning'
                        return 'Danger'
                    df['status'] = df['attendance_percentage'].apply(get_status)
                    status_counts = df['status'].value_counts()
                    colors = {'Safe': 'mediumseagreen', 'Warning': 'orange', 'Danger': 'tomato'}
                    fig = go.Figure(data=[go.Pie(labels=status_counts.index, values=status_counts.values, hole=.6, marker_colors=[colors.get(key) for key in status_counts.index])])
                    fig.update_layout(title_text='Status Overview', showlegend=False, height=200, margin=dict(t=30, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
            
            st.subheader("Detailed View")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No attendance data found.")

    # --- Timetable Page ---
    elif choice == "Timetable":
        with st.spinner("Fetching Timetable..."):
            data = client.get_timetable(selected_sem_id)
        if data.slots:
            df = pd.DataFrame([asdict(s) for s in data.slots])
            
            st.subheader("Weekly Grid View")
            
            # <-- FIX: Define days for rows and time slots for columns -->
            time_slots = [f"{h:02d}:00" for h in range(8, 18)]
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            day_map = {"MON": "Monday", "TUE": "Tuesday", "WED": "Wednesday", "THU": "Thursday", "FRI": "Friday", "SAT": "Saturday"}

            df['day_full'] = df['day'].map(day_map)

            valid_time_df = df[pd.to_datetime(df['start_time'], format='%H:%M', errors='coerce').notna()].copy()

            if not valid_time_df.empty:
                valid_time_df['start_hour'] = pd.to_datetime(valid_time_df['start_time'], format='%H:%M').dt.strftime('%H:00')
                
                # <-- FIX: Invert pivot table axes -->
                timetable_pivot = valid_time_df.pivot_table(index='day_full', columns='start_hour', values='name', aggfunc='first').reindex(index=days, columns=time_slots)

                html = "<table><tr><th>Day</th>" + "".join(f"<th>{time}</th>" for time in time_slots) + "</tr>"
                for day, row in timetable_pivot.iterrows():
                    html += f"<tr><td><b>{day}</b></td>"
                    for time in time_slots:
                        cell_content = row[time] if pd.notna(row[time]) else ""
                        course_info = valid_time_df[(valid_time_df['day_full'] == day) & (valid_time_df['start_hour'] == time)]
                        if not course_info.empty:
                            # <-- FIX: New dark-mode friendly colors with white text -->
                            cell_style = "background-color: #022B3A; color: white; border-left: 5px solid #00A9A5; padding: 10px; border-radius: 5px; text-align: center; font-size: 14px; min-height: 70px; vertical-align: middle;"
                            course_code = course_info.iloc[0]['course_code']
                            room_no = course_info.iloc[0]['room_no']
                            cell_content = f"<b>{course_code}</b><br>{cell_content}<br><i>{room_no}</i>"
                        else:
                            cell_style = "background-color: #262730;" # Dark background for empty slots
                        html += f"<td style='{cell_style}'>{cell_content}</td>"
                    html += "</tr>"
                html += "</table>"

                st.markdown("""
                <style>
                table { width: 100%; border-collapse: separate; border-spacing: 5px; }
                th, td { border: 1px solid #333; padding: 8px; text-align: center; border-radius: 5px; }
                th { background-color: #1a1a1a; color: #FAFAFA; } /* Dark header for dark mode */
                </style>
                """, unsafe_allow_html=True)

                st.markdown(html, unsafe_allow_html=True)
            else:
                st.warning("No valid timetable slots to display in grid view.")
        else:
            st.warning("No timetable data found.")


    # --- Marks Page ---
    elif choice == "Marks":
        with st.spinner("Fetching Marks..."):
            data = client.get_marks(selected_sem_id)
        if data.records:
            st.subheader("Detailed Marks per Course")
            for record in data.records:
                with st.expander(f"**{record.coursecode}** - {record.coursetitle}"):
                    st.write(f"**Faculty:** {record.faculity} | **Slot:** {record.slot}")
                    if record.marks:
                        marks_df = pd.DataFrame([asdict(m) for m in record.marks])
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
            st.subheader("Exam Schedules")
            for exam_group in data.exams:
                if hasattr(exam_group, 'exam_type'):
                    st.write(f"#### {exam_group.exam_type}")

                if exam_group.records:
                    df_exam = pd.DataFrame([asdict(r) for r in exam_group.records])
                    st.dataframe(df_exam, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No schedule found for this exam type.")
                st.markdown("---")
        else:
            st.warning("No exam schedule data found.")
