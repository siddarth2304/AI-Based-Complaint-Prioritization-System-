import React, { useState } from "react";
import { Send } from "lucide-react";
import { api } from "../api";

const initialState = {
  name: "",
  email: "",
  department: "CSE",
  title: "",
  description: "",
};

export default function ComplaintForm({ onCreated }) {
  const [form, setForm] = useState(initialState);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  function updateField(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    try {
      await api.submitComplaint(form);
      setForm(initialState);
      setMessage("Complaint submitted and prioritized successfully.");
      await onCreated();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card h-fit">
      <h2 className="section-title">Submit Complaint</h2>
      <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
        <input className="input" name="name" placeholder="Student name" value={form.name} onChange={updateField} required />
        <input className="input" name="email" type="email" placeholder="student@example.com" value={form.email} onChange={updateField} required />
        <input className="input" name="department" placeholder="Department" value={form.department} onChange={updateField} required />
        <input className="input" name="title" placeholder="Complaint title" value={form.title} onChange={updateField} required />
        <textarea className="input min-h-32 resize-y" name="description" placeholder="Describe the complaint clearly" value={form.description} onChange={updateField} required />
        <button className="primary-button w-full" type="submit" disabled={submitting}>
          <Send size={18} />
          {submitting ? "Analyzing..." : "Submit for AI Triage"}
        </button>
      </form>
      {message && <p className="mt-4 rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-700">{message}</p>}
    </section>
  );
}
