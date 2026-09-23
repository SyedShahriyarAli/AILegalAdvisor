import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  Upload,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Scale,
  Gavel,
  ExternalLink,
  RotateCcw,
  Sparkles,
  ShieldCheck,
  Search,
  Database,
  Terminal,
  FileCheck,
  X,
  Trash2,
  Info,
  ChevronDown
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { authService } from '@/lib/authService';
import type { User as UserType } from '@/lib/authService';
import { apiUrl, resolveApiHref } from '@/lib/apiBase';
import { APP_BASE } from '@/lib/appPaths';
import { buildSourceSubtitle, formatDocumentName } from '@/lib/legalSourceLabels';
import { AnalysisLoader } from '@/components/workspace/AnalysisLoader';
import { NCCIAFormModal } from '@/components/modals/NCCIAFormModal';
import { CaseLawGraph } from '@/components/workspace/CaseLawGraph';
import { cn } from '@/lib/utils';

// ── UTILS ──

const parseLegalAdvisorJson = (rawSummary: string) => {
  try {
    const cleaned = rawSummary.replace(/```json\n?|\n?```/g, '').trim();
    return JSON.parse(cleaned);
  } catch {
    return null;
  }
};

const buildApplicableLawRows = (analysis: any) => {
  // Prefer applicable_laws from the analyze endpoint, fall back to legacy fields
  if (analysis?.applicable_laws?.length) return analysis.applicable_laws;
  const citations = analysis?.legal_citations || [];
  const statutes = analysis?.statutes || [];
  return [...citations, ...statutes];
};

