import React, { useEffect, useState } from "react";
import { ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid, ReferenceLine } from "recharts";

const f = (x, d = 0) => (x == null ? "–" : Number(x).toLocaleString("en-GB", { maximumFractionDigits: d }));
const get = (u) => fetch(u).then((r) => (r.ok ? r.json() : r.json().then((e) => Promise.reject(e.detail || r.statusText))));
const tick = { fill: "#94a3b8", fontSize: 11 };
const fmtT = (t) => new Date(t).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" });
const fmtDT = (t) => new Date(t).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/London" });

function Kpi({ label, value, unit }) {
  return <div className="card kpi"><span>{label}</span><b>{value}<small style={{ fontSize: 12 }}> {unit}</small></b></div>;
}

export default function App() {
  const [cfg, setCfg] = useState(null);
  const [date, setDate] = useState("2026-01-15");
  const [cutoff, setCutoff] = useState(9);
  const [day, setDay] = useState(null);
  const [m, setM] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { get("/api/config").then((c) => { setCfg(c); setCutoff(c.default_cutoff_hour); }).catch((e) => setErr(String(e))); }, []);
  useEffect(() => {
    setLoading(true); setErr(null);
    Promise.all([get(`/api/decision/${date}?cutoff_hour=${cutoff}`), get(`/api/metrics?cutoff_hour=${cutoff}`)])
      .then(([d, mm]) => { setDay(d); setM(mm); }).catch((e) => setErr(String(e))).finally(() => setLoading(false));
  }, [date, cutoff]);

  const s = day?.summary, o = m?.overall;
  const series = (day?.series || []).map((r) => ({ ...r, time: fmtT(r.t) }));

  return (<>
    <header>
      <h1>⚡ Wind Forecast Desk – GB day-ahead</h1>
      <div className="ctl">
        <label>Delivery day
          <select value={date} onChange={(e) => setDate(e.target.value)}>{(cfg?.delivery_dates || [date]).map((d) => <option key={d}>{d}</option>)}</select></label>
        <label>Decision cut-off (London, D-1) {cutoff}:00
          <input type="range" min="0" max="23" step="1" value={cutoff} onChange={(e) => setCutoff(+e.target.value)} /></label>
      </div>
    </header>
    <main>
      {cfg?.demo_data && <div className="banner">DEMO MODE: synthetic data – not Elexon data.</div>}
      {err && <div className="card err">Error: {String(err)}. Is the API reachable at /api/health?</div>}
      {loading && <div className="sub">Loading from Elexon (first load can take ~30s)…</div>}

      {day && <>
        <div className="card">
          <h2>Forecast available at decision time for {date}</h2>
          <div className="sub">Latest WINDFOR forecast published at/before {fmtDT(day.decision_cutoff)}; most recent vintage used: {day.latest_publish ? fmtDT(day.latest_publish) : "none"}. Actuals (FUELHH) shown for hindsight.</div>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={series}><CartesianGrid stroke="#334155" />
              <XAxis dataKey="time" tick={tick} interval={5} /><YAxis tick={tick} unit=" MW" width={80} />
              <Tooltip contentStyle={{ background: "#0f172a" }} formatter={(v) => f(v) + " MW"} />
              <Legend />
              <Line dataKey="forecast" name="Forecast (at decision)" stroke="#38bdf8" dot={false} strokeWidth={2} />
              <Line dataKey="actual" name="Actual" stroke="#f59e0b" dot={false} strokeWidth={2} /></LineChart>
          </ResponsiveContainer>
        </div>

        <div className="kpis">
          <Kpi label="Day MAE" value={f(s.mae)} unit="MW" />
          <Kpi label="Day bias (fcst − actual)" value={f(s.bias)} unit="MW" />
          <Kpi label="Jan MAE" value={f(o?.mae)} unit="MW" />
          <Kpi label="Jan RMSE" value={f(o?.rmse)} unit="MW" />
          <Kpi label="Jan WAPE" value={f(o?.wape_pct, 1)} unit="%" />
          <Kpi label="Suggested buffer (P90 shortfall)" value={f(o?.p90_shortfall)} unit="MW" />
        </div>
      </>}

      {m && <>
        <div className="grid2">
          <div className="card"><h2>Error by delivery hour (Jan)</h2><div className="sub">MAE and P90 over-forecast (shortfall risk) per London hour.</div>
            <ResponsiveContainer width="100%" height={260}><BarChart data={m.by_hour}><CartesianGrid stroke="#334155" />
              <XAxis dataKey="hour" tick={tick} /><YAxis tick={tick} width={60} /><Tooltip contentStyle={{ background: "#0f172a" }} formatter={(v) => f(v) + " MW"} /><Legend />
              <Bar dataKey="mae" name="MAE" fill="#38bdf8" /><Bar dataKey="p90_shortfall" name="P90 shortfall" fill="#f87171" /></BarChart></ResponsiveContainer></div>
          <div className="card"><h2>Error vs forecast horizon</h2><div className="sub">All forecast vintages; shows why fresher forecasts matter.</div>
            <ResponsiveContainer width="100%" height={260}><BarChart data={m.by_horizon.map((h) => ({ ...h, label: `${h.horizon_from_h}-${h.horizon_from_h + 6}h` }))}><CartesianGrid stroke="#334155" />
              <XAxis dataKey="label" tick={tick} /><YAxis tick={tick} width={60} /><Tooltip contentStyle={{ background: "#0f172a" }} formatter={(v) => f(v) + " MW"} /><Legend />
              <Bar dataKey="mae" name="MAE" fill="#38bdf8" /><Bar dataKey="rmse" name="RMSE" fill="#a78bfa" /></BarChart></ResponsiveContainer></div>
        </div>
        <div className="card"><h2>Daily accuracy (click a row to inspect that day)</h2>
          <table><thead><tr><th>Delivery day</th><th>MAE MW</th><th>RMSE MW</th><th>Bias MW</th><th>WAPE %</th><th>P90 shortfall MW</th></tr></thead>
            <tbody>{m.by_day.map((r) => <tr key={r.date} style={{ cursor: "pointer", background: r.date === date ? "#334155" : "" }} onClick={() => setDate(r.date)}>
              <td>{r.date}</td><td>{f(r.mae)}</td><td>{f(r.rmse)}</td><td>{f(r.bias)}</td><td>{f(r.wape_pct, 1)}</td><td>{f(r.p90_shortfall)}</td></tr>)}</tbody></table>
        </div>
      </>}
    </main></>);
}
