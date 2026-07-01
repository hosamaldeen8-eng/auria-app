# v2 — BOM dropdown + work order timers + Yamamah tracking (deploy trigger)
"""
╔══════════════════════════════════════════════════════════╗
║   AURIA — Department App (Streamlit)                     ║
║   Live Odoo UI for Production, Procurement, Operations,  ║
║   Creative, and Customer Service                         ║
╚══════════════════════════════════════════════════════════╝
"""
import streamlit as st
import streamlit.components.v1 as components
import odoo_client as oc
from pathlib import Path
from datetime import datetime, timedelta
import base64

st.set_page_config(page_title="Auria", page_icon="🌿", layout="centered", initial_sidebar_state="collapsed")

# ── ASSETS ───────────────────────────────────────────────────
ASSETS = Path(__file__).parent / "assets"
def img_b64(name):
    p = ASSETS / name
    if p.exists():
        return base64.b64encode(p.read_bytes()).decode()
    return ""

LOGO_B64   = img_b64("auria-logo.png")
EMBLEM_B64 = img_b64("auria-emblem.png")
EMBLEM_SM  = img_b64("emblem-small.png")

# ── TRANSLATIONS ─────────────────────────────────────────────
T = {
    "en": {"login":"Sign in","email":"Email","password":"Password","signin":"Sign in",
           "home":"Home","tasks":"Tasks","report":"Daily Report","logout":"Sign out",
           "good_morning":"Welcome","dept_snapshot":"Department","my_performance":"My Performance",
           "company":"Company Today","my_tasks":"My Tasks","assigned":"Assigned","completed":"Done",
           "urgent":"Urgent","overdue":"Overdue","orders":"Orders","revenue":"Revenue LYD",
           "deliveries":"Deliveries","mos":"Active MOs","production":"Production","procurement":"Procurement",
           "operations":"Operations","creative":"Creative","cs":"Customer Service","inventory":"Inventory",
           "search":"Search...","stage":"Stage","priority":"Priority","deadline":"Deadline",
           "log_note":"Log note","post":"Post","rfqs":"RFQs","approve":"Approve","suppliers":"Suppliers",
           "tickets":"Tickets","reply":"Reply","order_lookup":"Order Lookup","achievements":"Achievements",
           "challenges":"Challenges","tomorrow":"Tomorrow's Plan","submit":"Submit Report","invalid":"Invalid credentials",
           "mark_done":"Mark done","all":"All","mine":"Mine","active":"Active","validate":"Validate"},
    "ar": {"login":"تسجيل الدخول","email":"البريد الإلكتروني","password":"كلمة المرور","signin":"دخول",
           "home":"الرئيسية","tasks":"المهام","report":"التقرير اليومي","logout":"خروج",
           "good_morning":"مرحباً","dept_snapshot":"القسم","my_performance":"أدائي",
           "company":"الشركة اليوم","my_tasks":"مهامي","assigned":"مكلّف","completed":"مكتمل",
           "urgent":"عاجل","overdue":"متأخر","orders":"الطلبات","revenue":"المبيعات",
           "deliveries":"التسليمات","mos":"أوامر إنتاج","production":"الإنتاج","procurement":"المشتريات",
           "operations":"العمليات","creative":"الكريتف","cs":"خدمة العملاء","inventory":"المخزون",
           "search":"بحث...","stage":"المرحلة","priority":"الأولوية","deadline":"الموعد",
           "log_note":"ملاحظة","post":"إرسال","rfqs":"طلبات العروض","approve":"اعتماد","suppliers":"الموردون",
           "tickets":"التذاكر","reply":"رد","order_lookup":"بحث طلب","achievements":"الإنجازات",
           "challenges":"التحديات","tomorrow":"خطة الغد","submit":"إرسال التقرير","invalid":"بيانات غير صحيحة",
           "mark_done":"إنهاء","all":"الكل","mine":"مهامي","active":"نشط","validate":"تأكيد"},
}

DEPT_COLORS = {"production":"#2E3D2E","procurement":"#633806","operations":"#1A5276",
               "creative":"#8B3A8B","cs":"#A32D2D","management":"#2E3D2E"}

