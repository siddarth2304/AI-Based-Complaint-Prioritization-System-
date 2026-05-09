import React, { useState } from "react";
import { Send, Mic, MicOff } from "lucide-react";
import { api } from "../api";

const initialState = {
  name: "",
  email: "",
  department: "CSE",
  title: "",
  description: "",
  image: null,
};

export default function ComplaintForm({ onCreated }) {
  const [form, setForm] = useState(initialState);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [isListening, setIsListening] = useState(false);

  function updateField(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  function handleImageChange(event) {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setForm({ ...form, image: reader.result }); // Base64
      };
      reader.readAsDataURL(file);
    } else {
      setForm({ ...form, image: null });
    }
  }

  function toggleListening() {
    if (isListening) {
      setIsListening(false);
      return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Your browser does not support Speech Recognition.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = () => setIsListening(true);
    
    recognition.onresult = (event) => {
      let currentTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        currentTranscript += event.results[i][0].transcript;
      }
      setForm((prev) => ({ ...prev, description: prev.description + " " + currentTranscript.trim() }));
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error", event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
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
        <div className="relative">
          <textarea className="input min-h-32 resize-y pb-10" name="description" placeholder="Describe the complaint clearly..." value={form.description} onChange={updateField} required />
          <button
            type="button"
            onClick={toggleListening}
            className={`absolute bottom-3 right-3 flex items-center justify-center rounded-full p-2 transition-colors ${
              isListening ? "bg-red-100 text-red-600 animate-pulse" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
            title={isListening ? "Stop listening" : "Start dictating"}
          >
            {isListening ? <MicOff size={18} /> : <Mic size={18} />}
          </button>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-slate-700">Optional Evidence (Image)</label>
          <input className="input py-2 text-sm" type="file" accept="image/*" onChange={handleImageChange} />
        </div>
        <button className="primary-button w-full" type="submit" disabled={submitting}>
          <Send size={18} />
          {submitting ? "Analyzing..." : "Submit for AI Triage"}
        </button>
      </form>
      {message && <p className="mt-4 rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-700">{message}</p>}
    </section>
  );
}
