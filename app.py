# v3 — full ops suite: PO/expenses/sales/CRM/sessions (deploy trigger)
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
           "mark_done":"Mark done","all":"All","mine":"Mine","active":"Active","validate":"Validate","profile":"Profile"},
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
           "mark_done":"إنهاء","all":"الكل","mine":"مهامي","active":"نشط","validate":"تأكيد","profile":"حسابي"},
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
  div.st-key-topnav { position: sticky; top: 0; z-index: 999; background: rgba(20,27,20,.96);
    backdrop-filter: blur(8px); padding: 6px 0 4px; border-bottom: 1px solid #2E3D2E; margin-bottom: 10px; }
  /* Force the nav columns to stay in ONE horizontal row (no vertical stacking
     on narrow phones) — square 1:1 buttons sized to fit side by side. */
  div.st-key-topnav [data-testid="stHorizontalBlock"] {
    display: flex !important; flex-wrap: nowrap !important; gap: 5px !important;
    overflow-x: auto; -webkit-overflow-scrolling: touch; }
  div.st-key-topnav [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 0 !important; min-width: 0 !important; width: auto !important; }
  div.st-key-topnav .stButton>button {
    background:#1A231A; border:1px solid #2A3A2A; color:#9BA58F;
    aspect-ratio: 1 / 1; width:100%; padding:4px 2px; border-radius:12px;
    font-size:10px; line-height:1.25; white-space:pre-line; font-weight:500;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    box-shadow:none; transition:all .15s; }
  div.st-key-topnav .stButton>button:hover { color:#E8E4D6; background:#22301F; border-color:#7FB069; }
  div.st-key-topnav .stButton>button p { margin:0 !important; font-size:10px; line-height:1.2; }
  div.st-key-topnav .stButton>button p:first-line { font-size:18px; }
  div.st-key-topnav .stButton>button[kind="primary"],
  div.st-key-topnav [data-testid="stBaseButton-primary"] {
    background:rgba(127,176,105,.16) !important; color:#7FB069 !important;
    border:1px solid rgba(127,176,105,.5) !important; font-weight:700; }
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

# One durable guard for the whole app: if Streamlit Cloud is running a
# cached odoo_client that predates the app.py we're serving, every new
# function call would crash. Instead we detect the mismatch once, here,
# and show a calm reload notice — no screen ever hits an AttributeError.
APP_EXPECTS_CLIENT = 16
if getattr(oc, "CLIENT_VERSION", 0) < APP_EXPECTS_CLIENT:
    st.warning("⏳ التطبيق يُحدَّث الآن. أعِد تحميل الصفحة بعد لحظات "
               "(أو Manage app ← Reboot).")
    st.stop()

ss.setdefault("uid", None)
ss.setdefault("pwd", None)
ss.setdefault("info", None)
ss.setdefault("email", None)
ss.setdefault("lang", "ar")
ss.setdefault("screen", "home")
ss.setdefault("mo_open", None)
ss.setdefault("op_pick_open", None)
ss.setdefault("po_open", None)
ss.setdefault("so_open", None)
ss.setdefault("chat_open", None)
ss.setdefault("so_lines", [])
ss.setdefault("so_selected_cust", None)
ss.setdefault("so_rowcount", 3)
ss.setdefault("so_just_created", None)
ss.setdefault("so_draft_snapshot", None)

def t(key):
    return T[ss.lang].get(key, key)


# ── Cached reference data ────────────────────────────────────
# Product lists, delivery companies, and zones change rarely. Without
# caching, every product selection or "add row" click re-fetched them from
# Odoo over XML-RPC — that network round-trip was the lag. Cache them so the
# first load hits Odoo once, then every interaction is instant. TTL keeps
# them fresh enough (5 min) that new products/prices still appear.
@st.cache_data(ttl=300, show_spinner=False)
def _cached_sellable_products(uid, pwd):
    return oc.get_sellable_products(uid, pwd)

@st.cache_data(ttl=600, show_spinner=False)
def _cached_delivery_companies(uid, pwd):
    return oc.get_delivery_companies(uid, pwd)

@st.cache_data(ttl=600, show_spinner=False)
def _cached_services(uid, pwd):
    return oc.get_shipping_services(uid, pwd)

@st.cache_data(ttl=600, show_spinner=False)
def _cached_canned(uid, pwd):
    return oc.get_canned_responses(uid, pwd)

@st.cache_data(ttl=600, show_spinner=False)
def _cached_zones(uid, pwd, query):
    return oc.get_accurate_zones(uid, pwd, query)

@st.cache_data(ttl=600, show_spinner=False)
def _cached_subzones(uid, pwd, zone_id):
    return oc.get_accurate_subzones(uid, pwd, zone_id)


def _flash(ok, msg):
    """Safely show a success/error toast. Coerces msg to a plain string so
    Streamlit never tries to introspect a non-string as a variable."""
    text = str(msg) if msg is not None else ("تم ✓" if ok else "حدث خطأ")
    if ok:
        st.success(text)
    else:
        st.error(text)


def _rear_camera(key, label="📸 صوّر الإيصال"):
    """Camera capture that defaults to the phone's REAR camera.

    Streamlit's st.camera_input opens the front camera with no toggle. We
    inject JS that overrides getUserMedia to request facingMode:environment
    (the rear/back camera — correct for photographing receipts & invoices),
    then reuse st.camera_input for its reliable capture plumbing.
    Returns the photo bytes (or None).
    """
    st.caption(label)
    # Force rear camera: patch getUserMedia so Streamlit's widget opens the
    # environment-facing lens. Runs once per render, before the widget mounts.
    st.markdown("""
    <script>
    (function(){
      try{
        var pdoc = window.parent.document;
        if(pdoc.__auriaRearCam) return;
        pdoc.__auriaRearCam = true;
        var md = window.parent.navigator.mediaDevices;
        if(md && md.getUserMedia){
          var orig = md.getUserMedia.bind(md);
          md.getUserMedia = function(constraints){
            try{
              constraints = constraints || {};
              if(constraints.video){
                if(constraints.video === true){ constraints.video = {}; }
                constraints.video.facingMode = { ideal: 'environment' };
              }
            }catch(e){}
            return orig(constraints);
          };
        }
      }catch(e){}
    })();
    </script>
    """, unsafe_allow_html=True)
    photo = st.camera_input(label, key=key, label_visibility="collapsed")
    return photo.getvalue() if photo else None

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
                oc.touch_session(uid, pwd)
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
                oc.touch_session(uid, pwd)
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
    c1, c2 = st.columns([1, 6])
    with c1:
        st.markdown(f"<img src='data:image/png;base64,{EMBLEM_B64}' width='42' style='border-radius:50%'/>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div style='padding-top:2px'><b style='font-size:15px'>{info['name']}</b><br><span style='color:#9BA58F;font-size:11px'>{t(info['dept'])} · {oc.today_str()}</span></div>", unsafe_allow_html=True)

# ── NAV ──────────────────────────────────────────────────────
def nav():
    dept = ss.info["dept"]
    tabs = [("home", "🏠", t("home"))]
    if dept in ("production","procurement","operations","creative","cs"):
        icons = {"production":"📦","procurement":"🛒","operations":"🚚","creative":"🎨","cs":"💬"}
        tabs.append((dept, icons[dept], t(dept)))
    if dept in ("management", "cs"):
        tabs.append(("sales", "🧾", "المبيعات"))
    tabs += [("tasks", "✅", t("tasks")), ("report", "📝", t("report")), ("profile", "👤", t("profile"))]

    with st.container(key="topnav"):
        cols = st.columns(len(tabs))
        for i, (key, icon, label) in enumerate(tabs):
            active = ss.screen == key
            with cols[i]:
                # Larger icon on top, small label under — reads clearly in a square
                btn_label = f"{icon}\n{label}"
                if st.button(btn_label, key=f"nav_{key}", use_container_width=True,
                             type="primary" if active else "secondary"):
                    if key == "production":
                        ss.mo_open = None  # tapping the tab returns to the list
                    ss.screen = key
                    st.rerun()
    st.markdown("<div style='border-bottom:1px solid #2E3D2E;margin:0 0 14px'></div>", unsafe_allow_html=True)

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

    # ── Production: pending stock movements ──
    if info["dept"] in ("production", "management"):
        pend = oc.get_pending_movements(uid, pwd)
        n_tr, n_rc = len(pend["transfers"]), len(pend["receipts"])
        st.markdown(f"**الحركات غير المُنجزة** <span style='opacity:.5;font-size:11px'>({n_tr} تحويل · {n_rc} استلام)</span>", unsafe_allow_html=True)
        pt1, pt2 = st.tabs([f"🔄 تحويلات ({n_tr})", f"📥 استلامات PO ({n_rc})"])

        with pt1:
            if not pend["transfers"]:
                st.caption("لا توجد تحويلات معلّقة")
            for m in pend["transfers"]:
                card = (
                    "<div class='task-row' style='margin-bottom:4px'>"
                    "<div style='display:flex;justify-content:space-between;align-items:center'>"
                    f"<span style='font-family:monospace;font-size:11px;color:#D4A853'>{m['name']}</span>"
                    f"<span style='color:{m['color']};font-size:11px;font-weight:600'>{m['state_ar']}</span>"
                    "</div>"
                    f"<div style='font-size:12px;margin-top:5px'>{m['type']}</div>"
                    f"<div style='font-size:11px;opacity:.6;margin-top:2px'>{m['route']} · {m['date']}</div>"
                    "</div>"
                )
                st.markdown(card, unsafe_allow_html=True)
                if m["state"] == "assigned":
                    if st.button("✅ إنهاء التحويل", key=f"fintr_{m['id']}", use_container_width=True):
                        ok, msg = oc.validate_picking(uid, pwd, m["id"])
                        _flash(ok, msg)
                        if ok: st.rerun()
                st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)

        with pt2:
            if not pend["receipts"]:
                st.caption("لا توجد استلامات معلّقة")
            for m in pend["receipts"]:
                card = (
                    "<div class='task-row' style='margin-bottom:4px'>"
                    "<div style='display:flex;justify-content:space-between;align-items:center'>"
                    f"<span style='font-family:monospace;font-size:11px;color:#D4A853'>{m['name']}</span>"
                    f"<span style='color:{m['color']};font-size:11px;font-weight:600'>{m['state_ar']}</span>"
                    "</div>"
                    f"<div style='font-weight:700;margin:6px 0 3px'>{m['partner']}</div>"
                    f"<div style='font-size:11px;opacity:.6'>{m['origin']} · {m['date']}</div>"
                    "</div>"
                )
                st.markdown(card, unsafe_allow_html=True)
                if m["state"] == "assigned":
                    if st.button("📥 استلام كامل", key=f"finrc_{m['id']}", use_container_width=True):
                        ok, msg = oc.validate_picking(uid, pwd, m["id"])
                        _flash(ok, msg)
                        if ok: st.rerun()
                st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)

    # ── My performance (deep) ──
    st.markdown(f"**{t('my_performance')}**")
    perf = oc.get_my_performance(uid, pwd)

    # Row 1: core numbers — tap any box to open Tasks with that filter
    core = [
        ("pf_open",    perf["open"],      "مفتوح",             "open",      "#E8E4D6"),
        ("pf_done",    perf["done_week"], "أُنجز هذا الأسبوع",  "done_week", "#7FB069"),
        ("pf_urgent",  perf["urgent"],    t("urgent"),          "urgent",    "#E07070" if perf["urgent"] else "#9BA58F"),
        ("pf_overdue", perf["overdue"],   t("overdue"),         "overdue",   "#E07070" if perf["overdue"] else "#7FB069"),
    ]
    # Metric-card styling for the clickable boxes (per-box number color)
    box_css = "".join(
        f"div.st-key-{k} .stButton>button{{background:#1E281E;border:1px solid #2E3D2E;"
        f"border-radius:12px;padding:10px 4px 2px;font-size:22px;font-weight:700;"
        f"color:{col};width:100%;box-shadow:none}}"
        f"div.st-key-{k} .stButton>button:hover{{border-color:#7FB069;background:#233023}}"
        for k, _, _, _, col in core)
    st.markdown(f"<style>{box_css}</style>", unsafe_allow_html=True)
    cols = st.columns(4)
    for i, (key, n, label, filt, col) in enumerate(core):
        with cols[i]:
            with st.container(key=key):
                if st.button(f"{n}", key=f"btn_{key}", use_container_width=True):
                    ss["task_status_f"] = filt
                    ss["task_scope"] = t("mine")
                    ss.screen = "tasks"
                    st.rerun()
            st.markdown(f"<div style='text-align:center;font-size:11px;color:#9BA58F;margin-top:-6px'>{label}</div>", unsafe_allow_html=True)

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
    # ── Management: CS team performance ──
    if info["dept"] == "management":
        cs = oc.get_cs_agent_stats(uid, pwd)
        st.markdown("**خدمة العملاء — هذا الأسبوع**")
        m1, m2, m3 = st.columns(3)
        rate = round(cs["answered"] / cs["inbound"] * 100) if cs["inbound"] else 0
        m1.markdown(f"<div class='metric-card'><p class='metric-n' style='color:#E8E4D6'>{cs['inbound']}</p><p class='metric-l'>رسائل واردة</p></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><p class='metric-n' style='color:#7FB069'>{cs['answered']}</p><p class='metric-l'>تم الرد</p></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><p class='metric-n' style='color:{'#7FB069' if rate>=70 else '#D4A853'}'>{rate}%</p><p class='metric-l'>معدل الرد</p></div>", unsafe_allow_html=True)
        # Per-agent (replies + time on app today)
        if cs["by_agent"]:
            CS_UIDS = [24, 12, 10, 9]  # Amal, Wala, Znjabel, Ala
            time_map = oc.get_team_time_on_app(uid, pwd, CS_UIDS)
            rows = ""
            for agent, s in sorted(cs["by_agent"].items(), key=lambda x: -x[1]["answered"]):
                mins = next((v for k, v in time_map.items() if agent.split(" ")[0] in k), 0)
                tstr = f"{mins//60}س {mins%60}د" if mins >= 60 else f"{mins}د"
                rows += (f"<div style='display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05)'>"
                         f"<span style='font-size:12px'>{agent.split(' ')[0]}</span>"
                         f"<span style='font-size:12px'><span style='color:#7FB069'>{s['answered']} رد</span> · <span style='opacity:.6'>⏱ {tstr}</span></span></div>")
            st.markdown(f"<div class='metric-card' style='text-align:start'>{rows}</div>", unsafe_allow_html=True)
        # By channel
        if cs["by_channel"]:
            chips = "".join(
                f"<span style='background:{oc.CHANNEL_META.get(ch,{}).get('color','#888')}22;color:{oc.CHANNEL_META.get(ch,{}).get('color','#888')};padding:3px 9px;border-radius:20px;font-size:11px;margin:2px'>"
                f"{oc.CHANNEL_META.get(ch,{}).get('icon','•')} {v['in']}↓ {v['out']}↑</span>"
                for ch, v in cs["by_channel"].items())
            st.markdown(f"<div style='margin-top:8px'>{chips}</div>", unsafe_allow_html=True)

