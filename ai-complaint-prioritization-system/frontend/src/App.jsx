import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Activity,
  BarChart3,
  Bot,
  CheckCircle2,
  ClipboardList,
  Cloud,
  Database,
  FileCheck2,
  FileText,
  Gauge,
  KeyRound,
  Lock,
  LogOut,
  Plus,
  RefreshCw,
  Route,
  ShieldCheck,
  ShieldAlert,
  Star,
  UserCog,
  Users,
  UploadCloud,
} from "lucide-react";
import { api, getToken, setAuthHandlers, setToken } from "./api";
import PriorityChart from "./components/PriorityChart";
import SDGChart from "./components/SDGChart";

const categoryOptions = ["GENERAL", "ACADEMIC", "HOSTEL", "INFRASTRUCTURE", "SAFETY", "SECURITY", "ADMINISTRATION", "IT"];
const statusOptions = ["OPEN", "IN_PROGRESS", "RESOLVED", "REJECTED"];
const roleOptions = ["STUDENT", "STAFF", "ADMIN"];
const maxEvidenceSize = 2 * 1024 * 1024;
const allowedEvidenceTypes = ["application/pdf", "image/png", "image/jpeg"];
const securityFeatures = [
  { icon: KeyRound, title: "Authentication and Tokens", text: "Signed bearer tokens protect API requests and the backend reloads the trusted user record." },
  { icon: UserCog, title: "Role-Based Access Control", text: "Student, Staff, and Admin permissions are enforced server-side before data is returned." },
  { icon: ShieldAlert, title: "XSS Mitigation", text: "Complaint and AI text are sanitized and rendered safely as text in React." },
  { icon: Lock, title: "Injection Prevention", text: "Strict type validation and fixed Firestore queries reduce NoSQL injection-style risk." },
  { icon: Cloud, title: "Restricted CORS", text: "Bearer-token APIs and controlled origins reduce CSRF-style browser abuse." },
  { icon: Activity, title: "Rate Limiting", text: "Login, register, complaint submission, and admin-sensitive operations use request limits." },
  { icon: UploadCloud, title: "Secure File Uploads", text: "Evidence files are checked by extension, MIME type, signature, and size before acceptance." },
  { icon: FileCheck2, title: "Password and Secret Safety", text: "Passwords are hashed and runtime secrets are loaded from environment configuration." },
  { icon: BarChart3, title: "Audit Logs", text: "Unauthorized attempts, upload rejections, login events, and admin changes are recorded." },
  { icon: Database, title: "Firestore / GCP Support", text: "The same API supports local demo mode and Firestore-backed cloud deployment." },
  { icon: Bot, title: "Safe AI Triage", text: "AI helps classify priority and escalation while output remains treated as untrusted text." },
];
const attackDemos = [
  ["XSS payload", "Sanitization + safe React rendering", "Script does not execute"],
  ["Injection-style login bypass", "Input validation + fixed auth logic", "Login fails safely"],
  ["Student opens Admin route", "Backend RBAC + route guard", "Access Denied / 403"],
  ["IDOR complaint URL reuse", "Ownership and assignment checks", "Foreign complaint blocked"],
  ["Brute-force login attempts", "Rate limiting", "429 Too Many Requests"],
  ["Malicious file upload", "Type, size, extension, and signature checks", "Upload rejected"],
  ["Unauthorized API request", "Bearer token verification + audit logging", "401/403 and event recorded"],
];
const roleCards = [
  { title: "Student", icon: ClipboardList, items: ["Submit complaints", "View own complaints only"] },
  { title: "Staff", icon: FileText, items: ["View assigned complaints", "Update complaint status"] },
  { title: "Admin", icon: ShieldCheck, items: ["Manage users", "Assign complaints", "View audit logs and security events"] },
];
const viewPaths = {
  dashboard: "/",
  submit: "/submit",
  complaints: "/complaints",
  users: "/admin/users",
  audit: "/audit-logs",
};

