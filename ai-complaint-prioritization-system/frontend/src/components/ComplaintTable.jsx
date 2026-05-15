import React from "react";

export default function ComplaintTable({ complaints = [], loading = false }) {
  return (
    <section className="card">
      <h2 className="section-title">Complaint Queue</h2>
      <div className="mt-5 overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <tbody className="divide-y divide-slate-100 bg-white">
            {loading && <tr><td className="table-cell text-center text-slate-500">Loading complaints...</td></tr>}
            {!loading && complaints.map((item) => (
              <tr key={item.id}>
                <td className="table-cell">
                  <strong>{item.title}</strong>
                  <p className="mt-1 whitespace-pre-wrap text-slate-600">{item.description}</p>
                  {item.ai_solution && <pre className="mt-2 whitespace-pre-wrap rounded bg-blue-50 p-2 text-blue-950">{item.ai_solution}</pre>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
