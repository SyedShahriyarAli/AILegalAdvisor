import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Scale,
  ArrowRight,
  BarChart3,
  MessageSquare,
  FileText,
  Gavel,
  Network,
  BookOpen,
  ScanSearch,
  Layers,
  ChevronDown,
  CheckCircle2,
  Sparkles,
  Shield,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { authService } from '@/lib/authService';
import { APP_BASE } from '@/lib/appPaths';

/* ─── Data ──────────────────────────────────────────────────────────────── */

const capabilities = [
  {
    icon: Network,
    title: 'Graph RAG Architecture',
    desc: 'Neo4j-powered knowledge graph maps relationships between statutes, precedents, and constitutional provisions for deep legal reasoning.',
  },
  {
    icon: Layers,
    title: 'Multi-Statute Reasoning',
    desc: 'Simultaneously analyses PECA 2016, PPC, ETO 2002, and Constitutional law to deliver holistic defence strategies.',
  },
  {
    icon: ScanSearch,
    title: 'CrossEncoder Reranking',
    desc: 'ms-marco-MiniLM-L-6-v2 rescores retrieved passages for jurisdiction-specific precision before the answer is generated.',
  },
  {
    icon: BarChart3,
    title: 'Case Analyzer',
    desc: 'Structured intake, statutory mapping, and evidence-aware checklists grounded in Pakistani cyber law.',
  },
  {
    icon: MessageSquare,
    title: 'Legal Assistant',
    desc: 'Ask questions in plain language with citations to statutes and precedents where available.',
  },
  {
    icon: FileText,
    title: 'Knowledge Base',
    desc: 'Upload and index matter documents to keep answers aligned with your own file set.',
  },
  {
    icon: Gavel,
    title: 'Court Precedents',
    desc: 'Surface related decisions to compare fact patterns and procedural posture across courts.',
  },
  {
    icon: BookOpen,
    title: 'Legal Domains',
    desc: 'Covers PECA 2016, PPC, ETO 2002, Constitution 1973, NCCIA Regulations, and High Court case law.',
  },
];

const steps = [
  {
    n: '01',
    title: 'Describe Your Case',
    desc: 'Submit a plain-language narrative. OCR support lets you upload scanned documents directly.',
  },
  {
    n: '02',
    title: 'AI Classifies Complexity',
    desc: 'LangGraph orchestration routes simple queries to fast-path retrieval and complex ones to deep graph traversal.',
  },
  {
    n: '03',
    title: 'Multi-Stage Retrieval',
    desc: 'Parallel vector search, keyword lookup, and graph traversal surface every relevant passage.',
  },
  {
    n: '04',
    title: 'CrossEncoder Reranking',
    desc: 'Passages are rescored by jurisdiction and relevance before being passed to the language model.',
  },
  {
    n: '05',
    title: 'Structured Legal Report',
    desc: 'Receive applicable statutes, precedents, win-probability indicators, and draft document templates.',
  },
];

const stats = [
  { value: '90%', label: 'Benchmark Accuracy' },
  { value: '5+', label: 'Legal Corpora' },
  { value: '384D', label: 'Embedding Dimensions' },
  { value: '<2s', label: 'Avg. Response Time' },
];

const faqs = [
  {
    q: 'How accurate is the legal analysis?',
    a: 'Our system achieves 90% accuracy on curated Pakistani cyber-law benchmarks. Every answer includes statute citations so you can verify outputs against the original text.',
  },
  {
    q: 'Can I upload evidence documents?',
    a: 'Yes. The Knowledge Base module supports PDF, DOCX, and scanned images via OCR. Uploaded documents are indexed and kept private to your account.',
  },
  {
    q: 'Can the system draft actual legal documents?',
    a: 'The assistant can generate complaint templates, bail applications, and petition drafts grounded in the retrieved statutes. Always review outputs with a qualified advocate before filing.',
  },
  {
    q: 'Is my case data private?',
    a: 'Queries are encrypted in transit and at rest. Enterprise plans offer air-gapped deployment options for maximum confidentiality.',
  },
  {
    q: 'What AI model powers the system?',
    a: 'The retrieval pipeline uses a custom LangGraph orchestration layer. The language model is Llama-3.1:8b, selected for its balance of speed, cost, and legal reasoning quality.',
  },
];