export default function App() {
  const [user, setUser] = useState(null);
  const [view, setView] = useState("dashboard");
  const [authMode, setAuthMode] = useState("login");
  const [complaints, setComplaints] = useState([]);
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [securityEvents, setSecurityEvents] = useState([]);
  const [selectedComplaint, setSelectedComplaint] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setAuthHandlers({
      onUnauthorized: () => {
        setToken(null);
        setUser(null);
        setView("login");
      },
      onForbidden: () => setView("denied"),
    });
    const handlePopState = () => {
      setView(resolveViewForPath(window.location.pathname));
    };
    window.addEventListener("popstate", handlePopState);
    if (getToken()) {
      api.me()
        .then((data) => {
          setUser(data.user);
          setView(resolveAuthorizedView(resolveViewForPath(window.location.pathname), data.user.role));
        })
        .catch(() => setToken(null));
    }
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (!user) return;
    loadCoreData();
  }, [user]);

  async function loadCoreData() {
    setLoading(true);
    setMessage("");
    try {
      const [complaintData, statsData] = await Promise.all([api.getComplaints(), api.getStats()]);
      setComplaints(complaintData);
      setStats(statsData);
      if (user?.role === "ADMIN") {
        const [userData, logData, eventData] = await Promise.all([api.getUsers(), api.getAuditLogs(), api.getSecurityEvents()]);
        setUsers(userData);
        setAuditLogs(logData);
        setSecurityEvents(eventData);
      }
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleAuthenticated(data) {
    setToken(data.token);
    setUser(data.user);
    setView(resolveAuthorizedView(resolveViewForPath(window.location.pathname), data.user.role));
    setMessage("");
  }

  async function handleLogout() {
    try {
      await api.logout();
    } catch (_) {
      // Token may already be expired; local cleanup is still correct.
    }
    setToken(null);
    setUser(null);
    setView("login");
    setComplaints([]);
    setStats(null);
  }

  const navItems = useMemo(() => {
    if (!user) return [];
    const base = [{ key: "dashboard", label: "Dashboard", icon: BarChart3 }];
    if (user.role === "STUDENT") base.push({ key: "submit", label: "Submit", icon: Plus }, { key: "complaints", label: "My Complaints", icon: ClipboardList });
    if (user.role === "STAFF") base.push({ key: "complaints", label: "Assigned", icon: ClipboardList });
    if (user.role === "ADMIN") base.push({ key: "complaints", label: "Complaints", icon: ClipboardList }, { key: "users", label: "Users", icon: Users }, { key: "audit", label: "Audit Logs", icon: ShieldCheck });
    return base;
  }, [user]);

  function navigateTo(nextView) {
    setView(resolveAuthorizedView(nextView, user.role));
    const nextPath = viewPaths[nextView] || "/";
    if (window.location.pathname !== nextPath) {
      window.history.pushState({}, "", nextPath);
    }
  }

  function navigateToComplaint(complaintId) {
    const nextPath = `/complaints/${encodeURIComponent(complaintId)}`;
    setView(resolveAuthorizedView("complaintDetail", user.role));
    if (window.location.pathname !== nextPath) {
      window.history.pushState({}, "", nextPath);
    }
  }

  if (!user) {
    return <AuthScreen mode={authMode} setMode={setAuthMode} onAuthenticated={handleAuthenticated} />;
  }

  const activeView = resolveAuthorizedView(view, user.role);

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold uppercase text-blue-700">
                <Lock size={18} /> Secure AI-Based Complaint Management System
              </div>
              <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">RBAC, Firestore, Google Cloud, and Attack Prevention</h1>
              <p className="mt-1 text-sm text-slate-600">Signed in as {user.name} ({user.role})</p>
            </div>
            <button className="small-button" onClick={handleLogout}><LogOut size={16} /> Logout</button>
          </div>
          <nav className="flex flex-wrap gap-2">
            {navItems.map(({ key, label, icon: Icon }) => (
              <button key={key} className={`tab-button ${activeView === key ? "tab-active" : ""}`} onClick={() => navigateTo(key)}>
                <Icon size={16} /> {label}
              </button>
            ))}
            <button className="tab-button" onClick={loadCoreData}><RefreshCw size={16} /> Refresh</button>
          </nav>
          {message && <Alert text={message} />}
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        {activeView === "denied" && <AccessDenied onBack={() => navigateTo("dashboard")} />}
        {activeView === "dashboard" && <Dashboard role={user.role} stats={stats} complaints={complaints} loading={loading} />}
        {activeView === "submit" && <SubmitComplaint onCreated={loadCoreData} />}
        {activeView === "complaints" && (
          <ComplaintWorkspace
            role={user.role}
            complaints={complaints}
            users={users}
            selectedComplaint={selectedComplaint}
            setSelectedComplaint={setSelectedComplaint}
            onViewDetails={navigateToComplaint}
            onRefresh={loadCoreData}
          />
        )}
        {activeView === "complaintDetail" && (
          <ComplaintDetailPage
            role={user.role}
            users={users}
            complaintId={complaintIdFromPath(window.location.pathname)}
            onBack={() => navigateTo("complaints")}
            onRefresh={loadCoreData}
          />
        )}
        {activeView === "users" && <ManageUsers users={users} onRefresh={loadCoreData} />}
        {activeView === "audit" && <AuditLogs logs={auditLogs} events={securityEvents} />}
      </div>
    </main>
  );
}

