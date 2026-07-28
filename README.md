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

4. **Run the Application**:
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

5. **Run Unit Tests**:
   ```bash
   python -m unittest discover -s tests
   ```



---

## 📦 Packaging & Windows Installer

If you want to package GameFlowConnect into a standalone Windows executable and generate a professional installation wizard (`setup.exe`) for distributing the software, follow these steps:

### Step 1: Build the Standalone Executable & Portable Package
Before generating the setup installer, compile the Python application using the automated build script. With your virtual environment (`venv`) active, run:
```powershell
# On Windows PowerShell
.\venv\Scripts\python.exe build_exe.py
```
This will clean up any previous build outputs and bundle all required libraries (including CustomTkinter themes and assets) under the directory `dist/GameFlowConnect/`.
It also automatically generates a compressed portable ZIP package at:
`👉 dist/GameFlowConnect_v<version>_Portable.zip`

You can verify the portable version by running the executable directly:
`👉 dist/GameFlowConnect/GameFlowConnect.exe`

### Step 2: Compile the Setup Installer (Inno Setup)
To bundle the compiled files into a modern Windows installation wizard:

1. Download and install [Inno Setup](https://jrsoftware.org/isdl.php).
2. Open the Inno Setup Compiler.
3. Open the **`GameFlowConnect.iss`** script (located in the project root directory).
4. Click **Build > Compile** from the top menu or press **`F9`**.
5. The compiler will package the executable directory and output the installer program at:
   `👉 Output/GameFlowConnect_Setup.exe`

This `GameFlowConnect_Setup.exe` is the final wizard ready to install the application with Desktop and Start Menu shortcuts.

> [!NOTE]
> This project is open-source and non-commercial. The Windows installer generated via Inno Setup is intended for non-commercial distribution and testing purposes.

> [!TIP]
> **Troubleshooting Installer Error 4551**: If running `GameFlowConnect_Setup.exe` fails with *"Unable to execute file in the temporary directory. Error 4551: an access control policy blocked this file"*, a Windows policy (e.g., Smart App Control or AppLocker) is blocking execution in the user Temp folder.
> - **Easiest Solution**: Simply use the portable version `dist/GameFlowConnect_v<version>_Portable.zip`. Extract the ZIP and run `GameFlowConnect.exe` directly. Since it runs out-of-the-box and does not extract helper stubs to the Temp directory, it bypasses the policy block entirely.
> - **Bypass via CMD**: Alternatively, you can override the temp environment variables before launching the installer:
>   ```cmd
>   mkdir C:\Temp
>   set TEMP=C:\Temp
>   set TMP=C:\Temp
>   GameFlowConnect_Setup.exe
>   ```

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
