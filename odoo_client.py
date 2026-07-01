"""
Auria — Odoo connection layer
Wraps XML-RPC calls. Each user authenticates with their own Odoo account,
so every action respects Odoo's permissions and audit log.
"""
import xmlrpc.client
from datetime import date
from collections import defaultdict

ODOO_URL = "https://odoo.auria.global"
ODOO_DB  = "Auria_Business"

_common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
_models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

# ── Department mapping (uid → info) ──────────────────────────
USER_DEPT = {
    18: {"dept": "production",  "name": "عبدالله",    "color": "#2E3D2E"},
    29: {"dept": "procurement", "name": "علاء الديب", "color": "#633806"},
    9:  {"dept": "procurement", "name": "علاء وشاح",  "color": "#7A4410"},
    27: {"dept": "procurement", "name": "خان",        "color": "#8B5E3C"},
    15: {"dept": "operations",  "name": "مروان",      "color": "#1A5276"},
    13: {"dept": "operations",  "name": "ناصر",       "color": "#2C6E3B"},
    11: {"dept": "creative",    "name": "وصال",       "color": "#8B3A8B"},
    31: {"dept": "creative",    "name": "وئام",       "color": "#A34FA3"},
    24: {"dept": "cs",          "name": "أمل",        "color": "#A32D2D"},
    12: {"dept": "cs",          "name": "ولاء",       "color": "#8B2020"},
    10: {"dept": "cs",          "name": "زنجابيل",    "color": "#6B1818"},
    8:  {"dept": "management",  "name": "حسام",       "color": "#2E3D2E"},
    23: {"dept": "management",  "name": "بدر",        "color": "#4A5D48"},
}

DEPT_PROJECT = {
    "production": 3, "procurement": 4, "creative": 5,
    "cs": 6, "operations": 7, "management": 8,
}

DAILY_REPORT_TASKS = {18: 27, 29: 28, 11: 29, 15: 30, 13: 31, 27: 39, 23: 45, 31: 50}


def is_done(stage_name):
    """Robust done-check — handles the D0NE typo in Odoo."""
    if not stage_name:
        return False
    return stage_name.strip().upper().replace("0", "O") in {
        "DONE", "RECEIVED", "PUBLISHED", "RESOLVED", "APPROVED", "DELIVERED", "DECIDED"
    }


def authenticate(email, password):
    """Returns (uid, info) or (None, None)."""
    uid = _common.authenticate(ODOO_DB, email.strip(), password, {})
    if not uid:
        return None, None
    info = USER_DEPT.get(uid, {"dept": "management", "name": email, "color": "#2E3D2E"})
    return uid, info


def odoo(uid, pwd, model, method, args=None, kwargs=None):
    return _models.execute_kw(ODOO_DB, uid, pwd, model, method, args or [[]], kwargs or {})


def today_str():
    return str(date.today())


# ── DASHBOARD ────────────────────────────────────────────────
def get_company_snapshot(uid, pwd):
    today = today_str()
    orders = odoo(uid, pwd, "sale.order", "search_read",
        [[["date_order", ">=", f"{today} 00:00:00"]]], {"fields": ["amount_total"]})
    deliveries = odoo(uid, pwd, "stock.picking", "search_count",
        [[["date_done", ">=", f"{today} 00:00:00"], ["state", "=", "done"]]])
    mos = odoo(uid, pwd, "mrp.production", "search_count",
        [[["state", "in", ["confirmed", "progress"]]]])
    return {
        "orders": len(orders),
        "revenue": round(sum(o["amount_total"] for o in orders)),
        "deliveries": deliveries,
        "mos": mos,
    }


def get_my_stats(uid, pwd):
    today = today_str()
    tasks = odoo(uid, pwd, "project.task", "search_read",
        [[["user_ids", "in", [uid]]]],
        {"fields": ["stage_id", "priority", "date_deadline"]})
    def st(t): return t["stage_id"][1] if t["stage_id"] else None
    return {
        "assigned": len(tasks),
        "done":    sum(1 for t in tasks if is_done(st(t))),
        "urgent":  sum(1 for t in tasks if t["priority"] == "1" and not is_done(st(t))),
        "overdue": sum(1 for t in tasks if t["date_deadline"] and t["date_deadline"] < today and not is_done(st(t))),
    }


