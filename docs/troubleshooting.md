# **Troubleshooting Guide**

This guide provides solutions to common issues encountered while using GameFlow Connect. If your issue is not listed here, consider checking the FAQ or reaching out to the project maintainers.

---

## **Common Issues and Solutions**

### **1. Application Fails to Launch**
**Cause:** Missing dependencies or incorrect installation.

**Solution:**

- Verify that Python, Tkinter, and Git are installed on your system.
- Ensure all dependencies listed in `requirements.txt` are installed by running:
  ```bash
  pip install -r requirements.txt
  ```

### **2. Unable to Authenticate with Google Drive or GitHub**
**Cause:** Authentication token not generated or expired.

**Solution:**

- Double-check your credentials.
- For Google Drive, ensure OAuth credentials are correctly configured in your Google Cloud project.
- For GitHub, verify that your personal access token has the required scopes (e.g., repo access).

### **3. Files Not Syncing with Google Drive**
**Cause:** Network connectivity issues or incorrect API setup.

**Solution:**

- Check your internet connection.
- Verify API credentials in the configuration file.
- Restart the application to reinitialize API connections.

### **4. Git Operations Failing**
**Cause:** Misconfigured repository or invalid Git commands.

**Solution:**

- Ensure the correct repository is linked in the application.
- Verify your SSH key or HTTPS access settings.
- Run the following to reset the Git connection:
  ```bash
  git remote remove origin
  git remote add origin <repository_url>
  ```

### **5. UI Freezing or Slow Performance**
**Cause:** Excessive operations or large datasets.

**Solution:**

- Optimize file operations and reduce the size of datasets.
- Restart the application if it becomes unresponsive.
- Check for application updates that may include performance fixes.

---

## **Contact and Reporting Issues**
If the above solutions do not resolve your issue, you can:
- Check the [GitHub Issues page](https://github.com/Germano123/python-gameflowconnect/issues) for similar problems or report a new issue.
- Include detailed steps to reproduce the problem, along with relevant error logs or screenshots.

---

!!! note "**Troubleshooting Updates**"
    - This troubleshooting guide will be updated regularly as new issues and solutions arise.
    - Contributions to improve this guide are welcome through pull requests!
