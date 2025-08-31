import streamlit as st
import pandas as pd
from vtop_client import VtopClient # Assuming you have this client library
from dataclasses import asdict
from datetime import datetime
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar
import requests
from streamlit_lottie import st_lottie # <-- NEW Import

# --- Page Configuration ---
st.set_page_config(page_title="VTOP Client", layout="wide")

st.title("🎓 VTOP Streamlit Client")
st.caption("A modern dashboard to visualize your VTOP data.")

# --- Helper Functions ---
# <-- NEW: Lottie loader function -->
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

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

def map_exam_name(long_name):
    name = long_name.lower()
    if "continuous assessment test - i" in name: return "CAT-1"
    if "continuous assessment test - ii" in name: return "CAT-2"
    if "final assessment test" in name: return "FAT"
    return long_name.title()

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
    
    # Sidebar Navigation
    with st.sidebar:
        st.success(f"Logged in as {client.reg_no}")
        choice = option_menu("VTOP Menu", ["Attendance", "Timetable", "Marks", "Exam Schedule"],
                             icons=['pie-chart-fill', 'calendar-week-fill', 'clipboard2-data-fill', 'pencil-square'],
                             menu_icon="robot", default_index=0)
        st.button("Logout", on_click=logout, use_container_width=True)

    # Semester Selection
    if not st.session_state.semesters:
        st.session_state.semesters = client.get_semesters().semesters
    sem_options = {sem.name: sem.id for sem in st.session_state.semesters}
    selected_sem_name = st.sidebar.selectbox("Select Semester", options=sem_options.keys())
    selected_sem_id = sem_options[selected_sem_name]

    st.header(f"{choice} for {selected_sem_name}")
    st.markdown("---")

    # --- Attendance Page ---
    if choice == "Attendance":
        # <-- NEW: Using Lottie for loading animation -->
        lottie_url = "https://assets9.lottiefiles.com/packages/lf20_tmsi6g2i.json"
        lottie_json = load_lottieurl(lottie_url)
        data = None
        if lottie_json:
            with st_lottie(lottie_json, height=150, speed=1, quality="high"):
                data = client.get_attendance(selected_sem_id)
        else:
            with st.spinner("Fetching Attendance..."):
                data = client.get_attendance(selected_sem_id)

        if data and data.records:
            df = pd.DataFrame([asdict(r) for r in data.records])
            df = df[['course_code', 'course_name', 'attendance_percentage', 'classes_attended', 'total_classes']]
            
            # Summary Metrics & Donut Chart
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
            
            # <-- NEW: Interactive Scatter Plot -->
            st.markdown("---")
            st.subheader("Course Performance Scatter Plot")
            scatter_fig = go.Figure(data=go.Scatter(
                x=df['total_classes'], y=df['classes_attended'], mode='markers',
                marker=dict(size=df['attendance_percentage']/5, color=df['attendance_percentage'], colorscale='Viridis', showscale=True, colorbar=dict(title='Attendance %')),
                text=df['course_name'], hovertemplate='<b>%{text}</b><br>Attended: %{y}<br>Total: %{x}<br>Percentage: %{marker.color:.2f}%<extra></extra>'))
            scatter_fig.update_layout(title='Attended vs. Total Classes', xaxis_title='Total Classes Held', yaxis_title='Classes Attended')
            st.plotly_chart(scatter_fig, use_container_width=True)

            # Detailed Dataframe
            st.markdown("---")
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
            # ... (code for live status remains the same) ...

            # <-- NEW: Full Visual Timetable Grid -->
            st.markdown("---")
            st.subheader("Weekly Grid View")
            time_slots = [f"{h:02d}:00" for h in range(8, 18)]
            days = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
            df['start_hour'] = pd.to_datetime(df['start_time'], format='%H:%M').dt.strftime('%H:00')
            timetable_pivot = df.pivot_table(index='start_hour', columns='day', values='name', aggfunc='first').reindex(index=time_slots, columns=days)

            html = "<table><tr><th>Time</th>" + "".join(f"<th>{day}</th>" for day in days) + "</tr>"
            for time, row in timetable_pivot.iterrows():
                html += f"<tr><td>{time}</td>"
                for day in days:
                    cell_content = row[day] if pd.notna(row[day]) else ""
                    course_info = df[(df['day'] == day) & (df['start_hour'] == time)]
                    if not course_info.empty:
                        cell_style = "background-color: #d1e7dd; border-left: 5px solid #198754; padding: 5px; border-radius: 5px; text-align: center; font-size: 14px; min-height: 60px;"
                        cell_content = f"<b>{course_info.iloc[0]['course_code']}</b><br>{cell_content}<br><i>{course_info.iloc[0]['room_no']}</i>"
                    else:
                        cell_style = "background-color: #f8f9fa;"
                    html += f"<td style='{cell_style}'>{cell_content}</td>"
                html += "</tr>"
            html += "</table>"
            st.markdown("""<style>table{width:100%;border-collapse:collapse;}th,td{border:1px solid #dee2e6;padding:8px;text-align:left;}th{background-color:#e9ecef;}</style>""", unsafe_allow_html=True)
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.warning("No timetable data found.")

    # --- Marks Page ---
    elif choice == "Marks":
        with st.spinner("Fetching Marks..."):
            data = client.get_marks(selected_sem_id)
        if data.records:
            # <-- NEW: Sunburst Chart -->
            if st.button("📊 Show Overall Marks Sunburst Chart"):
                all_marks_data = [{'course': f"{r.coursecode}", 'assessment': m.assessment_title, 'scored': pd.to_numeric(m.scored_mark, errors='coerce'), 'max': pd.to_numeric(m.max_mark, errors='coerce')} for r in data.records if r.marks for m in r.marks]
                if all_marks_data:
                    marks_sunburst_df = pd.DataFrame(all_marks_data).dropna()
                    sunburst_fig = go.Figure(go.Sunburst(
                        labels=['All Courses'] + list(marks_sunburst_df['course'].unique()) + list(marks_sunburst_df['assessment']),
                        parents=[''] * (1 + marks_sunburst_df['course'].nunique()) + list(marks_sunburst_df['course']),
                        values=[marks_sunburst_df['scored'].sum()] + list(marks_sunburst_df.groupby('course')['scored'].sum()) + list(marks_sunburst_df['scored']),
                        branchvalues="total", hoverinfo="label+percent parent"))
                    sunburst_fig.update_layout(title_text="Hierarchical Marks Distribution", margin = dict(t=40, l=0, r=0, b=0))
                    st.plotly_chart(sunburst_fig, use_container_width=True)

            # Expander view with Gauges
            for record in data.records:
                with st.expander(f"**{record.coursecode}** - {record.coursetitle}"):
                    # ... (gauge and dataframe logic remains the same) ...
        else:
            st.warning("No marks data found.")

    # --- Exam Schedule Page ---
    elif choice == "Exam Schedule":
        with st.spinner("Fetching Exam Schedule..."):
            data = client.get_exam_schedule(selected_sem_id)
        if data and data.exams:
            # ... (calendar logic remains the same) ...
        else:
            st.warning("No exam schedule data found.")
