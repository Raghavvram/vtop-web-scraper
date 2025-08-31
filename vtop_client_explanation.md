# VTOP Client (`vtop_client.py`) Documentation

This document provides a detailed explanation of the `vtop_client.py` file, which contains the `VtopClient` class for interacting with the VIT-AP VTOP website.

## 1. Imports

The script begins by importing necessary libraries:

- `requests`: For making HTTP requests to the VTOP website.
- `BeautifulSoup` (from `bs4`): For parsing HTML and extracting data.
- `base64`: For encoding captcha images.
- `dataclasses`: To create simple classes for storing structured data.
- `typing`: For type hinting.
- `time`: For getting the current timestamp.

```python
import requests
from bs4 import BeautifulSoup
import base64
from dataclasses import dataclass, field
from typing import List, Optional
import time
```

## 2. Constants

Two constants are defined at the beginning of the file:

- `BASE_URL`: The base URL for the VTOP website.
- `CAPTCHA_URL`: The URL of the external service used to solve captchas.

```python
BASE_URL = "https://vtop.vitap.ac.in/vtop"
CAPTCHA_URL = "https://cap.va.synaptic.gg/captcha"
```

## 3. Data Classes

Several data classes are defined to hold the data scraped from VTOP in a structured way.

- **`SemesterInfo`**: Represents a single semester with its ID and name.
- **`SemesterData`**: Holds a list of `SemesterInfo` objects and the time of the last update.
- **`AttendanceRecord`**: Represents the attendance details for a single course.
- **`AttendanceData`**: Holds a list of `AttendanceRecord` objects for a specific semester and the update time.
- **`FullAttendanceRecord`**: Represents a detailed attendance record for a single class session.
- **`FullAttendanceData`**: Holds a list of `FullAttendanceRecord` objects for a specific course in a semester.
- **`TimetableSlot`**: Represents a single slot in the timetable.
- **`TimetableData`**: Holds a list of `TimetableSlot` objects for a specific semester.
- **`MarksRecordEach`**: Represents the marks for a single assessment component.
- **`MarksRecord`**: Represents the marks for a single course, including a list of `MarksRecordEach`.
- **`MarksData`**: Holds a list of `MarksRecord` objects for a specific semester.
- **`ExamScheduleRecord`**: Represents the schedule for a single exam.
- **`PerExamScheduleRecord`**: Groups exam schedules by exam type (e.g., "FAT", "CAT").
- **`ExamScheduleData`**: Holds a list of `PerExamScheduleRecord` objects for a specific semester.

## 4. `VtopClient` Class

This is the main class that encapsulates all the logic for interacting with VTOP.

### `__init__(self, username, password)`

The constructor initializes the `VtopClient` object.

- **Parameters**:
    - `username` (str): The student's registration number.
    - `password` (str): The student's VTOP password.
- **Functionality**:
    - Stores the `username` and `password`.
    - Creates a `requests.Session` object to persist cookies across requests.
    - Sets a `User-Agent` header to mimic a browser.
    - Initializes `is_authenticated` to `False`, `csrf_token` to `None`, and `reg_no` to `None`.

### `_get_text(self, element)`

A helper method to safely extract text from a BeautifulSoup element.

- **Parameters**:
    - `element`: A BeautifulSoup element.
- **Functionality**:
    - Returns the stripped text of the element if it exists, otherwise returns an empty string.

### `_get_csrf(self, soup)`

A helper method to extract the CSRF token from the HTML.

- **Parameters**:
    - `soup`: A BeautifulSoup object representing the parsed HTML.
- **Functionality**:
    - Finds the input tag with the name `_csrf` and stores its value in `self.csrf_token`.

### `_solve_captcha(self, captcha_data)`

This method sends the captcha image data to an external service to get the solution.

- **Parameters**:
    - `captcha_data` (str): The base64 encoded captcha image data.
- **Functionality**:
    - Encodes the captcha data and sends it to the `CAPTCHA_URL`.
    - Returns the captcha solution as text if successful, otherwise returns `None`.

### `login(self)`

This method handles the login process.