# ── STYLE (dark forest theme) ────────────────────────────────
st.markdown("""
<style>
  .stApp { background: #141B14; }
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 1.5rem; max-width: 480px; }
  .metric-card { background:#1E281E; border:1px solid #2E3D2E; border-radius:12px; padding:14px; text-align:center; color:#E8E4D6; }
  .metric-n { font-size:24px; font-weight:700; margin:0; }
  .metric-l { font-size:11px; color:#9BA58F; margin:0; }
  .greeting { background:linear-gradient(135deg,#2E3D2E,#1A241A); border:1px solid #3A4A38; border-radius:14px; padding:18px; color:#F0EEE2; margin-bottom:16px; }
  .stButton>button { border-radius:10px; font-weight:600; }
  .task-row { background:#1E281E; border:1px solid #2E3D2E; border-radius:10px; padding:12px 14px; margin-bottom:8px; color:#E8E4D6; }
  .task-row a { color:#7FB069; }
  .badge { font-size:10px; padding:2px 8px; border-radius:20px; }
  [data-testid="stStatusWidget"] { visibility: hidden; }
  .auria-loader{position:fixed;inset:0;background:rgba(20,27,20,.78);display:none;align-items:center;justify-content:center;z-index:99999}
  body:has([data-testid="stStatusWidget"]) .auria-loader{display:flex}
  .auria-loader img{width:70px;height:70px;border-radius:50%;animation:apulse 1.1s ease-in-out infinite;box-shadow:0 0 34px rgba(127,176,105,.35)}
  @keyframes apulse{0%,100%{transform:scale(1);opacity:.85}50%{transform:scale(1.16);opacity:1}}
</style>
""", unsafe_allow_html=True)

# Branded loading overlay — appears automatically whenever the app is
# processing (page moves, button clicks) via the :has() selector above.
st.markdown(f"<div class='auria-loader'><img src='data:image/png;base64,{EMBLEM_SM}'/></div>", unsafe_allow_html=True)

# ── SESSION ──────────────────────────────────────────────────
ss = st.session_state
ss.setdefault("uid", None)
ss.setdefault("pwd", None)
ss.setdefault("info", None)
ss.setdefault("email", None)
ss.setdefault("lang", "ar")
ss.setdefault("screen", "home")
ss.setdefault("mo_open", None)

def t(key):
    return T[ss.lang].get(key, key)

# ── PERSISTENT LOGIN (cookies, no external component) ───────
# Read: st.context.cookies (native Streamlit ≥1.37, reliable)
# Write/delete: a tiny JS snippet — parent.document.cookie
def save_login_cookie(email, pwd):
    token = base64.b64encode(f"{email}|{pwd}".encode()).decode()
    components.html(
        f"<script>parent.document.cookie = 'auria_auth={token}; "
        f"max-age=2592000; path=/; SameSite=Lax';</script>",
        height=0,
    )

def clear_login_cookie():
    components.html(
        "<script>parent.document.cookie = "
        "'auria_auth=; max-age=0; path=/; SameSite=Lax';</script>",
        height=0,
    )

# Deferred cookie ops — st.rerun() can interrupt the JS iframe before it
# executes, so writes happen on the render AFTER the rerun.
if ss.get("pending_cookie_save") and ss.uid:
    email_c, pwd_c = ss.pop("pending_cookie_save")
    save_login_cookie(email_c, pwd_c)
if ss.get("pending_cookie_clear"):
    ss.pop("pending_cookie_clear")
    clear_login_cookie()

# Auto-login: if no session but a saved cookie exists, sign in silently
if not ss.uid and not ss.get("auto_login_tried"):
    raw = None
    try:
        raw = st.context.cookies.get("auria_auth")
    except Exception:
        pass
    if raw:
        ss.auto_login_tried = True
        try:
            email, pwd = base64.b64decode(raw.encode()).decode().split("|", 1)
            uid, info = oc.authenticate(email, pwd)
            if uid:
                ss.uid, ss.pwd, ss.info, ss.email = uid, pwd, info, email
                st.rerun()
        except Exception:
            pass