# ── TASKS ────────────────────────────────────────────────────
def tasks_screen():
    uid, pwd = ss.uid, ss.pwd

    # ── Filter bar ──
    TASK_FILTERS = {"all": "الكل", "open": "🔵 مفتوحة", "done_week": "✅ أُنجزت هذا الأسبوع",
                    "urgent": "🔴 عاجلة", "overdue": "⏰ متأخرة"}
    fc1, fc2 = st.columns([2, 3])
    scope = fc1.radio("النطاق", [t("mine"), t("all")], horizontal=True,
                      label_visibility="collapsed", key="task_scope")
    status_f = fc2.selectbox("الحالة", list(TASK_FILTERS.keys()),
                             format_func=lambda k: TASK_FILTERS[k], key="task_status_f")
    query = st.text_input(t("search"), key="task_search", placeholder="اسم المهمة...")

    scope_key = "mine" if scope == t("mine") else "all"
    tasks = oc.get_tasks(uid, pwd, scope_key)

    from datetime import date, timedelta
    today = str(date.today())
    week_ago = str(date.today() - timedelta(days=7))

    def keep(tk):
        done = oc.is_done(tk["stage"])
        if query and query.lower() not in tk["name"].lower():
            return False
        if status_f == "open":      return not done
        if status_f == "done_week": return done and tk.get("updated", "") >= week_ago
        if status_f == "urgent":    return tk["priority"] == "1" and not done
        if status_f == "overdue":   return bool(tk["due"]) and tk["due"] < today and not done
        return True

    filtered = [tk for tk in tasks if keep(tk)]
    st.caption(f"{len(filtered)} مهمة")

    for task in filtered:
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

    # Smooth client-side clocks below advance without page refresh.

    # ── Header card with SMOOTH LIVE production clock (client-side JS) ──
    state_ar = {"progress":"🟡 جاري","confirmed":"🟢 مؤكد","done":"⚪ منتهي","draft":"◻️ مسودة","to_close":"🔵 للإغلاق"}.get(mo["state"], mo["state"])
    running_badge = "<span style='color:#7FB069'>● يعمل الآن</span>" if mo["any_running"] else ""
    base_sec = mo["total_elapsed_sec"]
    running = "true" if mo["any_running"] else "false"
    st.markdown(f"""<div class='greeting'>
        <div style='display:flex;justify-content:space-between;align-items:start'>
          <div>
            <div style='font-family:monospace;font-size:12px;opacity:.6'>{mo['name']}</div>
            <div style='font-size:18px;font-weight:700'>{mo['product']}</div>
            <div style='font-size:12px;opacity:.7;margin-top:2px'>{mo['qty']:g} وحدة · {state_ar} {running_badge}</div>
          </div>
          <div style='text-align:center;background:rgba(255,255,255,.08);border-radius:10px;padding:8px 14px'>
            <div id='auria-clock' style='font-size:22px;font-weight:700;color:#7FB069;font-variant-numeric:tabular-nums;letter-spacing:.5px'>—:—:—</div>
            <div style='font-size:9px;opacity:.6'>ساعة إنتاج ⏱</div>
          </div>
        </div>
    </div>
    <script>
    (function(){{
      var base = {base_sec}, running = {running};
      var t0 = Date.now();
      function fmt(s){{
        s = Math.max(0, Math.floor(s));
        var h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sec = s%60;
        return h + ':' + String(m).padStart(2,'0') + ':' + String(sec).padStart(2,'0');
      }}
      function tick(){{
        var el = window.parent.document.getElementById('auria-clock');
        if(!el){{ return; }}
        var extra = running ? (Date.now()-t0)/1000 : 0;
        el.textContent = fmt(base + extra);
        if(running){{ requestAnimationFrame(tick); }}
      }}
      tick();
    }})();
    </script>""", unsafe_allow_html=True)

    # ── MO actions ──
    c0, c1, c2 = st.columns(3)
    with c0:
        if mo["state"] in ("confirmed", "progress") and not mo["any_running"] and st.button("▶️ بدء العمل", use_container_width=True, type="primary"):
            ok, msg = oc.mo_start_work(uid, pwd, mo_id)
            _flash(ok, msg)
            if ok: st.rerun()
    with c1:
        if mo["state"] == "draft" and st.button("🟢 تأكيد الأمر", use_container_width=True):
            ok, msg = oc.mo_confirm(uid, pwd, mo_id)
            _flash(ok, msg)
            if ok: st.rerun()
    with c2:
        if mo["state"] in ("confirmed", "progress", "to_close") and st.button("✅ إنهاء الأمر بالكامل", use_container_width=True):
            ok, msg = oc.mo_validate(uid, pwd, mo_id)
            _flash(ok, msg)
            if ok: st.rerun()

    # ── Work orders with individual timers ──
    st.markdown("**مراحل العمل**")
    for w in mo["workorders"]:
        pct = min(100, round(w["elapsed"] / w["expected"] * 100)) if w["expected"] else 0
        dot = "🟢" if w["working"] else "⚪"
        state_ar = {"progress":"جاري","ready":"جاهز","waiting":"بانتظار","pending":"معلق","done":"✓ منتهي","cancel":"ملغي"}.get(w["state"], w["state"])
        worker_txt = f"· 🟢 {w['worker']}" if w.get("worker") else ""
        wclock_id = f"wo-clock-{w['id']}"
        w_base = w["elapsed_sec"]
        w_running = "true" if w["working"] else "false"
        st.markdown(f"""<div class='task-row'>
            <div style='display:flex;justify-content:space-between'>
              <b>{w['name']}</b>
              <span style='font-size:11px'>{dot} {state_ar}</span>
            </div>
            <div style='margin-top:6px;background:rgba(255,255,255,.12);border-radius:6px;height:6px;overflow:hidden'>
              <div style='width:{pct}%;height:100%;background:{"#E07070" if pct>100 else "#7FB069"}'></div>
            </div>
            <div style='display:flex;justify-content:space-between;font-size:11px;opacity:.7;margin-top:3px'>
              <span>⏱ <span id='{wclock_id}' style='font-variant-numeric:tabular-nums'>—:—:—</span> {worker_txt}</span>
              <span>متوقع: {w['expected']:g} دقيقة</span>
            </div>
        </div>
        <script>
        (function(){{
          var base={w_base}, running={w_running}, t0=Date.now();
          function fmt(s){{s=Math.max(0,Math.floor(s));var h=Math.floor(s/3600),m=Math.floor((s%3600)/60),x=s%60;return h+':'+String(m).padStart(2,'0')+':'+String(x).padStart(2,'0');}}
          function tick(){{var el=window.parent.document.getElementById('{wclock_id}');if(!el)return;var e=running?(Date.now()-t0)/1000:0;el.textContent=fmt(base+e);if(running)requestAnimationFrame(tick);}}
          tick();
        }})();
        </script>""", unsafe_allow_html=True)
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
    tab1, tab2, tab3, tab4 = st.tabs([f"⚙️ {t('mos')}", "▶️ Timer", f"📦 {t('inventory')}", "🔄 تحويلات"])

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
        # ── Filters ──
        MO_STATES = {"all": "الكل", "progress": "🟡 جاري", "confirmed": "🟢 مؤكد",
                     "done": "⚪ منتهي", "draft": "◻️ مسودة", "to_close": "🔵 للإغلاق"}
        fc1, fc2 = st.columns([2, 3])
        state_f = fc1.selectbox("الحالة", list(MO_STATES.keys()),
                                format_func=lambda k: MO_STATES[k],
                                index=1, key="mo_state_f")  # default: جاري
        query_f = fc2.text_input("بحث", key="mo_query_f", placeholder="منتج أو رقم الأمر")

        running_map = oc.get_running_map(uid, pwd)
        STATE_CHIP = {
            "progress":  ("جاري",    "#D4A853", "rgba(212,168,83,.15)"),
            "confirmed": ("مؤكد",    "#7FB069", "rgba(127,176,105,.15)"),
            "to_close":  ("للإغلاق", "#6FA8DC", "rgba(111,168,220,.15)"),
            "done":      ("منتهي",   "#9BA58F", "rgba(155,165,143,.12)"),
            "draft":     ("مسودة",   "#888",    "rgba(255,255,255,.08)"),
        }
        for mo in oc.get_mos(uid, pwd, state_f, query_f):
            label, s_col, s_bg = STATE_CHIP.get(mo["state"], (mo["state"], "#888", "rgba(255,255,255,.08)"))
            worker = running_map.get(mo["id"])
            worker_box = (f"<span style='background:rgba(127,176,105,.15);color:#7FB069;"
                          f"padding:4px 10px;border-radius:8px;font-size:11px'>🟢 {worker}</span>") if worker else ""
            card = (
                "<div class='task-row' style='margin-bottom:4px'>"
                "<div style='display:flex;justify-content:space-between;align-items:center'>"
                f"<span style='font-family:monospace;font-size:11px;background:rgba(212,168,83,.12);color:#D4A853;padding:3px 9px;border-radius:7px'>{mo['name']}</span>"
                f"<span style='background:{s_bg};color:{s_col};padding:3px 11px;border-radius:20px;font-size:11px;font-weight:600'>{label}</span>"
                "</div>"
                f"<div style='font-size:15px;font-weight:700;margin:9px 0 7px'>{mo['product']}</div>"
                "<div style='display:flex;gap:6px;flex-wrap:wrap'>"
                f"<span style='background:rgba(255,255,255,.07);padding:4px 10px;border-radius:8px;font-size:11px'>📦 {mo['qty']:g} وحدة</span>"
                f"<span style='background:rgba(255,255,255,.07);padding:4px 10px;border-radius:8px;font-size:11px'>📅 {mo['date']}</span>"
                f"{worker_box}"
                "</div></div>"
            )
            st.markdown(card, unsafe_allow_html=True)
            if st.button("إدارة الأمر ←", key=f"mo_{mo['id']}", use_container_width=True):
                ss.mo_open = mo["id"]
                st.rerun()
            st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)

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
        # Product type: category IDs in Odoo (Raw=9 incl. Herbs/Oils, RTF=7, FG=2, PKG=6)
        PROD_TYPES = {"all": "كل الأنواع", 9: "🌿 RAW خام", 7: "⚗️ RTF نصف مصنع",
                      2: "📦 FG منتج نهائي", 6: "🎁 PKG تغليف"}
        locs = oc.get_stock_locations(uid, pwd)
        default_loc = next((i + 1 for i, l in enumerate(locs) if "SJ" in l and "RM-Storage" in l), 0)
        lc1, lc2 = st.columns(2)
        type_f = lc1.selectbox("النوع", list(PROD_TYPES.keys()),
                               format_func=lambda k: PROD_TYPES[k], key="inv_type_f")
        loc_f = lc2.selectbox("الموقع", ["all"] + locs,
                              format_func=lambda x: "كل المواقع" if x == "all" else x.split("/")[-1],
                              index=default_loc, key="inv_loc_f")  # default: SJ/RM-Storage
        q = st.text_input(t("search"), key="inv_search")
        for item in oc.get_inventory(uid, pwd, q, loc_f, type_f):
            color = "#A32D2D" if item["qty"] == 0 else "#D4A853"
            st.markdown(f"<div class='task-row' style='display:flex;justify-content:space-between'><span><b>{item['name']}</b><br><span style='color:#888;font-size:11px'>{item['loc']}</span></span><span style='font-size:18px;font-weight:700;color:{color}'>{item['qty']:g}</span></div>", unsafe_allow_html=True)


    # ── Tab 4: Transfers ──
    with tab4:
        st.markdown("**📥 استلام المشتريات** <span style='opacity:.5;font-size:11px'>(مورد ← الاستلام)</span>", unsafe_allow_html=True)
        receipts = oc.get_pending_receipts(uid, pwd)
        if not receipts:
            st.caption("لا توجد استلامات معلقة")
        for r in receipts:
            lines_txt = " · ".join(f"{l['name'][:22]} ×{l['qty']:g}" for l in r["lines"][:3])
            card = (
                "<div class='task-row' style='margin-bottom:4px'>"
                "<div style='display:flex;justify-content:space-between;align-items:center'>"
                f"<span style='font-family:monospace;font-size:11px;background:rgba(212,168,83,.12);color:#D4A853;padding:3px 9px;border-radius:7px'>{r['name']}</span>"
                f"<span style='background:rgba(255,255,255,.07);padding:3px 10px;border-radius:8px;font-size:11px'>📅 {r['date']}</span>"
                "</div>"
                f"<div style='font-weight:700;margin:8px 0 5px'>{r['supplier']}</div>"
                f"<div style='font-size:11px;opacity:.7'>{r['po']} — {lines_txt}</div>"
                "</div>"
            )
            st.markdown(card, unsafe_allow_html=True)
            if st.button("📥 استلام كامل", key=f"rcv_{r['id']}", use_container_width=True):
                ok, msg = oc.validate_picking(uid, pwd, r["id"])
                _flash(ok, msg)
                if ok: st.rerun()
            st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin:12px 0'>", unsafe_allow_html=True)
        st.markdown("**🔄 تحويل داخلي**")
        route_key = st.selectbox("المسار",
            list(oc.TRANSFER_ROUTES.keys()),
            format_func=lambda k: oc.TRANSFER_ROUTES[k]["label"],
            key="tr_route")
        route = oc.TRANSFER_ROUTES[route_key]
        avail = oc.get_products_at_location(uid, pwd, route["src"])
        if not avail:
            st.info("لا يوجد مخزون في موقع المصدر")
        else:
            pnames = [f"{p['name']} (متاح {p['available']:g})" for p in avail]
            pi = st.selectbox("المنتج", range(len(pnames)),
                              format_func=lambda i: pnames[i], key="tr_prod")
            chosen = avail[pi]
            qty = st.number_input("الكمية", min_value=0.01,
                                  max_value=float(chosen["available"]),
                                  value=float(chosen["available"]), key="tr_qty")
            if st.button("🔄 نفّذ التحويل", type="primary", use_container_width=True, key="tr_go"):
                ok, msg = oc.create_transfer(uid, pwd, route_key, chosen["id"], qty)
                _flash(ok, msg)

