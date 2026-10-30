const icons = {
  logo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M4 17.5 10 6l4 7 2-3 4 7.5H4Z"/><path d="M4 20h16"/></svg>',
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-6v-7h-4v7H4a1 1 0 0 1-1-1Z"/></svg>',
  briefcase: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m-13 5h18m-11 0v2h4v-2"/></svg>',
  building: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="3" width="16" height="18" rx="1"/><path d="M8 7h2m4 0h2M8 11h2m4 0h2M8 15h2m4 0h2M10 21v-3h4v3"/></svg>',
  bookmark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v17l-6-4-6 4Z"/></svg>',
  person: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></svg>',
  chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 19V5m0 14h17M8 15l4-4 3 2 5-7"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="10.8" cy="10.8" r="7.3"/><path d="m16 16 5 5"/></svg>',
  bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9m-8 12h4"/></svg>',
  arrow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 12h14m-6-6 6 6-6 6"/></svg>'
};

const state = { token: localStorage.getItem("skillmatch_token"), user: null, page: "dashboard", cache: {} };
const API_BASE_URL = location.port === "5500" ? "http://127.0.0.1:8000" : "";
const app = document.querySelector("#app");
const esc = (value = "") => String(value).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const initials = name => String(name || "SM").split(/\s+/).slice(0, 2).map(p => p[0]).join("").toUpperCase();
function notify(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2600);
}
async function api(path, options = {}) {
  const headers = { ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }), ...(options.headers || {}) };
  const token = state.token;
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  const data = response.status === 204 ? null : await response.json();
  if (response.status === 401 && token && state.token === token && !["/api/auth/login", "/api/auth/register"].includes(path)) {
    state.token = null;
    state.user = null;
    localStorage.removeItem("skillmatch_token");
    history.replaceState({}, "", "/login");
    authPage("login", "Your session expired or is invalid. Please sign in again.");
  }
  if (!response.ok) {
    const error = new Error(data?.detail || "Something went wrong. Please try again.");
    error.status = response.status;
    throw error;
  }
  return data;
}
function authPage(mode = "login", notice = "") {
  const register = mode === "register";
  app.innerHTML = `<main class="auth-wrap">
    <section class="auth-visual"><a class="brand" href="#">${`<span class="brand-mark">${icons.logo}</span>`}<span>skillmatch</span></a>
      <div><div class="eyebrow" style="color:#b9dbc4">A clearer path to your next role</div>
      <h1>Find work that fits <span style="color:#b5ddc0">who you are.</span></h1>
      <p>Real opportunities, matched to your skills and ambitions. Know where you shine, and what to learn next.</p></div>
      <small style="color:#c1d6c8">Thoughtful matches. Better beginnings.</small>
    </section>
    <section class="auth-form-wrap"><form id="auth-form" class="auth-form">
      <div class="eyebrow">${register ? "Start your journey" : "Welcome back"}</div>
      <h2>${register ? "Create your account" : "Good to see you again"}</h2>
      <p class="subtitle">${esc(notice || (register ? "Build a profile and discover your next opportunity." : "Sign in to see opportunities picked for you."))}</p>
      ${register ? `<div class="field"><label for="auth-name">Full name</label><input class="input" id="auth-name" name="name" placeholder="Alex Morgan" required minlength="2"></div>` : ""}
      <div class="field"><label for="auth-email">Email address</label><input class="input" id="auth-email" name="email" type="email" placeholder="you@example.com" required></div>
      <div class="field"><label for="auth-password">Password</label><input class="input" id="auth-password" name="password" type="password" placeholder="${register ? "At least 8 characters" : "Enter your password"}" required minlength="${register ? "8" : "1"}"></div>
      <button class="button" type="submit">${register ? "Create account" : "Sign in"} ${icons.arrow}</button>
      <div class="auth-foot">${register ? "Already have an account?" : "New to SkillMatch?"} <button id="auth-switch" type="button">${register ? "Sign in" : "Create an account"}</button></div>
    </form></section></main>`;
  document.querySelector("#auth-switch").onclick = () => {
    const nextMode = register ? "login" : "register";
    history.pushState({}, "", nextMode === "register" ? "/register" : "/login");
    authPage(nextMode);
  };
  document.querySelector("#auth-form").onsubmit = async event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      const result = await api(register ? "/api/auth/register" : "/api/auth/login", { method: "POST", body: JSON.stringify(data) });
      state.token = result.token;
      state.user = result.user;
      localStorage.setItem("skillmatch_token", result.token);
      state.page = "dashboard";
      history.replaceState({}, "", "/");
      await render();
    } catch (error) { notify(error.message); }
  };
}
const navItems = [
  ["dashboard", "Overview", icons.home, "GENERAL"],
  ["jobs", "Find jobs", icons.briefcase],
  ["companies", "Companies", icons.building],
  ["recommendations", "For you", icons.chart],
  ["saved", "Saved", icons.bookmark, "YOUR SPACE"],
  ["profile", "My profile", icons.person],
  ["admin", "Admin panel", icons.chart, "MANAGEMENT"]
];
function layout(content) {
  const nav = navItems.filter(item => item[0] !== "admin" || state.user?.role === "admin");
  app.innerHTML = `<div class="shell"><aside class="sidebar">
    <a class="brand" href="#" data-page="dashboard"><span class="brand-mark">${icons.logo}</span><span class="brand-name">skillmatch</span></a>
    ${nav.map((item, i) => `${item[3] ? `<div class="nav-label" style="${i ? "margin-top:20px" : ""}">${item[3]}</div>` : ""}<a class="nav-link ${state.page === item[0] ? "active" : ""}" href="#${item[0]}" data-page="${item[0]}">${item[2]}<span>${item[1]}</span></a>`).join("")}
    <div class="sidebar-bottom"><div class="upgrade"><strong>Make your next move</strong><p>Your profile helps us find the roles where you can do your best work.</p><button class="button small" data-page="profile">Complete profile</button></div>
      <div class="profile-chip"><div class="avatar">${esc(initials(state.user?.name))}</div><div><strong>${esc(state.user?.name)}</strong><small>${esc(state.user?.role === "admin" ? "Administrator" : "Member")}</small></div><button class="icon-button" id="logout" title="Sign out">↗</button></div>
    </div></aside>
    <main class="main"><header class="topbar"><div class="crumb">Workspace <span style="padding:0 8px;color:#c1c9c3">/</span> <strong style="color:#45534a">${esc(pageTitle(state.page))}</strong></div><div class="top-actions"><button class="icon-button" data-page="jobs" aria-label="Search">${icons.search}</button><button class="icon-button" id="notifications" aria-label="Notifications">${icons.bell}</button><div class="avatar">${esc(initials(state.user?.name))}</div></div></header><div class="content">${content}</div></main></div>`;
  app.querySelectorAll("[data-page]").forEach(element => element.addEventListener("click", async event => {
    event.preventDefault();
    state.page = element.dataset.page;
    await render();
  }));
  document.querySelector("#logout").onclick = () => {
    state.token = null;
    state.user = null;
    localStorage.removeItem("skillmatch_token");
    history.pushState({}, "", "/login");
    authPage("login");
  };
  document.querySelector("#notifications").onclick = () => notify("You're all caught up.");
}
function pageTitle(page) {
  return ({ dashboard: "Overview", jobs: "Find jobs", companies: "Companies", recommendations: "Your matches", saved: "Saved items", profile: "My profile", admin: "Admin panel" })[page] || "Overview";
}
function heading(title, subtitle, action = "") {
  return `<div class="welcome"><div><div class="eyebrow">${esc(pageTitle(state.page))}</div><h1>${title}</h1><p class="subtitle" style="margin-bottom:0">${subtitle}</p></div>${action}</div>`;
}
function stat(label, value, note, icon) {
  return `<div class="stat"><div class="stat-top">${label}<span class="stat-icon">${icon}</span></div><div class="stat-value">${value}</div><div class="stat-note">${note}</div></div>`;
}
function chips(items = [], missing = false) {
  return items.length ? `<div class="skill-chips">${items.map(item => `<span class="chip ${missing ? "missing" : ""}">${esc(item)}</span>`).join("")}</div>` : "";
}
function jobCard(job) {
  return `<article class="job-card"><div class="job-top"><span class="company-logo">${esc(initials(job.company?.name))}</span><span class="match-pill">${job.score ?? 0}% match</span></div>
    <h3>${esc(job.title)}</h3><div class="company-name">${esc(job.company?.name)} · ${esc(job.company?.industry)}</div>
    <div class="job-meta"><span>⌖ ${esc(job.company?.location)}</span><span>◷ ${job.experience_min}–${job.experience_max} yrs</span><span>${esc(job.work_mode)}</span></div>
    <p class="job-description">${esc(job.description)}</p>${job.reasons?.[0] ? `<p style="font-size:10px;color:#5b7865;line-height:1.5;margin:8px 0 0">✳ ${esc(job.reasons[0])}</p>` : ""}${chips((job.matching_skills || []).slice(0, 4))}
    ${job.missing_skills?.length ? chips(job.missing_skills.slice(0, 3), true) : ""}
    <div class="job-actions"><span class="match-line">${job.salary_min ? `₹${(job.salary_min / 100000).toFixed(0)}–${(job.salary_max / 100000).toFixed(0)} LPA` : "Salary not listed"}</span>
      <div><button class="button secondary small" data-save-job="${job.id}">Save role</button> <button class="button small" data-apply-job="${job.id}" ${job.applied ? "disabled" : ""}>${job.applied ? "Applied" : "Apply"}</button></div></div></article>`;
}
function bindSaveButtons() {
  document.querySelectorAll("[data-save-job]").forEach(button => button.onclick = async () => {
    try {
      const result = await api(`/api/saved/job/${button.dataset.saveJob}`, { method: "POST" });
      notify(result.saved ? "Role saved to your list" : "Role removed from saved");
      if (state.page === "saved") await render();
    } catch (error) { notify(error.message); }
  });
  document.querySelectorAll("[data-apply-job]").forEach(button => button.onclick = async () => {
    try {
      const result = await api(`/api/jobs/${button.dataset.applyJob}/apply`, { method: "POST" });
      button.disabled = true;
      button.textContent = "Applied";
      notify(result.already_applied ? "You have already applied to this role" : "Application submitted");
    } catch (error) { notify(error.message); }
  });
  document.querySelectorAll("[data-save-company]").forEach(button => button.onclick = async () => {
    try {
      const result = await api(`/api/saved/company/${button.dataset.saveCompany}`, { method: "POST" });
      notify(result.saved ? "Company saved to your list" : "Company removed from saved");
      if (state.page === "saved") await render();
    } catch (error) { notify(error.message); }
  });
}
async function dashboardPage() {
  const data = await api("/api/dashboard");
  const best = data.top_jobs[0]?.score || 0;
  const skills = data.in_demand_skills || [];
  return `${heading(`Good morning, ${esc((state.user?.name || "there").split(" ")[0])} <span style="color:#91a398">✳</span>`, "Here’s a little momentum for your next career move.", `<button class="button" data-page="recommendations">Explore matches ${icons.arrow}</button>`)}
    <div class="stats">${stat("Profile strength", `${data.profile_completion}%`, "Complete your profile to improve matches", icons.person)}${stat("Open opportunities", data.total_jobs, "Roles selected for your profile", icons.briefcase)}${stat("Best match", `${best}%`, data.top_jobs[0]?.title || "Add skills to see your matches", icons.chart)}${stat("Saved for later", data.saved_count, "Roles and teams on your list", icons.bookmark)}</div>
    <div class="dashboard-grid"><section>
      <div class="panel"><div class="panel-heading"><h2>Recommended for you</h2><button class="text-link" data-page="recommendations">See all →</button></div>
        ${data.top_jobs.length ? `<div class="recommend-list">${data.top_jobs.slice(0, 3).map(job => `<div class="recommend-item"><div class="company-logo">${esc(initials(job.company.name))}</div><div><strong>${esc(job.title)}</strong><small>${esc(job.company.name)} · ${esc(job.company.location)}</small></div><span class="match-pill">${job.score}%</span></div>`).join("")}</div>` : `<div class="empty">Add your skills to discover roles made for you.</div>`}
      </div>
      <div class="panel"><div class="panel-heading"><h2>Skills in demand</h2><span class="text-link">Across open roles</span></div><div class="skill-bars">${skills.map(skill => `<div class="skill-bar-row"><span>${esc(skill.skill)}</span><div class="progress-track"><div class="progress-fill" style="width:${Math.max(12, Math.min(100, skill.demand * 25))}%"></div></div><span>${skill.demand}</span></div>`).join("")}</div></div>
    </section><section>
      <div class="panel"><div class="panel-heading"><h2>Your profile</h2><button class="text-link" data-page="profile">Edit profile →</button></div><div class="progress-row"><span>Profile completion</span><strong>${data.profile_completion}%</strong></div><div class="progress-track"><div class="progress-fill" style="width:${data.profile_completion}%"></div></div><div class="progress-row"><span>Keep it up — your details power better matches</span></div></div>
      <div class="panel"><div class="panel-heading"><h2>Skills to explore</h2><button class="text-link" data-page="recommendations">Skill gaps →</button></div>${data.skill_gaps.length ? `<div class="skill-chips">${data.skill_gaps.slice(0, 6).map(item => `<span class="chip missing">${esc(item.skill)} · ${item.count}</span>`).join("")}</div>` : `<div class="empty" style="padding:16px 4px">Your recommendations will surface the skills to learn next.</div>`}</div>
    </section></div>`;
}
async function jobsPage() {
  const data = await api("/api/jobs");
  return `${heading("Find your next role", "A good next step starts with a role that sees what you can do.", `<span class="match-pill">${data.length} open roles</span>`)}
    <div class="filters"><input class="input search" id="job-search" placeholder="Search roles, teams, or keywords"><input class="input" id="job-skill" placeholder="Skill (e.g. Python)"><input class="input" id="job-role" placeholder="Job role"><select class="select" id="job-mode"><option value="">Any work mode</option><option>Remote</option><option>Hybrid</option><option>On-site</option></select><select class="select" id="job-industry"><option value="">Any industry</option>${["Technology", "Finance", "Healthcare", "E-commerce", "Energy"].map(x => `<option>${x}</option>`).join("")}</select><select class="select" id="job-location"><option value="">Any location</option>${["Bengaluru", "Mumbai", "Hyderabad", "Pune", "Delhi"].map(x => `<option>${x}</option>`).join("")}</select><select class="select" id="job-size"><option value="">Any company size</option>${["51-200", "201-500", "501-1000"].map(x => `<option>${x}</option>`).join("")}</select><input class="input" id="job-experience" type="number" min="0" placeholder="Your experience (yrs)"><input class="input" id="job-salary" type="number" min="0" placeholder="Max salary (₹/yr)"><input class="input" id="job-match" type="number" min="0" max="100" placeholder="Min match %"></div>
    <div class="job-grid" id="job-results">${data.map(jobCard).join("") || `<div class="panel empty">No roles match just yet.</div>`}</div>`;
}
async function companyPage() {
  const data = await api("/api/companies");
  return `${heading("Meet your next team", "Explore companies building things you care about.")}<div class="filters"><input class="input search" id="company-search" placeholder="Search company or mission"><select class="select" id="company-industry"><option value="">Every industry</option>${["Technology", "Finance", "Healthcare", "E-commerce", "Energy"].map(x => `<option>${x}</option>`).join("")}</select><select class="select" id="company-location"><option value="">Every location</option>${["Bengaluru", "Mumbai", "Hyderabad", "Pune", "Delhi"].map(x => `<option>${x}</option>`).join("")}</select><select class="select" id="company-size"><option value="">Every company size</option>${["51-200", "201-500", "501-1000"].map(x => `<option>${x}</option>`).join("")}</select></div><div class="company-grid" id="company-results">${companyCards(data)}</div>`;
}
function companyCards(companies) {
  return companies.length ? companies.map(c => `<article class="company-card"><span class="company-logo">${esc(initials(c.name))}</span><h3>${esc(c.name)}</h3><div class="company-meta">${esc(c.industry)} · ${esc(c.location)} · ${esc(c.size)} people</div><p>${esc(c.description)}</p><div class="job-actions"><span class="match-line">${c.job_count ?? "—"} open roles</span><button class="button secondary small" data-save-company="${c.id}">Save company</button></div></article>`).join("") : `<div class="panel empty">No companies found for those filters.</div>`;
}
async function recommendationsPage() {
  const data = await api("/api/recommendations");
  const top = data.jobs[0];
  return `${heading("Made for your next move", "Every match comes with a clear score, the skills you bring, and the ones to grow next.")}
    ${top ? `<div class="panel"><div class="panel-heading"><h2>Your strongest match: ${esc(top.title)} at ${esc(top.company.name)}</h2><span class="match-pill">${top.score}% match</span></div><p style="font-size:12px;color:#718077;line-height:1.7">${top.reasons.map(esc).join(" ")}</p><strong style="font-size:11px">Why this role fits</strong>${chips(top.matching_skills)}<strong style="display:block;font-size:11px;margin-top:15px">Skills to grow</strong>${chips(top.missing_skills, true)}</div>` : ""}
    <div class="panel"><div class="panel-heading"><h2>Recommended jobs</h2><span class="text-link">${data.jobs.length} roles ranked by fit</span></div><div class="job-grid">${data.jobs.map(jobCard).join("")}</div></div>
    <div class="panel"><div class="panel-heading"><h2>Companies worth exploring</h2><span class="text-link">${data.companies.length} teams</span></div><div class="company-grid">${data.companies.map(c => `<article class="company-card"><span class="company-logo">${esc(initials(c.name))}</span><h3>${esc(c.name)}</h3><div class="company-meta">${esc(c.industry)} · ${esc(c.location)}</div><div class="match-pill">${c.score}% match</div><p>${esc(c.reasons[0] || "")}</p><button class="button secondary small" data-save-company="${c.id}">Save company</button></article>`).join("")}</div></div>`;
}
async function savedPage() {
  const data = await api("/api/saved");
  return `${heading("Keep the good ones close", "Roles and companies you’ve saved for another look.")}
    <div class="panel"><div class="panel-heading"><h2>Saved roles</h2><span class="text-link">${data.jobs.length} roles</span></div>${data.jobs.length ? `<div class="job-grid">${data.jobs.map(jobCard).join("")}</div>` : `<div class="empty">Your saved roles will show up here.</div>`}</div>
    <div class="panel"><div class="panel-heading"><h2>Saved companies</h2><span class="text-link">${data.companies.length} companies</span></div>${data.companies.length ? `<div class="company-grid">${companyCards(data.companies)}</div>` : `<div class="empty">Save a company to come back to it later.</div>`}</div>`;
}
function splitInput(value) { return value.split(",").map(x => x.trim()).filter(Boolean); }
async function profilePage() {
  const [p, companies] = await Promise.all([api("/api/profile"), api("/api/companies")]);
  const value = items => (items || []).join(", ");
  return `${heading("Your skills, your story", "A complete profile leads to more meaningful recommendations.")}
    <form class="panel" id="profile-form"><div class="panel-heading"><h2>Career profile</h2><span class="text-link">Your details stay yours</span></div><div class="form-grid">
    <div class="field"><label>Full name</label><input class="input" name="name" value="${esc(p.name)}" required></div>
    <div class="field"><label>Email</label><input class="input" value="${esc(p.email)}" disabled></div>
    <div class="field"><label>Years of experience</label><input class="input" name="experience_years" type="number" min="0" max="60" step=".5" value="${p.experience_years}"></div>
    <div class="field"><label>Education / qualification</label><input class="input" name="education" value="${esc(p.education)}" placeholder="e.g. Bachelor's in Computer Science"></div>
    <div class="field full"><label>Your skills <small style="color:#94a098;font-weight:400">(comma separated)</small></label><input class="input" name="skills" value="${esc(value(p.skills.map(x => x.skill)))}" placeholder="Python, SQL, Machine Learning"></div>
    <div class="field"><label>Preferred job roles</label><input class="input" name="preferred_roles" value="${esc(value(p.preferred_roles))}" placeholder="Data Analyst, ML Engineer"></div>
    <div class="field"><label>Preferred industries</label><input class="input" name="preferred_industries" value="${esc(value(p.preferred_industries))}" placeholder="Technology, Finance"></div>
    <div class="field"><label>Preferred locations</label><input class="input" name="preferred_locations" value="${esc(value(p.preferred_locations))}" placeholder="Bengaluru, Remote"></div>
    <div class="field"><label>Certifications</label><input class="input" name="certifications" value="${esc(value(p.certifications))}" placeholder="AWS Cloud Practitioner"></div>
    <div class="field full"><label>Education history <small style="color:#94a098;font-weight:400">(one per line: qualification | field of study | institution | graduation year)</small></label><textarea class="textarea" name="education_history" placeholder="BSc | Computer Science | State University | 2025">${esc((p.education_history || []).map(x => [x.qualification, x.field_of_study, x.institution, x.graduation_year].join(" | ")).join("\n"))}</textarea></div>
    <div class="field full"><label>Projects <small style="color:#94a098;font-weight:400">(one per line: project name — description)</small></label><textarea class="textarea" name="projects" placeholder="Sales forecast — Built a forecasting model with Python">${esc((p.projects || []).map(x => `${x.name} — ${x.description}`).join("\n"))}</textarea></div>
    </div><div class="form-actions"><label class="button secondary" for="resume-file" style="cursor:pointer">Upload resume</label><input id="resume-file" type="file" accept=".pdf,.doc,.docx" hidden><button class="button" type="submit">Save profile</button></div></form>
    <div class="panel"><div class="panel-heading"><h2>Find companies</h2><button class="text-link" data-page="companies">Explore all companies →</button></div>
      <div class="filters"><input class="input search" id="company-search" placeholder="Search company or mission"><select class="select" id="company-industry"><option value="">Every industry</option>${["Technology", "Finance", "Healthcare", "E-commerce", "Energy"].map(x => `<option>${x}</option>`).join("")}</select><select class="select" id="company-location"><option value="">Every location</option>${["Bengaluru", "Mumbai", "Hyderabad", "Pune", "Delhi"].map(x => `<option>${x}</option>`).join("")}</select><select class="select" id="company-size"><option value="">Every company size</option>${["51-200", "201-500", "501-1000"].map(x => `<option>${x}</option>`).join("")}</select></div>
      <div class="company-grid" id="company-results">${companyCards(companies)}</div></div>
    <div class="panel"><div class="panel-heading"><h2>Profile tips</h2></div><p style="font-size:12px;color:#78857c;line-height:1.7;margin:0">Add specific skills, roles you’re interested in, and a few projects. SkillMatch uses these details to calculate transparent matches — we never hide why a role is recommended.</p></div>`;
}
async function saveProfile(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const projects = String(form.get("projects") || "").split("\n").map(line => {
    const [name, ...description] = line.split(/[—-]/);
    return { name: name.trim(), description: description.join(" ").trim() };
  }).filter(x => x.name);
  const education_history = String(form.get("education_history") || "").split("\n").map(line => {
    const [qualification = "", field_of_study = "", institution = "", graduation_year = ""] = line.split("|").map(value => value.trim());
    return { qualification, field_of_study, institution, graduation_year };
  }).filter(x => x.qualification);
  const body = { name: form.get("name"), experience_years: Number(form.get("experience_years") || 0), education: form.get("education"),
    skills: splitInput(form.get("skills") || ""), education_history, preferred_roles: splitInput(form.get("preferred_roles") || ""),
    preferred_industries: splitInput(form.get("preferred_industries") || ""), preferred_locations: splitInput(form.get("preferred_locations") || ""),
    certifications: splitInput(form.get("certifications") || ""), projects };
  try { await api("/api/profile", { method: "PUT", body: JSON.stringify(body) }); notify("Profile updated. Your matches are refreshed."); await render(); }
  catch (error) { notify(error.message); }
}
async function adminPage() {
  const data = await api("/api/admin/overview");
  const weights = await api("/api/admin/weights");
  const factors = { skills: "Skill match", experience: "Experience", education: "Education", role: "Job role", industry: "Industry", location: "Location", extras: "Certifications & projects" };
  return `${heading("Manage the marketplace", "Keep company data, roles, and recommendation logic up to date.")}
    <div class="stats">${stat("Registered members", data.users, "Active user accounts", icons.person)}${stat("Companies", data.companies, "In the directory", icons.building)}${stat("Open jobs", data.jobs, "Across all companies", icons.briefcase)}${stat("Match factors", Object.keys(weights).length, "Configurable scoring inputs", icons.chart)}</div>
    <div class="dashboard-grid"><section><div class="panel"><div class="panel-heading"><h2>Companies</h2><button class="button small" id="add-company">Add company</button></div><div class="company-admin-row header"><span>Company</span><span>Industry</span><span>Location</span><span>Manage</span></div>${data.companies_list.map(c => `<div class="company-admin-row"><strong>${esc(c.name)}</strong><span>${esc(c.industry)}</span><span>${esc(c.location)}</span><span><button class="text-link" data-edit-company="${c.id}">Edit</button> <button class="text-link" data-delete-company="${c.id}" style="color:#bd5145">Delete</button></span></div>`).join("")}</div></section>
    <section><div class="panel"><div class="panel-heading"><h2>Recommendation weights</h2></div><p style="font-size:10px;color:#849087">Weights are relative; the engine normalizes them to produce a 0–100 score.</p>${Object.entries(weights).map(([key,weight]) => `<label class="weight-row"><span>${factors[key]}</span><input type="range" min="0" max="100" value="${Math.round(weight*100)}" data-weight="${key}"><strong id="weight-${key}">${Math.round(weight*100)}%</strong></label>`).join("")}<button class="button small" id="save-weights">Save weights</button></div>
    <div class="panel"><div class="panel-heading"><h2>Add a job</h2></div><form id="admin-job-form" class="form-grid"><div class="field full"><label>Company</label><select class="select" name="company_id" required>${data.companies_list.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join("")}</select></div><div class="field full"><label>Job title</label><input class="input" name="title" required></div><div class="field full"><label>Description</label><textarea class="textarea" name="description" required></textarea></div><div class="field full"><label>Skills (comma separated)</label><input class="input" name="skills" required></div><div class="field"><label>Min. experience</label><input class="input" type="number" name="experience_min" min="0" value="0"></div><div class="field"><label>Max. experience</label><input class="input" type="number" name="experience_max" min="0" value="5"></div><div class="field"><label>Education</label><input class="input" name="education"></div><div class="field"><label>Work mode</label><select class="select" name="work_mode"><option>Remote</option><option>Hybrid</option><option>On-site</option></select></div><div class="field"><label>Min. annual salary</label><input class="input" name="salary_min" type="number" min="0" value="0"></div><div class="field"><label>Max. annual salary</label><input class="input" name="salary_max" type="number" min="0" value="0"></div><div class="field full form-actions"><button class="button" type="submit">Create job</button></div></form></div></section></div>
    <div class="panel admin-job-list"><div class="panel-heading"><h2>Manage jobs</h2></div>${data.jobs_list.map(j => `<div class="admin-job-row"><strong>${esc(j.title)}</strong><span>${esc(j.company.name)}</span><span>${j.experience_min}–${j.experience_max} yrs</span><span><button class="text-link" data-edit-job="${j.id}">Edit</button> <button class="text-link" data-delete-job="${j.id}" style="color:#bd5145">Delete</button></span></div>`).join("")}</div>`;
}
async function adminHandlers() {
  document.querySelectorAll("[data-weight]").forEach(input => input.oninput = () => document.querySelector(`#weight-${input.dataset.weight}`).textContent = `${input.value}%`);
  document.querySelector("#save-weights").onclick = async () => {
    const body = Object.fromEntries([...document.querySelectorAll("[data-weight]")].map(x => [x.dataset.weight, Number(x.value) / 100]));
    try { await api("/api/admin/weights", { method: "PUT", body: JSON.stringify(body) }); notify("Recommendation weights updated."); }
    catch (error) { notify(error.message); }
  };
  document.querySelector("#add-company").onclick = async () => {
    const name = prompt("Company name");
    if (!name) return;
    const industry = prompt("Industry") || "";
    const location = prompt("Location") || "";
    const size = prompt("Company size (e.g. 51-200)") || "";
    const description = prompt("Company description") || "";
    try { await api("/api/admin/companies", { method: "POST", body: JSON.stringify({ name, industry, location, size, description }) }); notify("Company added."); await render(); }
    catch (error) { notify(error.message); }
  };
  document.querySelectorAll("[data-edit-company]").forEach(button => button.onclick = async () => {
    try {
      const company = (await api("/api/companies")).find(c => c.id === Number(button.dataset.editCompany));
      const name = prompt("Company name", company.name); if (!name) return;
      const industry = prompt("Industry", company.industry) || "";
      const location = prompt("Location", company.location) || "";
      const size = prompt("Company size", company.size) || "";
      const description = prompt("Description", company.description) || "";
      await api(`/api/admin/companies/${company.id}`, { method: "PUT", body: JSON.stringify({ name, industry, location, size, description }) });
      notify("Company updated."); await render();
    } catch (error) { notify(error.message); }
  });
  document.querySelectorAll("[data-delete-company]").forEach(button => button.onclick = async () => {
    if (!confirm("Delete this company and all of its jobs?")) return;
    try { await api(`/api/admin/companies/${button.dataset.deleteCompany}`, { method: "DELETE" }); notify("Company deleted."); await render(); }
    catch (error) { notify(error.message); }
  });
  document.querySelectorAll("[data-delete-job]").forEach(button => button.onclick = async () => {
    if (!confirm("Delete this job?")) return;
    try { await api(`/api/admin/jobs/${button.dataset.deleteJob}`, { method: "DELETE" }); notify("Job deleted."); await render(); }
    catch (error) { notify(error.message); }
  });
  document.querySelectorAll("[data-edit-job]").forEach(button => button.onclick = async () => {
    try {
      const jobs = await api("/api/jobs");
      const job = jobs.find(j => j.id === Number(button.dataset.editJob));
      if (!job) { notify("This job is not available."); return; }
      const title = prompt("Job title", job.title); if (!title) return;
      const description = prompt("Description", job.description) || "";
      const skills = prompt("Required skills (comma separated)", job.skills.join(", ")) || "";
      const body = { company_id: job.company_id, title, description, skills: splitInput(skills), experience_min: job.experience_min,
        experience_max: job.experience_max, education: job.education, salary_min: job.salary_min, salary_max: job.salary_max, work_mode: job.work_mode };
      await api(`/api/admin/jobs/${job.id}`, { method: "PUT", body: JSON.stringify(body) }); notify("Job updated."); await render();
    } catch (error) { notify(error.message); }
  });
  document.querySelector("#admin-job-form").onsubmit = async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = Object.fromEntries(form.entries());
    body.company_id = Number(body.company_id); body.experience_min = Number(body.experience_min); body.experience_max = Number(body.experience_max);
    body.salary_min = Number(body.salary_min); body.salary_max = Number(body.salary_max); body.skills = splitInput(body.skills);
    try { await api("/api/admin/jobs", { method: "POST", body: JSON.stringify(body) }); notify("Job opening created."); await render(); }
    catch (error) { notify(error.message); }
  };
}
function wireSearch(route) {
  const fields = route === "jobs" ? ["job-search", "job-skill", "job-role", "job-mode", "job-industry", "job-location", "job-size", "job-experience", "job-salary", "job-match"] : ["company-search", "company-industry", "company-location", "company-size"];
  const run = async () => {
    const value = id => document.querySelector(`#${id}`).value;
    try {
      if (route === "jobs") {
        const params = new URLSearchParams({ search: value(fields[0]), skill: value(fields[1]), role: value(fields[2]), work_mode: value(fields[3]), industry: value(fields[4]), location: value(fields[5]), company_size: value(fields[6]), min_experience: value(fields[7]), max_salary: value(fields[8]), min_match: value(fields[9]) || 0 });
        const jobs = await api(`/api/jobs?${params}`);
        document.querySelector("#job-results").innerHTML = jobs.map(jobCard).join("") || `<div class="panel empty">No roles match those filters. Try a different search.</div>`;
        bindSaveButtons();
      } else {
        const params = new URLSearchParams({ search: value(fields[0]), industry: value(fields[1]), location: value(fields[2]), size: value(fields[3]) });
        const companies = await api(`/api/companies?${params}`);
        document.querySelector("#company-results").innerHTML = companyCards(companies);
        bindSaveButtons();
      }
    } catch (error) { notify(error.message); }
  };
  fields.forEach(id => {
    const element = document.querySelector(`#${id}`);
    element.addEventListener(element.tagName === "INPUT" && element.type !== "number" ? "input" : "change", run);
  });
}
async function render() {
  if (!state.token) { authPage(); return; }
  try {
    state.user = await api("/api/auth/me");
    let content;
    if (state.page === "dashboard") content = await dashboardPage();
    else if (state.page === "jobs") content = await jobsPage();
    else if (state.page === "companies") content = await companyPage();
    else if (state.page === "recommendations") content = await recommendationsPage();
    else if (state.page === "saved") content = await savedPage();
    else if (state.page === "profile") content = await profilePage();
    else if (state.page === "admin" && state.user.role === "admin") content = await adminPage();
    else { state.page = "dashboard"; content = await dashboardPage(); }
    layout(content);
    if (state.page === "jobs" || state.page === "recommendations" || state.page === "saved") bindSaveButtons();
    if (state.page === "jobs" || state.page === "companies") wireSearch(state.page);
    if (state.page === "profile") {
      wireSearch("companies");
      document.querySelector("#profile-form").onsubmit = saveProfile;
      document.querySelector("#resume-file").onchange = async event => {
        if (!event.target.files[0]) return;
        const form = new FormData(); form.append("file", event.target.files[0]);
        try { await api("/api/profile/resume", { method: "POST", body: form }); notify("Resume uploaded securely."); }
        catch (error) { notify(error.message); }
      };
    }
    if (state.page === "admin") await adminHandlers();
  } catch (error) {
    if (error.status !== 401) app.innerHTML = `<main class="content"><div class="panel empty">${esc(error.message)} <button class="button" onclick="location.reload()">Try again</button></div></main>`;
  }
}
window.addEventListener("popstate", () => {
  if (!state.token) authPage(location.pathname === "/register" ? "register" : "login");
  else render();
});
if (!state.token) authPage(location.pathname === "/register" ? "register" : "login");
else render();