function resolveViewForPath(pathname) {
  if (pathname === "/admin" || pathname === "/admin/" || pathname === "/admin/users") return "users";
  if (pathname === "/audit-logs" || pathname === "/admin/audit-logs") return "audit";
  if (pathname === "/submit") return "submit";
  if (complaintIdFromPath(pathname)) return "complaintDetail";
  if (pathname === "/complaints") return "complaints";
  return "dashboard";
}

function resolveAuthorizedView(nextView, role) {
  if (nextView === "denied") return "denied";
  if (nextView === "users" || nextView === "audit") return role === "ADMIN" ? nextView : "denied";
  if (nextView === "submit") return role === "STUDENT" ? "submit" : "denied";
  if (nextView === "complaints" || nextView === "complaintDetail" || nextView === "dashboard") return nextView;
  return "dashboard";
}

function complaintIdFromPath(pathname) {
  const match = pathname.match(/^\/complaints\/([^/]+)$/);
  return match ? decodeURIComponent(match[1]) : "";
}

function AuthScreen({ mode, setMode, onAuthenticated }) {
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const authPanelRef = useRef(null);

  function switchMode(nextMode) {
    setMode(nextMode);
    setError("");
    authPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = mode === "login" ? await api.login({ email: form.email, password: form.password }) : await api.register(form);
      await onAuthenticated(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="landing-shell min-h-screen text-slate-950">
      <section className="landing-hero">
        <div className="landing-container hero-grid">
          <div className="hero-copy">
            <div className="hero-kicker"><ShieldCheck size={18} /> Cyber Security Course Project</div>
            <h1>Secure AI-Based Complaint Management System</h1>
            <p className="hero-subtitle">An AI-powered complaint triage platform designed with authentication, RBAC, input validation, audit logging, and attack prevention.</p>
            <div className="hero-tags">
              <span>Secure complaint handling</span>
              <span>AI triage</span>
              <span>Role-based access control</span>
              <span>Attack prevention</span>
              <span>Firestore / Google Cloud support</span>
            </div>
            <div className="hero-actions">
              <button className="landing-primary" onClick={() => switchMode("login")}><KeyRound size={18} /> Login</button>
              <button className="landing-secondary" onClick={() => switchMode("register")}><UserCog size={18} /> Register</button>
              <a className="landing-link-button" href="#security-features"><ShieldAlert size={18} /> View Security Features</a>
            </div>
          </div>

          <form ref={authPanelRef} className="auth-panel" onSubmit={handleSubmit}>
            <div className="auth-panel-header">
              <div>
                <p className="panel-label">Secure Access</p>
                <h2>{mode === "login" ? "Login" : "Register Student"}</h2>
              </div>
              <Lock className="text-cyan-500" size={28} />
            </div>
            <p className="mt-2 text-sm text-slate-500">Use the seeded demo accounts for the presentation or create a new student account.</p>
            {mode === "register" && <input className="input mt-5" placeholder="Full name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} maxLength={80} required />}
            <input className="input mt-4" type="email" placeholder="email@example.com" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            <input className="input mt-4" type="password" placeholder="Password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
            {error && <Alert text={error} />}
            <button className="primary-button mt-5 w-full" disabled={loading}>{loading ? "Please wait..." : mode === "login" ? "Login to Dashboard" : "Create Student Account"}</button>
            <button type="button" className="mt-4 text-sm font-semibold text-blue-700" onClick={() => switchMode(mode === "login" ? "register" : "login")}>
              {mode === "login" ? "Need an account? Register" : "Already registered? Login"}
            </button>
            <div className="demo-credentials">
              <strong>Demo accounts</strong>
              <span>admin@example.com</span>
              <span>staff@example.com</span>
              <span>student1@example.com / student2@example.com</span>
              <span>Password: DemoPass123!</span>
            </div>
          </form>
        </div>
      </section>

      <section id="security-features" className="landing-section landing-container">
        <SectionHeading eyebrow="Implemented Countermeasures" title="Security Features Built Into the Platform" text="The system demonstrates secure coding practices that mitigate common attacks without claiming perfect security." />
        <div className="feature-grid">
          {securityFeatures.map(({ icon: Icon, title, text }) => (
            <article className="feature-card" key={title}>
              <div className="feature-icon"><Icon size={22} /></div>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section muted-band">
        <div className="landing-container">
          <SectionHeading eyebrow="Presentation Demo" title="Attack Mitigation Demonstrations" text="Each test is designed to show an attack attempt, the countermeasure, and the expected blocked result." />
          <div className="attack-grid">
            {attackDemos.map(([attack, countermeasure, result]) => (
              <article className="attack-card" key={attack}>
                <strong>{attack}</strong>
                <span>{countermeasure}</span>
                <em>{result}</em>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section landing-container architecture-grid">
        <div>
          <SectionHeading eyebrow="Architecture" title="React Frontend -> Flask Backend API -> Firestore / Google Cloud" text="The frontend never directly accesses Firestore. All authentication, authorization, validation, AI triage, and audit logging are enforced by the backend API." />
          <div className="flow-row">
            <span>React Frontend</span>
            <Route size={18} />
            <span>Flask Backend API</span>
            <Route size={18} />
            <span>Firestore / GCP</span>
          </div>
        </div>
        <div className="architecture-panel">
          <p><strong>Backend enforcement:</strong> bearer token verification, active-user checks, role checks, ownership checks, validation, rate limiting, and audit logging.</p>
          <p><strong>Stored collections:</strong> users, complaints, audit logs, and security events.</p>
          <p><strong>Cloud-ready mode:</strong> local in-memory demo support plus Firestore/Google Cloud configuration for deployment.</p>
        </div>
      </section>

      <section className="landing-section landing-container">
        <SectionHeading eyebrow="Roles and Permissions" title="Clear RBAC Boundaries" text="The UI reflects role permissions, while the backend remains the source of truth." />
        <div className="role-grid">
          {roleCards.map(({ title, icon: Icon, items }) => (
            <article className="role-card" key={title}>
              <Icon size={26} />
              <h3>{title}</h3>
              {items.map((item) => <p key={item}>{item}</p>)}
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section muted-band">
        <div className="landing-container ai-grid">
          <div>
            <SectionHeading eyebrow="AI Triage" title="AI Assistance With Safe Output Handling" text="Complaint text is validated and sanitized before processing. AI classification helps prioritize escalation, and generated output is treated as untrusted text before display." />
          </div>
          <div className="ai-panel">
            <div><CheckCircle2 size={18} /> Validates and sanitizes complaint content</div>
            <div><CheckCircle2 size={18} /> Classifies priority and escalation signals</div>
            <div><CheckCircle2 size={18} /> Supports staff/admin triage decisions</div>
            <div><CheckCircle2 size={18} /> Renders AI output safely, without raw HTML</div>
          </div>
        </div>
      </section>

    </main>
  );
}

function SectionHeading({ eyebrow, title, text }) {
  return (
    <div className="section-heading">
      <span>{eyebrow}</span>
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  );
}

function Dashboard({ role, stats, complaints, loading }) {
  const chartData = {
    priority: [
      { name: "Urgent", value: stats?.urgent || 0 },
      { name: "High", value: stats?.high || 0 },
      { name: "Medium", value: stats?.medium || 0 },
      { name: "Low", value: stats?.low || 0 },
    ],
    sdg: [
      { name: "SDG 9", value: stats?.sdg_9_count || 0 },
      { name: "SDG 16", value: stats?.sdg_16_count || 0 },
    ],
  };
  return (
    <section className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label={role === "ADMIN" ? "Total Complaints" : role === "STAFF" ? "Assigned" : "Submitted"} value={stats?.total} icon={ClipboardList} loading={loading} />
        {role === "ADMIN" && <Metric label="Total Users" value={stats?.totalUsers} icon={Users} loading={loading} />}
        <Metric label="Open" value={stats?.pending} icon={FileText} loading={loading} />
        <Metric label="Resolved" value={stats?.resolved} icon={CheckCircle2} loading={loading} />
        <Metric label="Escalated" value={stats?.escalation_count} icon={AlertTriangle} loading={loading} />
        <Metric label="Avg Priority" value={stats?.average_priority_score} icon={Gauge} loading={loading} />
      </div>
      <div className="grid gap-6 xl:grid-cols-2"><PriorityChart data={chartData.priority} /><SDGChart data={chartData.sdg} /></div>
      <RecentComplaints complaints={complaints.slice(0, 5)} />
    </section>
  );
}

function SubmitComplaint({ onCreated }) {
  const [form, setForm] = useState({ title: "", description: "", category: "GENERAL", department: "CSE" });
  const [evidence, setEvidence] = useState(null);
  const [assistMessage, setAssistMessage] = useState("");
  const [assistReply, setAssistReply] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef(null);

  function handleFile(event) {
    const file = event.target.files?.[0];
    setMessage("");
    setEvidence(null);
    if (!file) return;
    if (file.size > maxEvidenceSize) {
      setMessage("Evidence file must be 2 MB or less.");
      event.target.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onloadend = () => setEvidence({ name: file.name, type: file.type, base64: reader.result });
    reader.readAsDataURL(file);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      await api.submitComplaint({ ...form, evidence });
      setForm({ title: "", description: "", category: "GENERAL", department: "CSE" });
      setEvidence(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      setMessage("Complaint submitted. AI triage result is stored with the complaint.");
      await onCreated();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function askAssist(event) {
    event.preventDefault();
    if (!assistMessage.trim()) return;
    setAssistReply("Loading...");
    try {
      const data = await api.askAiAssist(assistMessage.trim());
      setAssistReply(data.reply || "No response.");
    } catch (err) {
      setAssistReply(err.message);
    }
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[1fr_380px]">
      <form className="card" onSubmit={handleSubmit}>
        <h2 className="section-title">Submit Complaint</h2>
        <input className="input mt-5" placeholder="Complaint title" maxLength={120} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
        <textarea className="input mt-4 min-h-44 resize-y" placeholder="Describe the issue, location, impact, and urgency" maxLength={2000} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <select className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>{categoryOptions.map((item) => <option key={item}>{item}</option>)}</select>
          <input className="input" placeholder="Department" maxLength={80} value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} required />
        </div>
        <input ref={fileInputRef} className="input mt-4" type="file" accept="application/pdf,image/png,image/jpeg" onChange={handleFile} />
        {evidence && <p className="mt-2 text-sm text-slate-600">Selected evidence: {evidence.name}</p>}
        {message && <Alert text={message} />}
        <button className="primary-button mt-5" disabled={loading}><Plus size={18} /> {loading ? "Submitting..." : "Submit for Secure AI Triage"}</button>
      </form>
      <form className="card h-fit" onSubmit={askAssist}>
        <h2 className="section-title flex items-center gap-2"><Bot size={18} /> AI Complaint Writing Help</h2>
        <textarea className="input mt-5 min-h-32 resize-y" maxLength={600} value={assistMessage} onChange={(e) => setAssistMessage(e.target.value)} placeholder="Ask how to write a clear complaint" />
        <button className="small-button mt-3 w-full bg-blue-100 text-blue-800" type="submit">Ask AI</button>
        {assistReply && <p className="mt-4 whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-sm text-slate-700">{assistReply}</p>}
      </form>
    </section>
  );
}

function ComplaintWorkspace({ role, complaints, users, selectedComplaint, setSelectedComplaint, onViewDetails, onRefresh }) {
  const staffUsers = users.filter((item) => item.role === "STAFF" && item.isActive);
  return (
    <section className="grid gap-6 xl:grid-cols-[1fr_420px]">
      <div className="card overflow-hidden">
        <h2 className="section-title">{role === "STUDENT" ? "My Complaints" : role === "STAFF" ? "Assigned Complaints" : "Manage Complaints"}</h2>
        <div className="mt-5 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-100 text-left text-xs uppercase text-slate-500"><tr><th className="table-cell">Complaint</th><th className="table-cell">Priority</th><th className="table-cell">Status</th><th className="table-cell">Action</th></tr></thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {complaints.length === 0 && <tr><td className="table-cell text-center text-slate-500" colSpan="4">No complaints available.</td></tr>}
              {complaints.map((item) => (
                <tr key={item.id} className="align-top">
                  <td className="table-cell max-w-md"><strong>{item.title}</strong><p className="mt-1 line-clamp-2 text-slate-600">{item.description}</p><p className="mt-1 text-xs text-slate-500">{item.studentName || "Student"} | {item.department}</p></td>
                  <td className="table-cell"><span className={`priority priority-${priorityClass(item.priority)}`}>{item.priorityLabel || item.priority}</span>{item.aiEscalationRequired && <p className="mt-2 text-xs font-bold text-red-700">Escalated</p>}</td>
                  <td className="table-cell"><span className="status-pill">{displayStatus(item.status)}</span></td>
                  <td className="table-cell">
                    <div className="flex flex-wrap gap-2">
                      <button className="small-button" onClick={() => setSelectedComplaint(item)}>Preview</button>
                      <button className="small-button" onClick={() => onViewDetails(item.id)}>View Details</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <ComplaintDetails role={role} complaint={selectedComplaint || complaints[0]} staffUsers={staffUsers} onRefresh={onRefresh} />
    </section>
  );
}

function ComplaintDetailPage({ role, users, complaintId, onBack, onRefresh }) {
  const [complaint, setComplaint] = useState(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const staffUsers = users.filter((item) => item.role === "STAFF" && item.isActive);

  useEffect(() => {
    let cancelled = false;
    async function loadComplaint() {
      setLoading(true);
      setMessage("");
      setComplaint(null);
      try {
        const data = await api.getComplaint(complaintId);
        if (!cancelled) setComplaint(data);
      } catch (err) {
        if (!cancelled && err.status !== 401 && err.status !== 403) {
          setMessage(err.message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    if (complaintId) loadComplaint();
    else {
      setLoading(false);
      setMessage("Complaint ID is missing.");
    }
    return () => {
      cancelled = true;
    };
  }, [complaintId]);

  return (
    <section className="space-y-4">
      <button className="small-button" onClick={onBack}>Back to Complaints</button>
      {loading && <section className="card"><h2 className="section-title">Complaint Details</h2><p className="mt-4 text-sm text-slate-500">Loading complaint...</p></section>}
      {!loading && message && <Alert text={message} />}
      {!loading && complaint && <ComplaintDetails role={role} complaint={complaint} staffUsers={staffUsers} onRefresh={onRefresh} />}
    </section>
  );
}

function ComplaintDetails({ role, complaint, staffUsers, onRefresh }) {
  const [status, setStatus] = useState("OPEN");
  const [staffNote, setStaffNote] = useState("");
  const [assignTo, setAssignTo] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    setStatus(complaint?.status || "OPEN");
    setAssignTo(complaint?.assignedStaffId || "");
    setMessage("");
  }, [complaint?.id]);

  if (!complaint) return <section className="card"><h2 className="section-title">Complaint Details</h2><p className="mt-4 text-sm text-slate-500">Select a complaint to inspect.</p></section>;

  async function updateStatus() {
    try {
      await api.updateStatus(complaint.id, status, staffNote);
      setMessage("Status updated.");
      await onRefresh();
    } catch (err) {
      setMessage(err.message);
    }
  }

  async function assignComplaint() {
    try {
      await api.assignComplaint(complaint.id, assignTo);
      setMessage("Complaint assigned.");
      await onRefresh();
    } catch (err) {
      setMessage(err.message);
    }
  }

  async function generateSolution() {
    try {
      await api.generateSolution(complaint.id);
      setMessage("AI resolution steps generated.");
      await onRefresh();
    } catch (err) {
      setMessage(err.message);
    }
  }

  async function rateComplaint(rating) {
    try {
      await api.submitRating(complaint.id, rating);
      setMessage("Rating submitted.");
      await onRefresh();
    } catch (err) {
      setMessage(err.message);
    }
  }

  return (
    <section className="card h-fit">
      <h2 className="section-title">Complaint Details</h2>
      <div className="mt-5 space-y-3 text-sm">
        <h3 className="text-lg font-bold">{complaint.title}</h3>
        <p className="whitespace-pre-wrap text-slate-700">{complaint.description}</p>
        <p><strong>AI priority:</strong> {complaint.priorityLabel || complaint.priority} ({complaint.priority_score})</p>
        <p><strong>AI reason:</strong> {complaint.aiReason || complaint.ai_reason}</p>
        <p><strong>Escalation:</strong> {complaint.aiEscalationRequired ? "Required" : "Not required"}</p>
        <p><strong>Evidence:</strong> {complaint.evidenceFilePath || "No evidence"}</p>
        {complaint.staffNote && <p className="whitespace-pre-wrap"><strong>Staff note:</strong> {complaint.staffNote}</p>}
        {complaint.ai_solution && <pre className="whitespace-pre-wrap rounded-md bg-blue-50 p-3 text-blue-950">{complaint.ai_solution}</pre>}
      </div>
      {(role === "STAFF" || role === "ADMIN") && (
        <div className="mt-5 border-t border-slate-200 pt-4">
          <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>{statusOptions.map((item) => <option key={item}>{item}</option>)}</select>
          <textarea className="input mt-3 min-h-20 resize-y" maxLength={500} placeholder="Staff note" value={staffNote} onChange={(e) => setStaffNote(e.target.value)} />
          <div className="mt-3 flex flex-wrap gap-2"><button className="small-button" onClick={updateStatus}>Update Status</button><button className="small-button" onClick={generateSolution}>Generate AI Resolution</button></div>
        </div>
      )}
      {role === "ADMIN" && (
        <div className="mt-4 border-t border-slate-200 pt-4">
          <select className="input" value={assignTo} onChange={(e) => setAssignTo(e.target.value)}><option value="">Select active staff</option>{staffUsers.map((staff) => <option key={staff.id} value={staff.id}>{staff.name} ({staff.email})</option>)}</select>
          <button className="small-button mt-3" disabled={!assignTo} onClick={assignComplaint}>Assign Staff</button>
        </div>
      )}
      {role === "STUDENT" && complaint.status === "RESOLVED" && !complaint.satisfaction_rating && <div className="mt-4 flex gap-1">{[1, 2, 3, 4, 5].map((star) => <button key={star} className="text-yellow-500" onClick={() => rateComplaint(star)}><Star size={20} /></button>)}</div>}
      {message && <Alert text={message} />}
    </section>
  );
}

function ManageUsers({ users, onRefresh }) {
  const [message, setMessage] = useState("");
  async function patchUser(uid, data) {
    try {
      await api.updateUser(uid, data);
      setMessage("User updated.");
      await onRefresh();
    } catch (err) {
      setMessage(err.message);
    }
  }
  return (
    <section className="card">
      <h2 className="section-title">Manage Users</h2>
      {message && <Alert text={message} />}
      <div className="mt-5 overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm"><thead className="bg-slate-100 text-left text-xs uppercase text-slate-500"><tr><th className="table-cell">User</th><th className="table-cell">Role</th><th className="table-cell">Status</th><th className="table-cell">Actions</th></tr></thead><tbody className="divide-y divide-slate-100 bg-white">
          {users.map((item) => <tr key={item.id}><td className="table-cell"><strong>{item.name}</strong><p className="text-slate-500">{item.email}</p></td><td className="table-cell"><select className="input py-2" value={item.role} onChange={(e) => patchUser(item.id, { role: e.target.value })}>{roleOptions.map((role) => <option key={role}>{role}</option>)}</select></td><td className="table-cell">{item.isActive ? "Active" : "Disabled"}</td><td className="table-cell"><button className="small-button" onClick={() => patchUser(item.id, { isActive: !item.isActive })}>{item.isActive ? "Disable" : "Enable"}</button></td></tr>)}
        </tbody></table>
      </div>
    </section>
  );
}

function AuditLogs({ logs, events }) {
  return (
    <section className="grid gap-6 xl:grid-cols-2">
      <LogTable title="Audit Logs" rows={logs} />
      <SecurityEventsTable events={events} />
    </section>
  );
}

function LogTable({ title, rows, security = false }) {
  return <div className="card overflow-hidden"><h2 className="section-title">{title}</h2><div className="mt-5 max-h-[620px] overflow-auto"><table className="min-w-full divide-y divide-slate-200 text-sm"><tbody className="divide-y divide-slate-100">{rows.map((row) => <tr key={row.id}><td className="table-cell"><strong>{security ? row.eventType : row.action}</strong><p className="text-xs text-slate-500">{formatDate(row.createdAt)} | {row.userRole || "anonymous"}</p><pre className="mt-2 whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs text-slate-600">{JSON.stringify(security ? row.details : row.safeDetails, null, 2)}</pre></td></tr>)}</tbody></table></div></div>;
}

function SecurityEventsTable({ events }) {
  return (
    <div className="card overflow-hidden">
      <h2 className="section-title">Security Events</h2>
      <div className="mt-5 max-h-[620px] overflow-auto">
        <div className="grid gap-3">
          {events.length === 0 && <p className="text-sm text-slate-500">No security events recorded.</p>}
          {events.map((event) => {
            const details = event.details || {};
            const severity = event.severity || "MEDIUM";
            const pattern = event.detectedPattern || details.detectedPattern || event.eventType;
            const preview = event.safePayloadPreview || details.safePayloadPreview || "";
            const route = event.route || details.route || details.path || "-";
            const method = event.method || details.method || "-";
            const action = event.actionTaken || details.actionTaken || "-";
            const source = event.source || details.source || "backend";
            const user = event.userEmail || event.userId || "anonymous";
            return (
              <article className="security-event-card" key={event.id}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <strong>{friendlySecurityEvent(pattern)}</strong>
                    <p className="mt-1 text-xs text-slate-500">{formatDate(event.createdAt)} | {source} | {method} {route}</p>
                  </div>
                  <span className={`severity-badge severity-${String(severity).toLowerCase()}`}>{severity}</span>
                </div>
                <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
                  <p><strong>Action:</strong> {action}</p>
                  <p><strong>User:</strong> {user}</p>
                  {preview && <p className="sm:col-span-2"><strong>Safe preview:</strong> {preview}</p>}
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function RecentComplaints({ complaints }) {
  return <section className="card"><h2 className="section-title">Recent Complaints</h2><div className="mt-4 grid gap-3">{complaints.map((item) => <div className="rounded-md border border-slate-200 p-3" key={item.id}><strong>{item.title}</strong><p className="text-sm text-slate-600">{item.priorityLabel || item.priority} | {displayStatus(item.status)}</p></div>)}{complaints.length === 0 && <p className="text-sm text-slate-500">No complaints yet.</p>}</div></section>;
}

function Metric({ label, value, icon: Icon, loading }) {
  return <div className="metric-card"><div className="flex items-center justify-between"><span className="text-sm font-medium text-slate-500">{label}</span><Icon className="text-blue-700" size={20} /></div><strong className="mt-3 block text-3xl font-bold">{loading ? "--" : value ?? 0}</strong></div>;
}

function AccessDenied({ onBack }) {
  return <section className="card mx-auto max-w-xl text-center"><AlertTriangle className="mx-auto text-red-600" size={42} /><h2 className="mt-4 text-xl font-bold">Access Denied</h2><p className="mt-2 text-slate-600">The backend rejected this action because your role is not authorized.</p><button className="primary-button mt-5" onClick={onBack}>Return to Dashboard</button></section>;
}

function Alert({ text }) {
  return <div className="mt-4 flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"><AlertTriangle size={18} /> {text}</div>;
}

function displayStatus(value) {
  return { OPEN: "Open", IN_PROGRESS: "In Progress", RESOLVED: "Resolved", REJECTED: "Rejected", Pending: "Open", "In Progress": "In Progress", Resolved: "Resolved" }[value] || value || "Open";
}

function priorityClass(value) {
  return String(value || "low").toLowerCase();
}

function formatDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function friendlySecurityEvent(value) {
  const text = String(value || "");
  if (text.includes("SQL")) return "SQL injection pattern detected";
  if (text.includes("NoSQL") || text.includes("OBJECT")) return "NoSQL object payload detected";
  if (text.includes("XSS")) return "XSS payload detected";
  if (text.includes("file") || text.includes("FILE") || text.includes("UPLOAD")) return "Malicious file upload rejected";
  return text.replaceAll("_", " ").toLowerCase().replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());
}