# ── PROCUREMENT ──────────────────────────────────────────────
def procurement_screen():
    uid, pwd = ss.uid, ss.pwd

    # Sub-page: PO detail
    if ss.get("po_open"):
        _po_detail(uid, pwd, ss.po_open)
        return

    tab1, tab2, tab3 = st.tabs(["🛒 أوامر الشراء", "🧾 المصروفات", "🔄 الاستلام"])

    # ── Tab 1: PO Management ──
    with tab1:
        # Create RFQ
        with st.expander("➕ إنشاء طلب شراء جديد"):
            sups = oc.get_suppliers(uid, pwd)
            sup_names = [s["name"] for s in sups]
            si = st.selectbox("المورّد", range(len(sup_names)),
                              format_func=lambda i: sup_names[i], key="rfq_sup")
            prods = oc.get_purchasable_products(uid, pwd)
            pnames = [f"{p['code']+' ' if p['code'] else ''}{p['name']}" for p in prods]
            # Build up lines in session
            if "rfq_lines" not in ss:
                ss.rfq_lines = []
            lc1, lc2, lc3 = st.columns([3, 1, 1])
            pi = lc1.selectbox("المنتج", range(len(pnames)),
                               format_func=lambda i: pnames[i], key="rfq_prod")
            qty = lc2.number_input("كمية", min_value=1.0, value=1.0, step=1.0, key="rfq_qty")
            price = lc3.number_input("سعر", min_value=0.0, value=float(prods[pi]["cost"]) if prods else 0.0, step=1.0, key="rfq_price")
            if st.button("➕ أضف المنتج", key="rfq_addline", use_container_width=True):
                ss.rfq_lines.append({"pid": prods[pi]["id"], "name": prods[pi]["name"], "qty": qty, "price": price})
            # Show added lines
            if ss.rfq_lines:
                total = sum(l["qty"] * l["price"] for l in ss.rfq_lines)
                for idx, l in enumerate(ss.rfq_lines):
                    st.markdown(f"<div class='task-row' style='display:flex;justify-content:space-between;padding:6px 12px'><span>{l['name'][:28]} ×{l['qty']:g}</span><span style='color:#D4A853'>{l['qty']*l['price']:,.0f}</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:left;font-weight:700;color:#D4A853;margin:6px 0'>الإجمالي: {total:,.0f} د.ل</div>", unsafe_allow_html=True)
                cc1, cc2 = st.columns(2)
                if cc1.button("🗑️ مسح", key="rfq_clear", use_container_width=True):
                    ss.rfq_lines = []; st.rerun()
                if cc2.button("✅ إنشاء الطلب", key="rfq_create", type="primary", use_container_width=True):
                    lines = [(l["pid"], l["qty"], l["price"]) for l in ss.rfq_lines]
                    ok, res = oc.create_rfq(uid, pwd, sups[si]["id"], lines)
                    if ok:
                        ss.rfq_lines = []
                        st.success(f"تم إنشاء {res['name']} ✓")
                        ss.po_open = res["id"]; st.rerun()
                    else:
                        st.error(res)

        st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)
        f1, f2 = st.columns([2, 3])
        po_state = f1.selectbox("الحالة", ["all", "draft", "sent", "purchase", "done", "cancel"],
            format_func=lambda k: {"all": "الكل", "draft": "طلب عرض", "sent": "مُرسل",
                                   "purchase": "مؤكد", "done": "مُغلق", "cancel": "ملغي"}[k],
            index=3, key="po_state_f")  # default: confirmed
        po_q = f2.text_input(t("search"), key="po_q", placeholder="رقم أو مورّد")
        pos = oc.get_pos(uid, pwd, po_state, po_q)
        st.caption(f"{len(pos)} أمر")
        for p in pos:
            meta = oc.PO_STATE.get(p["state"], {"ar": p["state"], "color": "#9BA58F", "bg": "rgba(255,255,255,.07)"})
            rc = oc.RECEIPT_STATE.get(p["receipt"], "")
            rc_chip = f"<span style='background:rgba(127,176,105,.12);color:#7FB069;padding:3px 9px;border-radius:8px;font-size:10px'>📦 {rc}</span>" if rc else ""
            card = (
                "<div class='task-row' style='margin-bottom:4px'>"
                "<div style='display:flex;justify-content:space-between;align-items:center'>"
                f"<span style='font-family:monospace;font-size:11px;background:rgba(212,168,83,.12);color:#D4A853;padding:3px 9px;border-radius:7px'>{p['name']}</span>"
                f"<span style='background:{meta['bg']};color:{meta['color']};padding:3px 11px;border-radius:20px;font-size:11px;font-weight:600'>{meta['ar']}</span>"
                "</div>"
                f"<div style='font-size:15px;font-weight:700;margin:9px 0 6px'>{p['supplier']}</div>"
                "<div style='display:flex;gap:6px;flex-wrap:wrap;align-items:center'>"
                f"<span style='background:rgba(255,255,255,.07);padding:4px 10px;border-radius:8px;font-size:11px'>💰 {p['total']:,.0f} {p['currency']}</span>"
                f"<span style='background:rgba(255,255,255,.07);padding:4px 10px;border-radius:8px;font-size:11px'>📅 {p['date']}</span>"
                f"{rc_chip}</div></div>"
            )
            st.markdown(card, unsafe_allow_html=True)
            if st.button("إدارة الأمر ←", key=f"po_{p['id']}", use_container_width=True):
                ss.po_open = p["id"]; st.rerun()
            st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)

    # ── Tab 2: Expenses (with camera) ──
    with tab2:
        _expenses_tab(uid, pwd)

    # ── Tab 3: Receiving / Transfers ──
    with tab3:
        _receiving_tab(uid, pwd)


