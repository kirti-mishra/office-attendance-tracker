# Office Attendance Policy Tracker

🏢 A Streamlit-based application to track office attendance and ensure compliance with attendance policies.

## Features

- Mark attendance and out-of-office (OOO) days for past and future weeks.
- Visualize attendance summaries and projections.
- Calculate future attendance requirements to meet policy compliance.

---

## Prerequisites

Before running the application, ensure you have the following installed:

- Python 3.8 or higher
- `pip` (Python package manager)

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/kirti-mishra/office-attendance-tracker.git
   cd office-attendance-tracker
2. **Set Up a Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
3. **Set Up a Virtual Environment**:
    ```bash
    pip install -r requirements.txt
## Running the Application

1. **Start the Streamlit App: Run the following command in the terminal:**
    ```bash
    streamlit run attendance_tracker.py
2. **Access the Application: Open your browser and navigate to:**
    ```bash
    http://localhost:8501
## Data Persistence
The application saves attendance and OOO data in a JSON file named attendance_data.json in the project directory.

## Dependencies
The project uses the following Python libraries:
- Streamlit: For building the web application.
- Pandas: For data manipulation.
- Plotly: For creating interactive visualizations.
- Datetime: For date and time operations.
