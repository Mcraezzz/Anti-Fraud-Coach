# Anti-Fraud Coach

[简体中文](README.md) · English

Anti-Fraud Coach is a WeChat Mini Program that helps university students recognize scams and practice responding to them. A student who receives a job offer demanding an upfront deposit can paste the message, inspect the phrases that triggered the warning, and try the fake job scenario to decide what to do next.

## Features

- **Risk detection** accepts chat text, SMS messages, links, and screenshots. Local OCR extracts text from screenshots. The results show the risk level, highlighted passages, and suggested next steps.
- **Questions and answers** retrieve guidance from a campus fraud prevention knowledge base and show the sources alongside each answer. The service retrieves evidence separately for each question.
- **Scenario training** covers fake jobs, task rebate scams, customer service impersonation, gaming trade scams, campus loan scams, and impersonation of acquaintances. The backend scores each choice. A report tracks six skill dimensions and marks those the student has yet to practice.
- **History and administration** store scan history, training progress, and privacy preferences per device session. Administrators can view aggregate scan activity and training completion.

## Run in WeChat DevTools

Open PowerShell at the repository root. These commands start the FastAPI backend with keyword-based retrieval and load OCR on demand.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
$env:ANTI_FRAUD_SEMANTIC_RAG = "0"
$env:ANTI_FRAUD_OCR_PRELOAD = "0"
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open the [health check](http://127.0.0.1:8000/api/coach/health) and confirm that `ok` is `true`. Leave the backend running, import the [miniprogram](miniprogram/) directory into WeChat DevTools, and click **Compile**. Open **识别** (Scan), select a built-in sample, and tap **开始智能识别** (Analyze) to verify the connection. [Local API documentation](http://127.0.0.1:8000/docs)

To test on a phone, change the server's bind address to `0.0.0.0` and connect the phone and computer to the same local network. Under **我的 → 系统偏好设置 → 个人资料与后端连接设置**, enter the computer's LAN address and port, for example `http://192.168.1.20:8000`.

## Data and models

The Mini Program calls the backend through `/api/coach`. By default the service stores device sessions and activity in `backend/app/data/coach.sqlite3`. Set `ANTI_FRAUD_COACH_DB` to choose a different database location. Clearing the Mini Program's local storage removes access to the original device session.

Screenshot analysis requires a local OCR runtime and model files. To enable semantic retrieval, install the model dependencies, point `ANTI_FRAUD_RESOURCE_ROOT` to the resource directory containing the `models` subdirectory, set `ANTI_FRAUD_SEMANTIC_RAG` to `1`, and restart the backend. [Model dependencies](backend/requirements-models.txt) · [Retrieval configuration (Chinese)](docs/RAG语义检索说明.md) · [Integration and testing guide (Chinese)](docs/新版小程序接入说明.md)
