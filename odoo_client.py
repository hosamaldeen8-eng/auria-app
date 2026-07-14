"""
Auria — Odoo connection layer
Wraps XML-RPC calls. Each user authenticates with their own Odoo account,
so every action respects Odoo's permissions and audit log.
"""

# Bump this whenever app.py depends on a new function here.
CLIENT_VERSION = 31
import xmlrpc.client
import threading
from datetime import date
from collections import defaultdict

ODOO_URL = "https://odoo.auria.global"
ODOO_DB  = "Auria_Business"

# Streamlit serves each user session on its own thread. xmlrpc.client's
# ServerProxy is NOT thread-safe — sharing one across threads corrupts the
# HTTP connection state (http.client.CannotSendRequest). So each thread
# gets its own proxies via threading.local.
_tl = threading.local()

def _get_common():
    if not hasattr(_tl, "common"):
        _tl.common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    return _tl.common

def _get_models():
    if not hasattr(_tl, "models"):
        _tl.models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return _tl.models

def _reset_models():
    if hasattr(_tl, "models"):
        del _tl.models

# ── Department mapping (uid → info) ──────────────────────────
USER_DEPT = {
    18: {"dept": "production",  "name": "عبدالله",    "color": "#2E3D2E"},
    29: {"dept": "procurement", "name": "علاء الديب", "color": "#633806"},
    9:  {"dept": "cs",          "name": "ألاء وشاح",  "color": "#8B2020"},
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
    30: {"dept": "management",  "name": "وجدان",      "color": "#2E3D2E"},
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
    try:
        uid = _get_common().authenticate(ODOO_DB, email.strip(), password, {})
    except (xmlrpc.client.ProtocolError, ConnectionError, OSError):
        # Stale connection — rebuild and retry once
        if hasattr(_tl, "common"):
            del _tl.common
        uid = _get_common().authenticate(ODOO_DB, email.strip(), password, {})
    if not uid:
        return None, None
    info = USER_DEPT.get(uid, {"dept": "management", "name": email, "color": "#2E3D2E"})
    return uid, info


def odoo(uid, pwd, model, method, args=None, kwargs=None):
    """Thread-safe Odoo call with one retry on connection-state errors."""
    import http.client
    try:
        return _get_models().execute_kw(ODOO_DB, uid, pwd, model, method,
                                        args or [[]], kwargs or {})
    except (http.client.CannotSendRequest, http.client.ResponseNotReady,
            xmlrpc.client.ProtocolError, ConnectionError, BrokenPipeError, OSError):
        # Connection state corrupted (e.g. after an interrupted request) —
        # rebuild this thread's proxy and retry once.
        _reset_models()
        return _get_models().execute_kw(ODOO_DB, uid, pwd, model, method,
                                        args or [[]], kwargs or {})


class PagedList(list):
    """A list that also carries the true total count for the query, so the
    UI can show 'showing X of Y' and offer load-more. Backward-compatible
    with plain-list callers (len() still gives what's loaded)."""
    total = 0
    shown = 0


def _paged(uid, pwd, model, domain, fields, limit, order):
    """search_count + search_read in one place, returning a PagedList."""
    total = odoo(uid, pwd, model, "search_count", [domain])
    recs = odoo(uid, pwd, model, "search_read", [domain],
                {"fields": fields, "limit": limit, "order": order})
    return total, recs


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


def get_my_performance(uid, pwd):
    """Deeper personal tracking: week activity, notes, report status, WO time."""
    from datetime import date, timedelta
    today = date.today()
    week_ago = str(today - timedelta(days=7))
    today_s = str(today)

    # Tasks
    tasks = odoo(uid, pwd, "project.task", "search_read",
        [[["user_ids", "in", [uid]]]],
        {"fields": ["name", "stage_id", "priority", "date_deadline", "project_id", "write_date"]})
    def st(t): return t["stage_id"][1] if t["stage_id"] else None

    open_tasks = [t for t in tasks if not is_done(st(t))]
    done_tasks = [t for t in tasks if is_done(st(t))]
    done_this_week = [t for t in done_tasks if (t.get("write_date") or "") >= week_ago]
    overdue_list = [t for t in open_tasks
                    if t["date_deadline"] and t["date_deadline"] < today_s]

    # Notes/messages I posted this week (activity signal)
    notes_week = odoo(uid, pwd, "mail.message", "search_count",
        [[["author_id.user_ids", "in", [uid]],
          ["date", ">=", f"{week_ago} 00:00:00"],
          ["message_type", "in", ["comment", "email"]]]])

    # Daily report submitted today?
    report_task = DAILY_REPORT_TASKS.get(uid)
    report_today = False
    report_week = 0
    if report_task:
        report_today = odoo(uid, pwd, "mail.message", "search_count",
            [[["res_id", "=", report_task], ["model", "=", "project.task"],
              ["date", ">=", f"{today_s} 00:00:00"],
              ["message_type", "in", ["comment", "email"]]]]) > 0
        report_week = odoo(uid, pwd, "mail.message", "search_count",
            [[["res_id", "=", report_task], ["model", "=", "project.task"],
              ["date", ">=", f"{week_ago} 00:00:00"],
              ["message_type", "in", ["comment", "email"]]]])

    # Completion rate
    rate = round(len(done_tasks) / len(tasks) * 100) if tasks else 0

    return {
        "assigned": len(tasks),
        "open": len(open_tasks),
        "done": len(done_tasks),
        "done_week": len(done_this_week),
        "urgent": sum(1 for t in open_tasks if t["priority"] == "1"),
        "overdue": len(overdue_list),
        "overdue_names": [t["name"][:35] for t in overdue_list[:3]],
        "notes_week": notes_week,
        "report_today": report_today,
        "report_week": report_week,
        "completion_rate": rate,
        "next_due": sorted([t for t in open_tasks if t["date_deadline"]],
                           key=lambda x: x["date_deadline"])[:3],
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
        today = today_str()
        # Orders validated to go from HD FG → Yamamah today (picking type 3:
        # "Pick From FG to Alyamama"). This is the dispatch-to-courier count.
        deliv = odoo(uid, pwd, "stock.picking", "search_count",
            [[["picking_type_id", "=", 3], ["date_done", ">=", f"{today} 00:00:00"], ["state", "=", "done"]]])
        # Yamamah live: out for delivery + returned
        out_delivery = odoo(uid, pwd, "accurate.shipment", "search_count", [[["state", "=", "sent"]]])
        returned = odoo(uid, pwd, "accurate.shipment", "search_count", [[["state", "=", "returned"]]])
        return [
            ("مُرسل ليمامة اليوم", deliv),
            ("قيد التوصيل", out_delivery),
            ("مرتجع", returned),
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
        {"fields": ["id", "name", "stage_id", "priority", "date_deadline", "project_id", "write_date"],
         "limit": 100, "order": "priority desc, date_deadline asc"})
    return [{
        "id": t["id"], "name": t["name"],
        "stage": t["stage_id"][1].strip() if t["stage_id"] else "—",
        "priority": t["priority"], "due": t["date_deadline"] or "",
        "project": t["project_id"][1] if t["project_id"] else "—",
        "updated": (t.get("write_date") or "")[:10],
    } for t in tasks]


def get_project_stages(uid, pwd, task_id):
    task = odoo(uid, pwd, "project.task", "read", [[task_id]], {"fields": ["project_id"]})
    if not task or not task[0].get("project_id"):
        return []  # task has no project (e.g. a personal onboarding task)
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
def get_mos(uid, pwd, state="all", query=""):
    domain = [["state", "!=", "cancel"]]
    if state != "all":
        domain.append(["state", "=", state])
    if query:
        domain += ["|", ["name", "ilike", query], ["product_id.name", "ilike", query]]
    mos = odoo(uid, pwd, "mrp.production", "search_read", [domain],
        {"fields": ["id", "name", "product_id", "product_qty", "state", "date_start"],
         "limit": 30, "order": "date_start desc"})
    return [{
        "id": m["id"], "name": m["name"],
        "product": m["product_id"][1] if m["product_id"] else "—",
        "qty": m["product_qty"], "state": m["state"],
        "date": (m["date_start"] or "")[:10],
    } for m in mos]


def get_stock_locations(uid, pwd):
    """Internal storage locations that actually hold stock (for the filter)."""
    quants = odoo(uid, pwd, "stock.quant", "search_read",
        [[["location_id.usage", "=", "internal"], ["quantity", ">", 0]]],
        {"fields": ["location_id"], "limit": 500})
    names = sorted({q["location_id"][1] for q in quants if q.get("location_id")})
    return names


def get_product_categories(uid, pwd):
    """Product categories that hold stock, short display names."""
    cats = odoo(uid, pwd, "product.category", "search_read", [[]],
        {"fields": ["id", "complete_name"]})
    out = []
    for c in cats:
        name = c["complete_name"]
        if name == "All":
            continue
        out.append({"id": c["id"], "name": name.replace("All / ", "")})
    return sorted(out, key=lambda x: x["name"])


def get_inventory(uid, pwd, query="", location="all", category="all"):
    domain = [["location_id.usage", "=", "internal"], ["quantity", ">", 0]]
    if location != "all":
        domain.append(["location_id.complete_name", "=", location])
    if category != "all":
        domain.append(["product_categ_id", "child_of", category])
    quants = odoo(uid, pwd, "stock.quant", "search_read", [domain],
        {"fields": ["product_id", "quantity", "location_id"], "limit": 300})
    agg = defaultdict(lambda: {"qty": 0, "locs": set()})
    for qt in quants:
        name = qt["product_id"][1]
        if query and query.lower() not in name.lower():
            continue
        agg[name]["qty"] += qt["quantity"]
        if qt["location_id"]:
            agg[name]["locs"].add(qt["location_id"][1].split("/")[-1])
    return [{"name": n, "qty": round(v["qty"], 1), "loc": " · ".join(sorted(v["locs"]))}
            for n, v in sorted(agg.items(), key=lambda x: -x[1]["qty"])[:60]]


# ── BOM / PRODUCT DROPDOWN ───────────────────────────────────
def get_manufacturable_products(uid, pwd):
    """Products that have a normal BOM — for the 'create MO' dropdown."""
    boms = odoo(uid, pwd, "mrp.bom", "search_read",
        [[["type", "=", "normal"]]],
        {"fields": ["id", "product_tmpl_id", "product_qty"], "order": "id"})
    out = []
    for b in boms:
        out.append({
            "bom_id": b["id"],
            "tmpl_id": b["product_tmpl_id"][0],
            "name": b["product_tmpl_id"][1],
            "batch": b["product_qty"],
        })
    return out


def get_bom_detail(uid, pwd, bom_id):
    """Full BOM: components + quantities + the operations."""
    bom = odoo(uid, pwd, "mrp.bom", "read", [[bom_id]],
        {"fields": ["product_tmpl_id", "product_qty", "operation_ids"]})
    if not bom:
        return None
    bom = bom[0]
    lines = odoo(uid, pwd, "mrp.bom.line", "search_read",
        [[["bom_id", "=", bom_id]]],
        {"fields": ["product_id", "product_qty", "product_uom_id"]})
    components = [{
        "name": l["product_id"][1],
        "qty": l["product_qty"],
        "uom": l["product_uom_id"][1] if l["product_uom_id"] else "",
    } for l in lines]
    # Operations (routing steps)
    ops = []
    if bom.get("operation_ids"):
        op_recs = odoo(uid, pwd, "mrp.routing.workcenter", "read", [bom["operation_ids"]],
            {"fields": ["name", "workcenter_id", "time_cycle"]})
        ops = [{
            "name": o["name"],
            "workcenter": o["workcenter_id"][1] if o.get("workcenter_id") else "",
            "time": o.get("time_cycle", 0),
        } for o in op_recs]
    return {
        "product": bom["product_tmpl_id"][1],
        "batch": bom["product_qty"],
        "components": components,
        "operations": ops,
    }


def create_mo_from_bom(uid, pwd, tmpl_id, qty):
    """Create a manufacturing order for a product template."""
    variant = odoo(uid, pwd, "product.product", "search_read",
        [[["product_tmpl_id", "=", tmpl_id]]], {"fields": ["id"], "limit": 1})
    if not variant:
        return None
    mo_id = odoo(uid, pwd, "mrp.production", "create", [{
        "product_id": variant[0]["id"],
        "product_qty": float(qty),
    }])
    return mo_id


# ── MO MANAGEMENT PAGE ───────────────────────────────────────
def _utcnow():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _elapsed_min(date_start_str):
    """Minutes since an Odoo UTC datetime string."""
    from datetime import datetime
    try:
        start = datetime.strptime(date_start_str, "%Y-%m-%d %H:%M:%S")
        return max(0.0, (_utcnow() - start).total_seconds() / 60.0)
    except Exception:
        return 0.0


def get_mo_detail(uid, pwd, mo_id):
    """Everything for the MO management page: header, components,
    work orders with LIVE elapsed time (running logs included)."""
    mo = odoo(uid, pwd, "mrp.production", "read", [[mo_id]],
        {"fields": ["name", "product_id", "product_qty", "qty_producing",
                    "state", "date_start", "bom_id", "workorder_ids"]})
    if not mo:
        return None
    mo = mo[0]

    # Components (raw moves) with reservation state
    moves = odoo(uid, pwd, "stock.move", "search_read",
        [[["raw_material_production_id", "=", mo_id]]],
        {"fields": ["product_id", "product_uom_qty", "quantity", "state", "product_uom"]})
    components = [{
        "name": m["product_id"][1] if m["product_id"] else "—",
        "needed": m["product_uom_qty"],
        "done": m.get("quantity", 0),
        "state": m["state"],
        "uom": m["product_uom"][1] if m.get("product_uom") else "",
    } for m in moves]

    # Work orders with live elapsed
    workorders = []
    total_elapsed = 0.0
    if mo["workorder_ids"]:
        wos = odoo(uid, pwd, "mrp.workorder", "read", [mo["workorder_ids"]],
            {"fields": ["id", "name", "state", "is_user_working", "duration",
                        "duration_expected", "workcenter_id"]})
        for w in wos:
            elapsed = w["duration"]  # accumulated (closed logs)
            running_since = None
            worker = None
            # Open time log (ANY user) → live elapsed + who's working.
            # Note: is_user_working is per-caller, so check the log directly.
            open_log = odoo(uid, pwd, "mrp.workcenter.productivity", "search_read",
                [[["workorder_id", "=", w["id"]], ["date_end", "=", False]]],
                {"fields": ["date_start", "user_id"], "limit": 1, "order": "id desc"})
            if open_log:
                running_since = open_log[0]["date_start"]
                elapsed += _elapsed_min(running_since)
                worker = open_log[0]["user_id"][1] if open_log[0].get("user_id") else None
            total_elapsed += elapsed
            workorders.append({
                "id": w["id"], "name": w["name"],
                "state": w["state"], "working": bool(open_log),
                "worker": worker,
                "elapsed": round(elapsed, 1),
                "elapsed_sec": round(elapsed * 60),  # for smooth client counter
                "expected": round(w["duration_expected"], 1),
                "workcenter": w["workcenter_id"][1] if w.get("workcenter_id") else "",
                "running_since": running_since,
            })

    return {
        "id": mo_id, "name": mo["name"],
        "product": mo["product_id"][1] if mo["product_id"] else "—",
        "qty": mo["product_qty"], "producing": mo.get("qty_producing", 0),
        "state": mo["state"],
        "date_start": (mo.get("date_start") or "")[:16],
        "components": components,
        "workorders": workorders,
        "total_elapsed_min": round(total_elapsed, 1),
        "total_elapsed_sec": round(total_elapsed * 60),  # for smooth client counter
        "any_running": any(w["working"] for w in workorders),
    }


# ── TRANSFERS (Buy receipts + internal moves) ────────────────
# Odoo picking types (verified live):
#   64 Buy Raw:        Partners/Vendors(4) → SJ/RM-Receiving(36)
#   51 RM Storage:     SJ/RM-Receiving(36) → SJ/RM-Storage(37)
#   66 PKG Storage:    SJ/RM-Receiving(36) → SJ/PKG-Storage(38)
#   57 FG SJ→HD:       SJ/FG-Storage(55)   → HD/FG-Storage(45)
# Short, clean shipment-status groupings (for the Sales screen). Each maps a
# friendly label to the granular Yamamah api_status_name values it covers.
SHORT_SHIP_STATUS = {
    "in_transit": {"label": "🚚 قيد التوصيل",
                   "names": ["قيد التوصيل", "طلب شحن", "تم الاستلام بالمخزن", "انتظار لاعادة التوصيل"]},
    "delivered":  {"label": "✅ تم التسليم", "names": ["تم التسليم"]},
    "returned":   {"label": "↩️ مرتجع",
                   "names": ["Returned", "ارتجاع للراسل", "تعذر التسليم", "Cancelled"]},
}

TRANSFER_ROUTES = {
    "putaway_rm":  {"label": "استلام → مخزن المواد الخام", "type_id": 51, "src": 36, "dest": 37},
    "putaway_pkg": {"label": "استلام → مخزن التغليف",      "type_id": 66, "src": 36, "dest": 38},
    "fg_to_hd":    {"label": "منتج نهائي: من سراج إلى حي دمشق", "type_id": 57, "src": 55, "dest": 45, "two_step": True},
}


# ── EXPENSES ─────────────────────────────────────────────────
def get_expense_categories(uid, pwd):
    """Expensable products (categories) for the expense form."""
    prods = odoo(uid, pwd, "product.product", "search_read",
        [[["can_be_expensed", "=", True]]], {"fields": ["id", "name"]})
    return [{"id": p["id"], "name": p["name"]} for p in prods]


def get_my_employee(uid, pwd):
    """The hr.employee linked to this Odoo user (expenses need it)."""
    emp = odoo(uid, pwd, "hr.employee", "search_read",
        [[["user_id", "=", uid]]], {"fields": ["id", "name"], "limit": 1})
    return emp[0] if emp else None


def get_my_expenses(uid, pwd):
    """This user's recent expenses, with edit-ability info."""
    emp = get_my_employee(uid, pwd)
    if not emp:
        return []
    exps = odoo(uid, pwd, "hr.expense", "search_read",
        [[["employee_id", "=", emp["id"]]]],
        {"fields": ["id", "name", "total_amount", "state", "date", "product_id", "sheet_id"],
         "limit": 20, "order": "date desc"})
    # Sheet states tell us where it is in the approval chain
    sheet_ids = [e["sheet_id"][0] for e in exps if e.get("sheet_id")]
    sheets = {}
    if sheet_ids:
        for s in odoo(uid, pwd, "hr.expense.sheet", "read", [sheet_ids],
                      {"fields": ["state", "payment_state"]}):
            sheets[s["id"]] = s
    ST = {"draft": "مسودة", "reported": "مُقدّم", "submitted": "قيد المراجعة",
          "approved": "معتمد", "done": "مدفوع", "refused": "مرفوض"}
    out = []
    for e in exps:
        sid = e["sheet_id"][0] if e.get("sheet_id") else None
        sh = sheets.get(sid, {})
        sstate = sh.get("state")            # draft/submit/approve/post/done/cancel
        paid = sh.get("payment_state") == "paid"
        # Freely editable before the manager approves it.
        editable = (not paid) and (sstate in (None, "draft", "submit"))
        # Approved but not yet paid — can be withdrawn to draft, then edited.
        withdrawable = (not paid) and sstate == "approve"
        out.append({
            "id": e["id"], "sheet_id": sid,
            "name": e["name"], "amount": e["total_amount"],
            "state": ST.get(e["state"], e["state"]),
            "sheet_state": sstate, "paid": paid,
            "editable": editable, "withdrawable": withdrawable,
            "date": (e.get("date") or "")[:10],
            "category": e["product_id"][1] if e.get("product_id") else "—",
            "category_id": e["product_id"][0] if e.get("product_id") else None,
        })
    return out


def update_expense(uid, pwd, expense_id, category_id=None, description=None, amount=None):
    """Edit an expense that hasn't been approved/paid yet. Returns (ok, msg)."""
    try:
        exp = odoo(uid, pwd, "hr.expense", "read", [[expense_id]],
                   {"fields": ["sheet_id", "state"]})
        if not exp:
            return False, "المصروف غير موجود"
        sid = exp[0]["sheet_id"][0] if exp[0].get("sheet_id") else None
        if sid:
            sh = odoo(uid, pwd, "hr.expense.sheet", "read", [[sid]],
                      {"fields": ["state", "payment_state"]})[0]
            if sh.get("payment_state") == "paid":
                return False, "لا يمكن التعديل — المصروف مدفوع"
            if sh.get("state") not in ("draft", "submit"):
                return False, "لا يمكن التعديل — تم اعتماده. اسحبه أولاً"
            # A submitted sheet must go back to draft before its lines can change
            if sh.get("state") == "submit":
                try:
                    odoo(uid, pwd, "hr.expense.sheet", "action_reset_expense_sheets", [[sid]])
                except Exception as e:
                    if "cannot marshal None" not in str(e):
                        odoo(uid, pwd, "hr.expense.sheet", "write", [[sid], {"state": "draft"}])
        vals = {}
        if description:
            vals["name"] = description
        if category_id:
            vals["product_id"] = category_id
        if amount is not None:
            vals["total_amount_currency"] = float(amount)
        if vals:
            odoo(uid, pwd, "hr.expense", "write", [[expense_id], vals])
        # Re-submit so it goes back to the manager for approval
        if sid:
            if description:
                odoo(uid, pwd, "hr.expense.sheet", "write", [[sid], {"name": description}])
            try:
                odoo(uid, pwd, "hr.expense.sheet", "action_submit_sheet", [[sid]])
            except Exception as e:
                if "cannot marshal None" not in str(e):
                    odoo(uid, pwd, "hr.expense.sheet", "write", [[sid], {"state": "submit"}])
        return True, "تم تعديل المصروف وإعادة إرساله للاعتماد ✓"
    except Exception as e:
        return False, _clean_odoo_error(e)


def withdraw_expense(uid, pwd, expense_id):
    """Pull an approved-but-unpaid expense back to draft so it can be edited.
    (Re-approval by the manager is then required.) Returns (ok, msg)."""
    try:
        exp = odoo(uid, pwd, "hr.expense", "read", [[expense_id]], {"fields": ["sheet_id"]})
        sid = exp[0]["sheet_id"][0] if exp and exp[0].get("sheet_id") else None
        if not sid:
            return False, "لا يوجد تقرير مرتبط"
        sh = odoo(uid, pwd, "hr.expense.sheet", "read", [[sid]],
                  {"fields": ["state", "payment_state"]})[0]
        if sh.get("payment_state") == "paid":
            return False, "لا يمكن السحب — المصروف مدفوع"
        try:
            odoo(uid, pwd, "hr.expense.sheet", "action_reset_expense_sheets", [[sid]])
        except Exception as e:
            if "cannot marshal None" not in str(e):
                odoo(uid, pwd, "hr.expense.sheet", "write", [[sid], {"state": "draft"}])
        return True, "تم سحب المصروف — يمكنك تعديله الآن"
    except Exception as e:
        return False, _clean_odoo_error(e)


def delete_expense(uid, pwd, expense_id):
    """Delete an unpaid, unapproved expense (and its sheet). Returns (ok, msg)."""
    try:
        exp = odoo(uid, pwd, "hr.expense", "read", [[expense_id]], {"fields": ["sheet_id"]})
        sid = exp[0]["sheet_id"][0] if exp and exp[0].get("sheet_id") else None
        if sid:
            sh = odoo(uid, pwd, "hr.expense.sheet", "read", [[sid]],
                      {"fields": ["state", "payment_state"]})[0]
            if sh.get("payment_state") == "paid" or sh.get("state") in ("post", "done"):
                return False, "لا يمكن الحذف — المصروف مدفوع أو مُرحَّل"
            try:
                odoo(uid, pwd, "hr.expense.sheet", "action_reset_expense_sheets", [[sid]])
            except Exception:
                pass
            odoo(uid, pwd, "hr.expense.sheet", "unlink", [[sid]])
        odoo(uid, pwd, "hr.expense", "unlink", [[expense_id]])
        return True, "تم حذف المصروف ✓"
    except Exception as e:
        return False, _clean_odoo_error(e)


def create_expense(uid, pwd, category_id, description, amount, photo_bytes=None, photo_name="receipt.jpg"):
    """Create a COMPANY-PAID expense, wrap it in an expense report (sheet), and
    submit it to the expense manager (Haitem) for approval.

    After this, the only steps left for the manager in Odoo are:
      Approve → Post Journal Entry → Register Payment.
    Returns (ok, msg)."""
    emp = get_my_employee(uid, pwd)
    if not emp:
        return False, "لا يوجد ملف موظف مرتبط بحسابك"
    try:
        # 1. The expense line — paid by the COMPANY (not employee reimbursement)
        exp_id = odoo(uid, pwd, "hr.expense", "create", [{
            "name": description,
            "product_id": category_id,
            "total_amount_currency": float(amount),
            "quantity": 1.0,
            "employee_id": emp["id"],
            "payment_mode": "company_account",   # Paid By = Company
        }])

        # 2. Attach the receipt image, if provided
        if photo_bytes:
            import base64 as _b64
            _n = (photo_name or "").lower()
            mt = ("application/pdf" if _n.endswith(".pdf")
                  else "image/png" if _n.endswith(".png") else "image/jpeg")
            odoo(uid, pwd, "ir.attachment", "create", [{
                "name": photo_name,
                "res_model": "hr.expense",
                "res_id": exp_id,
                "datas": _b64.b64encode(photo_bytes).decode(),
                "mimetype": mt,
            }])

        # 3. Create the expense report (sheet) holding this expense
        sheet_id = odoo(uid, pwd, "hr.expense.sheet", "create", [{
            "name": description,
            "employee_id": emp["id"],
            "expense_line_ids": [(6, 0, [exp_id])],
            "payment_mode": "company_account",
        }])

        # 4. Submit the report to the manager for approval
        submitted = False
        try:
            odoo(uid, pwd, "hr.expense.sheet", "action_submit_sheet", [[sheet_id]])
            submitted = True
        except Exception as e:
            if "cannot marshal None" in str(e):
                submitted = True
            else:
                # Fall back to setting the state directly
                try:
                    odoo(uid, pwd, "hr.expense.sheet", "write", [[sheet_id], {"state": "submit"}])
                    submitted = True
                except Exception:
                    pass

        if submitted:
            return True, "تم تسجيل المصروف وإرساله للاعتماد ✓"
        return True, "تم تسجيل المصروف (لم يُرسل للاعتماد — أرسله من أودو)"
    except Exception as e:
        return False, _clean_odoo_error(e)


# ── PENDING STOCK MOVEMENTS (production oversight) ───────────
def get_pending_movements(uid, pwd):
    """Unfinalized transfers + PO receipts awaiting action, for the
    production home tab. Returns two lists with per-line context."""
    PSTATE = {"assigned": ("جاهز", "#7FB069"), "confirmed": ("بانتظار", "#D4A853"),
              "waiting": ("ينتظر عملية", "#9BA58F"), "draft": ("مسودة", "#9BA58F")}

    def _pack(p):
        loc = p["location_id"][1].split("/")[-1] if p.get("location_id") else "?"
        dest = p["location_dest_id"][1].split("/")[-1] if p.get("location_dest_id") else "?"
        label, color = PSTATE.get(p["state"], (p["state"], "#9BA58F"))
        return {
            "id": p["id"], "name": p["name"],
            "state": p["state"], "state_ar": label, "color": color,
            "route": f"{loc} → {dest}",
            "type": p["picking_type_id"][1].split(":")[-1].strip() if p.get("picking_type_id") else "",
            "partner": p["partner_id"][1] if p.get("partner_id") else "",
            "origin": p.get("origin") or "",
            "date": (p.get("scheduled_date") or "")[:10],
        }

    transfers = odoo(uid, pwd, "stock.picking", "search_read",
        [[["picking_type_id.code", "=", "internal"], ["state", "not in", ["done", "cancel"]]]],
        {"fields": ["id", "name", "state", "picking_type_id", "location_id",
                    "location_dest_id", "scheduled_date"],
         "limit": 200, "order": "scheduled_date asc"})
    receipts = odoo(uid, pwd, "stock.picking", "search_read",
        [[["picking_type_id.code", "=", "incoming"], ["state", "not in", ["done", "cancel"]]]],
        {"fields": ["id", "name", "state", "partner_id", "origin", "scheduled_date",
                    "picking_type_id", "location_id", "location_dest_id"],
         "limit": 200, "order": "scheduled_date asc"})
    return {
        "transfers": [_pack(p) for p in transfers],
        "receipts": [_pack(p) for p in receipts],
    }


def get_pending_receipts(uid, pwd):
    """Incoming purchase receipts waiting to be received (Partner → RM-Receiving)."""
    picks = odoo(uid, pwd, "stock.picking", "search_read",
        [[["picking_type_id.code", "=", "incoming"],
          ["state", "in", ["assigned", "confirmed"]]]],
        {"fields": ["id", "name", "partner_id", "origin", "state", "scheduled_date"],
         "limit": 20, "order": "scheduled_date"})
    out = []
    for p in picks:
        moves = odoo(uid, pwd, "stock.move", "search_read",
            [[["picking_id", "=", p["id"]], ["state", "not in", ["done", "cancel"]]]],
            {"fields": ["product_id", "product_uom_qty"]})
        out.append({
            "id": p["id"], "name": p["name"],
            "supplier": p["partner_id"][1] if p["partner_id"] else "—",
            "po": p.get("origin") or "—",
            "date": (p.get("scheduled_date") or "")[:10],
            "lines": [{"name": m["product_id"][1], "qty": m["product_uom_qty"]} for m in moves],
        })
    return out


def validate_picking(uid, pwd, picking_id):
    """Receive/validate a transfer in full. Returns (ok, message)."""
    try:
        moves = odoo(uid, pwd, "stock.move", "search_read",
            [[["picking_id", "=", picking_id], ["state", "not in", ["done", "cancel"]]]],
            {"fields": ["id", "product_uom_qty"]})
        for m in moves:  # full quantities → no backorder wizard
            odoo(uid, pwd, "stock.move", "write",
                 [[m["id"]], {"quantity": m["product_uom_qty"], "picked": True}])
        odoo(uid, pwd, "stock.picking", "button_validate", [[picking_id]])
        return True, "تم الاستلام ✓"
    except Exception as e:
        if "cannot marshal None" in str(e):
            return True, "تم الاستلام ✓"
        return False, _clean_odoo_error(e)


def get_products_at_location(uid, pwd, loc_id, categ_id=None):
    """Products with stock at a location — for the transfer picker.
    If categ_id is given, only products in that product category (e.g.
    Finished Goods) are returned."""
    quants = odoo(uid, pwd, "stock.quant", "search_read",
        [[["location_id", "=", loc_id], ["quantity", ">", 0]]],
        {"fields": ["product_id", "quantity"], "limit": 200})
    agg = defaultdict(float)
    pid_map = {}
    for q in quants:
        agg[q["product_id"][1]] += q["quantity"]
        pid_map[q["product_id"][1]] = q["product_id"][0]
    # Restrict to a product category if requested (e.g. Finished Goods only)
    if categ_id is not None and pid_map:
        allowed = odoo(uid, pwd, "product.product", "search",
            [[["id", "in", list(pid_map.values())], ["categ_id", "child_of", categ_id]]])
        allowed_set = set(allowed)
        return [{"id": pid_map[n], "name": n, "available": round(v, 2)}
                for n, v in agg.items() if pid_map[n] in allowed_set]
    return [{"id": pid_map[n], "name": n, "available": round(v, 2)}
            for n, v in sorted(agg.items(), key=lambda x: -x[1])]


def create_transfer(uid, pwd, route_key, product_id, qty):
    """Create an internal transfer on a preset route.
    For routes marked two_step=True, the transfer is created and confirmed
    but NOT validated — it waits for the destination site to receive it
    (a real handoff). Otherwise it auto-completes on creation.
    Returns (ok, message)."""
    r = TRANSFER_ROUTES[route_key]
    two_step = r.get("two_step", False)
    try:
        pick_id = odoo(uid, pwd, "stock.picking", "create", [{
            "picking_type_id": r["type_id"],
            "location_id": r["src"],
            "location_dest_id": r["dest"],
        }])
        odoo(uid, pwd, "stock.move", "create", [{
            "picking_id": pick_id,
            "product_id": product_id,
            "product_uom_qty": qty,
            "location_id": r["src"],
            "location_dest_id": r["dest"],
            "name": "transfer",
        }])
        try:
            odoo(uid, pwd, "stock.picking", "action_confirm", [[pick_id]])
        except Exception as e:
            if "cannot marshal None" not in str(e):
                raise
        # Reserve stock so the transfer is ready to be received
        try:
            odoo(uid, pwd, "stock.picking", "action_assign", [[pick_id]])
        except Exception as e:
            if "cannot marshal None" not in str(e):
                raise
        name = odoo(uid, pwd, "stock.picking", "read", [[pick_id]], {"fields": ["name"]})
        pname = name[0]["name"] if name else ""
        if two_step:
            # Stop here — destination site receives it in the Operations tab
            return True, f"تم إنشاء التحويل ✓ ({pname}) — بانتظار الاستلام في حي دمشق"
        # One-step routes: validate immediately
        ok, msg = validate_picking(uid, pwd, pick_id)
        if ok:
            return True, f"تم التحويل ✓ ({pname})"
        return ok, msg
    except Exception as e:
        return False, _clean_odoo_error(e)


def get_running_map(uid, pwd):
    """{mo_id: worker_first_name} for every MO with a live timer — 2 queries."""
    logs = odoo(uid, pwd, "mrp.workcenter.productivity", "search_read",
        [[["date_end", "=", False]]], {"fields": ["workorder_id", "user_id"]})
    if not logs:
        return {}
    wo_ids = list({l["workorder_id"][0] for l in logs if l.get("workorder_id")})
    wos = odoo(uid, pwd, "mrp.workorder", "read", [wo_ids], {"fields": ["production_id"]})
    wo_to_mo = {w["id"]: w["production_id"][0] for w in wos if w.get("production_id")}
    out = {}
    for l in logs:
        if not l.get("workorder_id"):
            continue
        mo_id = wo_to_mo.get(l["workorder_id"][0])
        if mo_id:
            out[mo_id] = l["user_id"][1].split(" ")[0] if l.get("user_id") else "…"
    return out


def mo_start_work(uid, pwd, mo_id):
    """Start the timer on the first startable stage of the MO."""
    wos = odoo(uid, pwd, "mrp.workorder", "search_read",
        [[["production_id", "=", mo_id], ["state", "in", ["ready", "progress", "waiting", "pending"]]]],
        {"fields": ["id", "name"], "order": "id"})
    for w in wos:
        open_log = odoo(uid, pwd, "mrp.workcenter.productivity", "search_count",
            [[["workorder_id", "=", w["id"]], ["date_end", "=", False]]])
        if open_log:
            continue  # already running
        ok, msg = wo_start(uid, pwd, w["id"])
        if ok:
            return True, f"بدأ المؤقّت: {w['name']}"
        return ok, msg
    return False, "كل المراحل تعمل بالفعل أو منتهية"


def mo_validate(uid, pwd, mo_id):
    """Mark the whole MO done. Returns (ok, message)."""
    try:
        odoo(uid, pwd, "mrp.production", "button_mark_done", [[mo_id]])
        return True, "تم إنهاء أمر التصنيع"
    except Exception as e:
        if "cannot marshal None" in str(e):
            return True, "تم إنهاء أمر التصنيع"
        return False, _clean_odoo_error(e)


def mo_confirm(uid, pwd, mo_id):
    """Confirm a draft MO. Returns (ok, message)."""
    try:
        odoo(uid, pwd, "mrp.production", "action_confirm", [[mo_id]])
        return True, "تم التأكيد"
    except Exception as e:
        if "cannot marshal None" in str(e):
            return True, "تم التأكيد"
        return False, _clean_odoo_error(e)


# ── WORK ORDER TIME TRACKING (start/stop) ────────────────────
def get_workorders(uid, pwd, product_filter=None):
    """Work orders with live time tracking. Optionally filter by product."""
    domain = [["state", "in", ["ready", "progress", "pending", "waiting"]]]
    wos = odoo(uid, pwd, "mrp.workorder", "search_read", [domain],
        {"fields": ["id", "name", "state", "is_user_working", "duration",
                    "duration_expected", "production_id", "product_id",
                    "qty_produced", "qty_producing", "workcenter_id", "date_start"],
         "limit": 50, "order": "date_start desc"})
    out = []
    for w in wos:
        pname = w["product_id"][1] if w.get("product_id") else "—"
        if product_filter and product_filter.lower() not in pname.lower():
            continue
        out.append({
            "id": w["id"], "name": w["name"],
            "state": w["state"],
            "working": w["is_user_working"],
            "duration": round(w["duration"], 1),
            "expected": round(w["duration_expected"], 1),
            "mo": w["production_id"][1] if w.get("production_id") else "—",
            "product": pname,
            "qty": w.get("qty_produced", 0),
            "workcenter": w["workcenter_id"][1] if w.get("workcenter_id") else "",
        })
    return out


def _wo_button(uid, pwd, wo_id, method, ok_msg):
    """Call a workorder button; Odoo buttons return None which XML-RPC
    can't marshal — that 'error' actually means success."""
    try:
        odoo(uid, pwd, "mrp.workorder", method, [[wo_id]])
        return True, ok_msg
    except Exception as e:
        if "cannot marshal None" in str(e):
            return True, ok_msg  # action succeeded; None return is the quirk
        return False, _clean_odoo_error(e)


def wo_start(uid, pwd, wo_id):
    return _wo_button(uid, pwd, wo_id, "button_start", "بدأ العمل")


def wo_stop(uid, pwd, wo_id):
    return _wo_button(uid, pwd, wo_id, "button_pending", "تم الإيقاف")


def wo_finish(uid, pwd, wo_id):
    return _wo_button(uid, pwd, wo_id, "button_finish", "تم الإنهاء")


def _clean_odoo_error(e):
    """Turn a raw Odoo XML-RPC fault into a short readable message."""
    msg = str(e)
    if 'type "view"' in msg or "view (SJ)" in msg or "view (HD)" in msg:
        return "خطأ في إعداد المخازن: الموقع المصدر نوعه 'view' — يحتاج مود ضبط مسارات المخزن."
    if "already done or cancelled" in msg:
        return "أمر الشغل منتهي أو ملغي — لا يمكن بدء المؤقّت."
    if "reserved" in msg.lower() or "reservation" in msg.lower():
        return "المكوّنات غير محجوزة بعد — تحقّق من توفر المواد."
    if "UserError" in msg:
        import re
        m = re.search(r"UserError\('([^']+)'", msg)
        if m:
            return m.group(1)[:150]
    # Extract the Fault text
    import re
    m = re.search(r"Fault \d+: '([^']+)'", msg)
    if m:
        return m.group(1)[:150]
    return msg[:150]


def get_time_by_product(uid, pwd):
    """Aggregate real production time per product (from finished WOs)."""
    wos = odoo(uid, pwd, "mrp.workorder", "search_read",
        [[["state", "=", "done"], ["duration", ">", 0]]],
        {"fields": ["product_id", "duration", "duration_expected", "qty_produced"], "limit": 500})
    agg = defaultdict(lambda: {"actual": 0, "expected": 0, "qty": 0, "count": 0})
    for w in wos:
        if not w.get("product_id"):
            continue
        name = w["product_id"][1]
        agg[name]["actual"] += w["duration"]
        agg[name]["expected"] += w.get("duration_expected", 0)
        agg[name]["qty"] += w.get("qty_produced", 0)
        agg[name]["count"] += 1
    out = []
    for name, v in sorted(agg.items(), key=lambda x: -x[1]["actual"]):
        out.append({
            "product": name,
            "actual_min": round(v["actual"], 1),
            "expected_min": round(v["expected"], 1),
            "runs": v["count"],
            "efficiency": round(v["expected"] / v["actual"] * 100) if v["actual"] else 0,
        })
    return out[:20]


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


# ── PROCUREMENT: PO management (mirrors MO module) ───────────
PO_STATE = {
    "draft":    {"ar": "طلب عرض",  "color": "#9BA58F", "bg": "rgba(255,255,255,.08)"},
    "sent":     {"ar": "مُرسل",    "color": "#D4A853", "bg": "rgba(212,168,83,.14)"},
    "purchase": {"ar": "مؤكد",     "color": "#7FB069", "bg": "rgba(127,176,105,.15)"},
    "done":     {"ar": "مُغلق",    "color": "#9BA58F", "bg": "rgba(255,255,255,.06)"},
    "cancel":   {"ar": "ملغي",     "color": "#E07070", "bg": "rgba(224,112,112,.12)"},
}
RECEIPT_STATE = {"full": "مُستلم", "partial": "جزئي", "pending": "بانتظار", "nothing": "لم يُستلم"}


def get_pos(uid, pwd, state="all", query=""):
    """Purchase orders list with filter + search."""
    domain = []
    if state != "all":
        domain.append(["state", "=", state])
    if query:
        domain += ["|", ["name", "ilike", query], ["partner_id.name", "ilike", query]]
    pos = odoo(uid, pwd, "purchase.order", "search_read", [domain],
        {"fields": ["id", "name", "partner_id", "state", "amount_total", "currency_id",
                    "date_order", "receipt_status", "invoice_status"],
         "limit": 200, "order": "date_order desc"})
    return [{
        "id": p["id"], "name": p["name"],
        "supplier": p["partner_id"][1] if p.get("partner_id") else "—",
        "state": p["state"], "total": p["amount_total"],
        "currency": p["currency_id"][1] if p.get("currency_id") else "LYD",
        "date": (p.get("date_order") or "")[:10],
        "receipt": p.get("receipt_status") or "",
        "invoice": p.get("invoice_status") or "",
    } for p in pos]


def get_po_detail(uid, pwd, po_id):
    """Full PO: supplier, lines with received qty, totals, linked receipts."""
    p = odoo(uid, pwd, "purchase.order", "read", [[po_id]],
        {"fields": ["name", "partner_id", "state", "amount_total", "amount_untaxed",
                    "currency_id", "date_order", "date_planned", "order_line",
                    "receipt_status", "invoice_status", "notes"]})
    if not p:
        return None
    p = p[0]
    lines = []
    if p.get("order_line"):
        recs = odoo(uid, pwd, "purchase.order.line", "read", [p["order_line"]],
            {"fields": ["product_id", "product_qty", "qty_received", "price_unit", "price_subtotal"]})
        for l in recs:
            lines.append({
                "name": l["product_id"][1] if l.get("product_id") else "—",
                "qty": l["product_qty"], "received": l.get("qty_received", 0),
                "price": l["price_unit"], "subtotal": l["price_subtotal"],
            })
    # Linked receipts (incoming pickings)
    receipts = odoo(uid, pwd, "stock.picking", "search_read",
        [[["origin", "=", p["name"]], ["picking_type_id.code", "=", "incoming"]]],
        {"fields": ["name", "state"], "limit": 10})
    return {
        "id": po_id, "name": p["name"],
        "supplier": p["partner_id"][1] if p.get("partner_id") else "—",
        "state": p["state"], "total": p["amount_total"], "untaxed": p["amount_untaxed"],
        "currency": p["currency_id"][1] if p.get("currency_id") else "LYD",
        "date": (p.get("date_order") or "")[:16],
        "planned": (p.get("date_planned") or "")[:10],
        "receipt": p.get("receipt_status") or "",
        "invoice": p.get("invoice_status") or "",
        "lines": lines, "receipts": receipts,
    }


def po_confirm(uid, pwd, po_id, create_bill=True):
    """Confirm a purchase order (button_confirm). If create_bill, also generate
    the vendor bill (account.move) — created as a DRAFT only. It is never
    posted and never paid here; posting/payment stays a deliberate accounting
    step done in Odoo after the invoice is reviewed. Returns (ok, msg)."""
    try:
        try:
            odoo(uid, pwd, "purchase.order", "button_confirm", [[po_id]])
        except Exception as e:
            if "cannot marshal None" not in str(e):
                raise
        if create_bill:
            try:
                odoo(uid, pwd, "purchase.order", "action_create_invoice", [[po_id]])
            except Exception as be:
                if "cannot marshal None" not in str(be):
                    # PO confirmed but bill failed — report partial success clearly
                    return True, "تم تأكيد أمر الشراء ✓ (تعذّر إنشاء الفاتورة: " + _clean_odoo_error(be) + ")"
            # Ensure any bill we just created is left as a DRAFT (not posted/paid)
            po = odoo(uid, pwd, "purchase.order", "read", [[po_id]],
                {"fields": ["invoice_ids", "invoice_count"]})
            bill_ids = po[0].get("invoice_ids", []) if po else []
            if bill_ids:
                bills = odoo(uid, pwd, "account.move", "read", [bill_ids],
                    {"fields": ["state"]})
                # If any bill is not in draft, pull it back to draft so confirming
                # a PO never results in a posted/paid bill.
                for b in bills:
                    if b.get("state") == "posted":
                        try:
                            odoo(uid, pwd, "account.move", "button_draft", [[b["id"]]])
                        except Exception:
                            pass
                return True, "تم تأكيد أمر الشراء وإنشاء الفاتورة (مسودة) ✓"
        return True, "تم تأكيد أمر الشراء ✓"
    except Exception as e:
        if "cannot marshal None" in str(e):
            return True, "تم تأكيد أمر الشراء ✓"
        return False, _clean_odoo_error(e)


def po_cancel(uid, pwd, po_id):
    """Cancel a purchase order. Also cancels any linked draft vendor bill so
    cancelling doesn't leave an orphan invoice."""
    try:
        # Cancel linked draft/posted bills first
        po = odoo(uid, pwd, "purchase.order", "read", [[po_id]], {"fields": ["invoice_ids"]})
        bill_ids = po[0].get("invoice_ids", []) if po else []
        for bid in bill_ids:
            try:
                odoo(uid, pwd, "account.move", "button_cancel", [[bid]])
            except Exception:
                pass
        odoo(uid, pwd, "purchase.order", "button_cancel", [[po_id]])
        return True, "تم الإلغاء"
    except Exception as e:
        if "cannot marshal None" in str(e):
            return True, "تم الإلغاء"
        return False, _clean_odoo_error(e)


# ── PROCUREMENT: RFQ creation + payment lifecycle ────────────
def get_suppliers(uid, pwd, query=""):
    domain = [["supplier_rank", ">", 0]]
    if query:
        domain.append(["name", "ilike", query])
    sups = odoo(uid, pwd, "res.partner", "search_read", [domain],
        {"fields": ["id", "name"], "limit": 40, "order": "name"})
    return [{"id": s["id"], "name": s["name"]} for s in sups]


def get_purchasable_products(uid, pwd):
    prods = odoo(uid, pwd, "product.product", "search_read",
        [[["purchase_ok", "=", True]]],
        {"fields": ["id", "name", "default_code", "standard_price"], "order": "name"})
    return [{"id": p["id"], "name": p["name"],
             "code": p.get("default_code") or "",
             "cost": p.get("standard_price", 0)} for p in prods]


def attach_po_photo(uid, pwd, po_id, photo_bytes, photo_name="po_document.jpg"):
    """Attach a document (image or PDF) to a purchase order. Returns (ok, msg)."""
    try:
        import base64 as _b64
        n = (photo_name or "").lower()
        mt = ("application/pdf" if n.endswith(".pdf")
              else "image/png" if n.endswith(".png")
              else "image/jpeg")
        odoo(uid, pwd, "ir.attachment", "create", [{
            "name": photo_name,
            "res_model": "purchase.order",
            "res_id": po_id,
            "datas": _b64.b64encode(photo_bytes).decode(),
            "mimetype": mt,
        }])
        return True, "تم إرفاق المستند ✓"
    except Exception as e:
        return False, _clean_odoo_error(e)


def get_expense_attachments(uid, pwd, expense_id):
    """Receipts attached to an expense."""
    atts = odoo(uid, pwd, "ir.attachment", "search_read",
        [[["res_model", "=", "hr.expense"], ["res_id", "=", expense_id]]],
        {"fields": ["id", "name", "create_date", "mimetype"], "order": "id desc"})
    return [{
        "id": a["id"], "name": a["name"],
        "date": (a.get("create_date") or "")[:10],
        "mimetype": a.get("mimetype") or "",
    } for a in atts]


def attach_expense_receipt(uid, pwd, expense_id, photo_bytes, photo_name="receipt.jpg",
                           replace=False):
    """Attach a receipt to an expense. If replace=True, existing receipts are
    removed first. Returns (ok, msg)."""
    try:
        import base64 as _b64
        if replace:
            old = odoo(uid, pwd, "ir.attachment", "search",
                [[["res_model", "=", "hr.expense"], ["res_id", "=", expense_id]]])
            if old:
                odoo(uid, pwd, "ir.attachment", "unlink", [old])
        n = (photo_name or "").lower()
        mt = ("application/pdf" if n.endswith(".pdf")
              else "image/png" if n.endswith(".png")
              else "image/jpeg")
        odoo(uid, pwd, "ir.attachment", "create", [{
            "name": photo_name,
            "res_model": "hr.expense",
            "res_id": expense_id,
            "datas": _b64.b64encode(photo_bytes).decode(),
            "mimetype": mt,
        }])
        return True, ("تم استبدال الإيصال ✓" if replace else "تم إرفاق الإيصال ✓")
    except Exception as e:
        return False, _clean_odoo_error(e)


def delete_expense_receipt(uid, pwd, attachment_id):
    """Remove a receipt attachment. Returns (ok, msg)."""
    try:
        odoo(uid, pwd, "ir.attachment", "unlink", [[attachment_id]])
        return True, "تم حذف الإيصال ✓"
    except Exception as e:
        return False, _clean_odoo_error(e)


def get_po_attachments(uid, pwd, po_id):
    """List document attachments on a PO."""
    atts = odoo(uid, pwd, "ir.attachment", "search_read",
        [[["res_model", "=", "purchase.order"], ["res_id", "=", po_id]]],
        {"fields": ["name", "create_date"], "limit": 20, "order": "id desc"})
    return [{"name": a["name"], "date": (a.get("create_date") or "")[:10]} for a in atts]


def create_rfq(uid, pwd, supplier_id, lines):
    """Create a draft RFQ. lines = [(product_id, qty, price), ...].
    Returns (ok, po_id_or_msg)."""
    try:
        order_lines = [(0, 0, {
            "product_id": pid, "product_qty": qty, "price_unit": price,
        }) for pid, qty, price in lines if qty > 0]
        if not order_lines:
            return False, "أضف منتجاً واحداً على الأقل"
        po_id = odoo(uid, pwd, "purchase.order", "create", [{
            "partner_id": supplier_id,
            "order_line": order_lines,
        }])
        name = odoo(uid, pwd, "purchase.order", "read", [[po_id]], {"fields": ["name"]})
        return True, {"id": po_id, "name": name[0]["name"]}
    except Exception as e:
        return False, _clean_odoo_error(e)


def create_vendor(uid, pwd, name, phone="", email="", city=""):
    """Create a new supplier/vendor contact. Returns (ok, id_or_msg).
    Odoo requires 'mobile' on contacts, so mobile defaults to phone."""
    try:
        if not name or not name.strip():
            return False, "اسم المورّد مطلوب"
        vals = {"name": name.strip(), "supplier_rank": 1, "company_type": "company"}
        if phone:
            vals["phone"] = phone
            vals["mobile"] = phone  # Odoo constraint: mobile required
        if email:
            vals["email"] = email
        if city:
            vals["city"] = city
        vid = odoo(uid, pwd, "res.partner", "create", [vals])
        return True, vid
    except Exception as e:
        return False, _clean_odoo_error(e)


def send_rfq(uid, pwd, po_id):
    """Submit an RFQ — moves draft → sent (marks it formally issued to the
    supplier). Returns (ok, msg)."""
    try:
        # button_confirm would jump to purchase; to just 'send' we set state=sent
        odoo(uid, pwd, "purchase.order", "write", [[po_id], {"state": "sent"}])
        return True, "تم إرسال طلب العرض ✓"
    except Exception as e:
        return False, _clean_odoo_error(e)


def get_po_payment(uid, pwd, po_id):
    """Payment/bill status for a PO — drives the payment step UI."""
    p = odoo(uid, pwd, "purchase.order", "read", [[po_id]],
        {"fields": ["invoice_ids", "invoice_status", "state", "amount_total"]})
    if not p:
        return None
    p = p[0]
    PAY = {"not_paid": "لم يُدفع", "in_payment": "قيد الدفع", "paid": "مدفوع",
           "partial": "مدفوع جزئياً", "reversed": "معكوس", "blocked": "محظور"}
    bills = []
    if p.get("invoice_ids"):
        recs = odoo(uid, pwd, "account.move", "read", [p["invoice_ids"]],
            {"fields": ["name", "state", "payment_state", "amount_total", "amount_residual"]})
        for b in recs:
            bills.append({
                "id": b["id"], "name": b["name"] if b.get("name") else "فاتورة مسودة",
                "state": b["state"],
                "payment": b.get("payment_state") or "not_paid",
                "payment_ar": PAY.get(b.get("payment_state"), b.get("payment_state") or "—"),
                "total": b["amount_total"], "residual": b.get("amount_residual", 0),
            })
    return {
        "invoice_status": p.get("invoice_status"),
        "can_bill": p["state"] == "purchase" and p.get("invoice_status") == "to invoice",
        "bills": bills,
        "total": p["amount_total"],
    }


def create_bill(uid, pwd, po_id):
    """Create the vendor bill from a confirmed PO. Returns (ok, msg)."""
    try:
        odoo(uid, pwd, "purchase.order", "action_create_invoice", [[po_id]])
        return True, "تم إنشاء الفاتورة ✓"
    except Exception as e:
        if "cannot marshal None" in str(e):
            return True, "تم إنشاء الفاتورة ✓"
        return False, _clean_odoo_error(e)


def confirm_payment(uid, pwd, bill_id):
    """Post the bill then mark as paid (register full payment). Returns (ok, msg)."""
    from datetime import date
    try:
        # Ensure the required Bill Date is set before posting
        bill = odoo(uid, pwd, "account.move", "read", [[bill_id]],
                    {"fields": ["state", "payment_state", "invoice_date"]})
        if bill and bill[0]["state"] == "draft":
            if not bill[0].get("invoice_date"):
                odoo(uid, pwd, "account.move", "write",
                     [[bill_id], {"invoice_date": str(date.today())}])
            try:
                odoo(uid, pwd, "account.move", "action_post", [[bill_id]])
            except Exception as e:
                if "cannot marshal None" not in str(e):
                    raise
        # Register payment via the payment register wizard (needs active_ids
        # context on BOTH create and action, plus a payment_date)
        ctx = {"active_model": "account.move", "active_ids": [bill_id], "active_id": bill_id}
        try:
            wiz = odoo(uid, pwd, "account.payment.register", "create",
                       [{"payment_date": str(date.today())}], {"context": ctx})
            odoo(uid, pwd, "account.payment.register", "action_create_payments",
                 [[wiz]], {"context": ctx})
        except Exception as e:
            if "cannot marshal None" not in str(e):
                return False, _clean_odoo_error(e)
        b2 = odoo(uid, pwd, "account.move", "read", [[bill_id]], {"fields": ["payment_state"]})
        if b2 and b2[0]["payment_state"] in ("paid", "in_payment"):
            return True, "تم تأكيد الدفع ✓"
        return True, "تم تسجيل الدفع"
    except Exception as e:
        return False, _clean_odoo_error(e)


# ── OPERATIONS ───────────────────────────────────────────────
# ── OPERATIONS: two-stage delivery flow ──────────────────────
# Stage 1: Pick From FG to Alyamama (type 3, internal) — ready/waiting to send
# Stage 2: Delivery by Alyamam (type 41, outgoing) → Yamamah API tracks it

# Sort options shared by all Operations lists.
# date_* is applied server-side; qty_desc is applied client-side on the
# loaded page (sum of product quantities per picking).
_OPS_ORDER = {
    "date_asc":  "scheduled_date asc, id asc",    # الأقدم أولاً
    "date_desc": "scheduled_date desc, id desc",  # الأحدث أولاً
}


def _pick_qty_map(uid, pwd, pick_ids):
    """Total demanded product qty per picking — one read_group call."""
    if not pick_ids:
        return {}
    try:
        groups = odoo(uid, pwd, "stock.move", "read_group",
            [[["picking_id", "in", pick_ids]], ["product_uom_qty"], ["picking_id"]])
        return {g["picking_id"][0]: g.get("product_uom_qty") or 0
                for g in groups if g.get("picking_id")}
    except Exception:
        return {}
def get_sj_to_hd_transfers(uid, pwd, state="ready", query="", limit=200, sort="date_asc"):
    """Finished-goods transfers made at SJ by production, moving to HD.
    picking_type 57: SJ/FG-Storage -> HD/FG-Storage. Operations receives them.
    Default shows ready-to-receive (not done); 'all' includes received."""
    domain = [["picking_type_id", "=", 57]]
    if state == "ready":
        domain.append(["state", "in", ["assigned", "confirmed", "waiting"]])
    elif state != "all":
        domain.append(["state", "=", state])
    if query:
        domain += ["|", ["name", "ilike", query], ["origin", "ilike", query]]
    total = odoo(uid, pwd, "stock.picking", "search_count", [domain])
    picks = odoo(uid, pwd, "stock.picking", "search_read", [domain],
        {"fields": ["id", "name", "state", "origin", "scheduled_date", "partner_id"],
         "limit": limit, "order": _OPS_ORDER.get(sort, _OPS_ORDER["date_asc"])})
    qmap = _pick_qty_map(uid, pwd, [p["id"] for p in picks])
    rows = [{
        "id": p["id"], "name": p["name"], "state": p["state"],
        "order": p.get("origin") or "—",
        "date": (p.get("scheduled_date") or "")[:10],
        "qty": qmap.get(p["id"], 0),
    } for p in picks]
    if sort == "qty_desc":
        rows.sort(key=lambda r: r["qty"], reverse=True)
    out = PagedList(rows)
    out.total = total
    out.shown = len(picks)
    return out


def get_yamamah_returns(uid, pwd, state="ready", query="", limit=200, sort="date_asc"):
    """Returns coming back from Yamamah/Alyamama into HD stock.
    picking_type 60: Alyamama WH -> HD/FG-Storage. Operations validates them
    to receive returned goods back into inventory.
    Default shows pending (not done); 'all' includes validated."""
    domain = [["picking_type_id", "=", 60]]
    if state == "ready":
        domain.append(["state", "in", ["assigned", "confirmed", "waiting"]])
    elif state != "all":
        domain.append(["state", "=", state])
    if query:
        domain += ["|", ["name", "ilike", query], ["origin", "ilike", query]]
    total = odoo(uid, pwd, "stock.picking", "search_count", [domain])
    picks = odoo(uid, pwd, "stock.picking", "search_read", [domain],
        {"fields": ["id", "name", "state", "origin", "scheduled_date", "partner_id"],
         "limit": limit, "order": _OPS_ORDER.get(sort, _OPS_ORDER["date_asc"])})
    qmap = _pick_qty_map(uid, pwd, [p["id"] for p in picks])
    rows = [{
        "id": p["id"], "name": p["name"], "state": p["state"],
        "origin": p.get("origin") or "—",
        "customer": p["partner_id"][1] if p.get("partner_id") else "—",
        "date": (p.get("scheduled_date") or "")[:10],
        "qty": qmap.get(p["id"], 0),
    } for p in picks]
    if sort == "qty_desc":
        rows.sort(key=lambda r: r["qty"], reverse=True)
    out = PagedList(rows)
    out.total = total
    out.shown = len(picks)
    return out


def get_fg_to_yamamah(uid, pwd, state="ready", query="", limit=200, sort="date_asc"):
    """Stage 1 pickings: FG → Alyamama warehouse. Default ready+waiting."""
    domain = [["picking_type_id", "=", 3]]
    if state == "ready":
        domain.append(["state", "in", ["assigned", "confirmed", "waiting"]])
    elif state != "all":
        domain.append(["state", "=", state])
    if query:
        domain += ["|", "|", ["name", "ilike", query], ["origin", "ilike", query],
                   ["accurate_shipment_code", "ilike", query]]
    total = odoo(uid, pwd, "stock.picking", "search_count", [domain])
    picks = odoo(uid, pwd, "stock.picking", "search_read", [domain],
        {"fields": ["id", "name", "state", "origin", "scheduled_date", "partner_id",
                    "accurate_shipment_code", "accurate_tracking_url"],
         "limit": limit, "order": _OPS_ORDER.get(sort, _OPS_ORDER["date_asc"])})
    qmap = _pick_qty_map(uid, pwd, [p["id"] for p in picks])
    rows = [{
        "id": p["id"], "name": p["name"], "state": p["state"],
        "order": p.get("origin") or "—",
        "customer": p["partner_id"][1] if p.get("partner_id") else "—",
        "date": (p.get("scheduled_date") or "")[:10],
        "shipment_code": p.get("accurate_shipment_code") or "",
        "tracking_url": p.get("accurate_tracking_url") or "",
        "qty": qmap.get(p["id"], 0),
    } for p in picks]
    if sort == "qty_desc":
        rows.sort(key=lambda r: r["qty"], reverse=True)
    out = PagedList(rows)
    out.total = total
    out.shown = len(picks)
    return out


def get_picking_detail(uid, pwd, picking_id):
    """Full detail of a delivery picking for the Operations validate view —
    includes full recipient contact and per-line + total pricing pulled from
    the linked sale order."""
    p = odoo(uid, pwd, "stock.picking", "read", [[picking_id]],
        {"fields": ["name", "state", "origin", "partner_id", "scheduled_date",
                    "move_ids_without_package", "sale_id",
                    "accurate_shipment_code", "accurate_tracking_url", "accurate_status"]})
    if not p:
        return None
    p = p[0]
    moves = odoo(uid, pwd, "stock.move", "search_read",
        [[["picking_id", "=", picking_id]]],
        {"fields": ["product_id", "product_uom_qty", "quantity", "state"]})
    # Recipient contact (full)
    partner = None
    if p.get("partner_id"):
        pr = odoo(uid, pwd, "res.partner", "read", [[p["partner_id"][0]]],
            {"fields": ["name", "phone", "mobile", "street", "street2", "city",
                        "email"]})
        partner = pr[0] if pr else None
    # Pricing from the linked sale order (per-product unit price + order total)
    price_map = {}
    order_total = 0.0
    order_name = p.get("origin") or "—"
    if p.get("sale_id"):
        so = odoo(uid, pwd, "sale.order", "read", [[p["sale_id"][0]]],
            {"fields": ["name", "amount_total", "amount_untaxed"]})
        if so:
            order_total = so[0].get("amount_total", 0.0)
            order_name = so[0].get("name", order_name)
        so_lines = odoo(uid, pwd, "sale.order.line", "search_read",
            [[["order_id", "=", p["sale_id"][0]]]],
            {"fields": ["product_id", "price_unit", "price_subtotal", "product_uom_qty"]})
        for l in so_lines:
            if l.get("product_id"):
                price_map[l["product_id"][0]] = {
                    "unit": l.get("price_unit", 0.0),
                    "subtotal": l.get("price_subtotal", 0.0),
                }
    lines = []
    for m in moves:
        pid = m["product_id"][0]
        pr = price_map.get(pid, {})
        lines.append({
            "name": m["product_id"][1], "qty": m["product_uom_qty"],
            "done": m.get("quantity", 0), "state": m["state"],
            "unit_price": pr.get("unit", 0.0),
            "subtotal": pr.get("subtotal", m["product_uom_qty"] * pr.get("unit", 0.0)),
        })
    full_addr = ", ".join(x for x in [
        partner.get("street") if partner else None,
        partner.get("street2") if partner else None,
        partner.get("city") if partner else None] if x) if partner else "—"
    return {
        "id": picking_id, "name": p["name"], "state": p["state"],
        "order": order_name,
        "date": (p.get("scheduled_date") or "")[:16],
        "customer": partner["name"] if partner else "—",
        "phone": (partner.get("phone") if partner else "") or "—",
        "mobile": (partner.get("mobile") if partner else "") or "—",
        "email": (partner.get("email") if partner else "") or "—",
        "address": full_addr or "—",
        "order_total": order_total,
        "shipment_code": p.get("accurate_shipment_code") or "",
        "tracking_url": p.get("accurate_tracking_url") or "",
        "ship_status": p.get("accurate_status") or "",
        "lines": lines,
    }


def get_yamamah_to_customer(uid, pwd, api_status="all", query="", limit=200, sort="date_asc"):
    """Stage 2: shipments handed to Yamamah, tracked via Accurate API.
    Filters by the granular live API status (api_status_name).
    sort: date_asc (default) / date_desc server-side; qty_desc sorts the
    loaded page by total product qty on the linked sale order."""
    domain = []
    if api_status and api_status != "all":
        if api_status == "none":
            domain.append(["api_status_name", "=", False])
        else:
            domain.append(["api_status_name", "=", api_status])
    if query:
        domain += ["|", "|", "|", ["name", "ilike", query], ["code", "ilike", query],
                   ["recipient_name", "ilike", query], ["sale_id.name", "ilike", query]]
    order = "date desc, id desc" if sort == "date_desc" else "date asc, id asc"
    ships = odoo(uid, pwd, "accurate.shipment", "search_read", [domain],
        {"fields": ["id", "name", "code", "state", "api_status_name", "tracking_url",
                    "sale_id", "recipient_name", "recipient_mobile", "recipient_zone_id",
                    "fee_collection", "date"],
         "limit": limit, "order": order})
    total = odoo(uid, pwd, "accurate.shipment", "search_count", [domain])
    # Total product qty per linked sale order — one read_group call
    so_ids = list({s["sale_id"][0] for s in ships if s.get("sale_id")})
    qmap = {}
    if so_ids:
        try:
            groups = odoo(uid, pwd, "sale.order.line", "read_group",
                [[["order_id", "in", so_ids], ["display_type", "=", False]],
                 ["product_uom_qty"], ["order_id"]])
            qmap = {g["order_id"][0]: g.get("product_uom_qty") or 0
                    for g in groups if g.get("order_id")}
        except Exception:
            qmap = {}
    rows = [{
        "id": s["id"], "name": s["name"], "code": s.get("code", ""),
        "state": s["state"], "api_status": s.get("api_status_name") or "—",
        "tracking_url": s.get("tracking_url", ""),
        "order": s["sale_id"][1] if s.get("sale_id") else "—",
        "recipient": s.get("recipient_name", "—"),
        "mobile": s.get("recipient_mobile", ""),
        "zone": s["recipient_zone_id"][1] if s.get("recipient_zone_id") else "—",
        "cod": s.get("fee_collection", 0),
        "date": (s.get("date") or "")[:16],
        "qty": qmap.get(s["sale_id"][0], 0) if s.get("sale_id") else 0,
    } for s in ships]
    if sort == "qty_desc":
        rows.sort(key=lambda r: r["qty"], reverse=True)
    out = PagedList(rows)
    out.total = total
    out.shown = len(ships)
    return out


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


# ── SALES ORDERS + ACCURATE API ──────────────────────────────
SO_STATE = {
    "draft": {"ar": "مسودة", "color": "#9BA58F", "bg": "rgba(255,255,255,.08)"},
    "sent":  {"ar": "عرض سعر", "color": "#D4A853", "bg": "rgba(212,168,83,.14)"},
    "sale":  {"ar": "مؤكد", "color": "#7FB069", "bg": "rgba(127,176,105,.15)"},
    "done":  {"ar": "مُغلق", "color": "#9BA58F", "bg": "rgba(255,255,255,.06)"},
    "cancel":{"ar": "ملغي", "color": "#E07070", "bg": "rgba(224,112,112,.12)"},
}

# Shipment lifecycle from the SO's point of view — drives the guidance UI
def _shipment_stage(state, api_status):
    if not state:
        return ("none", "لم تُرسل ليمامة بعد", "#9BA58F")
    if state == "error":
        return ("error", "خطأ من واجهة يمامة — يحتاج إصلاح", "#E07070")
    if state == "draft":
        return ("draft", "مسودة شحنة — لم تُرسل", "#D4A853")
    if state in ("sent", "delivered", "returned"):
        return ("ok", api_status or "تم الإرسال", "#7FB069")
    return (state, api_status or state, "#9BA58F")


def _diagnose_accurate_error(msg):
    """Turn an Accurate API error into a guided fix. Returns (title, steps, fix_type)."""
    m = (msg or "").lower()
    if "recipient mobile" in m or "رقم الهاتف" in m or ("mobile" in m and "missing" in m):
        return ("رقم الجوال غير صالح",
                ["صيغة الرقم غير مقبولة لدى يمامة.",
                 "يجب أن يكون بصيغة دولية: ‎+218 9X XXXXXXX‎",
                 "صحّح رقم جوال المستلم أدناه ثم أعد الإرسال."],
                "mobile")
    if "sub-zone" in m or "price list" in m or "المنطقة" in m:
        return ("المنطقة الفرعية غير مغطّاة",
                ["المنطقة الفرعية المختارة ليست ضمن قائمة أسعار يمامة.",
                 "اختر منطقة فرعية أخرى مغطّاة، أو راجع يمامة.",
                 "عدّل المنطقة الفرعية أدناه ثم أعد الإرسال."],
                "subzone")
    if "cannot reach" in m or "internet" in m or "connection" in m or "تعذر" in m:
        return ("تعذّر الاتصال بخادم يمامة",
                ["مشكلة مؤقتة في الاتصال — لا يوجد خطأ في البيانات.",
                 "تحقّق من الإنترنت وأعد المحاولة."],
                "retry")
    return ("خطأ من واجهة يمامة",
            [msg or "خطأ غير معروف — راجع التفاصيل في أودو."],
            "generic")


def get_shipment_api_statuses(uid, pwd):
    """Distinct granular API statuses on shipments (for the Ops filter)."""
    sh = odoo(uid, pwd, "accurate.shipment", "search_read",
        [[["api_status_name", "!=", False]]],
        {"fields": ["api_status_name"], "limit": 2000})
    seen = {}
    for s in sh:
        name = s.get("api_status_name")
        if name:
            seen[name] = seen.get(name, 0) + 1
    return [name for name, _ in sorted(seen.items(), key=lambda x: -x[1])]


def get_shipment_statuses(uid, pwd):
    """Distinct shipment statuses currently in use (from the API), for the
    sales-order filter dropdown."""
    sos = odoo(uid, pwd, "sale.order", "search_read",
        [[["accurate_status_name", "!=", False]]],
        {"fields": ["accurate_status_name"], "limit": 1000})
    seen = {}
    for s in sos:
        name = s.get("accurate_status_name")
        if name:
            seen[name] = seen.get(name, 0) + 1
    # Sorted by frequency, most common first
    return [name for name, _ in sorted(seen.items(), key=lambda x: -x[1])]


def get_sales_orders(uid, pwd, state="sale", query="", ship_status="all", limit=200):
    domain = []
    if state != "all":
        domain.append(["state", "=", state])
    if ship_status and ship_status != "all":
        if ship_status == "none":
            domain.append(["accurate_status_name", "=", False])
        elif ship_status in SHORT_SHIP_STATUS:
            # Short clean status → the set of granular API statuses it covers
            names = SHORT_SHIP_STATUS[ship_status]["names"]
            domain.append(["accurate_status_name", "in", names])
        else:
            domain.append(["accurate_status_name", "=", ship_status])
    if query:
        domain += ["|", ["name", "ilike", query], ["partner_id.name", "ilike", query]]
    # True total for this filter (so the UI can say "showing X of Y")
    total = odoo(uid, pwd, "sale.order", "search_count", [domain])
    sos = odoo(uid, pwd, "sale.order", "search_read", [domain],
        {"fields": ["id", "name", "partner_id", "state", "amount_total",
                    "date_order", "accurate_shipment_count", "accurate_status_name",
                    "accurate_tracking_url"],
         "limit": limit, "order": "date_order desc"})
    out = []
    for s in sos:
        out.append({
            "id": s["id"], "name": s["name"],
            "customer": s["partner_id"][1] if s.get("partner_id") else "—",
            "state": s["state"], "total": s["amount_total"],
            "date": (s.get("date_order") or "")[:10],
            "ship_count": s.get("accurate_shipment_count", 0),
            "ship_status": s.get("accurate_status_name") or "",
            "has_tracking": bool(s.get("accurate_tracking_url")),
        })
    # Attach the true total so the UI can show "showing X of Y"
    class _OrderList(list):
        pass
    result = _OrderList(out)
    result.total = total
    result.shown = len(out)
    return result


def get_so_detail(uid, pwd, so_id):
    s = odoo(uid, pwd, "sale.order", "read", [[so_id]],
        {"fields": ["name", "partner_id", "state", "amount_total", "amount_untaxed",
                    "date_order", "order_line", "accurate_shipment_ids",
                    "accurate_tracking_url", "accurate_status_name"]})
    if not s:
        return None
    s = s[0]
    lines = []
    if s.get("order_line"):
        recs = odoo(uid, pwd, "sale.order.line", "read", [s["order_line"]],
            {"fields": ["product_id", "product_uom_qty", "price_unit", "price_subtotal"]})
        for l in recs:
            if l.get("product_id"):
                lines.append({"name": l["product_id"][1], "qty": l["product_uom_qty"],
                              "price": l["price_unit"], "subtotal": l["price_subtotal"]})
    # Shipment state + guidance
    shipment = None
    if s.get("accurate_shipment_ids"):
        sh = odoo(uid, pwd, "accurate.shipment", "read", [s["accurate_shipment_ids"]],
            {"fields": ["name", "code", "state", "api_status_name", "error_message",
                        "tracking_url", "recipient_mobile", "recipient_phone",
                        "recipient_name", "recipient_address",
                        "recipient_zone_id", "recipient_subzone_id"]})
        if sh:
            latest = sh[-1]
            stage, label, color = _shipment_stage(latest["state"], latest.get("api_status_name"))
            guidance = None
            if latest["state"] == "error":
                title, steps, fix_type = _diagnose_accurate_error(latest.get("error_message"))
                guidance = {"title": title, "steps": steps, "fix_type": fix_type,
                            "raw": latest.get("error_message", "")}
            shipment = {
                "id": latest["id"], "name": latest["name"], "code": latest.get("code", ""),
                "state": latest["state"], "stage": stage, "label": label, "color": color,
                "tracking_url": latest.get("tracking_url", ""),
                "mobile": latest.get("recipient_mobile", ""),
                "phone": latest.get("recipient_phone", ""),
                "recipient": latest.get("recipient_name", ""),
                "address": latest.get("recipient_address", ""),
                "zone": latest["recipient_zone_id"][1] if latest.get("recipient_zone_id") else "",
                "subzone": latest["recipient_subzone_id"][1] if latest.get("recipient_subzone_id") else "",
                "api_status": latest.get("api_status_name", ""),
                "guidance": guidance,
            }
    return {
        "id": so_id, "name": s["name"],
        "customer": s["partner_id"][1] if s.get("partner_id") else "—",
        "state": s["state"], "total": s["amount_total"],
        "date": (s.get("date_order") or "")[:16],
        "lines": lines, "shipment": shipment,
        "tracking_url": s.get("accurate_tracking_url", ""),
    }


def so_confirm(uid, pwd, so_id):
    try:
        odoo(uid, pwd, "sale.order", "action_confirm", [[so_id]])
        return True, "تم تأكيد الطلب ✓"
    except Exception as e:
        if "cannot marshal None" in str(e):
            return True, "تم تأكيد الطلب ✓"
        return False, _clean_odoo_error(e)


# ── SALES ORDER CREATION + shipment generation ───────────────
def search_customers(uid, pwd, query):
    """Live search across ALL Odoo contacts by phone or name.
    Normalizes digits so '944' matches '+218 94-4904735', '094...', etc.
    Returns up to 20 matches, most relevant first."""
    query = (query or "").strip()
    if len(query) < 2:
        return []
    digits = "".join(ch for ch in query if ch.isdigit())
    domain = []
    if digits and len(digits) >= 3:
        # Phone search: match on the raw digits. Odoo stores formatted numbers,
        # so we ilike the digit run; also try name in case they typed a name.
        domain = ["|", "|", "|",
                  ["phone", "ilike", digits],
                  ["mobile", "ilike", digits],
                  ["name", "ilike", query],
                  ["phone_sanitized", "ilike", digits]] if _has_sanitized(uid, pwd) else \
                 ["|", "|",
                  ["phone", "ilike", digits],
                  ["mobile", "ilike", digits],
                  ["name", "ilike", query]]
    else:
        domain = [["name", "ilike", query]]
    custs = odoo(uid, pwd, "res.partner", "search_read", [domain],
        {"fields": ["id", "name", "mobile", "phone"], "limit": 20, "order": "name"})
    # If digits given but formatting split them (e.g. '944-904' vs '944904'),
    # do a second pass matching normalized stored digits in Python.
    if digits and len(digits) >= 4 and len(custs) < 20:
        seen = {c["id"] for c in custs}
        extra = odoo(uid, pwd, "res.partner", "search_read",
            [["|", ["mobile", "ilike", digits[:6]], ["phone", "ilike", digits[:6]]]],
            {"fields": ["id", "name", "mobile", "phone"], "limit": 20})
        for c in extra:
            if c["id"] in seen:
                continue
            stored = "".join(ch for ch in (c.get("mobile") or c.get("phone") or "") if ch.isdigit())
            if digits in stored:
                custs.append(c)
    return [{"id": c["id"], "name": c["name"] or "—",
             "mobile": c.get("mobile") or c.get("phone") or ""} for c in custs[:20]]


_SANITIZED_CACHE = {}
def _has_sanitized(uid, pwd):
    """Cache whether phone_sanitized field exists (base_phone module)."""
    if "v" not in _SANITIZED_CACHE:
        try:
            f = odoo(uid, pwd, "res.partner", "fields_get", ["phone_sanitized"], {})
            _SANITIZED_CACHE["v"] = "phone_sanitized" in f
        except Exception:
            _SANITIZED_CACHE["v"] = False
    return _SANITIZED_CACHE["v"]


def get_customers(uid, pwd, query=""):
    domain = [["customer_rank", ">", 0]]
    if query:
        domain += ["|", ["name", "ilike", query], ["mobile", "ilike", query]]
    custs = odoo(uid, pwd, "res.partner", "search_read", [domain],
        {"fields": ["id", "name", "mobile", "phone"], "limit": 30, "order": "name"})
    return [{"id": c["id"], "name": c["name"],
             "mobile": c.get("mobile") or c.get("phone") or ""} for c in custs]


def get_sellable_products(uid, pwd):
    prods = odoo(uid, pwd, "product.product", "search_read",
        [[["sale_ok", "=", True]]],
        {"fields": ["id", "name", "default_code", "list_price"], "order": "name"})
    return [{"id": p["id"], "name": p["name"],
             "code": p.get("default_code") or "",
             "price": p.get("list_price", 0)} for p in prods]


def get_accurate_zones(uid, pwd, query=""):
    """Parent zones only (top-level regions)."""
    domain = [["is_subzone", "=", False], ["name", "not like", "test"]]
    if query:
        domain.append(["name", "ilike", query])
    zones = odoo(uid, pwd, "accurate.zone", "search_read", [domain],
        {"fields": ["id", "name", "child_count"], "limit": 40, "order": "name"})
    return [{"id": z["id"], "name": z["name"], "has_subs": z.get("child_count", 0) > 0} for z in zones]


def get_accurate_subzones(uid, pwd, zone_id):
    """Sub-zones under a parent zone."""
    subs = odoo(uid, pwd, "accurate.zone", "search_read",
        [[["parent_id", "=", zone_id], ["is_subzone", "=", True]]],
        {"fields": ["id", "name"], "order": "name"})
    return [{"id": s["id"], "name": s["name"]} for s in subs]


def get_delivery_companies(uid, pwd):
    """Available delivery carriers; Alyamama is the default."""
    dcs = odoo(uid, pwd, "accurate.delivery.company", "search_read", [[]],
        {"fields": ["id", "name"], "order": "id"})
    return [{"id": d["id"], "name": d["name"]} for d in dcs]


def get_shipping_services(uid, pwd):
    """Accurate shipping services (شحن عادى, توصيل نسائي, etc.).
    Deduplicated by name — the module has mirrored ids."""
    svc = odoo(uid, pwd, "accurate.service", "search_read", [[]],
        {"fields": ["id", "name"], "order": "id"})
    seen, out = set(), []
    for s in svc:
        if s["name"] in seen:
            continue
        seen.add(s["name"])
        out.append({"id": s["id"], "name": s["name"]})
    return out


def create_customer(uid, pwd, name, phone, address="", mobile=None):
    """Create a new customer. `phone` is the primary number.
    `mobile` is optional — if empty, it duplicates `phone` so the Accurate
    API (which requires both phone and mobile) always has a value.
    Returns (ok, partner_id_or_msg)."""
    try:
        phone_v = (phone or "").strip()
        mobile_v = (mobile or "").strip() or phone_v  # fallback to phone
        pid = odoo(uid, pwd, "res.partner", "create", [{
            "name": name, "phone": phone_v, "mobile": mobile_v,
            "street": address, "customer_rank": 1,
        }])
        return True, pid
    except Exception as e:
        return False, _clean_odoo_error(e)


def create_sales_order(uid, pwd, customer_id, lines, delivery=None, discount=0.0):
    """Create a draft SO with optional Accurate delivery fields and an
    optional order-wide discount percentage applied to every line.
    lines = [(product_id, qty, price), ...]
    Returns (ok, {id, name} or msg)."""
    try:
        disc = max(0.0, min(100.0, float(discount or 0)))
        order_lines = [(0, 0, {
            "product_id": pid, "product_uom_qty": qty, "price_unit": price,
            "discount": disc,
        }) for pid, qty, price in lines if qty > 0]
        if not order_lines:
            return False, "أضف منتجاً واحداً على الأقل"
        vals = {"partner_id": customer_id, "order_line": order_lines}
        if delivery:
            if delivery.get("zone_id"):
                vals["accurate_recipient_zone_id"] = delivery["zone_id"]
            if delivery.get("subzone_id"):
                vals["accurate_recipient_subzone_id"] = delivery["subzone_id"]
            if delivery.get("payment_type"):
                vals["accurate_payment_type_code"] = delivery["payment_type"]
            # Shipping service (required at confirmation) + sensible defaults
            vals["accurate_service_id"] = delivery.get("service_id", 1)  # شحن عادى
            vals["accurate_type_code"] = delivery.get("type_code", "FDP")
            vals["accurate_price_type_code"] = delivery.get("price_type", "EXCLD")
            vals["accurate_openable_code"] = delivery.get("openable", "N")
            # Default delivery company to Alyamama (id 1) unless specified
            vals["accurate_delivery_company_id"] = delivery.get("delivery_company_id", 1)
        so_id = odoo(uid, pwd, "sale.order", "create", [vals])
        name = odoo(uid, pwd, "sale.order", "read", [[so_id]], {"fields": ["name"]})
        return True, {"id": so_id, "name": name[0]["name"]}
    except Exception as e:
        return False, _clean_odoo_error(e)


def create_shipment_for_so(uid, pwd, so_id, weight=0.5, pieces=1):
    """Create the Yamamah shipment for a confirmed SO by creating an
    accurate.shipment record (the real mechanism — verified from live data).
    An Odoo automation then fires the Yamamah API on state set.
    Returns (ok, msg, shipment_info)."""
    try:
        so = odoo(uid, pwd, "sale.order", "read", [[so_id]],
            {"fields": ["name", "partner_id", "partner_shipping_id", "amount_total",
                        "accurate_recipient_zone_id", "accurate_recipient_subzone_id",
                        "accurate_payment_type_code", "accurate_delivery_company_id"]})
        if not so:
            return False, "الطلب غير موجود", None
        so = so[0]

        # Recipient = shipping contact if set, else the customer
        pid = (so.get("partner_shipping_id") or so.get("partner_id"))[0]
        partner = odoo(uid, pwd, "res.partner", "read", [[pid]],
            {"fields": ["name", "mobile", "phone", "street", "street2", "city"]})[0]
        mobile = partner.get("mobile") or partner.get("phone") or ""
        phone = partner.get("phone") or partner.get("mobile") or ""
        address = ", ".join(x for x in [partner.get("street"), partner.get("street2"),
                                        partner.get("city")] if x) or partner["name"]

        zone = so.get("accurate_recipient_zone_id")
        subzone = so.get("accurate_recipient_subzone_id")
        if not zone or not subzone:
            return False, "بيانات الشحن ناقصة — حدّد المنطقة والمنطقة الفرعية في الطلب أولاً", None

        dc = so.get("accurate_delivery_company_id")
        vals = {
            "sale_id": so_id,
            "ref_number": so["name"],
            "recipient_name": partner["name"],
            "recipient_mobile": mobile,
            "recipient_phone": phone,
            "recipient_address": address,
            "recipient_zone_id": zone[0],
            "recipient_subzone_id": subzone[0],
            "delivery_company_id": dc[0] if dc else 1,
            "payment_type_code": so.get("accurate_payment_type_code") or "COLC",
            "price_type_code": "EXCLD",
            "type_code": "FDP",
            "openable_code": "N",
            "service_id": 1,        # شحن عادى
            "weight": weight,
            "pieces_count": pieces,
            "fee_amount": so.get("amount_total", 0),
            "price": so.get("amount_total", 0),
        }
        sid = odoo(uid, pwd, "accurate.shipment", "create", [vals])

        # Read back — the automation fires the API on create/state; capture result
        sh = odoo(uid, pwd, "accurate.shipment", "read", [[sid]],
            {"fields": ["state", "error_message", "tracking_url", "code", "api_status_name"]})[0]
        if sh["state"] == "error":
            return False, sh.get("error_message", "خطأ من واجهة يمامة"), {"id": sid, "state": "error"}
        if sh.get("code") or sh.get("tracking_url"):
            return True, f"تم إنشاء الشحنة ✓ ({sh.get('code') or ''})", {"id": sid, "state": sh["state"]}
        # Created but API may still be processing
        return True, "تم إنشاء الشحنة — بانتظار رمز يمامة", {"id": sid, "state": sh["state"]}
    except Exception as e:
        if "cannot marshal None" in str(e):
            # create returned None-marshal but likely succeeded; look it up
            recent = odoo(uid, pwd, "accurate.shipment", "search_read",
                [[["sale_id", "=", so_id]]],
                {"fields": ["id", "state", "code"], "order": "id desc", "limit": 1})
            if recent:
                r = recent[0]
                return True, f"تم إنشاء الشحنة ✓ ({r.get('code') or ''})", {"id": r["id"], "state": r["state"]}
        return False, _clean_odoo_error(e), None


def fix_shipment_mobile(uid, pwd, shipment_id, new_mobile):
    """Update recipient mobile on a failed shipment (guided fix)."""
    try:
        odoo(uid, pwd, "accurate.shipment", "write", [[shipment_id], {"recipient_mobile": new_mobile}])
        return True, "تم تحديث الرقم — أعد الإرسال الآن"
    except Exception as e:
        return False, _clean_odoo_error(e)


def resend_shipment(uid, pwd, shipment_id):
    """Retry sending a shipment to the Accurate API. Returns (ok, msg)."""
    for method in ("action_send_shipment", "action_create_shipment", "send_shipment", "action_confirm"):
        try:
            odoo(uid, pwd, "accurate.shipment", method, [[shipment_id]])
            sh = odoo(uid, pwd, "accurate.shipment", "read", [[shipment_id]],
                {"fields": ["state", "error_message", "code"]})
            if sh and sh[0]["state"] != "error":
                return True, f"تم الإرسال ✓ ({sh[0].get('code') or ''})"
            elif sh:
                return False, sh[0].get("error_message", "ما زال هناك خطأ")[:120]
        except Exception as e:
            if "cannot marshal None" in str(e):
                sh = odoo(uid, pwd, "accurate.shipment", "read", [[shipment_id]], {"fields": ["state", "code"]})
                if sh and sh[0]["state"] != "error":
                    return True, f"تم الإرسال ✓ ({sh[0].get('code') or ''})"
                continue
            continue
    return False, "تعذّر الإرسال — جرّب من أودو"


def get_orders(uid, pwd, query=""):
    domain = []
    if query:
        domain = ["|", ["name", "ilike", query], ["partner_id.name", "ilike", query]]
    orders = odoo(uid, pwd, "sale.order", "search_read", [domain],
        {"fields": ["id", "name", "partner_id", "amount_total", "state"],
         "limit": 200, "order": "date_order desc"})
    return [{
        "id": o["id"], "name": o["name"],
        "customer": o["partner_id"][1] if o["partner_id"] else "—",
        "total": o["amount_total"], "state": o["state"],
    } for o in orders]


# ── CUSTOMER SERVICE ─────────────────────────────────────────
# ── UNIFIED CRM INBOX (multi-channel) ────────────────────────
CHANNEL_META = {
    "facebook":  {"ar": "فيسبوك",    "icon": "📘", "color": "#4267B2"},
    "whatsapp":  {"ar": "واتساب",    "icon": "💬", "color": "#25D366"},
    "instagram": {"ar": "انستغرام",  "icon": "📸", "color": "#E4405F"},
    "tiktok":    {"ar": "تيك توك",   "icon": "🎵", "color": "#69C9D0"},
}


def get_conversations(uid, pwd, channel="all", status="all"):
    """Unified inbox — all channels in one list, newest activity first."""
    domain = []
    if channel != "all":
        domain.append(["x_channel", "=", channel])
    if status != "all":
        domain.append(["x_status", "=", status])
    convs = odoo(uid, pwd, "x_auria_conversation", "search_read", [domain],
        {"fields": ["id", "x_customer_name", "x_customer_handle", "x_channel",
                    "x_status", "x_last_message", "x_unread", "x_agent_id"],
         "limit": 200, "order": "x_last_message desc"})
    out = []
    for c in convs:
        # last message preview
        last = odoo(uid, pwd, "x_auria_message", "search_read",
            [[["x_conversation_id", "=", c["id"]]]],
            {"fields": ["x_body", "x_direction"], "limit": 1, "order": "x_timestamp desc"})
        out.append({
            "id": c["id"], "customer": c["x_customer_name"] or "—",
            "handle": c["x_customer_handle"] or "",
            "channel": c["x_channel"], "status": c["x_status"],
            "unread": c.get("x_unread", 0),
            "agent": c["x_agent_id"][1] if c.get("x_agent_id") else None,
            "preview": (last[0]["x_body"][:40] if last else ""),
            "last_dir": (last[0]["x_direction"] if last else "in"),
            "time": (c.get("x_last_message") or "")[:16],
        })
    return out


def get_messages(uid, pwd, conv_id):
    """All messages in a conversation, chronological."""
    msgs = odoo(uid, pwd, "x_auria_message", "search_read",
        [[["x_conversation_id", "=", conv_id]]],
        {"fields": ["x_body", "x_direction", "x_timestamp", "x_agent_id",
                    "x_msg_type", "x_is_note", "x_image"],
         "order": "x_timestamp asc", "limit": 200})
    return [{
        "body": m["x_body"], "direction": m["x_direction"],
        "time": (m.get("x_timestamp") or "")[:16],
        "agent": m["x_agent_id"][1].split(" ")[0] if m.get("x_agent_id") else None,
        "type": m.get("x_msg_type") or "text",
        "is_note": m.get("x_is_note", False),
        "image": m.get("x_image") or None,
    } for m in msgs]


def get_conversation_head(uid, pwd, conv_id):
    c = odoo(uid, pwd, "x_auria_conversation", "read", [[conv_id]],
        {"fields": ["x_customer_name", "x_customer_handle", "x_channel", "x_status"]})
    if not c:
        return None
    c = c[0]
    return {"customer": c["x_customer_name"], "handle": c["x_customer_handle"],
            "channel": c["x_channel"], "status": c["x_status"]}


def send_reply(uid, pwd, conv_id, body):
    """Agent replies — records outbound message, marks conversation answered.
    (When channel APIs are added later, this is where the send call goes.)"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    conv = odoo(uid, pwd, "x_auria_conversation", "read", [[conv_id]], {"fields": ["x_channel"]})
    channel = conv[0]["x_channel"] if conv else "facebook"
    odoo(uid, pwd, "x_auria_message", "create", [{
        "x_name": body[:20], "x_conversation_id": conv_id, "x_body": body,
        "x_direction": "out", "x_channel": channel,
        "x_timestamp": now, "x_agent_id": uid,
    }])
    odoo(uid, pwd, "x_auria_conversation", "write", [[conv_id], {
        "x_status": "answered", "x_last_message": now, "x_unread": 0,
    }])
    return True


# ── CRM: labels, reminders, triage, canned responses ─────────
def get_labels(uid, pwd):
    labs = odoo(uid, pwd, "x_auria_label", "search_read", [[]],
        {"fields": ["id", "x_name", "x_color"], "order": "x_name"})
    return [{"id": l["id"], "name": l["x_name"], "color": l.get("x_color") or "#7FB069"} for l in labs]


def get_conversation_labels(uid, pwd, conv_id):
    c = odoo(uid, pwd, "x_auria_conversation", "read", [[conv_id]], {"fields": ["x_label_ids"]})
    if not c or not c[0].get("x_label_ids"):
        return []
    labs = odoo(uid, pwd, "x_auria_label", "read", [c[0]["x_label_ids"]],
        {"fields": ["id", "x_name", "x_color"]})
    return [{"id": l["id"], "name": l["x_name"], "color": l.get("x_color") or "#7FB069"} for l in labs]


def toggle_conversation_label(uid, pwd, conv_id, label_id):
    """Add/remove a label on a conversation. Returns the new label list."""
    c = odoo(uid, pwd, "x_auria_conversation", "read", [[conv_id]], {"fields": ["x_label_ids"]})
    current = set(c[0].get("x_label_ids", []) if c else [])
    if label_id in current:
        current.discard(label_id)
    else:
        current.add(label_id)
    odoo(uid, pwd, "x_auria_conversation", "write", [[conv_id], {"x_label_ids": [(6, 0, list(current))]}])
    return list(current)


def create_label(uid, pwd, name, color="#7FB069"):
    lid = odoo(uid, pwd, "x_auria_label", "create", [{"x_name": name, "x_color": color}])
    return lid


def mark_conversation_status(uid, pwd, conv_id, status):
    """status: open / answered / closed. 'closed' = mark as done."""
    odoo(uid, pwd, "x_auria_conversation", "write", [[conv_id], {"x_status": status}])
    return True


def mark_unread(uid, pwd, conv_id, unread=True):
    odoo(uid, pwd, "x_auria_conversation", "write",
         [[conv_id], {"x_unread": 1 if unread else 0,
                      "x_status": "open" if unread else "answered"}])
    return True


def set_reminder(uid, pwd, conv_id, when_dt, note=""):
    """when_dt: 'YYYY-MM-DD HH:MM:SS' string or None to clear."""
    odoo(uid, pwd, "x_auria_conversation", "write",
         [[conv_id], {"x_reminder": when_dt or False, "x_reminder_note": note or False}])
    return True


def get_due_reminders(uid, pwd):
    """Conversations whose reminder time has passed — for the agent's queue."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    convs = odoo(uid, pwd, "x_auria_conversation", "search_read",
        [[["x_reminder", "!=", False], ["x_reminder", "<=", now]]],
        {"fields": ["id", "x_customer_name", "x_channel", "x_reminder", "x_reminder_note"],
         "order": "x_reminder"})
    return [{"id": c["id"], "customer": c["x_customer_name"], "channel": c["x_channel"],
             "when": (c.get("x_reminder") or "")[:16], "note": c.get("x_reminder_note") or ""}
            for c in convs]


def assign_conversation(uid, pwd, conv_id, agent_uid):
    odoo(uid, pwd, "x_auria_conversation", "write", [[conv_id], {"x_agent_id": agent_uid}])
    return True


def get_canned_responses(uid, pwd, category=None):
    domain = [["x_category", "=", category]] if category else []
    cans = odoo(uid, pwd, "x_auria_canned", "search_read", [domain],
        {"fields": ["id", "x_name", "x_body", "x_shortcut", "x_category"], "order": "x_category, x_name"})
    return [{"id": c["id"], "title": c["x_name"], "body": c["x_body"],
             "shortcut": c.get("x_shortcut") or "", "category": c.get("x_category") or ""} for c in cans]


def create_canned_response(uid, pwd, title, body, shortcut="", category="عام"):
    cid = odoo(uid, pwd, "x_auria_canned", "create",
        [{"x_name": title, "x_body": body, "x_shortcut": shortcut, "x_category": category}])
    return cid


def send_reply_full(uid, pwd, conv_id, body, is_note=False, image_b64=None):
    """Enhanced reply: supports internal notes and image attachments.
    (Real channel send plugs in here when APIs are wired.)"""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    conv = odoo(uid, pwd, "x_auria_conversation", "read", [[conv_id]], {"fields": ["x_channel"]})
    channel = conv[0]["x_channel"] if conv else "facebook"
    vals = {
        "x_name": (body or "image")[:20], "x_conversation_id": conv_id,
        "x_body": body or "", "x_direction": "out", "x_channel": channel,
        "x_timestamp": now, "x_agent_id": uid,
        "x_msg_type": "image" if image_b64 else ("note" if is_note else "text"),
        "x_is_note": is_note,
    }
    if image_b64:
        vals["x_image"] = image_b64
    odoo(uid, pwd, "x_auria_message", "create", [vals])
    # Internal notes don't change conversation status; replies mark answered
    if not is_note:
        odoo(uid, pwd, "x_auria_conversation", "write",
             [[conv_id], {"x_status": "answered", "x_last_message": now, "x_unread": 0}])
    return True


def get_inbox_counts(uid, pwd):
    """Badge counts for the inbox filter chips."""
    convs = odoo(uid, pwd, "x_auria_conversation", "search_read", [[]],
        {"fields": ["x_channel", "x_status", "x_unread"]})
    from collections import Counter
    return {
        "total": len(convs),
        "open": sum(1 for c in convs if c["x_status"] == "open"),
        "unread": sum(c.get("x_unread", 0) for c in convs),
        "by_channel": dict(Counter(c["x_channel"] for c in convs)),
    }


# ── SESSION TRACKING (time-on-app) ───────────────────────────
# Heartbeat model: one row per user per day. Login opens/updates it;
# each interaction pushes x_last_ping forward. Time-on-app for a day is
# approximated by summing gaps between pings (gaps > IDLE_GAP treated as
# away, so idle browser tabs don't inflate the number).
_SESSION_IDLE_GAP_MIN = 10  # a gap longer than this = user stepped away


def touch_session(uid, pwd):
    """Record activity heartbeat. Called on login and on key interactions."""
    from datetime import datetime, timezone
    now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
    now = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    today = now_dt.strftime("%Y-%m-%d")
    try:
        existing = odoo(uid, pwd, "x_auria_session", "search",
            [[["x_user_id", "=", uid], ["x_date", "=", today]]], {"limit": 1})
        if existing:
            odoo(uid, pwd, "x_auria_session", "write", [existing, {"x_last_ping": now}])
        else:
            odoo(uid, pwd, "x_auria_session", "create", [{
                "x_name": f"session-{uid}-{today}",
                "x_user_id": uid, "x_login_time": now,
                "x_last_ping": now, "x_date": today,
            }])
    except Exception:
        pass  # never let tracking break the app


def get_time_on_app(uid, pwd, target_uid=None):
    """Minutes active today for a user (login → last ping span)."""
    from datetime import date, datetime
    who = target_uid or uid
    today = str(date.today())
    rec = odoo(uid, pwd, "x_auria_session", "search_read",
        [[["x_user_id", "=", who], ["x_date", "=", today]]],
        {"fields": ["x_login_time", "x_last_ping"], "limit": 1})
    if not rec:
        return 0
    try:
        lo = datetime.strptime(rec[0]["x_login_time"], "%Y-%m-%d %H:%M:%S")
        hi = datetime.strptime(rec[0]["x_last_ping"], "%Y-%m-%d %H:%M:%S")
        return max(0, round((hi - lo).total_seconds() / 60))
    except Exception:
        return 0


def get_team_time_on_app(uid, pwd, user_ids):
    """Today's active minutes per user, for the management dashboard."""
    from datetime import date, datetime
    today = str(date.today())
    recs = odoo(uid, pwd, "x_auria_session", "search_read",
        [[["x_user_id", "in", user_ids], ["x_date", "=", today]]],
        {"fields": ["x_user_id", "x_login_time", "x_last_ping"]})
    out = {}
    for r in recs:
        try:
            lo = datetime.strptime(r["x_login_time"], "%Y-%m-%d %H:%M:%S")
            hi = datetime.strptime(r["x_last_ping"], "%Y-%m-%d %H:%M:%S")
            out[r["x_user_id"][1]] = max(0, round((hi - lo).total_seconds() / 60))
        except Exception:
            pass
    return out


def get_cs_agent_stats(uid, pwd):
    """Management dashboard: per-agent message counts (received/answered)."""
    from datetime import date, timedelta
    week_ago = str(date.today() - timedelta(days=7)) + " 00:00:00"
    msgs = odoo(uid, pwd, "x_auria_message", "search_read",
        [[["x_timestamp", ">=", week_ago]]],
        {"fields": ["x_direction", "x_agent_id", "x_channel"]})
    from collections import defaultdict
    stats = defaultdict(lambda: {"answered": 0})
    inbound = 0
    by_channel = defaultdict(lambda: {"in": 0, "out": 0})
    for m in msgs:
        by_channel[m["x_channel"]][m["x_direction"]] += 1
        if m["x_direction"] == "out" and m.get("x_agent_id"):
            stats[m["x_agent_id"][1]]["answered"] += 1
        if m["x_direction"] == "in":
            inbound += 1
    return {
        "inbound": inbound,
        "answered": sum(s["answered"] for s in stats.values()),
        "by_agent": dict(stats),
        "by_channel": dict(by_channel),
    }


def get_tickets(uid, pwd):
    tickets = odoo(uid, pwd, "project.task", "search_read",
        [[["project_id", "=", DEPT_PROJECT["cs"]]]],
        {"fields": ["id", "name", "stage_id", "partner_id", "create_date"],
         "limit": 200, "order": "create_date desc"})
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


# ── YAMAMAH DELIVERY (Accurate Logistics API) ────────────────
# Real status names from the Yamamah API, with display colors
YAMAMAH_STATUS = {
    "طلب شحن":                {"en": "Shipment requested", "color": "#633806", "bg": "#FFF3CD"},
    "قيد الارسال للمندوب":     {"en": "Assigning courier",   "color": "#633806", "bg": "#FFF3CD"},
    "تم الاستلام بالمخزن":     {"en": "At warehouse",        "color": "#1A5276", "bg": "#E6F1FB"},
    "قيد التوصيل":            {"en": "Out for delivery",    "color": "#1A5276", "bg": "#E6F1FB"},
    "تم التسليم":             {"en": "Delivered",           "color": "#3B6D11", "bg": "#EAF3DE"},
    "تعذر التسليم":           {"en": "Delivery failed",     "color": "#A32D2D", "bg": "#FCEBEB"},
    "انتظار لاعادة التوصيل":   {"en": "Awaiting re-delivery","color": "#633806", "bg": "#FFF3CD"},
    "ارتجاع للراسل":          {"en": "Returning to sender", "color": "#A32D2D", "bg": "#FCEBEB"},
    "Returned":              {"en": "Returned",            "color": "#A32D2D", "bg": "#FCEBEB"},
    "Cancelled":             {"en": "Cancelled",           "color": "#888780", "bg": "#F1EFE8"},
}

SHIPMENT_STATE = {
    "draft":     {"ar": "مسودة",   "en": "Draft",     "color": "#888"},
    "sent":      {"ar": "أُرسلت",   "en": "Sent",      "color": "#1A5276"},
    "delivered": {"ar": "سُلّمت",   "en": "Delivered", "color": "#3B6D11"},
    "returned":  {"ar": "مرتجعة",  "en": "Returned",  "color": "#A32D2D"},
    "cancelled": {"ar": "ملغاة",   "en": "Cancelled", "color": "#888"},
    "error":     {"ar": "خطأ",     "en": "Error",     "color": "#A32D2D"},
}


def get_shipments(uid, pwd, state_filter=None, query=""):
    """Get Yamamah shipments with live delivery status."""
    domain = []
    if state_filter and state_filter != "all":
        domain.append(["state", "=", state_filter])
    ships = odoo(uid, pwd, "accurate.shipment", "search_read", [domain],
        {"fields": ["id", "name", "code", "state", "api_status_name", "tracking_url",
                    "sale_id", "recipient_name", "recipient_mobile", "recipient_zone_id",
                    "fee_total", "fee_collection", "payment_type_code", "date"],
         "limit": 50, "order": "id desc"})
    out = []
    for s in ships:
        if query:
            hay = f"{s.get('name','')} {s.get('recipient_name','')} {s.get('sale_id') and s['sale_id'][1] or ''}"
            if query.lower() not in hay.lower():
                continue
        out.append({
            "id": s["id"], "name": s["name"], "code": s.get("code", ""),
            "state": s["state"],
            "api_status": s.get("api_status_name") or "—",
            "tracking_url": s.get("tracking_url", ""),
            "order": s["sale_id"][1] if s.get("sale_id") else "—",
            "recipient": s.get("recipient_name", "—"),
            "mobile": s.get("recipient_mobile", ""),
            "zone": s["recipient_zone_id"][1] if s.get("recipient_zone_id") else "—",
            "cod": s.get("fee_collection", 0),
            "total": s.get("fee_total", 0),
            "date": (s.get("date") or "")[:16],
        })
    return out


def get_shipment_summary(uid, pwd):
    """Count shipments by live Yamamah status for the ops dashboard."""
    ships = odoo(uid, pwd, "accurate.shipment", "search_read", [[]],
        {"fields": ["state", "api_status_name"], "limit": 3000})
    from collections import Counter
    by_state = Counter(s.get("state") or "?" for s in ships)
    by_status = Counter(s.get("api_status_name") or "?" for s in ships)
    return {"total": len(ships), "by_state": dict(by_state), "by_status": dict(by_status)}


def get_order_delivery_status(uid, pwd, sale_order_name):
    """Look up the Yamamah delivery status for a specific order (for CS)."""
    ship = odoo(uid, pwd, "accurate.shipment", "search_read",
        [[["sale_id.name", "=", sale_order_name]]],
        {"fields": ["name", "state", "api_status_name", "tracking_url",
                    "recipient_name", "recipient_mobile", "fee_collection", "date"],
         "limit": 1, "order": "id desc"})
    if not ship:
        return None
    s = ship[0]
    return {
        "shipment": s["name"], "state": s["state"],
        "api_status": s.get("api_status_name") or "—",
        "tracking_url": s.get("tracking_url", ""),
        "recipient": s.get("recipient_name", ""),
        "mobile": s.get("recipient_mobile", ""),
        "cod": s.get("fee_collection", 0),
        "date": (s.get("date") or "")[:16],
    }


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