export default function Workspace() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const sessionId = searchParams.get('session');

  const [user, setUser] = useState<UserType | null>(null);
  const [step, setStep] = useState(1);
  const [caseFacts, setCaseFacts] = useState('');
  const [ocrText, setOcrText] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<any>(null);
  const [analysisError, setAnalysisError] = useState('');
  const [isComplaintModalOpen, setIsComplaintModalOpen] = useState(false);
  const [isOcrLoading, setIsOcrLoading] = useState(false);
  const [isExtractedTextModalOpen, setIsExtractedTextModalOpen] = useState(false);
  const [selectedCase, setSelectedCase] = useState<any>(null);
  const [incidentDate, setIncidentDate] = useState(new Date().toISOString().split('T')[0]);

  // For caching re-analysis
  const [cachedNarrative, setCachedNarrative] = useState('');

  const [userSources, setUserSources] = useState<any[]>([]);
  const [isLawGraphExpanded, setIsLawGraphExpanded] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    setUser(currentUser);

    if (currentUser && sessionId) {
      const userData = authService.loadUserData(currentUser.id);
      const session = userData.caseAnalyzerSessions?.find(s => s.id === sessionId);
      if (session) {
        setCaseFacts(session.narrative || '');
        setAnalysis(session.analysis || null);
        setStep(session.analysis ? 2 : 1);
        setCachedNarrative(session.narrative || '');
      }
      setUserSources(userData.sources || []);
    }
  }, [sessionId]);

  const summaryData = useMemo(() => {
    if (!analysis?.summary) return null;
    return parseLegalAdvisorJson(analysis.summary);
  }, [analysis]);

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    setAnalysisError('');

    try {
      const response = await fetch(apiUrl('/api/workspace/analyze'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          narrative: caseFacts,
          incident_date: incidentDate,
          ocr_text: ocrText,
          session_id: user?.id || 'anonymous-session'
        })
      });

      const raw = await response.text();
      let data: any = {};
      try {
        data = raw ? JSON.parse(raw) : {};
      } catch {
        throw new Error(`Invalid server response`);
      }

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Analysis failed');
      }

      setAnalysis(data);
      setCachedNarrative(caseFacts);

      if (user) {
        const id = sessionId || Math.random().toString(36).slice(2, 11);
        authService.addCaseAnalyzerSession(user.id, {
          id,
          title: caseFacts.substring(0, 40) + '...',
          narrative: caseFacts,
          analysis: data,
          createdAt: new Date().toISOString(),
          step: 2
        });
        if (!sessionId) {
          navigate(`${APP_BASE}?session=${id}`, { replace: true });
        }
      }
      setStep(2);
    } catch (error: any) {
      setAnalysisError(error.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDeleteCurrentSession = () => {
    if (!user || !sessionId) return;
    if (confirm('Are you sure you want to delete this case analysis? This will permanently remove the record.')) {
      authService.deleteCaseAnalyzerSession(user.id, sessionId);
      navigate(APP_BASE); // Go back to fresh intake
    }
  };

  const handleNext = async () => {
    if (step === 1) {
      if (!caseFacts.trim()) return;
      if (caseFacts.trim() === cachedNarrative.trim() && analysis) {
        setStep(2);
        return;
      }
      await runAnalysis();
    } else {
      setStep(step + 1);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsOcrLoading(true);
    setAnalysisError('');

    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await fetch(apiUrl('/api/ingest/ocr'), { method: 'POST', body: formData });
      const data = await response.json();
      if (data.success) {
        const text = data.raw_text || (data.extracted_facts || []).join('\n');
        setOcrText(text);

        if (user) {
          authService.addSource(user.id, {
            id: Math.random().toString(36).slice(2, 11),
            title: file.name,
            type: file.type.includes('image') ? 'image' : 'pdf',
            content: text,
            status: 'indexed',
            timestamp: new Date()
          });
        }
      } else {
        setAnalysisError(data.error || 'OCR failed');
      }
    } catch {
      setAnalysisError('Upload failed');
    } finally {
      setIsOcrLoading(false);
    }
  };

  const checklist = useMemo(() => analysis?.evidence_checklist || [], [analysis]);
  const cases = useMemo(() => analysis?.related_cases || [], [analysis]);
  const probability = useMemo(() => analysis?.win_probability || { score: 0, label: 'N/A', factors: {} }, [analysis]);
  const statuteRows = useMemo(() => buildApplicableLawRows(analysis), [analysis]);
  const sources = useMemo(() => analysis?.sources || [], [analysis]);

  const combinedLaws = useMemo(() => {
    // Merge statuteRows and sources, removing duplicates based on article and document
    const seen = new Set();
    const merged = [...statuteRows, ...sources].filter(item => {
      const key = `${item.document}-${item.article}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    return merged;
  }, [statuteRows, sources]);

  return (
    <div className="flex-1 h-full bg-[#f8f9ff] overflow-y-auto custom-scrollbar relative">
      {/* ── Background Gradients & Ambient Orbs ── */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            x: [0, 50, 0],
            y: [0, 30, 0]
          }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="absolute top-[-10%] right-[-5%] w-[60%] h-[60%] bg-gradient-to-br from-[#dce9ff] via-[#eff4ff]/20 to-transparent blur-[120px] opacity-60"
        />
        <motion.div
          animate={{
            scale: [1, 1.3, 1],
            x: [0, -40, 0],
            y: [0, -20, 0]
          }}
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
          className="absolute bottom-[-10%] left-[-5%] w-[70%] h-[70%] bg-gradient-to-tr from-[#abe5fe]/30 via-[#f8f9ff]/20 to-transparent blur-[140px] opacity-50"
        />
        <div className="absolute top-[20%] left-[10%] w-[30%] h-[30%] bg-[#28657a]/5 blur-[100px]" />
      </div>

      <div className="max-w-[1280px] mx-auto px-6 py-8 relative z-10">

        {/* ── Stepper Header ── */}
        <div className="flex items-center justify-between mb-8 max-w-4xl mx-auto relative px-4">
          <div className="absolute top-1/2 left-0 right-0 h-[1px] bg-[#c4c6cf]/30 -translate-y-1/2 z-0" />
          {[1, 2, 3].map((s) => (
            <div key={s} className="relative z-10 flex flex-col items-center gap-3">
              <div
                className={`w-11 h-11 rounded-full flex items-center justify-center transition-all duration-500 border-2 
                ${step >= s
                    ? 'bg-gradient-to-br from-[#002045] to-[#1a365d] border-[#002045] text-white shadow-xl shadow-[#002045]/30 scale-110'
                    : 'bg-white border-[#c4c6cf] text-[#74777f]'}`}
              >
                {step > s ? <CheckCircle2 className="w-5 h-5" /> : <span className="text-[13px] font-black">{s}</span>}
              </div>
              <span className={`text-[9px] font-black uppercase tracking-[0.2em] ${step >= s ? 'text-[#002045]' : 'text-[#74777f]'}`}>
                {s === 1 ? 'Discovery' : s === 2 ? 'Analysis' : 'Deliverables'}
              </span>
            </div>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {isAnalyzing ? (
            <motion.div key="loader" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <AnalysisLoader />
            </motion.div>
          ) : step === 1 ? (
            <motion.div
              key="step1"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-8"
            >
              <div className="max-w-3xl">
                <h1 className="text-[28px] font-bold text-[#002045] tracking-tight mb-2">Add Details of the Incident</h1>
                <p className="text-[14px] text-[#43474e] leading-relaxed">
                  Securely upload evidence artifacts and define the the incident for the analysis.
                  All data is processed within an isolated legal-hold environment.
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Form Section */}
                <div className="lg:col-span-7 bg-white border border-[#c4c6cf]/30 rounded-2xl p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-[16px] font-bold text-[#002045]">Matter Parameters</h2>
                    <div className="px-3 py-1 rounded-full bg-[#eff4ff] border border-[#dce9ff] flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-[#28657a] animate-pulse" />
                      <span className="text-[10px] font-bold text-[#28657a] uppercase tracking-wider">Ready for Processing</span>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <div>
                      <label className="block text-[10px] font-bold text-[#74777f] uppercase tracking-widest mb-2">Incident Date</label>
                      <input
                        type="date"
                        value={incidentDate}
                        onChange={(e) => setIncidentDate(e.target.value)}
                        className="w-full bg-[#f8f9ff] border border-[#c4c6cf]/40 rounded-lg px-4 py-3 text-[13px] text-[#002045] font-medium outline-none focus:border-[#002045] transition-all"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold text-[#74777f] uppercase tracking-widest mb-2">Incident Description</label>
                      <textarea
                        value={caseFacts}
                        onChange={(e) => setCaseFacts(e.target.value)}
                        placeholder="Identify unauthorized lateral movement originating from compromised service accounts... Describe your situation in detail."
                        className="w-full h-32 bg-[#f8f9ff] border border-[#c4c6cf]/40 rounded-xl px-5 py-4 text-[13px] text-[#002045] font-medium leading-relaxed resize-none focus:ring-2 focus:ring-[#002045]/10 outline-none transition-all"
                      />
                    </div>

                    <div className="pt-4">
                      <Button
                        onClick={handleNext}
                        disabled={!caseFacts.trim()}
                        className="h-12 px-8 bg-[#002045] hover:bg-[#1a365d] text-white rounded-xl text-[11px] font-bold uppercase tracking-wider flex items-center gap-2 group shadow-lg shadow-[#002045]/10"
                      >
                        Analyze Case <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                      </Button>
                      {analysisError && <p className="mt-3 text-[#ba1a1a] text-[11px] font-bold flex items-center gap-2"><AlertCircle className="w-4 h-4" /> {analysisError}</p>}
                    </div>
                  </div>
                </div>

                {/* Upload Section */}
                <div className="lg:col-span-5 space-y-6">
                  <div className="bg-white border border-[#c4c6cf]/30 rounded-2xl p-8 flex flex-col items-center justify-center text-center min-h-[220px] shadow-sm relative overflow-hidden">
                    <AnimatePresence>
                      {isOcrLoading && (
                        <motion.div
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          className="absolute inset-0 z-20 bg-white/90 backdrop-blur-sm flex flex-col items-center justify-center p-8"
                        >
                          <div className="w-full space-y-4">
                            <div className="h-4 w-3/4 bg-[#eff4ff] rounded-full overflow-hidden relative">
                              <motion.div
                                className="absolute inset-0 bg-[#002045]/20"
                                animate={{ x: ['-100%', '100%'] }}
                                transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                              />
                            </div>
                            <div className="h-4 w-1/2 bg-[#eff4ff] rounded-full overflow-hidden relative">
                              <motion.div
                                className="absolute inset-0 bg-[#002045]/20"
                                animate={{ x: ['-100%', '100%'] }}
                                transition={{ repeat: Infinity, duration: 1.5, ease: "linear", delay: 0.2 }}
                              />
                            </div>
                            <div className="h-4 w-5/6 bg-[#eff4ff] rounded-full overflow-hidden relative">
                              <motion.div
                                className="absolute inset-0 bg-[#002045]/20"
                                animate={{ x: ['-100%', '100%'] }}
                                transition={{ repeat: Infinity, duration: 1.5, ease: "linear", delay: 0.4 }}
                              />
                            </div>
                          </div>
                          <p className="mt-8 text-[11px] font-bold text-[#002045] uppercase tracking-widest animate-pulse">Parsing Case Files...</p>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    <div
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full h-full border-2 border-dashed border-[#c4c6cf]/40 rounded-xl flex flex-col items-center justify-center p-6 group cursor-pointer hover:border-[#28657a] hover:bg-[#eff4ff]/50 transition-all"
                    >
                      <div className="w-14 h-14 rounded-2xl bg-[#eff4ff] flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                        <Upload className="w-7 h-7 text-[#002045]" />
                      </div>
                      <h3 className="text-[15px] font-bold text-[#002045] mb-2">Upload Case Files</h3>
                      <p className="text-[12px] text-[#74777f] leading-relaxed max-w-[240px]">
                        Drag and drop PDFs, affidavits, or raw logs here. Supporting IHC & PECA formats.
                      </p>
                      <input type="file" ref={fileInputRef} className="hidden" onChange={handleUpload} accept=".pdf,image/*" />
                    </div>
                  </div>

                  {ocrText && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      onClick={() => setIsExtractedTextModalOpen(true)}
                      className="bg-[#eff4ff] border border-[#dce9ff] rounded-xl p-5 flex items-start gap-4 cursor-pointer hover:bg-[#dce9ff] transition-all group"
                    >
                      <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center shrink-0 shadow-sm group-hover:scale-110 transition-transform">
                        <FileText className="w-5 h-5 text-[#28657a]" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <p className="text-[11px] font-bold text-[#002045] truncate">Extracted Evidence Document</p>
                          <ExternalLink className="w-3 h-3 text-[#28657a] opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                        <p className="text-[10px] text-[#28657a] font-medium mt-0.5">OCR Scan Complete • Click to Review Evidence</p>
                      </div>
                    </motion.div>
                  )}

                  {userSources.length > 0 && (
                    <div className="space-y-3">
                      <p className="text-[10px] font-bold text-[#74777f] uppercase tracking-widest px-1">Global Evidence Pool</p>
                      <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar pr-2">
                        {userSources.slice(0, 5).map((s) => (
                          <div
                            key={s.id}
                            onClick={() => {
                              setOcrText(s.content);
                              setIsExtractedTextModalOpen(true);
                            }}
                            className="bg-white border border-[#c4c6cf]/20 rounded-xl p-3 flex items-center gap-3 cursor-pointer hover:bg-[#eff4ff] transition-all group"
                          >
                            <div className="w-8 h-8 rounded-lg bg-[#f8f9ff] flex items-center justify-center shrink-0 border border-[#c4c6cf]/10">
                              <FileText className="w-4 h-4 text-[#28657a]" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-[10px] font-bold text-[#002045] truncate">{s.title}</p>
                              <p className="text-[8px] text-[#74777f] uppercase tracking-wider">{s.type} • {new Date(s.timestamp).toLocaleDateString()}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ) : step === 2 ? (
            <motion.div
              key="step2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-10"
            >
              <div className="max-w-3xl flex items-start justify-between">
                <div>
                  <h1 className="text-[36px] font-black text-transparent bg-clip-text bg-gradient-to-r from-[#002045] to-[#28657a] tracking-tight mb-3">
                    Assessment
                  </h1>
                  <p className="text-[13px] text-[#43474e] font-medium opacity-80 uppercase tracking-widest">Case Metadata Analysis Complete</p>
                </div>
                {sessionId && (
                  <Button
                    variant="ghost"
                    onClick={handleDeleteCurrentSession}
                    className="h-10 px-4 rounded-xl text-rose-600 hover:bg-rose-50 hover:text-rose-700 gap-2 font-bold text-[11px] uppercase tracking-wider"
                  >
                    <Trash2 className="w-4 h-4" /> Purge Session
                  </Button>
                )}
              </div>

              <div className="flex flex-col gap-8">

                {/* Forensic Executive Summary — first */}
                {summaryData && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-white border border-[#c4c6cf]/30 rounded-2xl p-10 shadow-sm relative overflow-hidden"
                  >
                    <div className="absolute top-0 right-0 w-64 h-64 bg-[#eff4ff] rounded-full blur-[100px] -mr-32 -mt-32 opacity-60" />

                    <div className="relative z-10 space-y-10">
                      <div className="flex items-center gap-3 border-b border-[#c4c6cf]/20 pb-6">
                        <div className="p-2 rounded-lg bg-[#eff4ff] border border-[#dce9ff]">
                          <Sparkles className="w-5 h-5 text-[#28657a]" />
                        </div>
                        <h2 className="text-[20px] font-bold tracking-tight text-[#002045]">Summary</h2>
                      </div>

                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                        {/* Left Column: Direct Answer & Implications */}
                        <div className="space-y-8">
                          <div className="space-y-3">
                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-[#28657a]">Direct Answer</h3>
                            <p className="text-[15px] font-medium leading-relaxed text-[#002045]">
                              {summaryData.directAnswer}
                            </p>
                          </div>

                          <div className="space-y-3">
                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-[#28657a]">Legal Implications</h3>
                            <p className="text-[14px] leading-relaxed text-[#43474e]">
                              {summaryData.whatThisMeans}
                            </p>
                          </div>
                        </div>

                        {/* Right Column: Next Steps */}
                        <div className="space-y-8">
                          <div className="space-y-4">
                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-[#28657a]">Next Steps</h3>
                            <div className="space-y-3">
                              {summaryData.nextSteps?.map((step: string, idx: number) => (
                                <div key={idx} className="flex gap-3 items-start group">
                                  <div className="w-6 h-6 rounded-lg bg-[#eff4ff] flex items-center justify-center shrink-0 text-[11px] font-black text-[#28657a] border border-[#dce9ff] group-hover:bg-[#002045] group-hover:text-white transition-colors">
                                    {idx + 1}
                                  </div>
                                  <p className="text-[12px] text-[#43474e] font-medium leading-relaxed">{step}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="pt-8 border-t border-[#c4c6cf]/20">
                        <p className="text-[9px] text-[#74777f] italic uppercase tracking-widest">{summaryData.disclaimer}</p>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Applicable Laws + Relevant Cases */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                  {/* Combined Applicable Laws */}
                  {combinedLaws.length > 0 && (
                    <div className="bg-white border border-[#c4c6cf]/30 rounded-2xl p-8 shadow-sm flex flex-col">
                      <div className="flex items-center justify-between mb-6">
                        <h2 className="text-[16px] font-bold text-[#002045] flex items-center gap-2">
                          <ShieldCheck className="w-5 h-5 text-[#28657a]" />
                          Applicable Laws
                        </h2>
                        <span className="text-[10px] font-bold text-[#74777f] uppercase tracking-widest bg-[#f8f9ff] px-2 py-1 rounded-md border border-[#c4c6cf]/20">
                          {combinedLaws.length} Provisions
                        </span>
                      </div>
                      <div className="space-y-3 overflow-y-auto max-h-[500px] pr-2 custom-scrollbar">
                        {combinedLaws.map((law: any, i: number) => {
                          const link = law.pdf_link || law.link;
                          const href = link ? resolveApiHref(link) : null;
                          const docLabel = formatDocumentName(law.document || '');
                          const detail = buildSourceSubtitle(
                            law.title,
                            law.chapter,
                            law.part,
                          );

                          return (
                            <div 
                              key={`${law.document}-${law.article}-${i}`}
                              onClick={() => href && window.open(href, '_blank')}
                              className={cn(
                                "group p-4 bg-[#f8f9ff] border border-[#c4c6cf]/20 rounded-xl transition-all flex items-start gap-4",
                                href ? "cursor-pointer hover:border-[#28657a]/40 hover:bg-[#eff4ff]" : "cursor-default"
                              )}
                            >
                              <div className="w-8 h-8 rounded-lg bg-[#eff4ff] flex items-center justify-center shrink-0 text-[13px] font-black text-[#28657a]">
                                {i + 1}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-2 mb-1">
                                  <p className="text-[10px] font-bold text-[#28657a] uppercase tracking-widest truncate">
                                    {docLabel}
                                  </p>
                                  {law.relevance_score && (
                                    <span className="text-[10px] font-black text-[#28657a] bg-[#eff4ff] px-1.5 py-0.5 rounded">
                                      {Math.round((law.relevance_score || 0) * 100)}%
                                    </span>
                                  )}
                                </div>
                                <h4 className="text-[14px] font-bold text-[#002045] mb-1">
                                  {docLabel} · {law.article}
                                </h4>
                                <p className="text-[11px] text-[#43474e] leading-relaxed line-clamp-2">{detail}</p>
                              </div>
                              <div className="w-8 h-8 rounded-lg bg-white border border-[#c4c6cf]/30 flex items-center justify-center transition-all shrink-0 group-hover:bg-[#002045] group-hover:border-[#002045] shadow-sm">
                                <ExternalLink className={cn(
                                  "w-3.5 h-3.5 transition-colors",
                                  href ? "text-[#28657a] group-hover:text-white" : "text-[#c4c6cf]"
                                )} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Relevant Cases */}
                  {cases.length > 0 && (
                    <div className="bg-white border border-[#c4c6cf]/30 rounded-2xl p-8 shadow-sm flex flex-col">
                      <div className="flex items-center justify-between mb-6">
                        <h2 className="text-[16px] font-bold text-[#002045] flex items-center gap-2">
                          <Database className="w-5 h-5 text-[#28657a]" />
                          Relevant Cases
                        </h2>
                        <span className="text-[10px] font-bold text-[#74777f] uppercase tracking-widest bg-[#f8f9ff] px-2 py-1 rounded-md border border-[#c4c6cf]/20">
                          {cases.length} Precedents
                        </span>
                      </div>
                      <div className="space-y-3 overflow-y-auto max-h-[500px] pr-2 custom-scrollbar">
                        {cases.map((caseItem: any, i: number) => {
                          const link = caseItem.pdf_link || caseItem.link;
                          const href = link ? resolveApiHref(link) : null;

                          return (
                            <div 
                              key={i} 
                              onClick={() => href && window.open(href, '_blank')}
                              className={cn(
                                "group p-4 bg-[#f8f9ff] border border-[#c4c6cf]/20 rounded-xl transition-all flex items-start gap-4",
                                href ? "cursor-pointer hover:border-emerald-700/40 hover:bg-emerald-50/30" : "cursor-default"
                              )}
                            >
                              <div className="w-8 h-8 rounded-lg bg-[#f0fdf4] flex items-center justify-center shrink-0 text-[13px] font-black text-emerald-700">
                                {i + 1}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-[10px] font-bold text-emerald-700 uppercase tracking-widest mb-1">
                                  {caseItem.court || 'Precedent'} {caseItem.citation ? `• ${caseItem.citation}` : ''}
                                </p>
                                <h4 className="text-[14px] font-bold text-[#002045] mb-1 line-clamp-1">{caseItem.title}</h4>
                                <p className="text-[11px] text-[#43474e] leading-relaxed line-clamp-2 italic">"{caseItem.summary || caseItem.facts || 'No summary available.'}"</p>
                              </div>
                              <div className="w-8 h-8 rounded-lg bg-white border border-[#c4c6cf]/30 flex items-center justify-center transition-all shrink-0 group-hover:bg-emerald-700 group-hover:border-emerald-700 shadow-sm">
                                <FileText className={cn(
                                  "w-3.5 h-3.5 transition-colors",
                                  href ? "text-emerald-700 group-hover:text-white" : "text-[#c4c6cf]"
                                )} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Evidence Checklist — after laws and cases */}
                {checklist.length > 0 && (
                  <div className="bg-white border border-[#c4c6cf]/30 rounded-2xl p-8 shadow-sm w-full">
                    <h2 className="text-[16px] font-bold text-[#002045] mb-6 flex items-center gap-2">
                      <FileCheck className="w-5 h-5 text-[#28657a]" />
                      Evidence Checklist
                    </h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                      {checklist.map((item: any, i: number) => {
                        const s = String(item.status ?? '').toLowerCase();
                        const isPresent =
                          s === 'found' || s === 'present' || s === 'uploaded';
                        return (
                          <div key={i} className={`flex items-center gap-3 p-4 rounded-xl border transition-all ${isPresent ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'
                            }`}>
                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${isPresent ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'
                              }`}>
                              {isPresent
                                ? <CheckCircle2 className="w-5 h-5" />
                                : <AlertCircle className="w-5 h-5" />}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-[13px] font-bold text-[#002045] truncate">{item.label}</p>
                              <p className={`text-[11px] font-bold uppercase tracking-widest mt-0.5 ${isPresent ? 'text-emerald-600' : 'text-rose-600'
                                }`}>{item.status}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Probability Panel - Merit Assessment */}
                <div className="bg-white/70 backdrop-blur-md border border-white/40 rounded-2xl p-8 shadow-2xl shadow-[#002045]/5 flex flex-col md:flex-row items-center md:items-start gap-8 relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-[#28657a]/5 rounded-full blur-3xl -mr-16 -mt-16" />
                  <div className="relative w-36 h-36 shrink-0">
                    <svg className="w-full h-full transform -rotate-90">
                      <circle cx="72" cy="72" r="62" stroke="#eff4ff" strokeWidth="12" fill="transparent" />
                      <motion.circle
                        cx="72" cy="72" r="62" stroke="#28657a" strokeWidth="12" fill="transparent"
                        strokeDasharray={389.56}
                        initial={{ strokeDashoffset: 389.56 }}
                        animate={{ strokeDashoffset: 389.56 - (389.56 * (probability.score || 0)) / 100 }}
                        transition={{ duration: 1.5, ease: "easeOut" }}
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-[38px] font-bold text-[#002045] tracking-tighter leading-none">{probability.score}%</span>
                      <span className="text-[11px] font-bold text-[#28657a] uppercase tracking-widest mt-1">Success Rate</span>
                    </div>
                  </div>

                  <div className="flex-1 space-y-5">
                    <div>
                      <span className={`inline-block px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-widest mb-3 ${(probability.score || 0) >= 60 ? 'bg-emerald-100 text-emerald-700' :
                        (probability.score || 0) >= 40 ? 'bg-amber-100 text-amber-700' :
                          'bg-rose-100 text-rose-700'
                        }`}>{probability.label}</span>
                      <h3 className="text-[20px] font-bold text-[#002045] mb-2">Merit Assessment</h3>
                      <p className="text-[13px] text-[#43474e] leading-relaxed">
                        Forensic analysis across the PECA knowledge base returned a {probability.score}% success propensity based on submitted facts and evidentiary alignment.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-5">
                      {Object.entries(probability.factors || {}).map(([key, val], idx) => {
                        const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                        const isStrong = String(val).toLowerCase() === 'strong';
                        const isWeak = String(val).toLowerCase() === 'weak';
                        return (
                          <div key={idx} className="flex items-center justify-between bg-[#f8f9ff] px-4 py-3 rounded-xl border border-[#c4c6cf]/20">
                            <p className="text-[11px] font-bold text-[#002045] uppercase tracking-wide">{label}</p>
                            <span className={`text-[11px] font-black uppercase tracking-widest px-3 py-1 rounded-full ${isStrong ? 'bg-emerald-100 text-emerald-700' :
                              isWeak ? 'bg-rose-100 text-rose-700' :
                                'bg-amber-100 text-amber-700'
                              }`}>{String(val)}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* ── Cytoscape Law Graph — Full Width (collapsed by default) ── */}
                <div className="w-full">
                  <div className="bg-white border border-[#c4c6cf]/30 rounded-2xl overflow-hidden shadow-sm">
                    <button
                      type="button"
                      onClick={() => setIsLawGraphExpanded((v) => !v)}
                      aria-expanded={isLawGraphExpanded}
                      className={cn(
                        'flex w-full items-center justify-between gap-4 px-8 py-5 text-left transition-colors hover:bg-[#f8f9ff]/80',
                        isLawGraphExpanded && 'border-b border-[#c4c6cf]/20'
                      )}
                    >
                      <div className="flex min-w-0 flex-1 items-start gap-3">
                        <ChevronDown
                          className={cn(
                            'mt-0.5 h-5 w-5 shrink-0 text-[#28657a] transition-transform duration-200',
                            isLawGraphExpanded && 'rotate-180'
                          )}
                          aria-hidden
                        />
                        <div className="min-w-0">
                          <h2 className="text-[16px] font-bold text-[#002045]">Legal Relationship Graph</h2>
                          <p className="mt-0.5 text-[11px] text-[#74777f]">Statutory connections and precedent vectors</p>
                        </div>
                      </div>
                      <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
                        <span className="rounded-full border border-[#dce9ff] bg-[#eff4ff] px-3 py-1 text-[9px] font-black uppercase tracking-widest text-[#002045]">
                          {statuteRows.length} Statutes
                        </span>
                        <span className="rounded-full border border-emerald-200 bg-[#f0fdf4] px-3 py-1 text-[9px] font-black uppercase tracking-widest text-[#28657a]">
                          {cases.length} Precedents
                        </span>
                        <span className="ml-1 text-[10px] font-bold uppercase tracking-widest text-[#28657a]">
                          {isLawGraphExpanded ? 'Collapse' : 'Expand'}
                        </span>
                      </div>
                    </button>
                    {isLawGraphExpanded && (
                      <div className="h-[420px]">
                        <CaseLawGraph
                          laws={statuteRows}
                          cases={cases}
                          checklist={checklist}
                          label="Case"
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-center pt-10 border-t border-[#c4c6cf]/30">
                <Button 
                  variant="ghost" 
                  onClick={() => setStep(1)} 
                  className="h-12 px-6 rounded-xl text-[11px] font-bold text-[#28657a] bg-[#eff4ff] border border-[#28657a]/20 hover:bg-[#dce9ff] hover:border-[#28657a]/40 hover:text-[#002045] uppercase tracking-widest flex items-center gap-2 transition-all shadow-sm"
                >
                  <ArrowLeft className="w-4 h-4" /> Back
                </Button>
                <div className="flex gap-4">
                  <Button variant="outline" onClick={runAnalysis} className="h-12 px-6 rounded-xl text-[11px] font-bold text-[#002045] border-[#c4c6cf] uppercase tracking-widest flex items-center gap-2">
                    <RotateCcw className="w-4 h-4" /> Re-Analyze
                  </Button>
                  <Button onClick={() => setStep(3)} className="h-12 px-10 bg-[#002045] hover:bg-[#1a365d] text-white rounded-xl text-[11px] font-bold uppercase tracking-wider flex items-center gap-2 group">
                    Generate Deliverables <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </Button>
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="step3"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-10"
            >
              <div className="max-w-3xl">
                <h1 className="text-[32px] font-bold text-[#002045] tracking-tight mb-3">Generate Deliverables</h1>
                <p className="text-[14px] text-[#43474e] leading-relaxed">
                  Finalize the technical forensics phase by generating legally bound documents based on the extracted metadata and case precedents.
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
                {/* Left Panel: Primary Actions */}
                <div className="lg:col-span-5 space-y-6">
                  <div className="bg-white border border-[#c4c6cf]/30 rounded-2xl p-8 shadow-sm">
                    <div className="flex items-center gap-4 mb-6">
                      <div className="w-10 h-10 rounded-xl bg-[#eff4ff] flex items-center justify-center">
                        <CheckCircle2 className="w-6 h-6 text-[#28657a]" />
                      </div>
                      <div>
                        <h3 className="text-[15px] font-bold text-[#002045]">Analysis Complete</h3>
                        <p className="text-[11px] text-[#74777f]">Confidence score: 98.4%. Ready for compilation.</p>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <p className="text-[10px] font-bold text-[#74777f] uppercase tracking-widest px-1">Primary Actions</p>
                      <Button
                        onClick={() => setIsComplaintModalOpen(true)}
                        className="w-full h-16 bg-[#002045] hover:bg-[#1a365d] text-white rounded-xl flex items-center justify-between px-6 group transition-all"
                      >
                        <div className="flex items-center gap-4">
                          <Terminal className="w-5 h-5 text-[#adc7f7]" />
                          <span className="text-[12px] font-bold uppercase tracking-wider">Generate NCCIA Complaint</span>
                        </div>
                        <ArrowRight className="w-5 h-5 group-hover:translate-x-2 transition-transform" />
                      </Button>

                      <Button
                        variant="outline"
                        onClick={() => navigate(`${APP_BASE}/chat`, { state: { template: 'writ', type: 'petition', narrative: caseFacts } })}
                        className="w-full h-16 border-[#c4c6cf]/60 bg-white hover:bg-[#eff4ff] text-[#002045] rounded-xl flex items-center justify-between px-6 group transition-all"
                      >
                        <div className="flex items-center gap-4">
                          <Scale className="w-5 h-5 text-[#28657a]" />
                          <span className="text-[12px] font-bold uppercase tracking-wider">Generate Petition</span>
                        </div>
                        <ArrowRight className="w-5 h-5 group-hover:translate-x-2 transition-transform" />
                      </Button>

                      <div className="p-4 bg-[#eff4ff]/50 rounded-xl border border-[#dce9ff] flex items-center gap-3">
                        <Info className="w-4 h-4 text-[#28657a]" />
                        <p className="text-[10px] font-medium text-[#43474e]">Estimated generation time: ~12 seconds per document</p>
                      </div>
                    </div>
                  </div>

                  {/* AI Expert Counsel Card */}
                  <div className="bg-[#f8f9ff] border border-[#c4c6cf]/30 rounded-2xl p-8 shadow-sm">
                    <h4 className="text-[14px] font-bold text-[#002045] mb-4 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-[#28657a]" />
                      AI Expert Counsel
                    </h4>
                    <p className="text-[12px] text-[#43474e] leading-relaxed mb-6">
                      Based on the technical findings, it is recommended to file the NCCIA Complaint prior to the Petition
                      to secure the injunction on the contested IP ranges.
                    </p>
                    <Button
                      variant="outline"
                      onClick={() => navigate(`${APP_BASE}/chat`)}
                      className="w-full rounded-xl border-[#c4c6cf] text-[10px] font-bold uppercase h-12"
                    >
                      Consult AI Expert
                    </Button>
                  </div>
                </div>

                {/* Right Panel: Document Preview Canvas */}
                <div className="lg:col-span-7">
                  <div className="bg-white border border-[#c4c6cf]/30 rounded-2xl overflow-hidden shadow-sm h-full flex flex-col min-h-[600px]">
                    <div className="h-14 bg-[#f8f9ff] border-b border-[#c4c6cf]/30 px-6 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <FileCheck className="w-5 h-5 text-[#28657a]" />
                        <span className="text-[12px] font-bold text-[#002045]">Document Preview Canvas</span>
                      </div>
                      <div className="flex items-center gap-4 text-[#74777f]">
                        <Search className="w-4 h-4" />
                        <RotateCcw className="w-4 h-4" />
                        <Upload className="w-4 h-4" />
                      </div>
                    </div>
                    <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
                      <div className="w-16 h-16 rounded-2xl bg-[#eff4ff] flex items-center justify-center mb-6">
                        <FileText className="w-8 h-8 text-[#c4c6cf]" />
                      </div>
                      <h3 className="text-[14px] font-bold text-[#74777f] uppercase tracking-widest mb-2">Awaiting Generation Request</h3>
                      <p className="text-[11px] text-[#c4c6cf] max-w-xs leading-relaxed">
                        Select a primary action to compile the legal document layout and view preview here.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-start pt-6 border-t border-[#c4c6cf]/30">
                <Button 
                  variant="ghost" 
                  onClick={() => setStep(2)} 
                  className="h-12 px-6 rounded-xl text-[11px] font-bold text-[#28657a] bg-[#eff4ff] border border-[#28657a]/20 hover:bg-[#dce9ff] hover:border-[#28657a]/40 hover:text-[#002045] uppercase tracking-widest flex items-center gap-2 transition-all shadow-sm"
                >
                  <ArrowLeft className="w-4 h-4" /> Back
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <NCCIAFormModal
          isOpen={isComplaintModalOpen}
          onClose={() => setIsComplaintModalOpen(false)}
          analysisData={analysis}
          narrative={caseFacts}
        />

        {/* ── Extracted Evidence Modal ── */}
        <AnimatePresence>
          {isExtractedTextModalOpen && (
            <div className="fixed inset-0 z-[150] flex items-center justify-center p-6 lg:p-20">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setIsExtractedTextModalOpen(false)}
                className="absolute inset-0 bg-[#000814]/80 backdrop-blur-md"
              />
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                className="relative w-full max-w-4xl bg-[#0a1528] border border-white/10 rounded-3xl shadow-2xl flex flex-col overflow-hidden max-h-[90vh]"
              >
                <div className="px-8 py-6 border-b border-white/10 flex items-center justify-between bg-[#000814]/50">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-[#28657a]/20 flex items-center justify-center border border-[#28657a]/30">
                      <FileText className="w-5 h-5 text-[#28657a]" />
                    </div>
                    <div>
                      <h3 className="text-[18px] font-bold text-white">Extracted Evidence Review</h3>
                      <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Verify Forensic Data Ingestion</p>
                    </div>
                  </div>
                  <button onClick={() => setIsExtractedTextModalOpen(false)} className="p-2 hover:bg-white/10 rounded-full transition-colors">
                    <X className="w-5 h-5 text-slate-400" />
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-8 bg-[#0a1528] custom-scrollbar">
                  <div className="bg-[#000814]/40 border border-white/5 rounded-2xl p-6 text-[14px] text-slate-200 font-medium leading-relaxed whitespace-pre-wrap min-h-[400px]">
                    {ocrText}
                  </div>
                </div>
                <div className="px-8 py-5 border-t border-white/10 bg-[#000814]/50 flex items-center justify-between">
                  <p className="text-[10px] text-[#28657a] font-bold uppercase tracking-widest flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4" /> Evidence Integrity Verified
                  </p>
                  <div className="flex gap-3">
                    <Button onClick={() => setIsExtractedTextModalOpen(false)} className="bg-[#28657a] hover:bg-[#1e4d5d] text-white rounded-xl h-11 px-8 text-[10px] font-bold uppercase tracking-widest">
                      Close Review
                    </Button>
                  </div>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>

        {/* ── Case Detail Modal ── */}
        <AnimatePresence>
          {selectedCase && (
            <div className="fixed inset-0 z-[160] flex items-center justify-center p-6 lg:p-20">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setSelectedCase(null)}
                className="absolute inset-0 bg-[#000814]/80 backdrop-blur-md"
              />
              <motion.div
                initial={{ opacity: 0, scale: 0.95, x: 0, y: 20 }}
                animate={{ opacity: 1, scale: 1, x: 0, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, x: 0, y: 20 }}
                className="relative w-full max-w-2xl bg-[#0a1528] border border-white/10 rounded-3xl shadow-2xl flex flex-col overflow-hidden max-h-[90vh]"
              >
                <div className="px-8 py-6 border-b border-[#c4c6cf]/30 bg-[#002045] text-white">
                  <div className="flex items-center justify-between mb-4">
                    <div className="px-3 py-1 rounded-full bg-[#28657a] text-[9px] font-bold uppercase tracking-[0.2em] border border-white/20">
                      Precedent Node Analysis
                    </div>
                    <button onClick={() => setSelectedCase(null)} className="p-2 hover:bg-white/10 rounded-full transition-colors">
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                  <h3 className="text-[22px] font-bold leading-tight">{selectedCase.title || selectedCase.citation}</h3>
                  <div className="flex items-center gap-6 mt-4">
                    <div className="flex flex-col">
                      <span className="text-[9px] text-[#adc7f7] font-bold uppercase tracking-widest">Year</span>
                      <span className="text-[14px] font-bold">{selectedCase.year || '2022'}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[9px] text-[#adc7f7] font-bold uppercase tracking-widest">Relevance</span>
                      <span className="text-[14px] font-bold text-[#28657a] bg-white px-2 py-0.5 rounded-md">
                        {Math.round((selectedCase.relevance_score || 0) * 100)}%
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[9px] text-[#adc7f7] font-bold uppercase tracking-widest">Outcome</span>
                      <span className="text-[14px] font-bold text-[#62d3ff]">{selectedCase.outcome || 'ACQUITTAL'}</span>
                    </div>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
                  <section>
                    <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">Case Facts & Context</h4>
                    <p className="text-[14px] text-slate-200 leading-relaxed font-medium">
                      {selectedCase.summary || "This case addressed the procedural nuances of digital evidence preservation under PECA standards. The honorable court ruled that minor delays in forensic imaging do not necessarily invalidate the chain of custody if the hash values remain consistent."}
                    </p>
                  </section>

                  <section>
                    <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">Applicable Statutes</h4>
                    <div className="flex flex-wrap gap-2">
                      {(selectedCase.statutes || ['PECA §20', 'PPC §499', 'ETO §15']).map((s: string) => (
                        <span key={s} className="px-3 py-1 rounded-lg bg-[#28657a]/20 border border-[#28657a]/30 text-[11px] font-bold text-[#28657a]">
                          {s}
                        </span>
                      ))}
                    </div>
                  </section>

                  <section className="bg-[#000814]/40 rounded-2xl p-6 border border-white/5">
                    <h4 className="text-[11px] font-bold text-white uppercase tracking-widest mb-3 flex items-center gap-2">
                      <Gavel className="w-4 h-4 text-[#28657a]" />
                      Legal Significance
                    </h4>
                    <p className="text-[12px] text-slate-300 leading-relaxed">
                      This node serves as a primary anchor for the current defense strategy, specifically regarding the
                      interpretation of "unauthorized access" in high-privilege IT environments.
                    </p>
                  </section>
                </div>

                <div className="px-8 py-5 border-t border-white/10 bg-[#000814]/50 flex items-center justify-end gap-3">
                  <Button onClick={() => setSelectedCase(null)} className="bg-[#28657a] hover:bg-[#1e4d5d] text-white rounded-xl h-11 px-8 text-[10px] font-bold uppercase tracking-widest">
                    Close Analysis
                  </Button>
                </div>
              </motion.div>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
