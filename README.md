# Juris360 Demo (Complete)

Unzip-and-run Flask app with:
- Auth (Flask-Login)
- Full CRUD: Clients, Cases, Documents, Billing, Schedule
- Dropdowns backed by lookup tables (seeded)
- Demo data for Kenya-style firms/cases/invoices/events
- Render deploy files and persistent data/uploads

## Run locally (Windows PowerShell)
```powershell
python -m venv venv
.env\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python run.py
```
Login: **admin / kwetutech00**

## Deploy to Render
- Push to GitHub
- New Web Service → connect repo
- Uses `render.yaml` (persistent disk)
- Start command: `gunicorn -c gunicorn_conf.py wsgi:app`
