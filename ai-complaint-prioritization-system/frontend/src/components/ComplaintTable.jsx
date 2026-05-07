import React, { useMemo, useState } from "react";
import { AlertTriangle } from "lucide-react";

const statuses = ["Pending", "In Progress", "Resolved"];
const priorities = ["All", "High", "Medium", "Low"];
const sdgs = ["All", "SDG 9", "SDG 16"];

export default function ComplaintTable({ complaints, loading, onStatusChange }) {
  const [priority, setPriority] = useState("All");
  const [status, setStatus] = useState("All");
  const [sdg, setSdg] = useState("All");
  const [category, setCategory] = useState("All");

  const categories = useMemo(
    () => ["All", ...Array.from(new Set(complaints.map((item) => item.category).filter(Boolean)))],
    [complaints]
  );

  const filtered = complaints.filter((item) => {
    return (
      (priority === "All" || item.priority === priority) &&
      (status === "All" || item.status === status) &&
      (sdg === "All" || item.sdg === sdg) &&
      (category === "All" || item.category === category)
    );
  });

  return (
    <section className="card">
      <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-center">
        <h2 className="section-title">Complaint Queue</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Filter value={priority} onChange={setPriority} options={priorities} />
          <Filter value={status} onChange={setStatus} options={["All", ...statuses]} />
          <Filter value={category} onChange={setCategory} options={categories} />
          <Filter value={sdg} onChange={setSdg} options={sdgs} />
        </div>
      </div>
      <div className="mt-5 overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-100 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="table-cell">Complaint</th>
              <th className="table-cell">Priority</th>
              <th className="table-cell">AI Reason</th>
              <th className="table-cell">SDG</th>
              <th className="table-cell">SLA Deadline</th>
              <th className="table-cell">Status</th>
              <th className="table-cell">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {loading && <TableMessage text="Loading complaints..." />}
            {!loading && filtered.length === 0 && <TableMessage text="No complaints found." />}
            {!loading &&
              filtered.map((item) => (
                <tr key={item.id} className="align-top">
                  <td className="table-cell max-w-xs">
                    <div className="font-semibold text-slate-900">{item.title}</div>
                    <div className="mt-1 text-slate-500">{item.department} | {item.name}</div>
                    <div className="mt-2 line-clamp-2 text-slate-600">{item.description}</div>
                    {item.escalation_required && (
                      <div className="mt-2 flex items-center gap-1 font-semibold text-red-700">
                        <AlertTriangle size={16} /> Needs Immediate Attention
                      </div>
                    )}
                  </td>
                  <td className="table-cell">
                    <span className={`priority priority-${item.priority?.toLowerCase()}`}>{item.priority}</span>
                    <div className="mt-2 font-semibold text-slate-700">Score: {item.priority_score}</div>
                  </td>
                  <td className="table-cell max-w-sm text-slate-600">{item.ai_reason}</td>
                  <td className="table-cell"><span className="sdg-pill">{item.sdg}</span></td>
                  <td className="table-cell whitespace-nowrap">{formatDate(item.sla_deadline)}</td>
                  <td className="table-cell"><span className="status-pill">{item.status}</span></td>
                  <td className="table-cell">
                    <div className="flex flex-wrap gap-2">
                      {statuses.map((nextStatus) => (
                        <button
                          className="small-button"
                          key={nextStatus}
                          onClick={() => onStatusChange(item.id, nextStatus)}
                          disabled={item.status === nextStatus}
                        >
                          {nextStatus}
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Filter({ value, onChange, options }) {
  return (
    <select className="input py-2 text-sm" value={value} onChange={(event) => onChange(event.target.value)}>
      {options.map((option) => (
        <option key={option} value={option}>{option}</option>
      ))}
    </select>
  );
}

function TableMessage({ text }) {
  return (
    <tr>
      <td className="table-cell text-center text-slate-500" colSpan="7">{text}</td>
    </tr>
  );
}

function formatDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