def get_dept_kpis(uid, pwd, dept):
    today = today_str()
    if dept == "production":
        return [
            ("Active MOs", odoo(uid, pwd, "mrp.production", "search_count", [[["state", "in", ["confirmed", "progress"]]]])),
            ("Done Today", odoo(uid, pwd, "mrp.production", "search_count", [[["state", "=", "done"], ["date_finished", ">=", f"{today} 00:00:00"]]])),
        ]
    if dept == "procurement":
        return [
            ("Open RFQs", odoo(uid, pwd, "purchase.order", "search_count", [[["state", "in", ["draft", "sent"]]]])),
            ("Confirmed POs", odoo(uid, pwd, "purchase.order", "search_count", [[["state", "=", "purchase"]]])),
        ]
    if dept == "operations":
        return [
            ("Deliveries Today", odoo(uid, pwd, "stock.picking", "search_count", [[["date_done", ">=", f"{today} 00:00:00"], ["state", "=", "done"]]])),
            ("Pending Orders", odoo(uid, pwd, "sale.order", "search_count", [[["state", "=", "sale"]]])),
        ]
    if dept == "cs":
        proj = DEPT_PROJECT["cs"]
        return [("CS Tasks", odoo(uid, pwd, "project.task", "search_count", [[["project_id", "=", proj]]]))]
    if dept == "creative":
        proj = DEPT_PROJECT["creative"]
        return [("Creative Tasks", odoo(uid, pwd, "project.task", "search_count", [[["project_id", "=", proj]]]))]
    return []


# ── TASKS ────────────────────────────────────────────────────
def get_tasks(uid, pwd, scope="mine"):
    domain = [["user_ids", "in", [uid]]] if scope == "mine" else []
    tasks = odoo(uid, pwd, "project.task", "search_read", [domain],
        {"fields": ["id", "name", "stage_id", "priority", "date_deadline", "project_id"],
         "limit": 100, "order": "priority desc, date_deadline asc"})
    return [{
        "id": t["id"], "name": t["name"],
        "stage": t["stage_id"][1].strip() if t["stage_id"] else "—",
        "priority": t["priority"], "due": t["date_deadline"] or "",
        "project": t["project_id"][1] if t["project_id"] else "—",
    } for t in tasks]


def get_project_stages(uid, pwd, task_id):
    task = odoo(uid, pwd, "project.task", "read", [[task_id]], {"fields": ["project_id"]})
    proj = task[0]["project_id"][0]
    stages = odoo(uid, pwd, "project.task.type", "search_read",
        [[["project_ids", "in", [proj]]]], {"fields": ["id", "name"], "order": "sequence"})
    return [(s["id"], s["name"].strip()) for s in stages]


def update_task(uid, pwd, task_id, vals):
    odoo(uid, pwd, "project.task", "write", [[task_id], vals])


def set_task_stage(uid, pwd, task_id, stage_id):
    odoo(uid, pwd, "project.task", "write", [[task_id], {"stage_id": stage_id}])


def post_task_note(uid, pwd, task_id, note):
    odoo(uid, pwd, "project.task", "message_post", [[task_id]],
        {"body": f"<p>{note}</p>", "message_type": "comment", "subtype_xmlid": "mail.mt_note"})


# ── PRODUCTION ───────────────────────────────────────────────
def get_mos(uid, pwd):
    mos = odoo(uid, pwd, "mrp.production", "search_read",
        [[["state", "!=", "cancel"]]],
        {"fields": ["id", "name", "product_id", "product_qty", "state", "date_start"],
         "limit": 30, "order": "date_start desc"})
    return [{
        "id": m["id"], "name": m["name"],
        "product": m["product_id"][1] if m["product_id"] else "—",
        "qty": m["product_qty"], "state": m["state"],
        "date": (m["date_start"] or "")[:10],
    } for m in mos]


def get_inventory(uid, pwd, query=""):
    domain = [["location_id.usage", "=", "internal"], ["quantity", ">", 0]]
    quants = odoo(uid, pwd, "stock.quant", "search_read", [domain],
        {"fields": ["product_id", "quantity", "location_id"], "limit": 300})
    agg = defaultdict(lambda: {"qty": 0, "loc": ""})
    for qt in quants:
        name = qt["product_id"][1]
        if query and query.lower() not in name.lower():
            continue
        agg[name]["qty"] += qt["quantity"]
        agg[name]["loc"] = qt["location_id"][1].split("/")[-1] if qt["location_id"] else ""
    return [{"name": n, "qty": round(v["qty"], 1), "loc": v["loc"]}
            for n, v in sorted(agg.items(), key=lambda x: -x[1]["qty"])[:60]]