/* ─── FAQ accordion ─────────────────────────────────────────────────────── */

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-[#c4c6cf]/40 last:border-0" onClick={() => setOpen(!open)}>
      <button
        className="flex w-full items-center justify-between gap-4 py-5 text-left text-[15px] font-semibold text-[#002045] hover:text-[#28657a] transition-colors"
        aria-expanded={open}
      >
        {q}
        <motion.span animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.25 }}>
          <ChevronDown className="h-4 w-4 shrink-0 text-[#28657a]" />
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.p
            key="answer"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: 'easeInOut' }}
            className="overflow-hidden pb-5 text-[13px] leading-relaxed text-[#43474e]"
          >
            {a}
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─── Page ──────────────────────────────────────────────────────────────── */

export default function Landing() {
  const user = authService.getCurrentUser();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const session = searchParams.get('session');
    if (session) {
      navigate(`${APP_BASE}?session=${encodeURIComponent(session)}`, { replace: true });
    }
  }, [searchParams, navigate]);

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#f8f9ff] text-[#0b1c30]">
      {/* Ambient blobs */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -right-[15%] -top-[25%] h-[65vmin] w-[65vmin] rounded-full bg-gradient-to-br from-[#dce9ff] via-[#eff4ff]/60 to-transparent blur-3xl" />
        <div className="absolute -bottom-[20%] -left-[10%] h-[55vmin] w-[55vmin] rounded-full bg-gradient-to-tr from-[#abe5fe]/25 to-transparent blur-3xl" />
      </div>

      {/* ── Navbar ── */}
      <header className="relative z-20 border-b border-[#c4c6cf]/30 bg-white/75 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4 lg:px-8">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#002045] shadow-lg shadow-[#002045]/20 group-hover:bg-[#1a365d] transition-colors">
              <Scale className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-[13px] font-bold tracking-tight text-[#002045]">AI Legal Advisor</p>
              <p className="text-[9px] font-semibold uppercase tracking-[0.14em] text-[#74777f]">
                Cyber-legal workspace
              </p>
            </div>
          </Link>

          <nav className="hidden items-center gap-6 sm:flex">
            {['Features', 'How It Works', 'FAQ'].map((label) => (
              <a
                key={label}
                href={`#${label.toLowerCase().replace(/\s+/g, '-')}`}
                className="text-[12px] font-medium text-[#43474e] hover:text-[#002045] transition-colors"
              >
                {label}
              </a>
            ))}
          </nav>

          <nav className="flex items-center gap-2 sm:gap-3">
            {user && (
              <Button asChild variant="ghost" className="hidden text-[11px] font-bold uppercase tracking-wider text-[#28657a] hover:bg-[#eff4ff] sm:inline-flex">
                <Link to={APP_BASE}>Open workspace</Link>
              </Button>
            )}
            <Button
              asChild
              variant="outline"
              className="h-9 rounded-xl border-[#c4c6cf] px-4 text-[11px] font-bold uppercase tracking-wider text-[#002045] hover:bg-[#eff4ff]"
            >
              <Link to="/login">Sign in</Link>
            </Button>
            <Button
              asChild
              className="h-9 rounded-xl bg-[#002045] px-4 text-[11px] font-bold uppercase tracking-wider text-white hover:bg-[#1a365d] shadow-md shadow-[#002045]/15"
            >
              <Link to="/register">Sign up</Link>
            </Button>
          </nav>
        </div>
      </header>

      <main className="relative z-10">

        {/* ── Hero ── */}
        <section className="mx-auto max-w-6xl px-5 pb-24 pt-20 text-center lg:px-8 lg:pt-32">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mx-auto max-w-4xl space-y-7"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1, duration: 0.4 }}
              className="inline-flex items-center gap-2 rounded-full border border-[#28657a]/25 bg-[#eff4ff] px-4 py-1.5 text-[10px] font-black uppercase tracking-[0.22em] text-[#28657a]"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Graph RAG · PECA 2016 · 90% Accuracy
            </motion.div>

            <h1 className="text-balance text-4xl font-black leading-[1.08] tracking-tight text-[#002045] sm:text-5xl lg:text-[3.5rem]">
              Pakistani Cyber Law{' '}
              <span className="bg-gradient-to-r from-[#28657a] to-[#004d61] bg-clip-text text-transparent">
                Intelligence.
              </span>
              <br />
              Powered by AI.
            </h1>

            <p className="text-balance text-base leading-relaxed text-[#43474e] sm:text-lg">
              Graph RAG-driven legal analysis across PECA 2016, PPC, ETO 2002, and Constitutional
              provisions — with{' '}
              <span className="font-semibold text-[#002045]">90% benchmark accuracy.</span>
            </p>

            <div className="flex flex-col items-center justify-center gap-3 pt-2 sm:flex-row sm:gap-4">
              <Button
                asChild
                size="lg"
                className="h-12 min-w-[200px] rounded-2xl bg-[#002045] text-[12px] font-bold uppercase tracking-wider text-white shadow-lg shadow-[#002045]/20 hover:bg-[#1a365d] hover:-translate-y-0.5 transition-all"
              >
                <Link to="/register" className="inline-flex items-center gap-2">
                  Analyze a Case <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="h-12 min-w-[200px] rounded-2xl border-[#28657a]/40 bg-white/90 text-[12px] font-bold uppercase tracking-wider text-[#002045] hover:bg-[#eff4ff] transition-all"
              >
                <a href="#how-it-works">See How It Works</a>
              </Button>
            </div>

            <p className="pt-1 text-[11px] font-medium text-[#74777f]">
              No separate "request access" flow — create an account or sign in to explore the product.
            </p>
          </motion.div>
        </section>

        {/* ── Stats bar ── */}
        <section className="border-y border-[#c4c6cf]/30 bg-white/60 py-10 backdrop-blur-sm">
          <div className="mx-auto grid max-w-4xl grid-cols-2 gap-8 px-5 sm:grid-cols-4 lg:px-8">
            {stats.map((s, i) => (
              <motion.div
                key={s.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.08 * i, duration: 0.4 }}
                className="flex flex-col items-center gap-1 text-center"
              >
                <span className="text-3xl font-black text-[#002045]">{s.value}</span>
                <span className="text-[11px] font-semibold uppercase tracking-widest text-[#74777f]">
                  {s.label}
                </span>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── Capabilities / Features ── */}
        <section id="features" className="mx-auto max-w-6xl px-5 py-24 lg:px-8">
          <div className="mb-14 text-center">
            <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[#28657a]">
              Platform Capabilities
            </p>
            <h2 className="mt-3 text-3xl font-bold text-[#002045] sm:text-4xl">
              Everything you need for cyber-law practice
            </h2>
            <p className="mx-auto mt-3 max-w-2xl text-[14px] leading-relaxed text-[#43474e]">
              A purpose-built suite for practitioners navigating Pakistan's digital legal landscape —
              from retrieval to report generation.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {capabilities.map((cap, i) => (
              <motion.div
                key={cap.title}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.06 * i, duration: 0.4 }}
                className="group rounded-2xl border border-[#c4c6cf]/30 bg-white/90 p-6 shadow-sm backdrop-blur-sm hover:border-[#28657a]/30 hover:shadow-md transition-all duration-300"
              >
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-[#eff4ff] text-[#002045] group-hover:bg-[#dce9ff] transition-colors">
                  <cap.icon className="h-5 w-5" />
                </div>
                <h3 className="text-[14px] font-bold text-[#002045]">{cap.title}</h3>
                <p className="mt-2 text-[12px] leading-relaxed text-[#43474e]">{cap.desc}</p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── How It Works ── */}
        <section id="how-it-works" className="border-t border-[#c4c6cf]/25 bg-white/60 py-24 backdrop-blur-sm">
          <div className="mx-auto max-w-6xl px-5 lg:px-8">
            <div className="mb-14 text-center">
              <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[#28657a]">
                How It Works
              </p>
              <h2 className="mt-3 text-3xl font-bold text-[#002045] sm:text-4xl">
                From case description to structured report
              </h2>
              <p className="mx-auto mt-3 max-w-xl text-[14px] leading-relaxed text-[#43474e]">
                A five-stage pipeline that turns a plain-language problem statement into
                statute-backed legal guidance.
              </p>
            </div>

            <div className="relative">
              {/* Connector line — desktop */}
              <div className="absolute left-0 right-0 top-[2.25rem] hidden h-px bg-gradient-to-r from-transparent via-[#c4c6cf]/60 to-transparent lg:block" />

              <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-5">
                {steps.map((step, i) => (
                  <motion.div
                    key={step.n}
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.08 * i, duration: 0.4 }}
                    className="relative flex flex-col items-center text-center"
                  >
                    <div className="relative z-10 mb-4 flex h-[4.5rem] w-[4.5rem] items-center justify-center rounded-full border border-[#28657a]/30 bg-white text-xl font-black text-[#28657a] shadow-md shadow-[#002045]/5">
                      {step.n}
                    </div>
                    <h3 className="text-[13px] font-bold text-[#002045]">{step.title}</h3>
                    <p className="mt-2 text-[11px] leading-relaxed text-[#43474e]">{step.desc}</p>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── Legal Domains ── */}
        <section className="mx-auto max-w-6xl px-5 py-20 lg:px-8">
          <div className="rounded-3xl border border-[#c4c6cf]/30 bg-white/80 p-8 shadow-sm backdrop-blur-sm md:p-12">
            <div className="grid gap-8 md:grid-cols-2 md:items-center">
              <div className="space-y-4">
                <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[#28657a]">
                  Coverage
                </p>
                <h2 className="text-2xl font-bold text-[#002045] sm:text-3xl">
                  Every major Pakistani cyber-law corpus
                </h2>
                <p className="text-[13px] leading-relaxed text-[#43474e]">
                  Our knowledge graph is built from primary legal sources and continuously updated
                  as statutes and precedents evolve.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  'PECA 2016',
                  'Pakistan Penal Code',
                  'ETO 2002',
                  'Constitution 1973',
                  'NCCIA Regulations',
                  'High Court Case Law',
                ].map((domain) => (
                  <div
                    key={domain}
                    className="flex items-center gap-2.5 rounded-xl border border-[#c4c6cf]/40 bg-[#f8f9ff] px-4 py-3 text-[12px] font-semibold text-[#0b1c30] hover:border-[#28657a]/30 hover:bg-[#eff4ff] transition-all"
                  >
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-[#28657a]" />
                    {domain}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── FAQ ── */}
        <section id="faq" className="border-t border-[#c4c6cf]/25 bg-white/60 py-24 backdrop-blur-sm">
          <div className="mx-auto max-w-3xl px-5 lg:px-8">
            <div className="mb-12 text-center">
              <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[#28657a]">FAQ</p>
              <h2 className="mt-3 text-3xl font-bold text-[#002045]">Frequently asked questions</h2>
            </div>
            <div className="rounded-2xl border border-[#c4c6cf]/30 bg-white/90 px-6 shadow-sm backdrop-blur-sm">
              {faqs.map((item) => (
                <FaqItem key={item.q} q={item.q} a={item.a} />
              ))}
            </div>
          </div>
        </section>

        {/* ── Bottom CTA ── */}
        <section className="py-24">
          <div className="mx-auto max-w-3xl px-5 text-center lg:px-8">
            <div className="relative overflow-hidden rounded-3xl border border-[#c4c6cf]/30 bg-white/80 p-10 shadow-xl shadow-[#002045]/5 backdrop-blur-sm md:p-14">
              {/* teal glow accent */}
              <div className="pointer-events-none absolute -top-20 left-1/2 h-56 w-56 -translate-x-1/2 rounded-full bg-[#abe5fe]/30 blur-3xl" />
              <div className="relative space-y-5">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#002045] shadow-lg shadow-[#002045]/20">
                  <Shield className="h-7 w-7 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-[#002045] sm:text-3xl">
                  Ready to navigate Pakistani cyber law with AI precision?
                </h2>
                <p className="text-[14px] leading-relaxed text-[#43474e]">
                  Sign up to register your firm profile, or sign in to walk through a guided demo of
                  the workspace.
                </p>
                <div className="flex flex-col items-center justify-center gap-3 pt-2 sm:flex-row sm:gap-4">
                  <Button
                    asChild
                    size="lg"
                    className="h-12 min-w-[200px] rounded-2xl bg-[#002045] text-[12px] font-bold uppercase tracking-wider text-white shadow-lg shadow-[#002045]/20 hover:bg-[#1a365d] hover:-translate-y-0.5 transition-all"
                  >
                    <Link to="/register" className="inline-flex items-center gap-2">
                      Sign up free <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Button>
                  <Button
                    asChild
                    size="lg"
                    variant="outline"
                    className="h-12 min-w-[200px] rounded-2xl border-[#28657a]/40 bg-white text-[12px] font-bold uppercase tracking-wider text-[#002045] hover:bg-[#eff4ff] transition-all"
                  >
                    <Link to="/login">Sign in for demo</Link>
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="relative z-10 border-t border-[#c4c6cf]/30 bg-[#f8f9ff] py-10">
        <div className="mx-auto max-w-6xl px-5 lg:px-8">
          <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
            <Link to="/" className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#002045]">
                <Scale className="h-4 w-4 text-white" />
              </div>
              <span className="text-[13px] font-bold text-[#002045]">AI Legal Advisor</span>
            </Link>

            <nav className="flex flex-wrap justify-center gap-x-6 gap-y-2">
              {['Features', 'How It Works', 'FAQ'].map((label) => (
                <a
                  key={label}
                  href={`#${label.toLowerCase().replace(/\s+/g, '-')}`}
                  className="text-[12px] text-[#74777f] hover:text-[#002045] transition-colors"
                >
                  {label}
                </a>
              ))}
            </nav>
          </div>

          <div className="mt-8 border-t border-[#c4c6cf]/30 pt-6 text-center">
            <p className="text-[11px] text-[#74777f]">
              © 2026 AI Legal Advisor · Not legal advice. Verify outputs against current statute and court practice.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
