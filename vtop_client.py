import requests
from bs4 import BeautifulSoup
import base64
from dataclasses import dataclass, field
from typing import List, Optional
import time

BASE_URL = "https://vtop.vitap.ac.in/vtop"
CAPTCHA_URL = "https://cap.va.synaptic.gg/captcha"

@dataclass
class SemesterInfo:
    id: str
    name: str

@dataclass
class SemesterData:
    semesters: List[SemesterInfo]
    update_time: int

@dataclass
class AttendanceRecord:
    serial: str
    category: str
    course_name: str
    course_code: str
    course_type: str
    faculty_detail: str
    classes_attended: str
    total_classes: str
    attendance_percentage: str
    attendence_fat_cat: str
    debar_status: str
    course_id: str

@dataclass
class AttendanceData:
    records: List[AttendanceRecord]
    semester_id: str
    update_time: int

@dataclass
class FullAttendanceRecord:
    serial: str
    date: str
    slot: str
    day_time: str
    status: str
    remark: str

@dataclass
class FullAttendanceData:
    records: List[FullAttendanceRecord]
    semester_id: str
    update_time: int
    course_id: str
    course_type: str

@dataclass
class TimetableSlot:
    serial: str
    day: str
    slot: str
    course_code: str
    course_type: str
    room_no: str
    block: str
    start_time: str
    end_time: str
    name: str

@dataclass
class TimetableData:
    slots: List[TimetableSlot]
    semester_id: str
    update_time: int

@dataclass
class MarksRecordEach:
    serial: str
    markstitle: str
    maxmarks: str
    weightage: str
    status: str
    scoredmark: str
    weightagemark: str
    remark: str

@dataclass
class MarksRecord:
    serial: str
    coursecode: str
    coursetitle: str
    coursetype: str
    faculity: str
    slot: str
    marks: List[MarksRecordEach]

@dataclass
class MarksData:
    records: List[MarksRecord]
    semester_id: str
    update_time: int

@dataclass
class ExamScheduleRecord:
    serial: str
    slot: str
    course_name: str
    course_code: str
    course_type: str
    course_id: str
    exam_date: str
    exam_session: str
    reporting_time: str
    exam_time: str
    venue: str
    seat_location: str
    seat_no: str

@dataclass
class PerExamScheduleRecord:
    exam_type: str
    records: List[ExamScheduleRecord]

@dataclass
class ExamScheduleData:
    exams: List[PerExamScheduleRecord]
    semester_id: str
    update_time: int

class VtopClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; U; Linux x86_64; en-US) Gecko/20100101 Firefox/130.5"
        })
        self.is_authenticated = False
        self.csrf_token = None
        self.reg_no = None

    def _get_text(self, element):
        return element.get_text(strip=True) if element else ""

    def _get_csrf(self, soup):
        csrf_tag = soup.find("input", {"name": "_csrf"})
        if csrf_tag:
            self.csrf_token = csrf_tag['value']

    def _solve_captcha(self, captcha_data):
        try:
            img_string = base64.urlsafe_b64encode(captcha_data.encode()).decode()
            response = requests.post(CAPTCHA_URL, json={"imgstring": img_string})
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            return None

    def login(self):
        max_retries = 3
        for _ in range(max_retries):
            try:
                # Step 1: Load initial page to get cookies
                res = self.session.get(f"{BASE_URL}/open/page")
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "lxml")
                self._get_csrf(soup)
                if not self.csrf_token:
                    continue

                # Step 2: Get captcha
                res = self.session.post(f"{BASE_URL}/prelogin/setup", data={"_csrf": self.csrf_token, "flag": "VTOP"})
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "lxml")
                captcha_tag = soup.find("img", class_="img-fluid")
                if not captcha_tag or 'base64,' not in captcha_tag['src']:
                    continue
                
                captcha_data = captcha_tag['src']
                captcha_solution = self._solve_captcha(captcha_data)
                if not captcha_solution:
                    continue

                # Step 3: Perform login
                login_payload = {
                    "_csrf": self.csrf_token,
                    "username": self.username,
                    "password": self.password,
                    "captchaStr": captcha_solution,
                }
                res = self.session.post(f"{BASE_URL}/login", data=login_payload)
                res.raise_for_status()

                if "error" in res.url or "Invalid LoginId" in res.text or "Invalid Username" in res.text:
                    if "Invalid Captcha" in res.text:
                        continue
                    else:
                        raise Exception("Invalid Credentials")
                
                soup = BeautifulSoup(res.text, "lxml")
                self._get_csrf(soup)
                reg_no_tag = soup.find("input", {"name": "authorizedIDX"})
                if reg_no_tag and reg_no_tag.get('value'):
                    self.reg_no = reg_no_tag['value']
                    self.is_authenticated = True
                    return
                else:
                    raise Exception("Login failed: Could not find registration number.")
            
            except Exception as e:
                print(f"Login attempt failed: {e}")
        
        raise Exception(f"Login failed after {max_retries} attempts.")

    def _make_request(self, url, payload):
        if not self.is_authenticated:
            raise Exception("Session Expired. Please login again.")
        
        payload["_csrf"] = self.csrf_token
        payload["authorizedID"] = self.reg_no

        res = self.session.post(url, data=payload)
        res.raise_for_status()

        if "login" in res.url:
            self.is_authenticated = False
            raise Exception("Session Expired. Please login again.")
        
        return res.text
    
    def get_semesters(self):
        url = f"{BASE_URL}/academics/common/StudentTimeTable"
        payload = {"verifyMenu": "true"}
        html = self._make_request(url, payload)
        
        soup = BeautifulSoup(html, 'lxml')
        records = []
        options = soup.select('select[name="semesterSubId"] option')
        for option in options:
            value = option.get('value')
            name = self._get_text(option)
            if value and name and "Select" not in name:
                records.append(SemesterInfo(id=value, name=name.replace("- AMR", "").strip()))
        return SemesterData(semesters=records, update_time=int(time.time()))

    def get_attendance(self, semester_id):
        url = f"{BASE_URL}/processViewStudentAttendance"
        payload = {"semesterSubId": semester_id}
        html = self._make_request(url, payload)

        soup = BeautifulSoup(html, 'lxml')
        rows = soup.find_all('tr')
        records = []
        for row in rows[1:]:
            cells = row.find_all('td')
            if len(cells) > 10:
                js_call = cells[10].find('a')['onclick']
                parts = js_call.replace("'", "").split(',')
                course_id = parts[2]
                course_type = parts[3].split(')')[0]
                records.append(AttendanceRecord(
                    serial=self._get_text(cells[0]), category=self._get_text(cells[1]),
                    course_name=self._get_text(cells[2]), course_code=self._get_text(cells[3]),
                    faculty_detail=self._get_text(cells[4]), classes_attended=self._get_text(cells[5]),
                    total_classes=self._get_text(cells[6]), attendance_percentage=self._get_text(cells[7]),
                    attendence_fat_cat=self._get_text(cells[8]), debar_status=self._get_text(cells[9]),
                    course_id=course_id, course_type=course_type
                ))
        return AttendanceData(records=records, semester_id=semester_id, update_time=int(time.time()))

    def get_timetable(self, semester_id):
        url = f"{BASE_URL}/processViewTimeTable"
        payload = {"semesterSubId": semester_id}
        html = self._make_request(url, payload)

        soup = BeautifulSoup(html, 'lxml')
        tables = soup.find_all('table')
        
        classname_code = {}
        if len(tables) > 0:
            for row in tables[0].find_all('tr'):
                cells = row.find_all('td')
                if len(cells) > 2:
                    full_text = self._get_text(cells[2])
                    parts = full_text.split('-', 1)
                    if len(parts) > 1:
                        code = parts[0].strip()
                        name = parts[1].split('(')[0].strip()
                        classname_code[code] = name
        
        slots = []
        timings = []
        if len(tables) > 1:
            rows = tables[1].find_all('tr')
            if len(rows) > 1:
                start_times = [self._get_text(c) for c in rows[0].find_all('td')]
                end_times = [self._get_text(c) for c in rows[1].find_all('td')]
                timings = list(zip(start_times, end_times))
            
            day = ""
            for row in rows[2:]:
                cells = row.find_all('td')
                current_day_cell = cells[0]
                if current_day_cell.has_attr('rowspan'):
                    day = self._get_text(current_day_cell)
                    cells.pop(0)
                
                for i, cell in enumerate(cells):
                    text = self._get_text(cell)
                    if len(text) > 5:
                        parts = [p.strip() for p in text.split('-')]
                        if len(parts) >= 4:
                            code = parts[1]
                            slots.append(TimetableSlot(
                                serial=str(i), day=day, slot=parts[0],
                                course_code=code, course_type=parts[2],
                                room_no=parts[3], block=parts[4] if len(parts) > 4 else "",
                                start_time=timings[i][0] if i < len(timings) else "",
                                end_time=timings[i][1] if i < len(timings) else "",
                                name=classname_code.get(code, "")
                            ))
        return TimetableData(slots=slots, semester_id=semester_id, update_time=int(time.time()))

    def get_marks(self, semester_id):
        url = f"{BASE_URL}/examinations/doStudentMarkView"
        payload = {"semesterSubId": semester_id}
        html = self._make_request(url, payload)
        
        soup = BeautifulSoup(html, 'lxml')
        courses = []
        rows = soup.select("tr.tableContent")
        
        for i in range(0, len(rows), 2):
            course_row = rows[i]
            marks_row = rows[i+1]
            
            c_cells = course_row.find_all('td')
            course_record = MarksRecord(
                serial=self._get_text(c_cells[0]), coursecode=self._get_text(c_cells[2]),
                coursetitle=self._get_text(c_cells[3]), coursetype=self._get_text(c_cells[4]),
                faculity=self._get_text(c_cells[6]), slot=self._get_text(c_cells[7]), marks=[]
            )
            
            marks_table = marks_row.find('table')
            if marks_table:
                for m_row in marks_table.select('tr.tableContent-level1'):
                    m_cells = m_row.find_all('td')
                    course_record.marks.append(MarksRecordEach(
                        serial=self._get_text(m_cells[0]), markstitle=self._get_text(m_cells[1]),
                        maxmarks=self._get_text(m_cells[2]), weightage=self._get_text(m_cells[3]),
                        status=self._get_text(m_cells[4]), scoredmark=self._get_text(m_cells[5]),
                        weightagemark=self._get_text(m_cells[6]), remark=self._get_text(m_cells[7])
                    ))
            courses.append(course_record)
        return MarksData(records=courses, semester_id=semester_id, update_time=int(time.time()))

    def get_exam_schedule(self, semester_id):
        url = f"{BASE_URL}/examinations/doSearchExamScheduleForStudent"
        payload = {"semesterSubId": semester_id}
        html = self._make_request(url, payload)
        
        soup = BeautifulSoup(html, 'lxml')
        exams = []
        current_exam_group = None
        
        rows = soup.find('table')
        if rows is None:
            return 
        rows = rows.find_all('tr', recursive=False)
        for row in rows[2:]:
            cells = row.find_all('td', recursive=False)
            if len(cells) == 1:
                if current_exam_group:
                    exams.append(current_exam_group)
                exam_type = self._get_text(cells[0].find('b'))
                current_exam_group = PerExamScheduleRecord(exam_type=exam_type, records=[])
            elif len(cells) > 12 and current_exam_group:
                current_exam_group.records.append(ExamScheduleRecord(
                    serial=self._get_text(cells[0]), course_code=self._get_text(cells[1]),
                    course_name=self._get_text(cells[2]), course_type=self._get_text(cells[3]),
                    course_id=self._get_text(cells[4]), slot=self._get_text(cells[5]),
                    exam_date=self._get_text(cells[6]), exam_session=self._get_text(cells[7]),
                    reporting_time=self._get_text(cells[8]), exam_time=self._get_text(cells[9]),
                    venue=self._get_text(cells[10]), seat_location=self._get_text(cells[11]),
                    seat_no=self._get_text(cells[12])
                ))
        if current_exam_group:
            exams.append(current_exam_group)

        return ExamScheduleData(exams=exams, semester_id=semester_id, update_time=int(time.time()))