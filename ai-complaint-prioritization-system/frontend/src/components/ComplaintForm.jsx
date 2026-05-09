import React, { useRef, useState } from "react";
import { Bot, Image, Mic, MicOff, Send, Trash2 } from "lucide-react";
import { api } from "../api";

const initialState = {
  name: "",
  email: "",
  department: "CSE",
  title: "",
  description: "",
};

const maxImageSize = 1024 * 1024;

export default function ComplaintForm({ onCreated }) {
  const [form, setForm] = useState(initialState);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [image, setImage] = useState(null);
  const [assistMessage, setAssistMessage] = useState("");
  const [assistReply, setAssistReply] = useState("");
  const [assistLoading, setAssistLoading] = useState(false);
  const recognitionRef = useRef(null);
  const fileInputRef = useRef(null);

  function updateField(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  function handleImageChange(event) {
    const file = event.target.files[0];
    setMessage("");
    if (!file) {
      setImage(null);
      return;
    }
    if (!file.type.startsWith("image/")) {
      setMessage("Please select a valid image file.");
      clearImage();
      return;
    }
    if (file.size > maxImageSize) {
      setMessage("Image size must be 1 MB or less.");
      clearImage();
      return;
    }
    const reader = new FileReader();
    reader.onloadend = () => {
      setImage({
        name: file.name,
        type: file.type,
        base64: reader.result,
      });
    };
    reader.readAsDataURL(file);
  }

  function clearImage() {
    setImage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function toggleListening() {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMessage("Voice input is not supported in this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-IN";
    recognitionRef.current = recognition;

    recognition.onstart = () => setIsListening(true);
    
    recognition.onresult = (event) => {
      let finalTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        finalTranscript += event.results[i][0].transcript;
      }
      const transcript = finalTranscript.trim();
      if (transcript) {
        setForm((prev) => ({
          ...prev,
          description: `${prev.description}${prev.description ? " " : ""}${transcript}`,
        }));
      }
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error", event.error);
      setIsListening(false);
      setMessage("Voice input stopped. You can continue typing manually.");
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
      await api.submitComplaint({
        ...form,
        image_uploaded: Boolean(image?.base64),
        image_name: image?.name || "",
        image_type: image?.type || "",
        image_base64: image?.base64 || "",
      });
      setForm(initialState);
      clearImage();
      setMessage("Complaint submitted and prioritized successfully.");
      await onCreated();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleAssist(event) {
    event.preventDefault();
    if (!assistMessage.trim()) return;
    setAssistLoading(true);
    setAssistReply("");
    try {
      const data = await api.askAiAssist(assistMessage.trim());
      setAssistReply(data.reply || "No reply received.");
    } catch (err) {
      setAssistReply(err.message || "AI assistance request failed.");
    } finally {
      setAssistLoading(false);
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
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-slate-700">Optional Evidence (Image)</label>
          <input ref={fileInputRef} className="input py-2 text-sm" type="file" accept="image/*" onChange={handleImageChange} />
          {image?.base64 && (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <img src={image.base64} alt="Selected evidence preview" className="max-h-36 rounded-md object-contain" />
              <div className="mt-2 flex items-center justify-between gap-3 text-sm text-slate-600">
                <span className="flex items-center gap-2">
                  <Image size={16} /> {image.name}
                </span>
                <button type="button" className="small-button" onClick={clearImage}>
                  <Trash2 size={14} /> Remove
                </button>
              </div>
            </div>
          )}
        </div>
        <button className="primary-button w-full" type="submit" disabled={submitting}>
          <Send size={18} />
          {submitting ? "Analyzing..." : "Submit for AI Triage"}
        </button>
      </form>
      {message && <p className="mt-4 rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-700">{message}</p>}
      <form className="mt-6 border-t border-slate-200 pt-5" onSubmit={handleAssist}>
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <Bot size={18} /> Ask AI Assistance
        </div>
        <textarea
          className="input mt-3 min-h-20 resize-y"
          value={assistMessage}
          onChange={(event) => setAssistMessage(event.target.value)}
          placeholder="Ask how to write a clear complaint..."
        />
        <button className="small-button mt-3 w-full bg-blue-100 text-blue-800" type="submit" disabled={assistLoading || !assistMessage.trim()}>
          <Bot size={16} />
          {assistLoading ? "Asking..." : "Ask AI"}
        </button>
        {assistReply && <p className="mt-3 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-900">{assistReply}</p>}
      </form>
    </section>
  );
}
