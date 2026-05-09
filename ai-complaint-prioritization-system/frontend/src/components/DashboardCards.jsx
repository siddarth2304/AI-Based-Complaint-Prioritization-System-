import React from "react";
import { AlertCircle, BarChart3, CheckCircle2, Clock, Gauge, Inbox, Siren, Star } from "lucide-react";

const cards = [
  ["Total", "total", Inbox],
  ["High Priority", "high", AlertCircle],
  ["Pending", "pending", Clock],
  ["In Progress", "in_progress", BarChart3],
  ["Resolved", "resolved", CheckCircle2],
  ["Avg Score", "average_priority_score", Gauge],
  ["Avg Rating", "average_satisfaction_rating", Star],
  ["Escalations", "escalation_count", Siren],
];

export default function DashboardCards({ stats, loading }) {
  return (
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map(([label, key, Icon]) => (
        <div className="metric-card" key={key}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-500">{label}</span>
            <Icon className="text-blue-700" size={20} />
          </div>
          <strong className="mt-3 block text-3xl font-bold">{loading ? "--" : stats?.[key] ?? 0}</strong>
        </div>
      ))}
    </section>
  );
}
