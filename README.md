# Management System v1 - Setup & Deployment Guide

This guide describes how to move this application to a new computer and set it up from scratch.

## 📋 Prerequisites

1.  **Python 3.10 or higher**: Download and install from [python.org](https://www.python.org/).
2.  **Microsoft SQL Server**: The application is tested with **SQL Server Express**.
3.  **ODBC Driver**: Ensure you have "SQL Server Native Client 11.0" or "ODBC Driver 17 for SQL Server" installed.
    - If you use a different driver, you will need to update `database_manager.py`.

## 🚀 Setup Steps

### 1. Copy Application Files
Copy the entire `managementv1` folder to the new computer (e.g., to `C:\managementv1`).

### 2. Prepare the Database
1.  On the new computer, open **SQL Server Management Studio (SSMS)**.
2.  Restore your database backup (the `.bak` file) to a new database named **POSDB**.
3.  Ensure the SQL Server instance allows **Windows Authentication** (or update the connection string if using SQL login).

### 3. Create a Virtual Environment
Open a terminal (Command Prompt or PowerShell) inside the application folder and run:
```bash
# Create the environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
```

### 4. Install Dependencies
With the virtual environment activated, run:
```bash
pip install -r requirements.txt
```

### 5. Configure Connection
Open `database_manager.py` and update the `CONNECTION_CONFIG` section with your actual server name:
```python
CONNECTION_CONFIG = {
    "driver": "SQL Server Native Client 11.0", # Or your installed driver
    "server": "YOUR_NEW_COMPUTER_NAME\\SQLEXPRESS",
    "database": "POSDB",
    "trusted_connection": "yes"
}
```

## 🏃 Running the Application

To start the server, run:
```bash
python app.py
```
The application will be available at `http://localhost:8080` (or the port configured in `app.py`).

## 📁 Project Structure
- `app.py`: Main entry point.
- `requirements.txt`: List of required Python libraries.
- `database_manager.py`: Database connection settings.
- `backups/`: Default folder for database backups.

## 🛠 Troubleshooting
- **Database Connection Error**: Ensure the SQL Server service is running and the computer name in `database_manager.py` is correct.
- **Missing Module**: Ensure you ran `pip install -r requirements.txt` while the `venv` was active.