- **Functionality**:
    1.  It retries the login process up to 3 times.
    2.  **GET Request to VTOP**: It first sends a GET request to the VTOP login page to get an initial session cookie and a CSRF token.
    3.  **POST to `/prelogin/setup`**: It then sends a POST request to set up the login page, which includes the CSRF token.
    4.  **Captcha Handling**: It finds the captcha image, extracts the base64 data, and sends it to the `_solve_captcha` method.
    5.  **Login POST Request**: It constructs the login payload with the username, password, CSRF token, and the solved captcha. It then sends a POST request to the `/login` endpoint.
    6.  **Login Verification**:
        - It checks for errors in the response URL or text (e.g., "Invalid LoginId", "Invalid Captcha"). If the captcha is invalid, it retries. If the credentials are invalid, it raises an exception.
        - If the login is successful, it extracts the registration number (`authorizedIDX`) from the response and sets `self.is_authenticated` to `True`.
    7.  If the login fails after all retries, it raises an exception.

### `_make_request(self, url, payload)`

A helper method for making authenticated POST requests to VTOP after logging in.

- **Parameters**:
    - `url` (str): The URL to send the request to.
    - `payload` (dict): The data to be sent in the request.
- **Functionality**:
    1.  Checks if the user is authenticated. If not, it raises an exception.
    2.  Adds the CSRF token and the registration number to the payload.
    3.  Sends the POST request using the session object.
    4.  Checks if the session has expired by looking for "login" in the response URL. If it has, it sets `self.is_authenticated` to `False` and raises an exception.
    5.  Returns the HTML content of the response.

### `get_semesters(self)`

Fetches the list of available semesters.

- **Functionality**:
    1.  Makes a POST request to the student timetable page.
    2.  Parses the HTML response using BeautifulSoup.
    3.  Finds the dropdown menu for semester selection (`semesterSubId`).
    4.  Iterates through the options, extracts the semester ID and name, and creates `SemesterInfo` objects.
    5.  Returns a `SemesterData` object containing the list of semesters and the current timestamp.

### `get_attendance(self, semester_id)`

Fetches the attendance data for a given semester.

- **Parameters**:
    - `semester_id` (str): The ID of the semester for which to fetch attendance.
- **Functionality**:
    1.  Makes a POST request to the attendance page with the `semester_id`.
    2.  Parses the HTML response.
    3.  Iterates through the rows of the attendance table.
    4.  For each row, it extracts the details of the course and attendance.
    5.  It also extracts the `course_id` and `course_type` from the `onclick` attribute of a link in the last cell.
    6.  Creates `AttendanceRecord` objects and returns them in an `AttendanceData` object.

### `get_timetable(self, semester_id)`

Fetches the timetable for a given semester.

- **Parameters**:
    - `semester_id` (str): The ID of the semester.
- **Functionality**:
    1.  Makes a POST request to the timetable page.
    2.  Parses the HTML response.
    3.  The timetable is spread across two tables. The first table contains the mapping of course codes to course names. The second table contains the actual timetable grid.
    4.  It first parses the course code-name mapping from the first table.
    5.  Then, it parses the second table to extract the slot details. It also extracts the start and end times for each slot.
    6.  It combines the information to create `TimetableSlot` objects.
    7.  Returns a `TimetableData` object containing the list of slots.

### `get_marks(self, semester_id)`

Fetches the marks for a given semester.

- **Parameters**:
    - `semester_id` (str): The ID of the semester.
- **Functionality**:
    1.  Makes a POST request to the marks page.
    2.  Parses the HTML response.
    3.  The marks are presented in a table where each course has two rows: one for the course details and one for the detailed marks.
    4.  It iterates through the rows, two at a time.
    5.  For each pair of rows, it extracts the course information from the first row and the detailed marks from the second row's nested table.
    6.  It creates `MarksRecord` and `MarksRecordEach` objects.
    7.  Returns a `MarksData` object containing the list of course marks.

### `get_exam_schedule(self, semester_id)`

Fetches the exam schedule for a given semester.

- **Parameters**:
    - `semester_id` (str): The ID of the semester.
- **Functionality**:
    1.  Makes a POST request to the exam schedule page.
    2.  Parses the HTML response.
    3.  The exam schedule is grouped by exam type (e.g., "FAT", "CAT").
    4.  It iterates through the rows of the schedule table.
    5.  When it encounters a row with a single cell, it treats it as a new exam group.
    6.  For subsequent rows, it extracts the exam details and adds them to the current exam group.
    7.  It creates `ExamScheduleRecord` and `PerExamScheduleRecord` objects.
    8.  Returns an `ExamScheduleData` object containing the list of exam schedules.
