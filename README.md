# ProcureFlow — SIH26032 working MVP

ProcureFlow is a Python/Flask application for farmer procurement scheduling, rule-based eligibility checks, token booking, queue tracking, centre operations, and automated email updates.

**Live demo:** https://procureflow-sih26032.abbaszaga04.chatgpt.site

## Included workflows

- Farmer: sign in, view schedules, check eligibility, book/cancel token, track queue and read messages.
- Centre staff: view assigned schedules, check farmers in, start service, complete visits and mark no-shows.
- Administrator: see system metrics, create schedules and open/close booking windows.
- Notifications: every booking/status change is stored in-app and can be delivered through Gmail SMTP.
- Language switcher: English, हिन्दी and मराठी across all farmer, staff and administrator screens.
- Authentication: ProcureFlow's own local role login only; no ChatGPT/OpenAI login or account dependency.
- Automation: the `send-reminders` command creates next-day procurement reminders.
- Safety: password hashing, role checks, CSRF protection, parameterized SQL, duplicate booking prevention and audit records.

## Start on Windows

```powershell
git clone https://github.com/DarkeBaby75/procureflow-sih26032.git
cd procureflow-sih26032
.\setup_and_run.ps1
```

Open <http://127.0.0.1:5000>.

## Demo accounts

| Role | Email | Password |
|---|---|---|
| Farmer | `farmer@demo.in` | `Farmer@123` |
| Centre staff | `staff@demo.in` | `Staff@123` |
| Administrator | `admin@demo.in` | `Admin@123` |

These accounts are for local demonstration only. Replace them before any real deployment.

## Gmail SMTP setup

1. Enable 2-Step Verification on the sending Google Account.
2. Create a Google App Password for the application.
3. Copy `.env.example` to `.env` and set:

```dotenv
SMTP_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-account@gmail.com
SMTP_APP_PASSWORD=your-16-character-app-password
SMTP_FROM_EMAIL=your-account@gmail.com
```

Do not use the normal Google Account password and never commit `.env`. Without SMTP credentials, notifications are still saved in the in-app message centre, so the full demo works offline.

After saving the credentials, restart ProcureFlow and send one real test message:

```powershell
.\.venv\Scripts\python.exe -m flask --app app test-smtp --to recipient@example.com
```

## Automated next-day reminders

Run manually:

```powershell
flask --app app send-reminders
```

For a daily local automation, create a Windows Task Scheduler job that runs this command from the project directory. Running it at 18:00 each day is suitable for next-day reminders.

## Tests

```powershell
.\run_tests.ps1
```

See `docs/RESEARCH.md` for the official references and scope rationale, and `docs/ARCHITECTURE.md` for the data flow and queue state machine.

## Research boundary

The MVP follows the relevant operational ideas from official e-NAM material: farmer registration, digital arrival/lot tracking and status communication. It intentionally stops before assaying, bidding, weighment, invoicing and payment. Eligibility declarations in this prototype are demonstrative; production rules must be configured from the sponsoring authority’s official scheme and state-specific procurement policy.