def _po_detail(uid, pwd, po_id):
    if st.button("← أوامر الشراء"):
        ss.po_open = None; st.rerun()
    d = oc.get_po_detail(uid, pwd, po_id)
    if not d:
        st.error("غير موجود"); return
    meta = oc.PO_STATE.get(d["state"], {"ar": d["state"]})
    st.markdown(f"""<div class='greeting'>
        <div style='display:flex;justify-content:space-between;align-items:start'>
          <div>
            <div style='font-family:monospace;font-size:12px;opacity:.6'>{d['name']}</div>
            <div style='font-size:18px;font-weight:700'>{d['supplier']}</div>
            <div style='font-size:12px;opacity:.7;margin-top:2px'>{meta['ar']} · {d['date']}</div>
          </div>
          <div style='text-align:center;background:rgba(255,255,255,.08);border-radius:10px;padding:8px 14px'>
            <div style='font-size:18px;font-weight:700;color:#D4A853'>{d['total']:,.0f}</div>
            <div style='font-size:9px;opacity:.6'>{d['currency']}</div>
          </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # Actions
    if d["state"] in ("draft", "sent"):
        c1, c2 = st.columns(2)
        if c1.button("🟢 تأكيد الأمر", use_container_width=True, type="primary"):
            ok, msg = oc.po_confirm(uid, pwd, po_id)
            _flash(ok, msg)
            if ok: st.rerun()
        if c2.button("✖️ إلغاء", use_container_width=True):
            ok, msg = oc.po_cancel(uid, pwd, po_id)
            _flash(ok, msg)
            if ok: st.rerun()

    # ── Document capture (supplier invoice / delivery note) ──
    with st.expander("📎 إرفاق مستند (فاتورة المورّد / إيصال)"):
        atts = oc.get_po_attachments(uid, pwd, po_id)
        if atts:
            for a in atts:
                st.markdown(f"<div class='task-row' style='display:flex;justify-content:space-between;padding:6px 12px'><span>📄 {a['name']}</span><span style='opacity:.5;font-size:11px'>{a['date']}</span></div>", unsafe_allow_html=True)
        po_photo = _rear_camera("po_cam", "📸 صوّر المستند")
        if st.button("إرفاق الصورة", key="po_attach", use_container_width=True):
            if po_photo:
                ok, msg = oc.attach_po_photo(uid, pwd, po_id, po_photo)
                _flash(ok, msg)
                if ok: st.rerun()
            else:
                st.error("التقط صورة أولاً")

    st.markdown("**المنتجات**")
    for l in d["lines"]:
        if not l["qty"]:
            continue
        recv_pct = min(100, round(l["received"] / l["qty"] * 100)) if l["qty"] else 0
        rc_col = "#7FB069" if recv_pct >= 100 else "#D4A853" if recv_pct > 0 else "#9BA58F"
        st.markdown(f"""<div class='task-row'>
            <div style='display:flex;justify-content:space-between'>
              <b>{l['name']}</b><span style='color:#D4A853'>{l['subtotal']:,.0f}</span>
            </div>
            <div style='font-size:11px;opacity:.7;margin-top:3px'>
              {l['qty']:g} × {l['price']:,.2f} · <span style='color:{rc_col}'>مستلم {l['received']:g}/{l['qty']:g}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    if d["receipts"]:
        st.markdown("**الاستلامات**")
        for r in d["receipts"]:
            st_ar = {"done": "✅ تم", "assigned": "🟡 جاهز", "confirmed": "🟠 بانتظار", "cancel": "ملغي"}.get(r["state"], r["state"])
            st.markdown(f"<div class='task-row' style='display:flex;justify-content:space-between'><span style='font-family:monospace;font-size:12px'>{r['name']}</span><span style='font-size:11px'>{st_ar}</span></div>", unsafe_allow_html=True)

    # ── Payment lifecycle ──
    if d["state"] == "purchase":
        st.markdown("**الفوترة والدفع**")
        pay = oc.get_po_payment(uid, pwd, po_id)
        if pay:
            if pay["can_bill"] and not pay["bills"]:
                st.info("الطلب مؤكد وجاهز للفوترة")
                if st.button("🧾 إنشاء الفاتورة", use_container_width=True, type="primary"):
                    ok, msg = oc.create_bill(uid, pwd, po_id)
                    _flash(ok, msg)
                    if ok: st.rerun()
            for b in pay["bills"]:
                pay_col = {"مدفوع": "#7FB069", "مدفوع جزئياً": "#D4A853"}.get(b["payment_ar"], "#E07070")
                state_ar = {"draft": "مسودة", "posted": "مُرحّلة", "cancel": "ملغاة"}.get(b["state"], b["state"])
                st.markdown(f"""<div class='task-row'>
                    <div style='display:flex;justify-content:space-between'>
                      <span style='font-family:monospace;font-size:12px'>{b['name']}</span>
                      <span style='color:{pay_col};font-size:12px;font-weight:600'>{b['payment_ar']}</span>
                    </div>
                    <div style='font-size:11px;opacity:.7;margin-top:3px'>{state_ar} · {b['total']:,.0f} د.ل{f" · متبقّي {b['residual']:,.0f}" if b['residual'] else ""}</div>
                </div>""", unsafe_allow_html=True)
                if b["payment"] not in ("paid", "in_payment"):
                    if st.button("💵 تأكيد الدفع", key=f"pay_{b['id']}", use_container_width=True, type="primary"):
                        ok, msg = oc.confirm_payment(uid, pwd, b["id"])
                        _flash(ok, msg)
                        if ok: st.rerun()


def _expenses_tab(uid, pwd):
    with st.expander("➕ تسجيل مصروف جديد"):
        cats = oc.get_expense_categories(uid, pwd)
        if not cats:
            st.info("لا توجد فئات مصروفات")
        else:
            cat_names = [c["name"] for c in cats]
            ci = st.selectbox("الفئة", range(len(cat_names)), format_func=lambda i: cat_names[i], key="exp_cat")
            desc = st.text_input("الوصف", key="exp_desc", placeholder="مثال: فاتورة كهرباء السراج")
            amount = st.number_input("المبلغ (د.ل)", min_value=0.0, step=5.0, key="exp_amount")
            # Receipt capture — defaults to the rear camera
            photo_bytes = _rear_camera("exp_cam", "📸 صوّر الإيصال (اختياري)")
            if st.button("حفظ المصروف", type="primary", use_container_width=True, key="exp_save"):
                if not desc.strip() or amount <= 0:
                    st.error("أدخل الوصف والمبلغ")
                else:
                    ok, msg = oc.create_expense(uid, pwd, cats[ci]["id"], desc, amount, photo_bytes)
                    if ok:
                        st.success(msg); st.rerun()
                    else:
                        st.error(msg)

    st.markdown("**مصروفاتي**")
    exps = oc.get_my_expenses(uid, pwd)
    if not exps:
        st.caption("لا توجد مصروفات")
    for e in exps:
        st_col = {"مدفوع": "#7FB069", "معتمد": "#7FB069", "مرفوض": "#E07070",
                  "قيد المراجعة": "#D4A853"}.get(e["state"], "#9BA58F")
        st.markdown(f"""<div class='task-row'>
            <div style='display:flex;justify-content:space-between'>
              <b>{e['name']}</b><span style='color:#D4A853'>{e['amount']:,.0f}</span>
            </div>
            <div style='font-size:11px;margin-top:3px'>
              <span style='opacity:.6'>{e['category']} · {e['date']}</span>
              <span style='color:{st_col};float:left'>{e['state']}</span>
            </div>
        </div>""", unsafe_allow_html=True)


def _receiving_tab(uid, pwd):
    st.markdown("**📥 استلام المشتريات** <span style='opacity:.5;font-size:11px'>(مورد ← الاستلام)</span>", unsafe_allow_html=True)
    receipts = oc.get_pending_receipts(uid, pwd)
    if not receipts:
        st.caption("لا توجد استلامات معلقة")
    for r in receipts:
        lines_txt = " · ".join(f"{l['name'][:22]} ×{l['qty']:g}" for l in r["lines"][:3])
        card = (
            "<div class='task-row' style='margin-bottom:4px'>"
            "<div style='display:flex;justify-content:space-between;align-items:center'>"
            f"<span style='font-family:monospace;font-size:11px;background:rgba(212,168,83,.12);color:#D4A853;padding:3px 9px;border-radius:7px'>{r['name']}</span>"
            f"<span style='background:rgba(255,255,255,.07);padding:3px 10px;border-radius:8px;font-size:11px'>📅 {r['date']}</span>"
            "</div>"
            f"<div style='font-weight:700;margin:8px 0 5px'>{r['supplier']}</div>"
            f"<div style='font-size:11px;opacity:.7'>{r['po']} — {lines_txt}</div>"
            "</div>"
        )
        st.markdown(card, unsafe_allow_html=True)
        if st.button("📥 استلام كامل", key=f"prcv_{r['id']}", use_container_width=True):
            ok, msg = oc.validate_picking(uid, pwd, r["id"])
            _flash(ok, msg)
            if ok: st.rerun()
        st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin:12px 0'>", unsafe_allow_html=True)
    st.markdown("**🔄 تحويل داخلي**")
    route_key = st.selectbox("المسار", list(oc.TRANSFER_ROUTES.keys()),
        format_func=lambda k: oc.TRANSFER_ROUTES[k]["label"], key="prc_route")
    route = oc.TRANSFER_ROUTES[route_key]
    avail = oc.get_products_at_location(uid, pwd, route["src"])
    if not avail:
        st.info("لا يوجد مخزون في موقع المصدر")
    else:
        pnames = [f"{p['name']} (متاح {p['available']:g})" for p in avail]
        pi = st.selectbox("المنتج", range(len(pnames)), format_func=lambda i: pnames[i], key="prc_prod")
        chosen = avail[pi]
        qty = st.number_input("الكمية", min_value=0.01, max_value=float(chosen["available"]),
                              value=float(chosen["available"]), key="prc_qty")
        if st.button("🔄 نفّذ التحويل", type="primary", use_container_width=True, key="prc_go"):
            ok, msg = oc.create_transfer(uid, pwd, route_key, chosen["id"], qty)
            _flash(ok, msg)


def _procurement_screen_old():
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

    # Sub-page: picking detail with validate
    if ss.get("op_pick_open"):
        _op_picking_detail(uid, pwd, ss.op_pick_open)
        return

    tab1, tab2 = st.tabs(["📤 FG ← يمامة", "🚚 يمامة ← العميل"])

    # ── Stage 1: FG → Yamamah (default ready+waiting, validate) ──
    with tab1:
        st.caption("تجهيز الطلبات وتسليمها ليمامة — الأقدم أولاً")
        S1 = {"ready": "🟡 جاهز/بانتظار", "done": "✅ تم", "all": "الكل"}
        f1c1, f1c2 = st.columns([2, 3])
        s1 = f1c1.selectbox("الحالة", list(S1.keys()), format_func=lambda k: S1[k], key="op_s1_f")
        q1 = f1c2.text_input(t("search"), key="op_s1_q", placeholder="رقم الطلب")
        picks = oc.get_fg_to_yamamah(uid, pwd, s1, q1)
        st.caption(f"{len(picks)} طلب")
        for p in picks:
            st_ar = {"assigned":"🟡 جاهز","confirmed":"🟠 بانتظار","waiting":"⚪ ينتظر","done":"✅ تم"}.get(p["state"], p["state"])
            card = (
                "<div class='task-row' style='margin-bottom:4px'>"
                "<div style='display:flex;justify-content:space-between;align-items:center'>"
                f"<span style='font-family:monospace;font-size:11px;background:rgba(212,168,83,.12);color:#D4A853;padding:3px 9px;border-radius:7px'>{p['order']}</span>"
                f"<span style='font-size:11px'>{st_ar}</span></div>"
                f"<div style='font-weight:700;margin:7px 0 3px'>{p['customer']}</div>"
                f"<div style='font-size:11px;opacity:.6'>{p['name']} · {p['date']}</div>"
                "</div>"
            )
            st.markdown(card, unsafe_allow_html=True)
            if st.button("عرض وتأكيد ←", key=f"op1_{p['id']}", use_container_width=True):
                ss.op_pick_open = p["id"]; st.rerun()
            st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

    # ── Stage 2: Yamamah → Customer (live API status) ──
    with tab2:
        st.caption("الشحنات لدى يمامة — حالة API المباشرة، الأقدم أولاً")
        S2 = {"all": "الكل", "sent": "🚚 قيد التوصيل", "delivered": "✅ تم التسليم", "returned": "↩️ مرتجع"}
        f2c1, f2c2 = st.columns([2, 3])
        s2 = f2c1.selectbox("الحالة", list(S2.keys()), format_func=lambda k: S2[k], key="op_s2_f")
        q2 = f2c2.text_input(t("search"), key="op_s2_q", placeholder="طلب أو اسم العميل")
        ships = oc.get_yamamah_to_customer(uid, pwd, s2, q2)
        st.caption(f"{len(ships)} شحنة")
        for s in ships:
            meta = oc.YAMAMAH_STATUS.get(s["api_status"], {"color": "#9BA58F", "bg": "rgba(255,255,255,.07)"})
            track = f"<a href='{s['tracking_url']}' target='_blank' style='color:#7FB069;font-size:11px'>🔗 {s['code']}</a>" if s["tracking_url"] else ""
            cod = f" · COD {s['cod']:,.0f}" if s["cod"] else ""
            card = (
                "<div class='task-row' style='margin-bottom:4px'>"
                "<div style='display:flex;justify-content:space-between;align-items:start'>"
                f"<div><span style='font-family:monospace;font-size:11px;color:#D4A853'>{s['order']}</span><br>"
                f"<b>{s['recipient']}</b><br>"
                f"<span style='font-size:11px;opacity:.6'>{s['zone']} · {s['mobile']}{cod}</span></div>"
                f"<span style='padding:3px 9px;border-radius:20px;font-size:10px;background:{meta['bg']};color:{meta['color']};white-space:nowrap'>{s['api_status']}</span>"
                f"</div><div style='margin-top:5px'>{track}</div></div>"
            )
            st.markdown(card, unsafe_allow_html=True)


def sales_screen():
    uid, pwd = ss.uid, ss.pwd
    if ss.get("so_open"):
        _so_detail(uid, pwd, ss.so_open)
        return

    # ── Create new sales order ──
    with st.expander("➕ إنشاء طلب بيع جديد"):
        _create_so_form(uid, pwd)

    st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)
    st.markdown("**طلبات البيع**")
    f1, f2 = st.columns([2, 3])
    so_state = f1.selectbox("الحالة", ["sale", "draft", "sent", "all", "cancel"],
        format_func=lambda k: {"sale": "مؤكد", "draft": "مسودة", "sent": "عرض سعر",
                               "all": "الكل", "cancel": "ملغي"}[k], key="so_state_f")
    so_q = f2.text_input(t("search"), key="so_q", placeholder="رقم أو عميل")
    sos = oc.get_sales_orders(uid, pwd, so_state, so_q)
    st.caption(f"{len(sos)} طلب")

    for s in sos:
        meta = oc.SO_STATE.get(s["state"], {"ar": s["state"], "color": "#9BA58F", "bg": "rgba(255,255,255,.07)"})
        # Shipment indicator
        if s["ship_count"] == 0 and s["state"] == "sale":
            ship_chip = "<span style='background:rgba(212,168,83,.14);color:#D4A853;padding:3px 9px;border-radius:8px;font-size:10px'>⚠️ لم تُرسل ليمامة</span>"
        elif s["has_tracking"]:
            ship_chip = f"<span style='background:rgba(127,176,105,.14);color:#7FB069;padding:3px 9px;border-radius:8px;font-size:10px'>🚚 {s['ship_status'][:18]}</span>"
        elif s["ship_count"] > 0:
            ship_chip = "<span style='background:rgba(224,112,112,.12);color:#E07070;padding:3px 9px;border-radius:8px;font-size:10px'>⚠️ خطأ شحنة</span>"
        else:
            ship_chip = ""
        card = (
            "<div class='task-row' style='margin-bottom:4px'>"
            "<div style='display:flex;justify-content:space-between;align-items:center'>"
            f"<span style='font-family:monospace;font-size:11px;background:rgba(212,168,83,.12);color:#D4A853;padding:3px 9px;border-radius:7px'>{s['name']}</span>"
            f"<span style='background:{meta['bg']};color:{meta['color']};padding:3px 11px;border-radius:20px;font-size:11px;font-weight:600'>{meta['ar']}</span>"
            "</div>"
            f"<div style='font-size:15px;font-weight:700;margin:9px 0 6px'>{s['customer']}</div>"
            "<div style='display:flex;gap:6px;flex-wrap:wrap;align-items:center'>"
            f"<span style='background:rgba(255,255,255,.07);padding:4px 10px;border-radius:8px;font-size:11px'>💰 {s['total']:,.0f}</span>"
            f"<span style='background:rgba(255,255,255,.07);padding:4px 10px;border-radius:8px;font-size:11px'>📅 {s['date']}</span>"
            f"{ship_chip}</div></div>"
        )
        st.markdown(card, unsafe_allow_html=True)
        if st.button("فتح الطلب ←", key=f"so_{s['id']}", use_container_width=True):
            ss.so_open = s["id"]; st.rerun()
        st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)


