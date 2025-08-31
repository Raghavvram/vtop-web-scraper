# VTOP Web Scraper & Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, user-friendly dashboard to view your academic data from the VTOP portal of Vellore Institute of Technology (VIT). This project scrapes data from VTOP and presents it in a clean, interactive Streamlit web application.

![VTOP Dashboard Screenshot](httpshttps://i.imgur.com/YOUR_SCREENSHOT_URL.png) <!-- Replace with a real screenshot -->

## ✨ Features

*   **Secure Login:** Your credentials are used only for the session and are not stored.
*   **Attendance Tracking:** View your attendance percentage for each course, with color-coded status (Safe, Warning, Danger).
*   **Interactive Timetable:** A weekly grid view of your class schedule.
*   **Marks Viewer:** See your marks for CATs, FATs, and other assessments.
*   **Exam Schedule:** Check your upcoming exam dates, times, and venues.
*   **Semester Selection:** Easily switch between different semesters.
*   **Responsive Design:** The dashboard is usable on both desktop and mobile devices.

## 🛠️ Tech Stack

*   **Backend:** Python
*   **Web Scraping:** `requests`, `beautifulsoup4`
*   **Web Framework:** `streamlit`
*   **Data Manipulation:** `pandas`
*   **Plotting:** `plotly`

## 🚀 Getting Started

### Prerequisites

*   Python 3.12+
*   `uv` (or `pip`) for package installation

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/vtop-web-scraper.git
    cd vtop-web-scraper
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install the dependencies:**
    Using `uv`:
    ```bash
    uv pip install -r requirements.txt
    ```
    Or using `pip`:
    ```bash
    pip install -r requirements.txt
    ```

### Usage

1.  **Run the Streamlit application:**
    ```bash
    streamlit run main.py
    ```

2.  **Open your browser:**
    Navigate to the local URL provided by Streamlit (usually `http://localhost:8501`).

3.  **Login:**
    Enter your VTOP username and password to access your dashboard.

## 📂 Project Structure

```
/
├── .gitignore
├── app.py              # Original Streamlit app
├── main.py             # Enhanced Streamlit app (use this one)
├── pyproject.toml      # Project metadata and dependencies
├── README.md           # This file
├── requirements.txt    # Project dependencies
├── vtop_client.py      # The core web scraping client
└── ...
```

*   `vtop_client.py`: This is the core of the project. It handles logging into VTOP, managing sessions, and scraping the required data. It uses `requests` for HTTP requests and `BeautifulSoup` for parsing HTML.
*   `main.py`: The main Streamlit application. It provides the user interface, handles user input, and uses `vtop_client.py` to fetch and display the data.
*   `app.py`: An earlier version of the Streamlit app. `main.py` is the recommended one to run.

## ⚙️ How It Works

The `VtopClient` class in `vtop_client.py` simulates a user browsing the VTOP website.

1.  **Login:** It first fetches the login page to get a CSRF token. It then uses an external service to solve the CAPTCHA and sends a POST request with your credentials.
2.  **Session Management:** The client maintains a session cookie to stay logged in for subsequent requests.
3.  **Data Scraping:** Once logged in, the client navigates to the respective pages for attendance, timetable, marks, and exam schedule. It then parses the HTML of these pages to extract the data into structured dataclasses.
4.  **Frontend:** The Streamlit app (`main.py`) creates an instance of `VtopClient` and calls its methods to get the data. The data is then displayed in interactive tables, charts, and grids using `pandas` and `plotly`.

## ⚠️ Disclaimer

This is an unofficial tool and is not affiliated with VIT. The purpose of this project is purely educational. The developers are not responsible for any misuse of this tool or for any issues that may arise from its use. Use it at your own risk. Your VTOP credentials are not stored or collected.

## 🤝 Contributing

Contributions are welcome! If you have any ideas, suggestions, or bug reports, please open an issue or create a pull request.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
