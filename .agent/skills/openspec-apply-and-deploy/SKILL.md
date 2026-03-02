---
name: openspec-apply-and-deploy
description: Apply tasks from an OpenSpec change and then automatically test and deploy the application using the deploy-manual skill.
---

# OpenSpec Apply and Deploy Skill

This skill automates the process of applying an OpenSpec change and immediately following it up with a full deployment using the `deploy-manual` skill.

## Workflow Steps

### 1. Apply OpenSpec Change
First, you must invoke the `openspec-apply-change` skill to implement the tasks.
- If a change name is provided by the user, use it.
- Follow all the steps defined in the `openspec-apply-change` skill (read context files, implement tasks, mark them complete).
- **Important**: Do not proceed to the deployment step if the implementation step fails, is blocked, or requires user clarification. Only proceed if the tasks for the current session have been successfully implemented.

### 2. Deploy Application
After successful implementation, invoke the `deploy-manual` skill to deploy the changes. Note that testing and validation are handled within the build steps of the deploy skill.
- Follow all the steps defined in the `deploy-manual` skill sequentially.
- This includes building the frontend (`npm run build`), **building and running the backend using Docker** (`docker compose up --build -d` in the backend directory), running the manual deploy script (`.\deploy_manual.bat`), and handling git version control.
- Ensure you report the deployment status back to the user upon completion.

## Guardrails
- **Stop on Failure**: If at any point the `openspec-apply-change` or the deployment builds/tests fail, stop the process immediately and ask the user for guidance.
- **Combined Reporting**: Once both the apply and deploy steps are successful, provide a consolidated report to the user summarizing the tasks applied and confirming the successful deployment.