def _create_so_form(uid, pwd):
    # ── Customer: live search across ALL Odoo contacts by phone/name ──
    st.markdown("<div style='font-size:12px;opacity:.7'>👤 العميل</div>", unsafe_allow_html=True)
    cust_q = st.text_input("ابحث برقم الهاتف أو الاسم", key="so_cust_q",
                           placeholder="اكتب رقم الهاتف أو الاسم...", label_visibility="collapsed")
    customer_id = None
    new_cust = None

    if "so_selected_cust" not in ss:
        ss.so_selected_cust = None

    if ss.so_selected_cust:
        # A customer is chosen — show it with a change button
        sc = ss.so_selected_cust
        cc1, cc2 = st.columns([4, 1])
        cc1.markdown(f"<div class='task-row' style='padding:8px 12px'>✅ <b>{sc['name']}</b> · {sc['mobile']}</div>", unsafe_allow_html=True)
        if cc2.button("تغيير", key="so_cust_change", use_container_width=True):
            ss.so_selected_cust = None; st.rerun()
        customer_id = sc["id"]
    elif cust_q and len(cust_q.strip()) >= 2:
        matches = oc.search_customers(uid, pwd, cust_q)
        if matches:
            st.caption(f"{len(matches)} نتيجة — اختر العميل")
            for m in matches:
                if st.button(f"{m['name']} · {m['mobile']}", key=f"pickcust_{m['id']}", use_container_width=True):
                    ss.so_selected_cust = m; st.rerun()
        else:
            # No contact found → offer create new
            st.info("لا يوجد عميل بهذا الرقم — أنشئ عميلاً جديداً")
            digits = "".join(ch for ch in cust_q if ch.isdigit())
            nc_name = st.text_input("اسم العميل", key="so_nc_name")
            nc_phone = st.text_input("الهاتف *", key="so_nc_phone",
                                     value=cust_q if digits else "",
                                     placeholder="+218 9X XXXXXXX")
            nc_mobile = st.text_input("الجوال (اختياري)", key="so_nc_mobile",
                                      placeholder="يُستخدم الهاتف إذا تُرك فارغاً")
            nc_addr = st.text_input("العنوان (اختياري)", key="so_nc_addr")
            new_cust = (nc_name, nc_phone, nc_addr, nc_mobile)
    else:
        st.caption("ابدأ بكتابة رقم الهاتف أو الاسم للبحث في جهات الاتصال")

    st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)

    # ── Products: inline rows (product + qty + live price display) ──
    st.markdown("<div style='font-size:12px;opacity:.7'>🛍️ المنتجات</div>", unsafe_allow_html=True)
    prods = _cached_sellable_products(uid, pwd)
    pnames = ["— اختر —"] + [f"{p['code']+' ' if p['code'] else ''}{p['name']}" for p in prods]

    # Start with 3 rows; "add another" grows the count
    if "so_rowcount" not in ss:
        ss.so_rowcount = 3

    # Column header
    hc1, hc2, hc3 = st.columns([3, 1, 1.2])
    hc1.markdown("<div style='font-size:10px;opacity:.5'>المنتج</div>", unsafe_allow_html=True)
    hc2.markdown("<div style='font-size:10px;opacity:.5'>الكمية</div>", unsafe_allow_html=True)
    hc3.markdown("<div style='font-size:10px;opacity:.5;text-align:left'>السعر (د.ل)</div>", unsafe_allow_html=True)

    built_lines = []
    running_total = 0.0
    for row in range(ss.so_rowcount):
        rc1, rc2, rc3 = st.columns([3, 1, 1.2])
        sel = rc1.selectbox("م", range(len(pnames)),
                            format_func=lambda i: pnames[i],
                            key=f"so_row_prod_{row}", label_visibility="collapsed")
        qty = rc2.number_input("ك", min_value=1.0, value=1.0, step=1.0,
                               key=f"so_row_qty_{row}", label_visibility="collapsed")
        if sel > 0:
            prod = prods[sel - 1]  # offset for the "— اختر —" placeholder
            line_price = float(prod["price"])
            line_total = line_price * qty
            running_total += line_total
            # Non-editable price display — reflects the chosen product live
            rc3.markdown(
                f"<div style='background:rgba(212,168,83,.10);border:1px solid rgba(212,168,83,.25);"
                f"border-radius:8px;padding:7px 10px;text-align:left;color:#D4A853;font-weight:600;"
                f"font-variant-numeric:tabular-nums'>{line_price:,.0f}</div>",
                unsafe_allow_html=True)
            built_lines.append({"pid": prod["id"], "name": prod["name"],
                                "qty": qty, "price": line_price})
        else:
            rc3.markdown(
                "<div style='background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);"
                "border-radius:8px;padding:7px 10px;text-align:left;opacity:.35'>—</div>",
                unsafe_allow_html=True)

    # Add another product line
    ac1, ac2 = st.columns([1, 1])
    if ac1.button("➕ منتج آخر", key="so_addrow", use_container_width=True):
        ss.so_rowcount += 1; st.rerun()
    if ss.so_rowcount > 3 and ac2.button("➖ أقل", key="so_delrow", use_container_width=True):
        ss.so_rowcount -= 1; st.rerun()

    # Store the built lines for the create action
    ss.so_lines = built_lines
    if built_lines:
        # Optional order-wide discount (percentage)
        discount_pct = st.number_input("خصم (%)", min_value=0.0, max_value=100.0,
                                       value=0.0, step=5.0, key="so_discount",
                                       help="خصم يُطبّق على كامل الطلب")
        disc_amount = running_total * discount_pct / 100.0
        net_total = running_total - disc_amount
        if discount_pct > 0:
            st.markdown(
                f"<div style='text-align:left;margin:6px 0'>"
                f"<div style='font-size:12px;opacity:.6'>المجموع الفرعي: {running_total:,.0f} د.ل</div>"
                f"<div style='font-size:12px;color:#E07070'>الخصم ({discount_pct:g}%): −{disc_amount:,.0f} د.ل</div>"
                f"<div style='font-weight:700;color:#D4A853;font-size:15px;margin-top:2px'>"
                f"الإجمالي بعد الخصم: {net_total:,.0f} د.ل</div></div>",
                unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div style='text-align:left;font-weight:700;color:#D4A853;margin:8px 0'>"
                f"الإجمالي: {running_total:,.0f} د.ل</div>", unsafe_allow_html=True)
    else:
        discount_pct = 0.0

    # ── Delivery (Accurate/Yamamah) fields ──
    st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:12px;opacity:.7'>🚚 بيانات الشحن</div>", unsafe_allow_html=True)

    # Delivery company — default Alyamama
    companies = _cached_delivery_companies(uid, pwd)
    default_dc = next((i for i, c in enumerate(companies) if "yamama" in c["name"].lower() or "لياما" in c["name"]), 0)
    dci = st.selectbox("شركة التوصيل", range(len(companies)),
                       format_func=lambda i: companies[i]["name"],
                       index=default_dc, key="so_dc")
    delivery_company_id = companies[dci]["id"]

    # Shipping service — required at confirmation; default شحن عادى
    services = _cached_services(uid, pwd)
    default_svc = next((i for i, s in enumerate(services) if "عاد" in s["name"]), 0)
    svci = st.selectbox("خدمة الشحن", range(len(services)),
                        format_func=lambda i: services[i]["name"],
                        index=default_svc, key="so_svc")
    service_id = services[svci]["id"]

    # Zone (parent)
    zone_q = st.text_input("ابحث عن المنطقة", key="so_zone_q", placeholder="مثال: طرابلس")
    zones = _cached_zones(uid, pwd, zone_q) if zone_q else []
    zone_id = None
    subzone_id = None
    if zones:
        znames = [z["name"] for z in zones]
        zi = st.selectbox("المنطقة", range(len(znames)), format_func=lambda i: znames[i], key="so_zone")
        zone_id = zones[zi]["id"]
        # Sub-zone (children of chosen zone)
        subs = _cached_subzones(uid, pwd, zone_id)
        if subs:
            snames = [s["name"] for s in subs]
            si_ = st.selectbox("المنطقة الفرعية", range(len(snames)),
                               format_func=lambda i: snames[i], key="so_subzone")
            subzone_id = subs[si_]["id"]
        else:
            st.caption("لا توجد مناطق فرعية لهذه المنطقة")

    pay_type = st.selectbox("نوع الدفع", ["COLC", "CASH", "CRDT"],
        format_func=lambda k: {"COLC": "دفع عند الاستلام (COD)", "CASH": "مدفوع مسبقاً", "CRDT": "آجل"}[k],
        key="so_paytype")

    cc1, cc2 = st.columns(2)
    if cc1.button("🗑️ مسح", key="so_clear", use_container_width=True):
        ss.so_lines = []
        ss.so_rowcount = 3
        ss.so_selected_cust = None
        ss.so_draft_snapshot = None
        st.rerun()
    if cc2.button("✅ إنشاء الطلب", key="so_create", type="primary", use_container_width=True):
        if not ss.so_lines:
            st.error("أضف منتجاً واحداً على الأقل")
        elif customer_id is None and new_cust is None:
            st.error("ابحث عن العميل واختره، أو أنشئ عميلاً جديداً")
        else:
            # Resolve customer (selected existing or new)
            if new_cust is not None:
                if not new_cust[0].strip() or not new_cust[1].strip():
                    st.error("أدخل اسم العميل والهاتف"); return
                # new_cust = (name, phone, address, mobile_optional)
                ok, cid = oc.create_customer(uid, pwd, new_cust[0], new_cust[1],
                                             new_cust[2], mobile=new_cust[3])
                if not ok:
                    st.error(cid); return
                customer_id = cid
            lines = [(l["pid"], l["qty"], l["price"]) for l in ss.so_lines]
            delivery = {"zone_id": zone_id, "subzone_id": subzone_id,
                        "payment_type": pay_type, "delivery_company_id": delivery_company_id,
                        "service_id": service_id}
            ok, res = oc.create_sales_order(uid, pwd, customer_id, lines, delivery,
                                            discount=discount_pct)
            if ok:
                # Order created in Odoo. Do NOT wipe the form yet — only clear
                # after the order is safely confirmed, so a failed confirm +
                # going back never strands the user with an empty form.
                ss.so_open = res["id"]
                ss.so_just_created = res["id"]  # detail page will try to confirm
                st.success(f"تم إنشاء {res['name']} ✓")
                st.rerun()
            else:
                # Creation failed — form data is untouched, user can retry
                st.error(res)


