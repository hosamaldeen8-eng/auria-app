"""
╔══════════════════════════════════════════════════════════╗
║   AURIA — Department App (Streamlit)                     ║
║   Live Odoo UI for Production, Procurement, Operations,  ║
║   Creative, and Customer Service                         ║
╚══════════════════════════════════════════════════════════╝
"""
import streamlit as st
import odoo_client as oc
from pathlib import Path
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

# ── STYLE ────────────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background: #F5F0E8; }
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 1.5rem; max-width: 480px; }
  .metric-card { background:#fff; border:1px solid #E5DFD3; border-radius:12px; padding:14px; text-align:center; }
  .metric-n { font-size:24px; font-weight:700; margin:0; }
  .metric-l { font-size:11px; color:#888780; margin:0; }
  .greeting { background:linear-gradient(135deg,#2E3D2E,#1F2B1F); border-radius:14px; padding:18px; color:#F0EEE2; margin-bottom:16px; }
  .stButton>button { border-radius:10px; font-weight:600; }
  .task-row { background:#fff; border:1px solid #E5DFD3; border-radius:10px; padding:12px 14px; margin-bottom:8px; }
  .badge { font-size:10px; padding:2px 8px; border-radius:20px; }
</style>
""", unsafe_allow_html=True)

# ── SESSION ──────────────────────────────────────────────────
ss = st.session_state
ss.setdefault("uid", None)
ss.setdefault("pwd", None)
ss.setdefault("info", None)
ss.setdefault("lang", "ar")
ss.setdefault("screen", "home")

def t(key):
    return T[ss.lang].get(key, key)

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
                ss.uid, ss.pwd, ss.info = uid, pwd, info
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
    tabs += [("tasks", "✅", t("tasks")), ("report", "📝", t("report"))]

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
            cols[i].markdown(f"<div class='metric-card'><p class='metric-n' style='color:#3B6D11'>{val}</p><p class='metric-l'>{label}</p></div>", unsafe_allow_html=True)

    # My performance
    st.markdown(f"**{t('my_performance')}**")
    stats = oc.get_my_stats(uid, pwd)
    c = st.columns(4)
    for i, (k, col) in enumerate([("assigned","#2E3D2E"),("done","#3B6D11"),("urgent","#A32D2D"),("overdue","#A32D2D")]):
        c[i].markdown(f"<div class='metric-card'><p class='metric-n' style='color:{col if stats[k]>0 else '#888'}'>{stats[k]}</p><p class='metric-l'>{t('assigned' if k=='assigned' else 'completed' if k=='done' else k)}</p></div>", unsafe_allow_html=True)

    # Company snapshot
    st.markdown(f"**{t('company')}**")
    snap = oc.get_company_snapshot(uid, pwd)
    c = st.columns(4)
    for i, (k, label, col) in enumerate([("orders",t("orders"),"#D4A853"),("revenue",t("revenue"),"#D4A853"),("deliveries",t("deliveries"),"#3B6D11"),("mos",t("mos"),"#1A5276")]):
        val = f"{snap[k]:,}" if k == "revenue" else snap[k]
        c[i].markdown(f"<div class='metric-card'><p class='metric-n' style='color:{col};font-size:18px'>{val}</p><p class='metric-l'>{label}</p></div>", unsafe_allow_html=True)

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
def production_screen():
    uid, pwd = ss.uid, ss.pwd
    tab1, tab2, tab3, tab4 = st.tabs([f"⚙️ {t('mos')}", "▶️ Timer", f"📦 {t('inventory')}", "⏱️ Time/Product"])

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
            state_colors = {"progress":"#D4A853","confirmed":"#3B6D11","done":"#888","draft":"#aaa"}
            st.markdown(f"<div class='task-row'><span style='font-family:monospace;color:#D4A853'>{mo['name']}</span> <span class='badge' style='background:#eee;color:{state_colors.get(mo['state'],'#888')}'>{mo['state']}</span><br><b>{mo['product']}</b><br><span style='color:#888;font-size:12px'>{mo['qty']:g} · {mo['date']}</span></div>", unsafe_allow_html=True)

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
                <div style='margin-top:6px;background:#eee;border-radius:6px;height:6px;overflow:hidden'>
                  <div style='width:{pct}%;height:100%;background:{"#A32D2D" if pct>100 else "#3B6D11"}'></div>
                </div>
                <div style='font-size:11px;color:#888;margin-top:3px'>{w['duration']:g} / {w['expected']:g} دقيقة ({pct}%)</div>
            </div>""", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                if not w["working"] and st.button("▶️ ابدأ", key=f"start_{w['id']}", use_container_width=True):
                    oc.wo_start(uid, pwd, w["id"]); st.rerun()
                if w["working"] and st.button("⏸️ أوقف", key=f"stop_{w['id']}", use_container_width=True):
                    oc.wo_stop(uid, pwd, w["id"]); st.rerun()
            with c2:
                if st.button("✅ أنهِ", key=f"fin_{w['id']}", use_container_width=True):
                    oc.wo_finish(uid, pwd, w["id"]); st.success("✓"); st.rerun()

    # ── Tab 3: Inventory ──
    with tab3:
        q = st.text_input(t("search"), key="inv_search")
        for item in oc.get_inventory(uid, pwd, q):
            color = "#A32D2D" if item["qty"] == 0 else "#D4A853"
            st.markdown(f"<div class='task-row' style='display:flex;justify-content:space-between'><span><b>{item['name']}</b><br><span style='color:#888;font-size:11px'>{item['loc']}</span></span><span style='font-size:18px;font-weight:700;color:{color}'>{item['qty']:g}</span></div>", unsafe_allow_html=True)

    # ── Tab 4: Time per product ──
    with tab4:
        st.caption("الوقت الفعلي لكل منتج (من أوامر الشغل المنتهية)")
        for tp in oc.get_time_by_product(uid, pwd):
            eff_color = "#3B6D11" if tp["efficiency"] >= 100 else "#D4A853" if tp["efficiency"] >= 60 else "#A32D2D"
            hrs = tp["actual_min"] / 60
            st.markdown(f"""<div class='task-row'>
                <div style='display:flex;justify-content:space-between'>
                  <b>{tp['product']}</b>
                  <span style='color:{eff_color};font-weight:600'>{tp['efficiency']}%</span>
                </div>
                <div style='font-size:11px;color:#888;margin-top:3px'>{hrs:.1f} ساعة فعلية · {tp['runs']} دورة إنتاج</div>
            </div>""", unsafe_allow_html=True)

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
            st.markdown(f"<div class='task-row'><span style='font-family:monospace;color:#D4A853'>{d['name']}</span> <span class='badge' style='background:#eee;color:#888'>{d['state']}</span><br><b>{d['customer']}</b> · <span style='color:#888;font-size:12px'>{d['date']}</span></div>", unsafe_allow_html=True)

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

# ── ROUTER ───────────────────────────────────────────────────
if not ss.uid:
    login_screen()
else:
    header()
    screen = ss.screen
    if screen == "home":         home_screen()
    elif screen == "production": production_screen()
    elif screen == "procurement":procurement_screen()
    elif screen == "operations": operations_screen()
    elif screen == "creative":   creative_screen()
    elif screen == "cs":         cs_screen()
    elif screen == "tasks":      tasks_screen()
    elif screen == "report":     report_screen()
    st.markdown("<hr style='margin:16px 0 8px'>", unsafe_allow_html=True)
    nav()
    if st.button(t("logout"), use_container_width=True):
        for k in ["uid","pwd","info","cs_open"]:
            ss.pop(k, None)
        st.rerun()
