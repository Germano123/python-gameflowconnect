# GameFlowConnect
**A Collaboration Tool for Game Artists, Programmers, and Designers**

GameFlowConnect is a tool designed to facilitate effective collaboration between game artists, programmers, and designers by providing a centralized platform for the exchange and submission of assets within a project. The system is built with Python, leveraging **Clean Architecture**, **SOLID principles**, and **CustomTkinter** for a user-friendly and intuitive experience.

---

## 🚀 Recent Progress & Architecture

GameFlowConnect has evolved to a production-ready **Clean Architecture** structure:

* **Domain Layer (`src/domain/`)**: Pure business entities (`Asset`, `ProjectContext`) and enums (`AssetType`, `SyncStatus`), completely decoupled from UI or external APIs.
* **Use Cases Layer (`src/use_cases/`)**: Application orchestrations (`SyncAssetUseCase`, `ListAssetsUseCase`) depending exclusively on repository abstractions (`IAssetStorageRepository`, `ILocalStorageRepository`) enforcing **Dependency Inversion (DIP)** and **Interface Segregation (ISP)**.
* **Adapters Layer (`src/adapters/`)**: Concrete implementations for Google Drive API (`GoogleDriveAdapter`), Local File System (`LocalFileAdapter`), and Mock Service (`MockDriveAdapter`) adhering to **Liskov Substitution (LSP)**.
* **UI / Presentation (`src/components/`)**: Atomic Design UI structure (`atoms`, `molecules`, `organisms`, `pages`, `templates`) with CustomTkinter.
* **Asset Synchronization Engine (Phase 1: Images)**: Enables seamless image asset sync (`.png`, `.jpg`, `.jpeg`, `.tga`, `.webp`) from Google Drive directly into local Game Engine asset directories (`/Assets/Images/`).
* **Automated Unit Tests (`tests/`)**: Fully covered unit and integration tests using `unittest` and `unittest.mock`.

---

## 🛠️ Problems & Solutions

### Version Control Conflicts
* **Problem:** In game development, mixing large binary assets (3D models, textures, audio) with source code in Git leads to repository bloat and merge conflicts.
* **Solution:** GameFlowConnect establishes a hybrid bridge: **Google Drive** for heavy binary assets and **GitHub** for code and scripts.

---

## 🔑 Key Features
1. **Google Drive Integration (Cloud Asset Storage)**
   Enables easy and secure storage, preview, and 1-click sync of game assets directly to local engine folders.
2. **GitHub Repository Integration**
   Provides repository tracking, commit histories, and code management directly within the application.
3. **Local Game Engine Sync (Unity / Unreal / Godot)**
   Automatically creates and organizes local asset subdirectories (`Assets/Images`, `Assets/Docs`, `Assets/Models`).
4. **Clean Architecture & SOLID Design System**
   Modular, testable, and maintainable codebase built with CustomTkinter.
5. **Demo Mode (1-Click Test)**
   Allows offline exploration of all UI features using simulated mock data.

---

## 📋 Requirements
- Python 3.9 or higher
- Google Drive account
- GitHub account & [GitHub Personal Access Token (PAT)](https://docs.github.com/en/enterprise-cloud@latest/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token)
- `credentials.json` (Google OAuth 2.0 Client ID credentials from Google Cloud Console)

---

## ⚙️ Google Drive Setup Guide (Google Cloud Console)

To connect GameFlowConnect with real Google Drive API storage, follow these setup steps:

### 1. Create a Project in Google Cloud Console
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click on the project dropdown at the top and select **New Project**.
3. Name your project (e.g., `GameFlowConnect-Dev`) and click **Create**.

### 2. Enable the Google Drive API
1. In the Google Cloud Console, navigate to **APIs & Services > Library**.
2. Search for **Google Drive API**.
3. Click on **Google Drive API** and click **Enable**.

### 3. Configure OAuth Consent Screen
1. Navigate to **APIs & Services > OAuth consent screen**.
2. Select **External** (or Internal if using Google Workspace) and click **Create**.
3. Fill in required fields:
   - **App name**: `GameFlowConnect`
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
4. Click **Save and Continue**.
5. Under **Scopes**, click **Add or Remove Scopes** and select:
   - `.../auth/drive` (See, edit, create, and delete all of your Google Drive files)
6. Under **Test users** (if in Testing mode), add the Google email addresses of your team members who will test the application.

### 4. Create OAuth 2.0 Credentials (`credentials.json`)
1. Navigate to **APIs & Services > Credentials**.
2. Click **+ Create Credentials** at the top and select **OAuth client ID**.
3. Choose **Application type**: **Desktop App**.
4. Set the **Name** to `GameFlowConnect Client`.
5. Click **Create**.
6. A dialog will appear with your Client ID. Click **Download JSON**.
7. Rename the downloaded file to `credentials.json` and place it in the root directory of `python-gameflowconnect` on each developer/artist machine.

---

## ⚡ Installation & Execution

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Germano123/python-gameflowconnect.git
   cd python-gameflowconnect
   ```

2. **Create and activate a virtual environment**:
   - **Windows (PowerShell/CMD)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Add Google OAuth Credentials**:
   Place your `credentials.json` file in the root directory of the project.

5. **Run the Application**:
   - **Windows**:
     ```cmd
     run.bat
     ```
   - **Linux / macOS**:
     ```bash
     chmod +x run.sh
     ./run.sh
     ```
   - **Direct Python**:
     ```bash
     python src/main.py
     ```

6. **Run Unit Tests**:
   ```bash
   python -m unittest discover -s tests
   ```

---

## 🎨 Visual Identity
The project's color scheme consists of:

<div style="display: flex; justify-content: center; align-items: center; height: 100px">
    <div style="display: flex; justify-content: center; align-items: center; color: white; background-color: #1e3743; width: 180px; height: 100%; margin: 5px; border-radius: 23px"><p>Primary: #1e3743</p></div>
    <div style="display: flex; justify-content: center; align-items: center; color: white; background-color: #1e3760; width: 180px; height: 100%; margin: 5px; border-radius: 23px"><p>Secondary: #1e3760</p></div>
    <div style="display: flex; justify-content: center; align-items: center; color: white; background-color: #00aa00; width: 180px; height: 100%; margin: 5px; border-radius: 23px"><p>Accent: #00aa00</p></div>
</div>

---

## 🤝 Contributions
Contributions are welcome! Please refer to `CONTRIBUTING.md` for details on how to contribute to the project.
