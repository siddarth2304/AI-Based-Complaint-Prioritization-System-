import React, { useMemo, useState } from "react";
import { AlertTriangle, Star, Lightbulb, Loader2 } from "lucide-react";
import { api } from "../api";

const statuses = ["Pending", "In Progress", "Resolved"];
const priorities = ["All", "High", "Medium", "Low"];
const sdgs = ["All", "SDG 9", "SDG 16"];

export default function ComplaintTable({ complaints, loading, onStatusChange, onRatingChange }) {
  const [priority, setPriority] = useState("All");
  const [status, setStatus] = useState("All");
  const [sdg, setSdg] = useState("All");
  const [category, setCategory] = useState("All");
  const [loadingSolution, setLoadingSolution] = useState(null);

  async function handleGetSolution(id) {
    setLoadingSolution(id);
    try {
      await api.generateSolution(id);
      // We need to trigger a refresh to show the new solution
      // Since we don't have a direct onRefresh prop, we'll reuse onStatusChange with the current status to force a reload 
      // or we can assume App.jsx will pass an onRefresh prop if we add it. 
      // Let's just update the local item if possible, but we don't own the state.
      // A safe hack is calling a parent function or reloading the page, but let's just use window.location.reload() for simplicity if onRefresh is missing, or add onRefresh to App.jsx.
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingSolution(null);
    }
  }

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
                    <div className="mt-1 font-medium text-blue-700">Assigned: {item.assigned_department}</div>
                    <div className="mt-2 line-clamp-2 text-slate-600">{item.description}</div>
                    {item.escalation_required && (
                      <div className="mt-2 flex items-center gap-1 font-semibold text-red-700">
                        <AlertTriangle size={16} /> Needs Immediate Attention
                      </div>
                    )}
                    
                    {item.ai_solution ? (
                      <div className="mt-3 rounded-md bg-blue-50 p-3 text-sm text-blue-900 border border-blue-100">
                        <div className="flex items-center gap-2 font-semibold mb-2">
                          <Lightbulb size={16} className="text-yellow-500" /> AI Co-Pilot Resolution:
                        </div>
                        <div className="prose prose-sm prose-blue max-w-none" dangerouslySetInnerHTML={{ __html: item.ai_solution.replace(/\n/g, '<br/>') }} />
                      </div>
                    ) : item.status !== "Resolved" ? (
                      <button
                        onClick={async () => {
                          setLoadingSolution(item.id);
                          try {
                            await api.generateSolution(item.id);
                            window.location.reload(); // Simple way to refresh data
                          } catch (e) {
                            console.error(e);
                            alert("Failed to get solution: " + e.message + "\nDid you restart the backend?");
                          } finally {
                            setLoadingSolution(null);
                          }
                        }}
                        disabled={loadingSolution === item.id}
                        className="mt-3 flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700 disabled:opacity-50"
                      >
                        {loadingSolution === item.id ? <Loader2 size={16} className="animate-spin" /> : <Lightbulb size={16} />}
                        Get AI Resolution Steps
                      </button>
                    ) : null}
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
                    {item.status === "Resolved" ? (
                      <div>
                        {item.rating ? (
                          <div className="flex gap-1 text-yellow-500">
                            {[...Array(item.rating)].map((_, i) => (
                              <Star key={i} size={16} fill="currentColor" />
                            ))}
                          </div>
                        ) : (
                          <div className="flex flex-col gap-2">
                            <span className="text-xs text-slate-500">Rate resolution:</span>
                            <div className="flex gap-1">
                              {[1, 2, 3, 4, 5].map((star) => (
                                <button
                                  key={star}
                                  onClick={() => onRatingChange(item.id, star)}
                                  className="text-slate-300 hover:text-yellow-500 transition-colors"
                                >
                                  <Star size={20} />
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
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
                    )}
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
