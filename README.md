# 🌿 Auria — Department App

A mobile-friendly Streamlit app that gives each Auria department a live
interface to Odoo. Every person signs in with their own Odoo account, so
all actions respect Odoo's permissions and show up in its audit log.

## Departments
- **Production** — manufacturing orders + Serraj inventory
- **Procurement** — RFQs + approve purchase orders
- **Operations** — deliveries + order lookup
- **Creative** — content tasks
- **Customer Service** — tickets + reply in-app
- **Shared** — dashboard, full task control, daily report

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Open http://localhost:8501 and sign in with an Odoo account.

## Deploy on Streamlit Cloud (free)
1. Push this folder to a GitHub repo
2. Go to https://share.streamlit.io
3. Click **New app**, pick your repo, set main file to `app.py`
4. Click **Deploy** — done in ~2 minutes

The app connects to `odoo.auria.global` directly (XML-RPC), so no separate
backend is needed. Odoo just needs to be reachable from the internet, which
it already is.

## Files
- `app.py` — the Streamlit UI (all screens)
- `odoo_client.py` — Odoo XML-RPC connection layer
- `assets/` — Auria logo + emblem
- `.streamlit/config.toml` — brand theme

## Security note
Passwords are sent to Odoo for authentication and held only in the user's
session (never stored). For production, keep the Streamlit app on HTTPS
(Streamlit Cloud provides this automatically).