# ── LOGIN ────────────────────────────────────────────────────
def login_screen():
    st.markdown(f"""
    <div style='text-align:center; padding:40px 0 20px;'>
      <img src='data:image/png;base64,{LOGO_B64}' width='220'/>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 3, 1])
    with c2:
        email = st.text_input(t("email"), key="login_email")
        pwd = st.text_input(t("password"), type="password", key="login_pwd")
        if st.button(t("signin"), use_container_width=True, type="primary"):
            uid, info = oc.authenticate(email, pwd)
            if uid:
                ss.uid, ss.pwd, ss.info, ss.email = uid, pwd, info, email.strip()
                ss.pending_cookie_save = (email.strip(), pwd)  # stay signed in 30 days
                ss.screen = "home"
                st.rerun()
            else:
                st.error(t("invalid"))
        lang_label = "English" if ss.lang == "ar" else "العربية"
        if st.button(f"🌐 {lang_label}", use_container_width=True):
            ss.lang = "en" if ss.lang == "ar" else "ar"
            st.rerun()

# ── HEADER ───────────────────────────────────────────────────
def header():
    info = ss.info
    c1, c2, c3 = st.columns([1, 4, 2])
    with c1:
        st.markdown(f"<img src='data:image/png;base64,{EMBLEM_B64}' width='40' style='border-radius:50%'/>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"**{info['name']}**  \n<span style='color:#888780;font-size:12px'>{t(info['dept'])}</span>", unsafe_allow_html=True)
    with c3:
        if st.button("🌐" + (" EN" if ss.lang == "ar" else " ع"), use_container_width=True):
            ss.lang = "en" if ss.lang == "ar" else "ar"; st.rerun()
    st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)

# ── NAV ──────────────────────────────────────────────────────
def nav():
    dept = ss.info["dept"]
    tabs = [("home", "🏠", t("home"))]
    if dept in ("production","procurement","operations","creative","cs"):
        icons = {"production":"📦","procurement":"🛒","operations":"🚚","creative":"🎨","cs":"💬"}
        tabs.append((dept, icons[dept], t(dept)))
    tabs += [("tasks", "✅", t("tasks")), ("report", "📝", t("report")), ("profile", "👤", "")]

    cols = st.columns(len(tabs))
    for i, (key, icon, label) in enumerate(tabs):
        with cols[i]:
            if st.button(f"{icon}\n{label}", key=f"nav_{key}", use_container_width=True):
                ss.screen = key; st.rerun()

# ── HOME ─────────────────────────────────────────────────────
def home_screen():
    uid, pwd, info = ss.uid, ss.pwd, ss.info
    st.markdown(f"""
    <div class='greeting'>
      <div style='font-size:12px;opacity:.6'>{t('good_morning')}</div>
      <div style='font-size:20px;font-weight:700'>{info['name']}</div>
      <div style='font-size:12px;color:#C6BEB1'>{oc.today_str()}</div>
    </div>""", unsafe_allow_html=True)

    # Department KPIs
    st.markdown(f"**{t('dept_snapshot')}**")
    kpis = oc.get_dept_kpis(uid, pwd, info["dept"])
    if kpis:
        cols = st.columns(len(kpis))
        for i, (label, val) in enumerate(kpis):
            cols[i].markdown(f"<div class='metric-card'><p class='metric-n' style='color:#7FB069'>{val}</p><p class='metric-l'>{label}</p></div>", unsafe_allow_html=True)

    # ── My performance (deep) ──
    st.markdown(f"**{t('my_performance')}**")
    perf = oc.get_my_performance(uid, pwd)

    # Row 1: core numbers
    c = st.columns(4)
    core = [
        (perf["open"],      "مفتوح",   "#E8E4D6"),
        (perf["done_week"], "أُنجز هذا الأسبوع", "#7FB069"),
        (perf["urgent"],    t("urgent"),  "#E07070" if perf["urgent"] else "#888"),
        (perf["overdue"],   t("overdue"), "#E07070" if perf["overdue"] else "#7FB069"),
    ]
    for i, (n, l, col) in enumerate(core):
        c[i].markdown(f"<div class='metric-card'><p class='metric-n' style='color:{col}'>{n}</p><p class='metric-l'>{l}</p></div>", unsafe_allow_html=True)

    # Row 2: completion rate bar + activity
    rate = perf["completion_rate"]
    rate_color = "#7FB069" if rate >= 60 else "#D4A853" if rate >= 30 else "#E07070"
    st.markdown(f"""<div class='metric-card' style='text-align:start;margin-top:6px'>
        <div style='display:flex;justify-content:space-between;margin-bottom:5px'>
          <span style='font-size:12px'>نسبة الإنجاز الكلية</span>
          <b style='color:{rate_color}'>{rate}%</b>
        </div>
        <div style='background:rgba(128,128,128,.25);border-radius:6px;height:8px;overflow:hidden'>
          <div style='width:{rate}%;height:100%;background:{rate_color}'></div>
        </div>
        <div style='display:flex;justify-content:space-between;margin-top:8px;font-size:11px;opacity:.75'>
          <span>💬 {perf['notes_week']} تحديث هذا الأسبوع</span>
          <span>📝 التقرير اليومي: {"✅ مُرسل" if perf['report_today'] else "❌ لم يُرسل"} · {perf['report_week']}/7</span>
        </div>
    </div>""", unsafe_allow_html=True)

    # Row 3: overdue names (if any) + next deadlines
    if perf["overdue_names"]:
        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        st.error("⏰ متأخر: " + " · ".join(perf["overdue_names"]))
    if perf["next_due"]:
        nd = perf["next_due"]
        items = "".join(f"<div style='display:flex;justify-content:space-between;padding:3px 0;font-size:12px'><span>{x['name'][:38]}</span><span style='opacity:.6'>{x['date_deadline']}</span></div>" for x in nd)
        st.markdown(f"<div class='metric-card' style='text-align:start;margin-top:6px'><div style='font-size:11px;opacity:.6;margin-bottom:4px'>المواعيد القادمة</div>{items}</div>", unsafe_allow_html=True)

# ── TASKS ────────────────────────────────────────────────────
def tasks_screen():
    uid, pwd = ss.uid, ss.pwd
    scope = st.radio("", [t("mine"), t("all")], horizontal=True, label_visibility="collapsed")
    scope_key = "mine" if scope == t("mine") else "all"
    tasks = oc.get_tasks(uid, pwd, scope_key)

    for task in tasks:
        done = oc.is_done(task["stage"])
        with st.container():
            c1, c2 = st.columns([5, 1])
            with c1:
                emoji = "🔴" if task["priority"] == "1" and not done else ("✅" if done else "⚪")
                overdue = task["due"] and task["due"] < oc.today_str() and not done
                due_txt = f"<span style='color:{'#A32D2D' if overdue else '#888'}'>{task['due']}</span>" if task["due"] else ""
                st.markdown(f"{emoji} **{task['name']}**  \n<span class='badge' style='background:#E6F1FB;color:#1A5276'>{task['stage']}</span> · {task['project']} · {due_txt}", unsafe_allow_html=True)
            with c2:
                with st.popover("⋯"):
                    stages = oc.get_project_stages(uid, pwd, task["id"])
                    st.caption(t("stage"))
                    for sid, sname in stages:
                        if st.button(sname, key=f"st_{task['id']}_{sid}", use_container_width=True):
                            oc.set_task_stage(uid, pwd, task["id"], sid); st.rerun()
                    note = st.text_input(t("log_note"), key=f"note_{task['id']}")
                    if st.button(t("post"), key=f"post_{task['id']}"):
                        if note.strip():
                            oc.post_task_note(uid, pwd, task["id"], note); st.success("✓"); st.rerun()

# ── PRODUCTION ───────────────────────────────────────────────
# ── MO MANAGEMENT PAGE ───────────────────────────────────────
def mo_detail_screen():
    uid, pwd = ss.uid, ss.pwd
    mo_id = ss.mo_open

    if st.button("← أوامر الإنتاج"):
        ss.mo_open = None
        st.rerun()

    mo = oc.get_mo_detail(uid, pwd, mo_id)
    if not mo:
        st.error("لم يتم العثور على الأمر")
        return

    # Auto-refresh every 15s while a timer is running (keeps clock live)
    if mo["any_running"]:
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=15000, key="mo_tick")
        except Exception:
            pass  # graceful if package missing

    # ── Header card with LIVE total production time ──
    hrs = int(mo["total_elapsed_min"] // 60)
    mins = int(mo["total_elapsed_min"] % 60)
    state_ar = {"progress":"🟡 جاري","confirmed":"🟢 مؤكد","done":"⚪ منتهي","draft":"◻️ مسودة","to_close":"🔵 للإغلاق"}.get(mo["state"], mo["state"])
    running_badge = "<span style='color:#7FB069'>● يعمل الآن</span>" if mo["any_running"] else ""
    st.markdown(f"""<div class='greeting'>
        <div style='display:flex;justify-content:space-between;align-items:start'>
          <div>
            <div style='font-family:monospace;font-size:12px;opacity:.6'>{mo['name']}</div>
            <div style='font-size:18px;font-weight:700'>{mo['product']}</div>
            <div style='font-size:12px;opacity:.7;margin-top:2px'>{mo['qty']:g} وحدة · {state_ar} {running_badge}</div>
          </div>
          <div style='text-align:center;background:rgba(255,255,255,.08);border-radius:10px;padding:8px 14px'>
            <div style='font-size:22px;font-weight:700;color:#7FB069'>{hrs}:{mins:02d}</div>
            <div style='font-size:9px;opacity:.6'>ساعة إنتاج ⏱</div>
          </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── MO actions ──
    c1, c2 = st.columns(2)
    with c1:
        if mo["state"] == "draft" and st.button("🟢 تأكيد الأمر", use_container_width=True):
            ok, msg = oc.mo_confirm(uid, pwd, mo_id)
            st.success(msg) if ok else st.error(msg)
            if ok: st.rerun()
    with c2:
        if mo["state"] in ("confirmed", "progress", "to_close") and st.button("✅ إنهاء الأمر بالكامل", use_container_width=True):
            ok, msg = oc.mo_validate(uid, pwd, mo_id)
            st.success(msg) if ok else st.error(msg)
            if ok: st.rerun()

    # ── Work orders with individual timers ──
    st.markdown("**مراحل العمل**")
    for w in mo["workorders"]:
        pct = min(100, round(w["elapsed"] / w["expected"] * 100)) if w["expected"] else 0
        e_h, e_m = int(w["elapsed"] // 60), int(w["elapsed"] % 60)
        dot = "🟢" if w["working"] else "⚪"
        state_ar = {"progress":"جاري","ready":"جاهز","waiting":"بانتظار","pending":"معلق","done":"✓ منتهي","cancel":"ملغي"}.get(w["state"], w["state"])
        st.markdown(f"""<div class='task-row'>
            <div style='display:flex;justify-content:space-between'>
              <b>{w['name']}</b>
              <span style='font-size:11px'>{dot} {state_ar}</span>
            </div>
            <div style='margin-top:6px;background:rgba(255,255,255,.12);border-radius:6px;height:6px;overflow:hidden'>
              <div style='width:{pct}%;height:100%;background:{"#E07070" if pct>100 else "#7FB069"}'></div>
            </div>
            <div style='display:flex;justify-content:space-between;font-size:11px;opacity:.7;margin-top:3px'>
              <span>⏱ {e_h}:{e_m:02d} {"(يعمل الآن)" if w['working'] else ""}</span>
              <span>متوقع: {w['expected']:g} دقيقة</span>
            </div>
        </div>""", unsafe_allow_html=True)
        if w["state"] not in ("done", "cancel"):
            b1, b2, b3 = st.columns(3)
            with b1:
                if not w["working"] and st.button("▶️ ابدأ", key=f"mstart_{w['id']}", use_container_width=True):
                    ok, msg = oc.wo_start(uid, pwd, w["id"])
                    if ok: st.rerun()
                    else: st.error(msg)
                if w["working"] and st.button("⏸️ أوقف", key=f"mstop_{w['id']}", use_container_width=True):
                    ok, msg = oc.wo_stop(uid, pwd, w["id"])
                    if ok: st.rerun()
                    else: st.error(msg)
            with b2:
                if st.button("✅ أنهِ المرحلة", key=f"mfin_{w['id']}", use_container_width=True):
                    ok, msg = oc.wo_finish(uid, pwd, w["id"])
                    if ok: st.rerun()
                    else: st.error(msg)

    # ── Components ──
    st.markdown("**المكوّنات**")
    for c in mo["components"]:
        state_icon = {"assigned":"🟢","done":"✓","partially_available":"🟡","confirmed":"🟡","waiting":"⚪","draft":"◻️"}.get(c["state"], "⚪")
        st.markdown(f"<div class='task-row' style='display:flex;justify-content:space-between;padding:8px 14px'><span>{state_icon} {c['name']}</span><span style='opacity:.8'>{c['done']:g} / {c['needed']:g} {c['uom']}</span></div>", unsafe_allow_html=True)


def production_screen():
    uid, pwd = ss.uid, ss.pwd
    # Guard against stale module cache after a deploy
    if not hasattr(oc, "get_manufacturable_products"):
        st.error("⚠️ App updating — please reboot from 'Manage app' → Reboot, or wait a moment and refresh.")
        st.stop()
    tab1, tab2, tab3 = st.tabs([f"⚙️ {t('mos')}", "▶️ Timer", f"📦 {t('inventory')}"])

    # ── Tab 1: MOs + create from BOM dropdown ──
    with tab1:
        with st.expander("➕ إنشاء أمر تصنيع جديد"):
            prods = oc.get_manufacturable_products(uid, pwd)
            names = [f"{p['name']} (batch {p['batch']:g})" for p in prods]
            idx = st.selectbox("المنتج", range(len(names)), format_func=lambda i: names[i], key="mo_prod")
            chosen = prods[idx]
            # Show BOM as soon as product is picked
            bom = oc.get_bom_detail(uid, pwd, chosen["bom_id"])
            if bom:
                st.markdown(f"**المكوّنات (batch {bom['batch']:g}):**")
                comp_html = "<div class='task-row'>"
                for c in bom["components"]:
                    comp_html += f"<div style='display:flex;justify-content:space-between;padding:2px 0'><span>{c['name']}</span><span style='color:#3B6D11;font-weight:600'>{c['qty']:g} {c['uom']}</span></div>"
                comp_html += "</div>"
                st.markdown(comp_html, unsafe_allow_html=True)
                if bom["operations"]:
                    st.caption("العمليات: " + " · ".join(o["name"] for o in bom["operations"]))
            qty = st.number_input("الكمية المطلوبة", min_value=1.0, value=float(chosen["batch"]), step=1.0, key="mo_qty")
            if st.button("إنشاء الأمر", type="primary", key="mo_create"):
                mo_id = oc.create_mo_from_bom(uid, pwd, chosen["tmpl_id"], qty)
                if mo_id:
                    st.success(f"✅ تم إنشاء أمر التصنيع #{mo_id}")
                    st.rerun()

        st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)
        for mo in oc.get_mos(uid, pwd):
            state_ar = {"progress":"🟡 جاري","confirmed":"🟢 مؤكد","done":"⚪ منتهي","draft":"◻️ مسودة","to_close":"🔵 للإغلاق"}.get(mo["state"], mo["state"])
            if st.button(f"{mo['name']}  ·  {mo['product'][:32]}  ·  {mo['qty']:g}  ·  {state_ar}",
                         key=f"mo_{mo['id']}", use_container_width=True):
                ss.mo_open = mo["id"]
                st.rerun()

    # ── Tab 2: Work order timers (start/stop) ──
    with tab2:
        st.caption("ابدأ وأوقف مؤقّت العمل لكل أمر شغل")
        wos = oc.get_workorders(uid, pwd)
        if not wos:
            st.info("لا توجد أوامر شغل نشطة")
        for w in wos:
            pct = min(100, round(w["duration"] / w["expected"] * 100)) if w["expected"] else 0
            state_ar = {"progress":"جاري","ready":"جاهز","waiting":"بانتظار مكوّنات","pending":"بانتظار","done":"منتهي"}.get(w["state"], w["state"])
            working_dot = "🟢" if w["working"] else "⚪"
            st.markdown(f"""<div class='task-row'>
                <div style='display:flex;justify-content:space-between;align-items:start'>
                  <div><b>{w['product']}</b><br><span style='font-family:monospace;color:#888;font-size:11px'>{w['mo']}</span></div>
                  <span style='font-size:11px'>{working_dot} {state_ar}</span>
                </div>
                <div style='margin-top:6px;background:rgba(255,255,255,.12);border-radius:6px;height:6px;overflow:hidden'>
                  <div style='width:{pct}%;height:100%;background:{"#A32D2D" if pct>100 else "#3B6D11"}'></div>
                </div>
                <div style='font-size:11px;color:#888;margin-top:3px'>{w['duration']:g} / {w['expected']:g} دقيقة ({pct}%)</div>
            </div>""", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                if not w["working"] and st.button("▶️ ابدأ", key=f"start_{w['id']}", use_container_width=True):
                    ok, msg = oc.wo_start(uid, pwd, w["id"])
                    if ok: st.rerun()
                    else: st.error(msg)
                if w["working"] and st.button("⏸️ أوقف", key=f"stop_{w['id']}", use_container_width=True):
                    ok, msg = oc.wo_stop(uid, pwd, w["id"])
                    if ok: st.rerun()
                    else: st.error(msg)
            with c2:
                if st.button("✅ أنهِ", key=f"fin_{w['id']}", use_container_width=True):
                    ok, msg = oc.wo_finish(uid, pwd, w["id"])
                    if ok: st.success("✓"); st.rerun()
                    else: st.error(msg)

    # ── Tab 3: Inventory ──
    with tab3:
        q = st.text_input(t("search"), key="inv_search")
        for item in oc.get_inventory(uid, pwd, q):
            color = "#A32D2D" if item["qty"] == 0 else "#D4A853"
            st.markdown(f"<div class='task-row' style='display:flex;justify-content:space-between'><span><b>{item['name']}</b><br><span style='color:#888;font-size:11px'>{item['loc']}</span></span><span style='font-size:18px;font-weight:700;color:{color}'>{item['qty']:g}</span></div>", unsafe_allow_html=True)


# ── PROCUREMENT ──────────────────────────────────────────────
def procurement_screen():
    uid, pwd = ss.uid, ss.pwd
    st.markdown(f"**{t('rfqs')}**")
    for rfq in oc.get_rfqs(uid, pwd):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f"<div class='task-row'><span style='font-family:monospace;color:#D4A853'>{rfq['name']}</span> <span class='badge' style='background:#FFF3CD;color:#633806'>{rfq['state']}</span><br><b>{rfq['supplier']}</b><br><span style='color:#888;font-size:12px'>{rfq['total']:,.0f} {rfq['currency']} · {rfq['due']}</span></div>", unsafe_allow_html=True)
        with c2:
            if rfq["state"] in ("draft", "sent"):
                if st.button(t("approve"), key=f"appr_{rfq['id']}"):
                    oc.approve_rfq(uid, pwd, rfq["id"]); st.success("✓"); st.rerun()

# ── OPERATIONS ───────────────────────────────────────────────
def operations_screen():
    uid, pwd = ss.uid, ss.pwd
    tab1, tab2, tab3 = st.tabs([f"🚚 {t('deliveries')}", "📦 يمامة Tracking", f"🔍 {t('order_lookup')}"])

    with tab1:
        for d in oc.get_deliveries(uid, pwd):
            st.markdown(f"<div class='task-row'><span style='font-family:monospace;color:#D4A853'>{d['name']}</span> <span class='badge' style='background:rgba(255,255,255,.1);color:#888'>{d['state']}</span><br><b>{d['customer']}</b> · <span style='color:#888;font-size:12px'>{d['date']}</span></div>", unsafe_allow_html=True)

    with tab2:
        # Live Yamamah delivery summary
        summ = oc.get_shipment_summary(uid, pwd)
        st.markdown(f"**{summ['total']} شحنة عبر يمامة**")
        # Status breakdown chips
        chips = ""
        for status, count in sorted(summ["by_status"].items(), key=lambda x: -x[1]):
            if status == "?": continue
            meta = oc.YAMAMAH_STATUS.get(status, {"color": "#888", "bg": "#eee"})
            chips += f"<span style='display:inline-block;margin:2px;padding:3px 9px;border-radius:20px;font-size:11px;background:{meta['bg']};color:{meta['color']}'>{status} · {count}</span>"
        st.markdown(chips, unsafe_allow_html=True)
        st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)

        # Filter by state
        state_filter = st.selectbox("Filter", ["sent", "delivered", "returned", "all"],
                                     format_func=lambda x: {"sent": "🚚 قيد التوصيل (Sent)", "delivered": "✅ تم التسليم", "returned": "↩️ مرتجع", "all": "الكل"}[x])
        query = st.text_input(t("search"), key="ymm_search", placeholder="Order # or recipient")

        for s in oc.get_shipments(uid, pwd, state_filter, query):
            meta = oc.YAMAMAH_STATUS.get(s["api_status"], {"color": "#888", "bg": "#eee"})
            track_link = f"<a href='{s['tracking_url']}' target='_blank' style='color:#1A5276;font-size:11px'>🔗 تتبّع {s['code']}</a>" if s["tracking_url"] else ""
            cod_txt = f" · COD {s['cod']:,.0f}" if s["cod"] else ""
            st.markdown(f"""<div class='task-row'>
                <div style='display:flex;justify-content:space-between;align-items:start'>
                  <div>
                    <span style='font-family:monospace;color:#D4A853;font-size:11px'>{s['order']}</span><br>
                    <b>{s['recipient']}</b><br>
                    <span style='color:#888;font-size:11px'>{s['zone']} · {s['mobile']}{cod_txt}</span>
                  </div>
                  <span style='padding:3px 9px;border-radius:20px;font-size:10px;background:{meta['bg']};color:{meta['color']};white-space:nowrap'>{s['api_status']}</span>
                </div>
                <div style='margin-top:4px'>{track_link}</div>
            </div>""", unsafe_allow_html=True)

    with tab3:
        q = st.text_input(t("search"), key="ord_search")
        for o in oc.get_orders(uid, pwd, q):
            st.markdown(f"<div class='task-row' style='display:flex;justify-content:space-between'><span><span style='font-family:monospace;color:#D4A853'>{o['name']}</span><br><b>{o['customer']}</b></span><span style='font-weight:700;color:#D4A853'>{o['total']:,.0f}</span></div>", unsafe_allow_html=True)

