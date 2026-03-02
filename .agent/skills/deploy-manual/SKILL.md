---
name: deploy-manual
description: Automates the process of building the frontend, building the backend, running the manual deploy script, and pushing to git.
---

# Deploy Manual Skill

This skill automates the deployment process for the SmartDocs application. When the user requests a deploy using this skill, you must follow the precise steps below sequentially.

## Workflow Steps

### 1. Build Frontend
Use the `run_command` tool to execute the frontend build.
```bash
cd frontend
npm run build
```
**Action on Error**: If the build fails, identify the root cause in the logs, attempt to fix the code if it's an obvious error, and inform the user about what happened and what you are doing to fix it. Do not proceed to the next step until the build is successful.

### 2. Build Backend
Use the `run_command` tool to build and spin up the backend via Docker. Make sure to run this command in the `backend/` directory.
```bash
cd backend
docker compose up --build -d
```
**Action on Error**: Monitor the output. If the containers fail to build or start, investigate the docker logs, attempt a fix, and communicate the issue to the user. Do not proceed until the backend is running correctly.

### 3. Run Manual Deploy Script
Once both frontend and backend are successfully built and running without errors, execute the deploy script. This script is located in the project root, so make sure to run it from there.
```bash
cd ..
.\deploy_manual.bat
```
*(Note: adjust the path if you are not in the backend directory)*.
**Action on Error**: Analyze the script's output. If it fails, identify the problem, stop the process, and notify the user immediately about the failure.


### 4. Git Version Control
If `deploy_manual.bat` is completely successful, you must commit and push the current changes.
First, perform a quick diff to understand what was changed so you can decide on a good commit message:
```bash
git diff
```
Then, stage the files:
```bash
git add .
```
Determine a concise and descriptive commit message using the Conventional Commits pattern (`feat:`, `fix:`, `chore:`, `refactor:`, etc.) based on the context of the recent changes and the `git diff` output.
```bash
git commit -m "type: descriptive message about the changes"
git push
```

### 5. Final Notification
Once `git push` is successful, communicate with the user (e.g., using a normal message or `notify_user` if in a task) to inform them that:
1. The frontend and backend builds passed.
2. The manual deploy script completed successfully.
3. The changes were committed and pushed to the repository.
