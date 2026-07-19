# Lambda MicroVM PoC

## Objective

Use AWS Lambda MicroVM as an isolated workspace where Codex creates,
executes, tests and validates generated application code.

## AWS configuration

- Region: us-east-1
- Current MicroVM:
  microvm-47c76726-b639-3140-9af1-cfad5347081c
- Shell access uses AWS Lambda MicroVM shell auth tokens.
- Local WebSocket client:
  ~/.local/bin/websocat
- Shell port: 8022

Always discover the current endpoint with AWS CLI. Never store auth
tokens in files or commit them.

## Remote workspace

- Application workspace: /workspace/api-poc
- Do not modify /app.
- Install Python dependencies only in:
  /workspace/api-poc/.venv
- Do not install packages globally.
- Do not deploy or create AWS resources without explicit approval.

## Current project status

The remote project contains:

- template.yaml
- requirements.txt
- pytest.ini
- src/app.py
- tests/test_app.py
- .venv

Validation already completed:

- pytest: 3 passed
- cfn-lint: success
- direct Lambda handler invocation: HTTP 200

## Safety rules

- Show AWS resource-changing commands before running them.
- Do not execute sam deploy.
- Do not terminate the current MicroVM without approval.
- Never print full AWS credentials or shell authentication tokens.
- Treat exit code 143 after a completed websocat PTY session as a
  transport shutdown issue only after confirming command completion.
