# **Decentralized Sync Architecture & gameflow.json**

This document outlines the design and architecture of the decentralized synchronization engine used in **GameFlow Connect**, detailing the structure of the central registry file (`gameflow.json`) and the progressive development guidelines for integrations.

---

## **1. Design Philosophy**

GameFlow Connect is a serverless, peer-to-peer style collaboration tool that uses **Google Drive** as its shared cloud repository. 
Rather than relying on a centralized intermediary database server, each client coordinates with other collaborators asynchronously by reading and writing files and metadata directly to shared folders.

To manage this, the sync engine relies on a dual-registry approach:
1. **Local SQLite Database (`gameflow_local.db`)**: Acts as a fast local cache, tracking the workspaces registered on the user's machine and their local assets' synchronization status.
2. **Remote Central Registry (`gameflow.json`)**: Stored in the root `GameFlow` directory of the user's Google Drive, coordinating workspace membership and active folders across different installations.

---

## **2. gameflow.json Specification**

The `gameflow.json` registry file acts as the single source of truth (SSOT) for the workspaces a user belongs to. It is located at:
`Google Drive > My Drive > GameFlow > gameflow.json`

### **JSON Schema**
```json
{
  "version": "1.0.0",
  "last_updated": "YYYY-MM-DD HH:MM:SS",
  "workspaces": [
    {
      "id": "ws_abcdef",
      "name": "My Godot RPG",
      "description": "Collaborative RPG project",
      "engine": "Godot",
      "drive_folder_id": "folder_id_xyz123",
      "owner": "creator@email.com",
      "created_at": "YYYY-MM-DD"
    }
  ]
}
```

### **Field Descriptions**
- `version`: The registry format version (for backwards compatibility).
- `last_updated`: Timestamp of the last local write.
- `workspaces`: Array of active workspace objects that this user is a participant or owner of.
  - `id`: Unique identifier of the workspace (`ws_<hash>`).
  - `name`: Name of the workspace project.
  - `description`: A brief description of the workspace.
  - `engine`: The game engine of choice (e.g., Godot, Unity, Unreal).
  - `drive_folder_id`: The ID of the shared folder in Google Drive.
  - `owner`: Email address of the creator who shared the workspace.
  - `created_at`: The creation date of the workspace.

---

## **3. Synchronization & Cleanup Workflow**

The synchronization routine runs in a background thread to prevent UI lockups and performs three primary tasks:

### **A. Remote Folder Verification (Orphan Detection)**
For each workspace registered in the local SQLite:
1. The app queries Google Drive to verify if the folder pointed to by `drive_folder_id` still exists and is not trashed (`trashed = false`).
2. If the remote folder has been deleted or is no longer accessible:
   - The workspace is flagged as orphaned.
   - The sync engine automatically cleans up the local database, removing the workspace entry and its cached assets to prevent broken sync states.

### **B. Auto-Discovery & Auto-Import**
1. The app reads the `gameflow.json` registry file from Google Drive.
2. If there are workspaces listed in `gameflow.json` that are **not** present in the local database (and not in the `ignored_workspaces` table):
   - The app automatically registers them locally.
   - It prompts the user or initializes the workspace folder structure on their local machine, allowing new shared projects to appear seamlessly.

### **C. Invitation Sync Integration**
1. When a user accepts a shared project invitation (profile page), the project is added to their local database and written to their remote `gameflow.json` file.
2. When a user declines or leaves a project:
   - They are removed from the `members` list in the project's local/remote `manifest.json`.
   - The project is deleted from their local SQLite and removed from their `gameflow.json` registry on Google Drive.

---

## **4. Progressive Development Guidelines**

Developers extending the synchronization engine should adhere to the following architectural guidelines:

1. **Thread Safety**: 
   - Never share raw `httplib2.Http()` instances across threads. Always request a fresh authorized HTTP transport using `drive_service._get_http()` when executing API requests.
2. **Encapsulation**:
   - Do not perform raw Google Drive API queries inside UI event handlers or use cases. All network access must be encapsulated inside `DriveService` wrapper methods.
3. **Database Consistency**:
   - Any modifications to the remote `gameflow.json` registry must be immediately reflected in the local SQLite cache to prevent race conditions.
4. **Idempotency**:
   - Sync routines must be idempotent. Re-running the sync sequence multiple times should never create duplicate database rows or duplicate directories.
