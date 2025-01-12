# GameFlowConnect
**A Collaboration Tool for Game Artists, Programmers, and Designers**

GameFlowConnect is a tool designed to facilitate effective collaboration between game artists, programmers, and designers by providing a centralized platform for the exchange and submission of assets within a project. The system is built with Python and leverages the Tkinter UI library for a user-friendly and intuitive experience.

## The Problems
The use of multiple assets in game development projects often involves repetitive tasks. Making minor adjustments and exporting files can be monotonous and time-consuming, creating an additional burden for artists who may lack experience with version control tools.

### Version Control Conflicts
**Problem:** In large game development teams, multiple members often work simultaneously on different parts of the game. This can lead to version control conflicts, especially when merging changes made by different developers. Resolving these conflicts manually can be time-consuming and error-prone.

### Asset Management and Duplication
**Problem:** Coordinating the creation and distribution of game assets in large teams can result in duplicated files, inconsistent naming conventions, and difficulty tracking the latest versions. This confusion can hinder overall efficiency.

### Communication Failures
**Problem:** As teams grow, effective communication becomes more challenging. Team members may miss important updates, changes, or discussions, leading to misunderstandings, duplicated efforts, and project delays.

### Integration Challenges
**Problem:** Integrating different components developed by various team members can be complex, especially in large teams where specialized work is distributed. Ensuring all game elements function cohesively and without bugs becomes a significant challenge.

### Security and Access Control
**Problem:** Large teams often include members with diverse roles and responsibilities. Ensuring that sensitive information such as credentials, API keys, or proprietary assets remains secure and accessible only to authorized team members is crucial. Poor access management can lead to data breaches or unauthorized project modifications.

## The Solutions
GameFlowConnect addresses these challenges by offering an accessible platform for artists to manage version control efficiently.

## Key Features
1. **Google Drive Integration**
   The tool allows users to connect their Google Drive accounts, enabling easy and secure storage of project assets. This integration streamlines the process of sharing and accessing files in a collaborative environment.

2. **GitHub Repository Integration**
   The tool supports GitHub repository integration, providing efficient version control and collaboration among team members. Developers can easily push and pull changes directly through the tool, ensuring a smooth workflow.

3. **Git Versioning**
   By default, the system uses Git for version control of project files. This ensures that changes made by different team members are tracked, and the project's history is maintained. Users can commit changes, create branches, and manage merges directly through the tool.

4. **User-Friendly Interface**
   The graphical user interface (GUI) is developed using the Tkinter library, offering an intuitive and easy-to-use design. The focus is on simplicity and efficiency to enhance the overall collaborative process.

## Secondary Features
1. **Real-Time Collaboration**
   Enable simultaneous editing and viewing of project files by multiple team members, promoting collaboration and immediate feedback.

2. **Asset Preview and Visualization**
   Implement a feature to preview and visualize game assets directly within the tool, allowing team members to inspect graphics, models, and other media without external applications.

3. **Task and Issue Tracker**
   Integrate a system for tracking tasks and issues to help team members assign, monitor, and manage tasks within the tool. This feature streamlines project management and improves communication among team members.

4. **Notification System**
   Develop a notification system to alert users about changes made by collaborators, newly assigned tasks, or important project updates. This enhances communication and keeps everyone informed about project progress.

5. **Offline Mode and Syncing**
   Implement an offline mode that allows users to work on the project without an internet connection. Changes made offline should be automatically synced with the cloud (Google Drive) and repository (GitHub) once the internet connection is restored, ensuring seamless collaboration across environments.

## Requirements
- Python 3.6 or higher
- Google Drive account (for integration)
- GitHub account (for integration)
- [GitHub Personal Access Token](https://docs.github.com/en/enterprise-cloud@latest/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token)

## Installation
1. Clone the GameFlowConnect repository:
   ```bash
   git clone https://github.com/Germano123/python-gameflowconnect.git
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the tool:
   ```bash
   python ./main.py
   ```
   Log in with your Google Drive and GitHub credentials.

Navigate through the intuitive features to share, preview, and version control your assets.

## Visual Identity
The project's color scheme consists of:
<div style="display: flex; justify-content: center; align-items: center; height: 100px">
    <div style="display: flex; justify-content: center; align-items: center; color: white; background-color: #1e3743; width: 180px; height: 100%; margin: 5px; border-radius: 23px"><p>Primary: #1e3743</p></div>
    <div style="display: flex; justify-content: center; align-items: center; color: white; background-color: #1e3760; width: 180px; height: 100%; margin: 5px; border-radius: 23px"><p>Secondary: #1e3760</p></div>
    <div style="display: flex; justify-content: center; align-items: center; color: white; background-color: #00aa00; width: 180px; height: 100%; margin: 5px; border-radius: 23px"><p>Accent: #00aa00</p></div>
</div>

## Contributions
Contributions are welcome! Please refer to CONTRIBUTING.md for details on how to contribute to the project.

## Suggestions
Leave your feature suggestions in the [issues](https://github.com/Germano123/python-gameflowconnect/issues).