def _so_detail(uid, pwd, so_id):
    if st.button("← طلبات البيع"):
        ss.so_open = None; st.rerun()
    d = oc.get_so_detail(uid, pwd, so_id)
    if not d:
        st.error("غير موجود"); return
    meta = oc.SO_STATE.get(d["state"], {"ar": d["state"]})

    # If this order was just created, try to confirm it once, automatically.
    # On success → the form draft is safe to clear. On failure → keep the
    # form intact so going back never loses the user's work.
    if ss.get("so_just_created") == so_id and d["state"] in ("draft", "sent"):
        ss.so_just_created = None
        with st.spinner("جارٍ تأكيد الطلب..."):
            ok, msg = oc.so_confirm(uid, pwd, so_id)
        if ok:
            ss.so_lines = []
            ss.so_selected_cust = None
            ss.so_rowcount = 3
            st.success(msg)
            st.rerun()
        else:
            # Confirmation failed — form data preserved. Tell the user clearly.
            st.warning("تم إنشاء الطلب لكن التأكيد لم يكتمل. بياناتك محفوظة — "
                       "أصلح الحقول الناقصة أدناه ثم أكّد، أو ارجع لتعديل الطلب.")
            st.error(msg)
    st.markdown(f"""<div class='greeting'>
        <div style='display:flex;justify-content:space-between;align-items:start'>
          <div>
            <div style='font-family:monospace;font-size:12px;opacity:.6'>{d['name']}</div>
            <div style='font-size:18px;font-weight:700'>{d['customer']}</div>
            <div style='font-size:12px;opacity:.7;margin-top:2px'>{meta['ar']} · {d['date']}</div>
          </div>
          <div style='text-align:center;background:rgba(255,255,255,.08);border-radius:10px;padding:8px 14px'>
            <div style='font-size:18px;font-weight:700;color:#D4A853'>{d['total']:,.0f}</div>
            <div style='font-size:9px;opacity:.6'>د.ل</div>
          </div>
        </div>
    </div>""", unsafe_allow_html=True)

    if d["state"] in ("draft", "sent"):
        if st.button("🟢 تأكيد الطلب", use_container_width=True, type="primary"):
            ok, msg = oc.so_confirm(uid, pwd, so_id)
            _flash(ok, msg)
            if ok: st.rerun()

    # ── Shipment / Accurate API status + guidance ──
    st.markdown("**حالة الشحن (يمامة)**")
    sh = d["shipment"]
    if not sh:
        st.info("لم تُنشأ شحنة لهذا الطلب بعد.")
        if d["state"] == "sale":
            if st.button("🚚 إنشاء شحنة يمامة", use_container_width=True, type="primary", key=f"mkship_{so_id}"):
                with st.spinner("جارٍ الإرسال ليمامة..."):
                    ok, msg, info = oc.create_shipment_for_so(uid, pwd, so_id)
                if ok:
                    st.success(msg); st.rerun()
                else:
                    # API error → the guidance panel will render after rerun once
                    # shipment exists; if not created, show the raw guidance now
                    st.error(msg)
                    if info and info.get("state") == "error":
                        st.rerun()
        else:
            st.caption("أكّد الطلب أولاً لإنشاء الشحنة")
    elif sh["stage"] == "ok":
        track = f"<a href='{sh['tracking_url']}' target='_blank' style='color:#7FB069'>🔗 تتبّع {sh['code']}</a>" if sh["tracking_url"] else ""
        st.markdown(f"<div class='task-row'><div style='color:#7FB069;font-weight:700'>✅ {sh['label']}</div><div style='margin-top:6px'>{track}</div></div>", unsafe_allow_html=True)
    elif sh["stage"] == "error" and sh["guidance"]:
        g = sh["guidance"]
        steps_html = "".join(f"<div style='font-size:12px;margin:3px 0'>• {s}</div>" for s in g["steps"])
        st.markdown(f"""<div class='task-row' style='border-color:#E07070'>
            <div style='color:#E07070;font-weight:700;margin-bottom:6px'>⚠️ {g['title']}</div>
            {steps_html}
        </div>""", unsafe_allow_html=True)
        # Guided fix per error type
        if g["fix_type"] == "mobile":
            new_mob = st.text_input("رقم الجوال الصحيح", value=sh["mobile"], key=f"fix_mob_{sh['id']}",
                                    placeholder="+218 9X XXXXXXX")
            c1, c2 = st.columns(2)
            if c1.button("💾 حفظ الرقم", key=f"savemob_{sh['id']}", use_container_width=True):
                ok, msg = oc.fix_shipment_mobile(uid, pwd, sh["id"], new_mob)
                _flash(ok, msg)
            if c2.button("🔄 أعد الإرسال", key=f"resend_{sh['id']}", use_container_width=True, type="primary"):
                ok, msg = oc.resend_shipment(uid, pwd, sh["id"])
                _flash(ok, msg)
                if ok: st.rerun()
        elif g["fix_type"] == "retry":
            if st.button("🔄 أعد المحاولة", key=f"retry_{sh['id']}", use_container_width=True, type="primary"):
                ok, msg = oc.resend_shipment(uid, pwd, sh["id"])
                _flash(ok, msg)
                if ok: st.rerun()
        elif g["fix_type"] == "subzone":
            st.caption("عدّل المنطقة الفرعية في أودو ثم أعد الإرسال")
            if st.button("🔄 أعد الإرسال", key=f"resendsz_{sh['id']}", use_container_width=True, type="primary"):
                ok, msg = oc.resend_shipment(uid, pwd, sh["id"])
                _flash(ok, msg)
                if ok: st.rerun()
    else:
        st.markdown(f"<div class='task-row'><span style='color:{sh['color']}'>{sh['label']}</span></div>", unsafe_allow_html=True)

    st.markdown("**المنتجات**")
    for l in d["lines"]:
        st.markdown(f"<div class='task-row' style='display:flex;justify-content:space-between'><span>{l['name']} <span style='opacity:.5;font-size:11px'>×{l['qty']:g}</span></span><span style='color:#D4A853'>{l['subtotal']:,.0f}</span></div>", unsafe_allow_html=True)


