import { useState } from "react";
import PageHeader from "../components/PageHeader";
import { Mail, BookOpen, MessageSquare, ChevronDown, CheckCircle2 } from "lucide-react";

const faqs = [
  {
    question: "What modal weights does DeepGuard utilize?",
    answer: "Our standard detection pipelines utilize EfficientNet-B0 architectures for visual deepfake detection and AASIST Graph Attention Networks for audio deepfake and synthetic speech analysis. The AI layer can be configured in settings.",
  },
  {
    question: "How do I fetch deepfake classifications via API?",
    answer: "Configure your secret key in Settings, then send a POST request with your media file payload to /api/analysis/image, /api/analysis/video, or /api/analysis/audio. Review our documentation and OpenAPI swagger schemas.",
  },
  {
    question: "Why does my file analysis output 'Demo Pipeline Active'?",
    answer: "This is a frontend sandbox console. The FastAPI backend python server and PyTorch modeling scripts must be started separately on local ports to achieve live classification outcomes.",
  },
];

export default function Help() {
  const [openFaq, setOpenFaq] = useState<number | null>(0);
  const [topic, setTopic] = useState("General Sandbox Help");
  const [message, setMessage] = useState("");
  const [ticketStatus, setTicketStatus] = useState<string | null>(null);

  const handleSubmitTicket = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    const ticketId = Math.floor(100000 + Math.random() * 900000);
    setTicketStatus(`Support ticket #${ticketId} submitted. Our engineering team will review your inquiry.`);
    setMessage("");
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Help & Documentation"
        description="Search our developer guides, access API tutorials, or reach out to support."
      />

      <div className="grid gap-6 md:grid-cols-3">
        {/* Left column: Resources */}
        <div className="md:col-span-2 space-y-6">
          {/* FAQ Accordion */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-4">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <BookOpen size={18} className="text-violet-400" />
              Frequently Asked Questions
            </h3>

            <div className="divide-y divide-white/5 pt-2">
              {faqs.map((faq, index) => {
                const isOpen = openFaq === index;
                return (
                  <div key={index} className="py-4 first:pt-0 last:pb-0">
                    <button
                      onClick={() => setOpenFaq(isOpen ? null : index)}
                      className="w-full flex items-center justify-between text-left text-sm sm:text-base font-semibold text-white hover:text-violet-300 transition"
                      aria-expanded={isOpen}
                    >
                      <span>{faq.question}</span>
                      <ChevronDown
                        size={16}
                        className={`text-slate-400 transition-transform duration-200 ${
                          isOpen ? "rotate-180 text-violet-400" : ""
                        }`}
                      />
                    </button>
                    {isOpen && (
                      <p className="mt-3 text-sm text-slate-400 leading-relaxed animate-in fade-in duration-200">
                        {faq.answer}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right column: Contact Card */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-6 h-fit">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <MessageSquare size={18} className="text-violet-400" />
            Support Center
          </h3>

          <p className="text-sm text-slate-400 leading-relaxed">
            Need help configuring the backend or training custom deepfake models? Get in touch with our team.
          </p>

          {ticketStatus && (
            <div className="flex items-start gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-xs text-emerald-300">
              <CheckCircle2 size={16} className="shrink-0 mt-0.5" />
              <span>{ticketStatus}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmitTicket}>
            <div>
              <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">
                Query Topic
              </label>
              <select
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-slate-300 outline-none focus:border-violet-500"
              >
                <option>General Sandbox Help</option>
                <option>FastAPI Backend Setup</option>
                <option>PyTorch Model Training</option>
                <option>Custom Feature Requests</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">
                Message Description
              </label>
              <textarea
                rows={3}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                required
                placeholder="Detail your question..."
                className="w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-white outline-none focus:border-violet-500 resize-none"
              />
            </div>
            <button
              type="submit"
              disabled={!message.trim()}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 py-3 font-semibold hover:bg-violet-500 transition text-sm text-white disabled:opacity-50"
            >
              <Mail size={14} />
              Submit Ticket
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
