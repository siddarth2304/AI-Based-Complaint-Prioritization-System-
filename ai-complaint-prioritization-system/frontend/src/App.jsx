import React, { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Cloud, ShieldCheck, ServerCog } from "lucide-react";
import { api } from "./api";
import ComplaintForm from "./components/ComplaintForm";
import DashboardCards from "./components/DashboardCards";
import ComplaintTable from "./components/ComplaintTable";
import PriorityChart from "./components/PriorityChart";
import SDGChart from "./components/SDGChart";

export default function App() {
  const [complaints, setComplaints] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const [complaintData, statsData] = await Promise.all([api.getComplaints(), api.getStats()]);
      setComplaints(complaintData);
      setStats(statsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const chartData = useMemo(
    () => ({
      priority: [
        { name: "High", value: stats?.high || 0 },
        { name: "Medium", value: stats?.medium || 0 },
        { name: "Low", value: stats?.low || 0 },
      ],
      sdg: [
        { name: "SDG 9", value: stats?.sdg_9_count || 0 },
        { name: "SDG 16", value: stats?.sdg_16_count || 0 },
      ],
    }),
    [stats]
  );

  async function handleStatusChange(id, status) {
    await api.updateStatus(id, status);
    await loadData();
  }

  async function handleRatingChange(id, rating) {
    await api.submitRating(id, rating);
    await loadData();
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-blue-700">
                <Cloud size={18} />
                Cloud Run + Firestore + Vertex AI + Cloud Functions
              </div>
              <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
                AI-Based Complaint Prioritization System
              </h1>
              <p className="mt-2 text-lg text-slate-600">Smart Triage using Cloud & AI</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <span className="badge badge-blue">
                <ServerCog size={16} /> SDG 9: Industry, Innovation & Infrastructure
              </span>
              <span className="badge badge-purple">
                <ShieldCheck size={16} /> SDG 16: Peace, Justice & Institutions
              </span>
            </div>
          </div>
          {error && (
            <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertTriangle size={18} />
              {error}
            </div>
          )}
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[380px_1fr] lg:px-8">
        <ComplaintForm onCreated={loadData} />
        <section className="space-y-6">
          <DashboardCards stats={stats} loading={loading} />
          <div className="grid gap-6 xl:grid-cols-2">
            <PriorityChart data={chartData.priority} />
            <SDGChart data={chartData.sdg} />
          </div>
          <ComplaintTable
            complaints={complaints}
            loading={loading}
            onStatusChange={handleStatusChange}
            onRatingChange={handleRatingChange}
            onRefresh={loadData}
          />
        </section>
      </div>
    </main>
  );
}