# ── CREATIVE ─────────────────────────────────────────────────
def creative_screen():
    uid, pwd = ss.uid, ss.pwd
    st.markdown(f"**{t('tasks')}**")
    for task in oc.get_tasks(uid, pwd, "mine"):
        done = oc.is_done(task["stage"])
        st.markdown(f"<div class='task-row'>{'✅' if done else '🎨'} <b>{task['name']}</b><br><span class='badge' style='background:#F8E8F8;color:#8B3A8B'>{task['stage']}</span></div>", unsafe_allow_html=True)

# ── CUSTOMER SERVICE ─────────────────────────────────────────
def cs_screen():
    uid, pwd = ss.uid, ss.pwd
    if "cs_open" not in ss:
        ss.cs_open = None

    tab1, tab2 = st.tabs([f"💬 {t('tickets')}", "📦 حالة الطلب"])

    with tab1:
        if ss.cs_open:
            ticket = ss.cs_open
            if st.button("← " + t("tickets")):
                ss.cs_open = None; st.rerun()
            st.markdown(f"**{ticket['customer']}** — {ticket['issue']}")
            for m in oc.get_ticket_messages(uid, pwd, ticket["id"]):
                st.markdown(f"<div class='task-row'><b style='font-size:12px'>{m['author']}</b><br>{m['text']}<br><span style='color:#aaa;font-size:10px'>{m['date']}</span></div>", unsafe_allow_html=True)
            reply = st.text_input(t("reply"), key="cs_reply")
            if st.button(t("post"), type="primary"):
                if reply.strip():
                    oc.reply_ticket(uid, pwd, ticket["id"], reply); st.success("✓"); st.rerun()
        else:
            for tk in oc.get_tickets(uid, pwd):
                if st.button(f"💬 {tk['customer']} — {tk['issue'][:30]}  ·  {tk['status']}", key=f"tk_{tk['id']}", use_container_width=True):
                    ss.cs_open = tk; st.rerun()

    with tab2:
        st.caption("ابحث عن طلب لمعرفة حالة التوصيل من يمامة")
        order_no = st.text_input("رقم الطلب", key="cs_order_lookup", placeholder="S02486")
        if order_no.strip():
            status = oc.get_order_delivery_status(uid, pwd, order_no.strip())
            if status:
                meta = oc.YAMAMAH_STATUS.get(status["api_status"], {"color": "#888", "bg": "#eee"})
                track = f"<a href='{status['tracking_url']}' target='_blank' style='color:#1A5276'>🔗 رابط التتبّع</a>" if status["tracking_url"] else ""
                st.markdown(f"""<div class='task-row'>
                    <div style='display:flex;justify-content:space-between;align-items:center'>
                      <b>{status['recipient']}</b>
                      <span style='padding:4px 12px;border-radius:20px;font-size:12px;background:{meta['bg']};color:{meta['color']}'>{status['api_status']}</span>
                    </div>
                    <div style='color:#888;font-size:12px;margin-top:6px'>
                      شحنة: {status['shipment']}<br>
                      الهاتف: {status['mobile']}<br>
                      COD: {status['cod']:,.0f} د.ل<br>
                      التاريخ: {status['date']}
                    </div>
                    <div style='margin-top:8px'>{track}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.warning(f"لا توجد شحنة للطلب {order_no}")

# ── DAILY REPORT ─────────────────────────────────────────────
def report_screen():
    uid, pwd = ss.uid, ss.pwd
    st.markdown(f"**{t('report')} — {oc.today_str()}**")
    ach = st.text_area(t("achievements"), key="rep_ach", placeholder="1.\n2.\n3.")
    challenges = st.text_area(t("challenges"), key="rep_chal")
    tomorrow = st.text_area(t("tomorrow"), key="rep_tom", placeholder="1.\n2.")
    if st.button(t("submit"), type="primary", use_container_width=True):
        ok = oc.submit_daily_report(uid, pwd,
            ach.split("\n"), challenges, tomorrow.split("\n"))
        if ok:
            st.success("✅ " + t("submit"))
            st.balloons()
        else:
            st.error("No report task assigned to this account.")

# ── PROFILE ──────────────────────────────────────────────────
def profile_screen():
    info = ss.info
    dept_label = t(info["dept"])
    st.markdown(f"""<div class='greeting' style='text-align:center;padding:26px 18px'>
        <img src='data:image/png;base64,{EMBLEM_B64}' width='72' style='border-radius:50%;margin-bottom:10px'/>
        <div style='font-size:22px;font-weight:700'>{info['name']}</div>
        <div style='font-size:13px;opacity:.7;margin-top:2px'>{dept_label}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class='metric-card' style='text-align:start'>
        <div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.07)'>
          <span style='opacity:.6;font-size:12px'>{t('email')}</span><span style='font-size:13px'>{ss.email or '—'}</span>
        </div>
        <div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.07)'>
          <span style='opacity:.6;font-size:12px'>Odoo ID</span><span style='font-size:13px'>#{ss.uid}</span>
        </div>
        <div style='display:flex;justify-content:space-between;padding:6px 0'>
          <span style='opacity:.6;font-size:12px'>{t('dept_snapshot')}</span><span style='font-size:13px'>{dept_label}</span>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
    lang_label = "English" if ss.lang == "ar" else "العربية"
    if st.button(f"🌐 {lang_label}", use_container_width=True, key="prof_lang"):
        ss.lang = "en" if ss.lang == "ar" else "ar"; st.rerun()

    st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
    if st.button(f"🚪 {t('logout')}", use_container_width=True, type="primary", key="prof_logout"):
        ss.pending_cookie_clear = True
        for k in ["uid","pwd","info","email","cs_open","mo_open","auto_login_tried"]:
            ss.pop(k, None)
        ss.auto_login_tried = True  # don't instantly re-login from cookie
        st.rerun()


# ── ROUTER ───────────────────────────────────────────────────
if not ss.uid:
    login_screen()
else:
    header()
    screen = ss.screen
    if screen == "home":         home_screen()
    elif screen == "production":
        mo_detail_screen() if ss.mo_open else production_screen()
    elif screen == "procurement":procurement_screen()
    elif screen == "operations": operations_screen()
    elif screen == "creative":   creative_screen()
    elif screen == "cs":         cs_screen()
    elif screen == "tasks":      tasks_screen()
    elif screen == "report":     report_screen()
    elif screen == "profile":    profile_screen()
    st.markdown("<hr style='margin:16px 0 8px'>", unsafe_allow_html=True)
    nav()
