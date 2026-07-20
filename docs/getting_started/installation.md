# **Getting Started: Installation & Setup**

Welcome to GameFlow Connect! This guide will help you set up and start using the application.

---

## **1. Prerequisites**

- **Python Version**: Python 3.9 or higher installed on your system ([python.org](https://www.python.org/downloads/)).
- **Git**: Installed for repository management ([git-scm.com](https://git-scm.com/)).
- **Google Drive Account**: For cloud asset storage.
- **GitHub Account & Token**: Personal Access Token (PAT) for repository integration.

---

## **2. Installation Steps**

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Germano123/python-gameflowconnect.git
   cd python-gameflowconnect
   ```

2. **Create a Virtual Environment**:
   - **Windows**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## **3. Google Drive OAuth Setup (`credentials.json`)**

To connect with your Google Drive account, you need an OAuth 2.0 Client ID file (`credentials.json`):

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a **New Project** (e.g., `GameFlowConnect`).
3. Under **APIs & Services > Library**, enable the **Google Drive API**.
4. Under **APIs & Services > OAuth consent screen**, set up the consent screen:
   - App Name: `GameFlowConnect`
   - Scope: `https://www.googleapis.com/auth/drive`
   - Add your Google account email under **Test Users**.
5. Under **APIs & Services > Credentials**, click **+ Create Credentials > OAuth client ID**:
   - Application Type: **Desktop App**
6. Download the generated OAuth client JSON file, rename it to `credentials.json`, and place it in the root folder of `python-gameflowconnect`.

---

## **4. Running the Application**

Run the following command to start GameFlow Connect:

```bash
python src/main.py
```

Or use the provided launcher scripts:
- **Windows**: `run.bat`
- **Linux/macOS**: `./run.sh`

---

## **5. Running Automated Tests**

To verify your installation and test all domain entities and use cases:

```bash
python -m unittest discover -s tests
```