# ── PROCUREMENT ──────────────────────────────────────────────
def get_rfqs(uid, pwd):
    rfqs = odoo(uid, pwd, "purchase.order", "search_read",
        [[["state", "in", ["draft", "sent", "purchase"]]]],
        {"fields": ["id", "name", "partner_id", "amount_total", "state", "date_planned", "currency_id"],
         "limit": 30, "order": "create_date desc"})
    return [{
        "id": r["id"], "name": r["name"],
        "supplier": r["partner_id"][1] if r["partner_id"] else "—",
        "total": r["amount_total"], "state": r["state"],
        "due": (r["date_planned"] or "")[:10],
        "currency": r["currency_id"][1] if r["currency_id"] else "LYD",
    } for r in rfqs]


def approve_rfq(uid, pwd, po_id):
    odoo(uid, pwd, "purchase.order", "button_confirm", [[po_id]])


# ── OPERATIONS ───────────────────────────────────────────────
def get_deliveries(uid, pwd):
    today = today_str()
    picks = odoo(uid, pwd, "stock.picking", "search_read",
        [[["picking_type_id.code", "=", "outgoing"], ["scheduled_date", ">=", f"{today} 00:00:00"]]],
        {"fields": ["id", "name", "partner_id", "state", "scheduled_date"], "limit": 30})
    return [{
        "id": p["id"], "name": p["name"],
        "customer": p["partner_id"][1] if p["partner_id"] else "—",
        "state": p["state"], "date": (p["scheduled_date"] or "")[:10],
    } for p in picks]


def get_orders(uid, pwd, query=""):
    domain = []
    if query:
        domain = ["|", ["name", "ilike", query], ["partner_id.name", "ilike", query]]
    orders = odoo(uid, pwd, "sale.order", "search_read", [domain],
        {"fields": ["id", "name", "partner_id", "amount_total", "state"],
         "limit": 30, "order": "date_order desc"})
    return [{
        "id": o["id"], "name": o["name"],
        "customer": o["partner_id"][1] if o["partner_id"] else "—",
        "total": o["amount_total"], "state": o["state"],
    } for o in orders]


# ── CUSTOMER SERVICE ─────────────────────────────────────────
def get_tickets(uid, pwd):
    tickets = odoo(uid, pwd, "project.task", "search_read",
        [[["project_id", "=", DEPT_PROJECT["cs"]]]],
        {"fields": ["id", "name", "stage_id", "partner_id", "create_date"],
         "limit": 40, "order": "create_date desc"})
    return [{
        "id": t["id"],
        "customer": t["partner_id"][1] if t["partner_id"] else t["name"][:20],
        "issue": t["name"],
        "status": t["stage_id"][1].strip() if t["stage_id"] else "New",
        "date": (t["create_date"] or "")[:16],
    } for t in tickets]


def get_ticket_messages(uid, pwd, task_id):
    msgs = odoo(uid, pwd, "mail.message", "search_read",
        [[["res_id", "=", task_id], ["model", "=", "project.task"],
          ["message_type", "in", ["comment", "email"]]]],
        {"fields": ["body", "author_id", "date"], "order": "date asc", "limit": 30})
    import re
    out = []
    for m in msgs:
        text = re.sub("<[^<]+?>", "", m["body"] or "").strip()
        if text:
            out.append({"author": m["author_id"][1] if m["author_id"] else "?", "text": text, "date": (m["date"] or "")[:16]})
    return out


def reply_ticket(uid, pwd, task_id, message):
    odoo(uid, pwd, "project.task", "message_post", [[task_id]],
        {"body": f"<p>{message}</p>", "message_type": "comment", "subtype_xmlid": "mail.mt_comment"})


# ── DAILY REPORT ─────────────────────────────────────────────
def submit_daily_report(uid, pwd, achievements, challenges, tomorrow):
    task_id = DAILY_REPORT_TASKS.get(uid)
    if not task_id:
        return False
    ach = "".join(f"<li>{a}</li>" for a in achievements if a.strip())
    plan = "".join(f"<li>{p}</li>" for p in tomorrow if p.strip())
    html = (
        f"<p><b>📋 التقرير اليومي — {today_str()}</b></p>"
        f"<p><b>✅ الإنجازات:</b></p><ul>{ach}</ul>"
        f"<p><b>🔴 التحديات:</b> {challenges or '—'}</p>"
        f"<p><b>📅 خطة الغد:</b></p><ul>{plan}</ul>"
    )
    odoo(uid, pwd, "project.task", "message_post", [[task_id]],
        {"body": html, "message_type": "comment", "subtype_xmlid": "mail.mt_note"})
    return True