def _op_picking_detail(uid, pwd, picking_id):
    if st.button("← رجوع"):
        ss.op_pick_open = None; st.rerun()
    d = oc.get_picking_detail(uid, pwd, picking_id)
    if not d:
        st.error("غير موجود"); return
    st.markdown(f"""<div class='greeting'>
        <div style='font-family:monospace;font-size:12px;opacity:.6'>{d['order']} · {d['name']}</div>
        <div style='font-size:18px;font-weight:700'>{d['customer']}</div>
        <div style='font-size:12px;opacity:.75;margin-top:4px'>📞 {d['phone']}<br>📍 {d['address']}</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("**المنتجات**")
    for l in d["lines"]:
        st.markdown(f"<div class='task-row' style='display:flex;justify-content:space-between'><span>{l['name']}</span><span style='opacity:.8'>{l['done']:g}/{l['qty']:g}</span></div>", unsafe_allow_html=True)
    if d["state"] not in ("done", "cancel"):
        if st.button("✅ تأكيد التسليم ليمامة", type="primary", use_container_width=True):
            ok, msg = oc.validate_picking(uid, pwd, picking_id)
            if ok:
                st.success(msg); ss.op_pick_open = None; st.rerun()
            else:
                st.error(msg)
    else:
        st.info("تم تأكيد هذا الطلب مسبقاً")


def _operations_screen_old():

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
    if "chat_open" not in ss:
        ss.chat_open = None

    # Chat view takes over the screen when a conversation is open
    if ss.chat_open:
        _chat_view(uid, pwd, ss.chat_open)
        return

    # The conversations inbox IS the CS module — it opens immediately.
    # Tickets and order-status are secondary tools tucked behind a toggle.
    _cs_inbox(uid, pwd)


def _cs_inbox(uid, pwd):
    counts = oc.get_inbox_counts(uid, pwd)

    # Due reminders surface at the top of the inbox
    due = oc.get_due_reminders(uid, pwd)
    if due:
        st.markdown(
            f"<div style='background:rgba(212,168,83,.12);border:1px solid rgba(212,168,83,.35);"
            f"border-radius:10px;padding:8px 12px;margin-bottom:8px'>"
            f"⏰ <b>{len(due)} تذكير مستحق</b></div>", unsafe_allow_html=True)
        for r in due[:5]:
            rm = oc.CHANNEL_META.get(r["channel"], {"icon": "•"})
            if st.button(f"⏰ {rm['icon']} {r['customer']} — {r['note'] or 'متابعة'}",
                         key=f"due_{r['id']}", use_container_width=True):
                ss.chat_open = r["id"]; st.rerun()
        st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)

    st.markdown(f"<div style='font-size:12px;opacity:.7;margin-bottom:6px'>"
                f"📥 {counts['open']} مفتوحة · {counts['unread']} غير مقروءة</div>",
                unsafe_allow_html=True)

    # Filters
    fc1, fc2 = st.columns(2)
    ch_opts = ["all"] + list(oc.CHANNEL_META.keys())
    channel_f = fc1.selectbox("القناة", ch_opts,
        format_func=lambda k: "كل القنوات" if k == "all" else f"{oc.CHANNEL_META[k]['icon']} {oc.CHANNEL_META[k]['ar']}",
        key="cs_channel_f")
    status_f = fc2.selectbox("الحالة", ["all", "open", "answered", "closed"],
        format_func=lambda k: {"all": "الكل", "open": "مفتوحة", "answered": "تم الرد", "closed": "مغلقة"}[k],
        key="cs_status_f")

    convs = oc.get_conversations(uid, pwd, channel_f, status_f)

    # One-time CSS: turn each conversation button into a rich, tappable row
    st.markdown("""<style>
    .conv-row .stButton>button {
        background:#1A231A; border:1px solid #2A3A2A; border-radius:12px;
        padding:11px 14px; width:100%; text-align:right; color:#E8E4D6;
        white-space:pre-line; line-height:1.5; font-weight:400;
        min-height:0; transition:all .12s;
    }
    .conv-row .stButton>button:hover {
        background:#22301F; border-color:#7FB069; }
    .conv-row.unread .stButton>button { border-inline-start:3px solid #E07070; }
    </style>""", unsafe_allow_html=True)

    if not convs:
        st.caption("لا توجد محادثات مطابقة")

    for c in convs:
        m = oc.CHANNEL_META.get(c["channel"], {"icon": "•", "color": "#888", "ar": ""})
        status_dot = {"open": "🟢", "answered": "🔵", "closed": "⚪"}.get(c["status"], "")
        prefix = "↩️ " if c["last_dir"] == "out" else ""
        unread_txt = f"  🔴{c['unread']}" if c["unread"] else ""
        # Compact preview
        preview = (c["preview"] or "")[:42]
        # Whole row is one button — label carries name, time, preview
        label = (f"{m['icon']} {c['customer']}{unread_txt}   ·   {c['time'][-5:]}\n"
                 f"{status_dot} {prefix}{preview}")
        row_cls = "conv-row unread" if c["unread"] else "conv-row"
        with st.container(key=f"convrow_{c['id']}"):
            st.markdown(f"<div class='{row_cls}'></div>", unsafe_allow_html=True)
            if st.button(label, key=f"conv_{c['id']}", use_container_width=True):
                ss.chat_open = c["id"]; st.rerun()
        # Label chips (only if present) — compact, below the row
        clabels = oc.get_conversation_labels(uid, pwd, c["id"])
        if clabels:
            chips = "".join(
                f"<span style='background:{l['color']}22;color:{l['color']};padding:1px 8px;"
                f"border-radius:10px;font-size:9px;margin-inline-end:3px'>{l['name']}</span>"
                for l in clabels)
            st.markdown(f"<div style='margin:-4px 0 8px 4px'>{chips}</div>", unsafe_allow_html=True)

    # Secondary tools — tickets + order lookup, tucked away
    with st.expander("🎫 التذاكر وحالة الطلب"):
        st.caption("ابحث عن طلب لمعرفة حالة التوصيل من يمامة")
        order_no = st.text_input("رقم الطلب", key="cs_order_lookup", placeholder="S02486")
        if order_no.strip():
            status = oc.get_order_delivery_status(uid, pwd, order_no.strip())
            if status:
                meta = oc.YAMAMAH_STATUS.get(status["api_status"], {"color": "#9BA58F", "bg": "rgba(255,255,255,.07)"})
                track = f"<a href='{status['tracking_url']}' target='_blank' style='color:#7FB069'>🔗 رابط التتبّع</a>" if status["tracking_url"] else ""
                st.markdown(f"""<div class='task-row'>
                    <div style='display:flex;justify-content:space-between;align-items:center'>
                      <b>{status['recipient']}</b>
                      <span style='padding:4px 12px;border-radius:20px;font-size:12px;background:{meta['bg']};color:{meta['color']}'>{status['api_status']}</span>
                    </div>
                    <div style='color:#9BA58F;font-size:12px;margin-top:6px'>
                      شحنة: {status['shipment']}<br>الهاتف: {status['mobile']}<br>COD: {status['cod']:,.0f} د.ل<br>التاريخ: {status['date']}
                    </div>
                    <div style='margin-top:8px'>{track}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.warning(f"لا توجد شحنة للطلب {order_no}")


def _chat_view(uid, pwd, conv_id):
    if st.button("← المحادثات"):
        ss.chat_open = None; st.rerun()
    head = oc.get_conversation_head(uid, pwd, conv_id)
    if not head:
        st.error("غير موجود"); return
    m = oc.CHANNEL_META.get(head["channel"], {"icon": "•", "ar": "", "color": "#888"})

    # ── Header: customer + channel + labels ──
    conv_labels = oc.get_conversation_labels(uid, pwd, conv_id)
    label_chips = "".join(
        f"<span style='background:{l['color']}22;color:{l['color']};padding:2px 8px;"
        f"border-radius:12px;font-size:10px;margin-inline-end:4px'>{l['name']}</span>"
        for l in conv_labels)
    st.markdown(f"""<div class='greeting'>
        <div style='display:flex;justify-content:space-between;align-items:center'>
          <div><div style='font-size:17px;font-weight:700'>{head['customer']}</div>
          <div style='font-size:12px;opacity:.6'>{head['handle']}</div></div>
          <span style='background:{m['color']}22;color:{m['color']};padding:4px 12px;border-radius:20px;font-size:12px'>{m['icon']} {m['ar']}</span>
        </div>
        <div style='margin-top:6px'>{label_chips}</div>
    </div>""", unsafe_allow_html=True)

    # ── Action toolbar: labels · remind · done · unread ──
    ac1, ac2, ac3, ac4 = st.columns(4)
    if ac1.button("🏷️ تصنيف", key=f"lbl_{conv_id}", use_container_width=True):
        ss[f"show_labels_{conv_id}"] = not ss.get(f"show_labels_{conv_id}", False)
    if ac2.button("⏰ ذكّرني", key=f"rem_{conv_id}", use_container_width=True):
        ss[f"show_remind_{conv_id}"] = not ss.get(f"show_remind_{conv_id}", False)
    if ac3.button("✅ إنهاء", key=f"done_{conv_id}", use_container_width=True):
        oc.mark_conversation_status(uid, pwd, conv_id, "closed")
        st.success("تم وضع علامة منجز"); ss.chat_open = None; st.rerun()
    if ac4.button("📩 غير مقروء", key=f"unr_{conv_id}", use_container_width=True):
        oc.mark_unread(uid, pwd, conv_id, True)
        st.success("وُضع كغير مقروء"); ss.chat_open = None; st.rerun()

    # Label picker (toggle panel)
    if ss.get(f"show_labels_{conv_id}"):
        labs = oc.get_labels(uid, pwd)
        applied = {l["id"] for l in conv_labels}
        st.caption("اختر التصنيفات:")
        lcols = st.columns(3)
        for i, l in enumerate(labs):
            mark = "✓ " if l["id"] in applied else ""
            if lcols[i % 3].button(f"{mark}{l['name']}", key=f"togglbl_{conv_id}_{l['id']}", use_container_width=True):
                oc.toggle_conversation_label(uid, pwd, conv_id, l["id"]); st.rerun()

    # Reminder panel
    if ss.get(f"show_remind_{conv_id}"):
        from datetime import date, timedelta
        st.caption("ذكّرني بهذه المحادثة:")
        rc1, rc2 = st.columns(2)
        when = rc1.selectbox("متى", ["خلال ساعة", "بعد 3 ساعات", "غداً صباحاً", "بعد يومين"],
                             key=f"remwhen_{conv_id}")
        rnote = rc2.text_input("ملاحظة", key=f"remnote_{conv_id}", placeholder="سبب التذكير")
        if st.button("ضبط التذكير", key=f"setrem_{conv_id}", use_container_width=True, type="primary"):
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            delta = {"خلال ساعة": timedelta(hours=1), "بعد 3 ساعات": timedelta(hours=3),
                     "غداً صباحاً": timedelta(days=1), "بعد يومين": timedelta(days=2)}[when]
            when_dt = (now + delta).strftime("%Y-%m-%d %H:%M:%S")
            oc.set_reminder(uid, pwd, conv_id, when_dt, rnote)
            st.success("تم ضبط التذكير ⏰"); ss[f"show_remind_{conv_id}"] = False; st.rerun()

    # ── Message stream: text, notes, images ──
    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
    msgs = oc.get_messages(uid, pwd, conv_id)
    for msg in msgs:
        if msg.get("is_note"):
            # Internal note — distinct amber style, not sent to customer
            st.markdown(
                f"<div style='display:flex;justify-content:center;margin:6px 0'>"
                f"<div style='background:rgba(212,168,83,.12);border:1px dashed rgba(212,168,83,.4);"
                f"border-radius:10px;padding:6px 12px;max-width:85%;font-size:12px;color:#D4A853'>"
                f"📝 <b>ملاحظة داخلية</b> · {msg['agent'] or ''}<br>{msg['body']}</div></div>",
                unsafe_allow_html=True)
        elif msg["direction"] == "in":
            img = f"<img src='data:image/jpeg;base64,{msg['image']}' style='max-width:180px;border-radius:8px;margin-top:4px'/>" if msg.get("image") else ""
            bubble = (f"<div style='display:flex;justify-content:flex-start;margin:4px 0'>"
                      f"<div style='background:#1E281E;border:1px solid #2E3D2E;border-radius:14px 14px 14px 4px;padding:8px 12px;max-width:78%'>"
                      f"<div style='font-size:13px'>{msg['body']}</div>{img}"
                      f"<div style='font-size:9px;opacity:.4;margin-top:3px'>{msg['time'][-5:]}</div></div></div>")
            st.markdown(bubble, unsafe_allow_html=True)
        else:
            agent = f" · {msg['agent']}" if msg["agent"] else ""
            img = f"<img src='data:image/jpeg;base64,{msg['image']}' style='max-width:180px;border-radius:8px;margin-top:4px'/>" if msg.get("image") else ""
            bubble = (f"<div style='display:flex;justify-content:flex-end;margin:4px 0'>"
                      f"<div style='background:rgba(127,176,105,.16);border:1px solid rgba(127,176,105,.3);border-radius:14px 14px 4px 14px;padding:8px 12px;max-width:78%'>"
                      f"<div style='font-size:13px'>{msg['body']}</div>{img}"
                      f"<div style='font-size:9px;opacity:.4;margin-top:3px;text-align:left'>{msg['time'][-5:]}{agent}</div></div></div>")
            st.markdown(bubble, unsafe_allow_html=True)

    # ── Composer: Reply / Note tabs, canned, emoji, image ──
    st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)
    tab_reply, tab_note = st.tabs(["💬 رد", "📝 ملاحظة داخلية"])

    with tab_reply:
        # Canned responses
        cans = _cached_canned(uid, pwd)
        with st.expander("⚡ ردود جاهزة"):
            for c in cans:
                if st.button(f"{c['title']} · {c['shortcut']}", key=f"can_{conv_id}_{c['id']}", use_container_width=True):
                    ss[f"chat_draft_{conv_id}"] = c["body"]; st.rerun()
        # Emoji quick-insert
        emojis = ["🌿", "💚", "✨", "🙏", "😊", "🚚", "❤️", "🌸"]
        ecols = st.columns(len(emojis))
        for i, e in enumerate(emojis):
            if ecols[i].button(e, key=f"emo_{conv_id}_{i}"):
                ss[f"chat_draft_{conv_id}"] = ss.get(f"chat_draft_{conv_id}", "") + e; st.rerun()
        reply = st.text_area("اكتب رداً...", value=ss.get(f"chat_draft_{conv_id}", ""),
                             key=f"chat_reply_{conv_id}", label_visibility="collapsed",
                             placeholder="اكتب رداً...", height=80)
        img = st.file_uploader("📎 صورة", type=["png", "jpg", "jpeg"], key=f"chat_img_{conv_id}")
        if st.button(f"إرسال إلى {m['ar']} ➤", type="primary", use_container_width=True, key=f"chat_send_{conv_id}"):
            image_b64 = None
            if img:
                import base64 as _b64
                image_b64 = _b64.b64encode(img.getvalue()).decode()
            if reply.strip() or image_b64:
                oc.send_reply_full(uid, pwd, conv_id, reply, is_note=False, image_b64=image_b64)
                ss[f"chat_draft_{conv_id}"] = ""
                st.rerun()

    with tab_note:
        st.caption("الملاحظات الداخلية لا تُرسل للعميل — للفريق فقط")
        note = st.text_area("ملاحظة...", key=f"chat_note_{conv_id}",
                            label_visibility="collapsed", placeholder="ملاحظة للفريق...", height=80)
        if st.button("حفظ الملاحظة", use_container_width=True, key=f"chat_savenote_{conv_id}"):
            if note.strip():
                oc.send_reply_full(uid, pwd, conv_id, note, is_note=True)
                st.rerun()


def _cs_screen_old():

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
    oc.touch_session(ss.uid, ss.pwd)  # activity heartbeat
    header()
    nav()
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
    elif screen == "sales":      sales_screen()
    elif screen == "profile":    profile_screen()
