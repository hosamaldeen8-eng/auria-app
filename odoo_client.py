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
        today = today_str()
        deliv = odoo(uid, pwd, "stock.picking", "search_count", [[["date_done", ">=", f"{today} 00:00:00"], ["state", "=", "done"]]])
        # Yamamah live: out for delivery + failed
        out_delivery = odoo(uid, pwd, "accurate.shipment", "search_count", [[["state", "=", "sent"]]])
        returned = odoo(uid, pwd, "accurate.shipment", "search_count", [[["state", "=", "returned"]]])
        return [
            ("Deliveries Today", deliv),
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


def wo_start(uid, pwd, wo_id):
    """Start the timer on a work order. Returns (ok, message)."""
    try:
        odoo(uid, pwd, "mrp.workorder", "button_start", [[wo_id]])
        return True, "بدأ العمل"
    except Exception as e:
        return False, _clean_odoo_error(e)


def wo_stop(uid, pwd, wo_id):
    """Pause the timer. Returns (ok, message)."""
    try:
        odoo(uid, pwd, "mrp.workorder", "button_pending", [[wo_id]])
        return True, "تم الإيقاف"
    except Exception as e:
        return False, _clean_odoo_error(e)


def wo_finish(uid, pwd, wo_id):
    """Mark a work order finished. Returns (ok, message)."""
    try:
        odoo(uid, pwd, "mrp.workorder", "button_finish", [[wo_id]])
        return True, "تم الإنهاء"
    except Exception as e:
        return False, _clean_odoo_error(e)


def _clean_odoo_error(e):
    """Turn a raw Odoo XML-RPC fault into a short readable message."""
    msg = str(e)
    if 'type "view"' in msg or "view (SJ)" in msg or "view (HD)" in msg:
        return "خطأ في إعداد المخازن: الموقع المصدر نوعه 'view' — يحتاج مود ضبط مسارات المخزن."
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
