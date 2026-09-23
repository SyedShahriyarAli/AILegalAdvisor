import { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChatArea } from '@/components/workspace/ChatArea';
import { SourceSidebar } from '@/components/workspace/SourceSidebar';
import type { Source } from '@/components/workspace/SourceSidebar';
import { authService } from '@/lib/authService';
import { apiUrl } from '@/lib/apiBase';
import { Button } from '@/components/ui/button';
import { X, Calendar as CalendarIcon, ShieldCheck, FileText } from 'lucide-react';

export default function Chat() {
  const [user] = useState(authService.getCurrentUser());
  const location = useLocation();
  const [sources, setSources] = useState<Source[]>([]);
  const [messages, setMessages] = useState<any[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const [processedState, setProcessedState] = useState(false);
  const [activeSourceId, setActiveSourceId] = useState<string | undefined>();
  const [input, setInput] = useState('');
  const [isPending, setIsPending] = useState(false);

  // Modal & File States
  const [isAddTextModalOpen, setIsAddTextModalOpen] = useState(false);
  const [isSourceDetailModalOpen, setIsSourceDetailModalOpen] = useState(false);
  const [newTextDate, setNewTextDate] = useState(new Date().toISOString().split('T')[0]);
  const [newTextContent, setNewTextContent] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load User Data
  useEffect(() => {
    let mounted = true;
    const run = async () => {
      if (user) {
        const data = await authService.getUserData(user.id);
        if (!mounted) return;
        setSources(data.sources || []);
        setMessages(data.chatHistory || []);
        setIsLoaded(true);
        if (data.sources && data.sources.length > 0) {
          setActiveSourceId(data.sources[0].id);
        }
      }
    };
    run();
    return () => {
      mounted = false;
    };
  }, [user]);

  useEffect(() => {
    if (user && isLoaded) {
      authService.saveUserData(user.id, {
        sources,
        chatHistory: messages,
        caseAnalyzerSessions: authService.loadUserData(user.id).caseAnalyzerSessions || []
      });
    }
  }, [sources, messages, user, isLoaded]);

  useEffect(() => {
    if (location.state?.template && !processedState) {
      const { template, narrative: stateNarrative } = location.state;
      const endpoint = template === 'petition' ? '/api/draft/petition' : '/api/draft/nccia' as const;
      
      const timer = setTimeout(() => {
        generateDraft(endpoint as any, stateNarrative);
        setProcessedState(true);
        window.history.replaceState({}, document.title);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [location.state, processedState]);

  const sessionId = user?.id || 'anonymous-session';

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { role: 'user' as const, content: input, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    const currentInput = input;
    setInput('');
    setIsPending(true);
    try {
      const response = await fetch(apiUrl('/api/query'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: currentInput,
          session_id: sessionId,
          use_orchestrator: true,
        }),
      });
      const data = await response.json();
      setMessages(prev => [...prev, {
        role: 'assistant' as const,
        content: data.answer || 'No response generated.',
        sources: data.sources || [],
        cases: data.cases || [],
        generationTime: data.duration || 0,
        timestamp: new Date()
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant' as const,
        content: 'Unable to reach backend right now. Please retry.',
        timestamp: new Date()
      }]);
    } finally {
      setIsPending(false);
    }
  };

  const handleAddTextSource = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTextContent) return;

    const newSource: Source = {
      id: Math.random().toString(36).substr(2, 9),
      title: `Narrative Log - ${newTextDate}`,
      type: 'text',
      content: newTextContent,
      status: 'indexed',
      timestamp: new Date(newTextDate)
    };

    setSources(prev => [newSource, ...prev]);
    setIsAddTextModalOpen(false);
    setNewTextContent('');
    setActiveSourceId(newSource.id);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const sourceId = Math.random().toString(36).slice(2, 11);
    const newSource: Source = {
      id: sourceId,
      title: file.name,
      type: file.type.includes('image') ? 'image' : 'pdf',
      content: 'Processing file...',
      status: 'processing',
      timestamp: new Date()
    };

    setSources(prev => [newSource, ...prev]);
    setActiveSourceId(sourceId);

    const formData = new FormData();
    formData.append('file', file);
    fetch(apiUrl('/api/ingest/ocr'), {
      method: 'POST',
      body: formData,
    })
      .then((res) => res.json())
      .then((data) => {
        const parsedContent = data.success
          ? (data.extracted_facts || []).join('\n') || data.raw_text || 'OCR complete'
          : 'OCR extraction failed';
        setSources(prev => prev.map(s =>
          s.id === sourceId ? { ...s, status: 'indexed', content: parsedContent } : s
        ));
      })
      .catch(() => {
        setSources(prev => prev.map(s =>
          s.id === sourceId ? { ...s, status: 'indexed', content: 'OCR upload failed' } : s
        ));
      });
  };

  const generateDraft = async (endpoint: '/api/draft/petition' | '/api/draft/nccia', overrideNarrative?: string) => {
    const promptLabel = endpoint === '/api/draft/petition' ? 'Generate a formal Writ Petition.' : 'Draft an NCCIA Complaint.';
    setMessages((prev) => [...prev, { role: 'user', content: promptLabel, timestamp: new Date() }]);
    setIsPending(true);
    try {
      const narrative = overrideNarrative || sources.map((s) => `${s.title}\n${s.content}`).join('\n\n').slice(0, 5000) || 'No source text provided.';
      const response = await fetch(apiUrl(endpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          narrative,
          sources: [],
          related_cases: []
        })
      });
      const data = await response.json();
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: data.body_markdown || 'Unable to generate draft.',
        timestamp: new Date()
      }]);
    } catch {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: 'Draft generation failed. Please retry.',
        timestamp: new Date()
      }]);
    } finally {
      setIsPending(false);
    }
  };

  return (
    <div className="relative flex h-full min-h-0 min-w-0 w-full overflow-hidden bg-[#f8f9ff]">
      {/* ── Background Gradients ── */}
      <div className="absolute inset-0 pointer-events-none opacity-40">
        <div className="absolute top-0 right-0 w-[50%] h-[50%] bg-gradient-to-br from-[#dce9ff] to-transparent blur-[120px]" />
        <div className="absolute bottom-0 left-0 w-[50%] h-[50%] bg-gradient-to-tr from-[#eff4ff] to-transparent blur-[120px]" />
      </div>

      <div className="relative z-10 flex min-h-0 min-w-0 flex-1 gap-6 overflow-hidden p-4 lg:p-6">
        <div className="hidden lg:block">
          <SourceSidebar
            sources={sources}
            activeSourceId={activeSourceId}
            onSourceSelect={(id) => {
              setActiveSourceId(id);
              setIsSourceDetailModalOpen(true);
            }}
            onDelete={(id) => setSources(prev => prev.filter(s => s.id !== id))}
            onDeleteAll={() => setSources([])}
            onAddText={() => setIsAddTextModalOpen(true)}
            onUploadFile={() => fileInputRef.current?.click()}
          />
        </div>

        <div className="relative min-h-0 min-w-0 flex-1 overflow-hidden rounded-[2.5rem] border border-[#c4c6cf]/30 bg-white shadow-[0_8px_40px_rgba(0,0,0,0.04)]">
          <ChatArea
            messages={messages}
            input={input}
            setInput={setInput}
            onSend={handleSend}
            isPending={isPending}
          />
        </div>
      </div>

      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        onChange={handleFileUpload}
        accept=".pdf,image/*"
      />

      {/* ── Add Text Modal ── */}
      <AnimatePresence>
        {isAddTextModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsAddTextModalOpen(false)}
              className="absolute inset-0 bg-[#000814]/80 backdrop-blur-md"
            />

            <motion.div
              initial={{ opacity: 0, scale: 0.98, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98, y: 10 }}
              className="relative w-full max-w-xl bg-[#0a1528] border border-white/10 rounded-3xl shadow-2xl overflow-hidden"
            >
              <div className="px-8 py-6 border-b border-white/10 flex items-center justify-between bg-[#000814]/50">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-[#28657a]/20 flex items-center justify-center border border-[#28657a]/30">
                    <CalendarIcon className="w-5 h-5 text-[#28657a]" />
                  </div>
                  <div>
                    <h2 className="text-[16px] font-bold text-white tracking-tight">Timestamp Evidence</h2>
                    <p className="text-[9px] text-slate-400 font-bold uppercase tracking-widest">Select relevant occurrence date</p>
                  </div>
                </div>
                <button
                  onClick={() => setIsAddTextModalOpen(false)}
                  className="rounded-lg hover:bg-white/10 p-2 text-slate-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleAddTextSource} className="p-8 space-y-8">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Event Date</label>
                  <div className="relative">
                    <input
                      type="date"
                      required
                      value={newTextDate}
                      onChange={e => setNewTextDate(e.target.value)}
                      className="w-full bg-[#000814]/40 border border-white/5 rounded-xl py-3.5 px-5 outline-none focus:ring-4 focus:ring-[#28657a]/10 focus:border-[#28657a] transition-all text-[12px] font-bold text-white"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1">Narrative Content</label>
                  <textarea
                    required
                    rows={6}
                    autoFocus
                    value={newTextContent}
                    onChange={e => setNewTextContent(e.target.value)}
                    className="w-full bg-[#000814]/40 border border-white/5 rounded-xl py-3.5 px-5 outline-none focus:ring-4 focus:ring-[#28657a]/10 focus:border-[#28657a] transition-all text-[12px] font-medium text-slate-200 placeholder:text-slate-600 resize-none leading-relaxed"
                    placeholder="Describe the incident details for temporal RAG analysis..."
                  />
                </div>

                <div className="flex items-center gap-4 pt-4">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setIsAddTextModalOpen(false)}
                    className="flex-1 h-12 rounded-xl text-[10px] font-bold uppercase tracking-widest text-slate-400 hover:bg-white/5 hover:text-white"
                  >
                    Discard
                  </Button>
                  <Button
                    type="submit"
                    className="flex-1 h-12 bg-[#28657a] hover:bg-[#1e4d5d] text-white rounded-xl text-[10px] font-bold uppercase tracking-widest shadow-lg shadow-[#28657a]/20"
                  >
                    Index into RAG
                  </Button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ── Source Detail Modal ── */}
      <AnimatePresence>
        {isSourceDetailModalOpen && activeSourceId && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsSourceDetailModalOpen(false)}
              className="absolute inset-0 bg-[#000814]/80 backdrop-blur-md"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.98, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98, y: 10 }}
              className="relative w-full max-w-2xl bg-[#0a1528] rounded-3xl shadow-2xl overflow-hidden border border-white/10"
            >
              <div className="px-8 py-6 border-b border-white/10 flex items-center justify-between bg-[#000814]/50">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-[#28657a]/20 flex items-center justify-center border border-[#28657a]/30">
                    <FileText className="w-5 h-5 text-[#28657a]" />
                  </div>
                  <div>
                    <h2 className="text-[16px] font-bold text-white tracking-tight">
                      {sources.find(s => s.id === activeSourceId)?.title || 'Source Detail'}
                    </h2>
                    <p className="text-[9px] text-slate-400 font-bold uppercase tracking-widest">Read-Only Forensic Extraction</p>
                  </div>
                </div>
                <button
                  onClick={() => setIsSourceDetailModalOpen(false)}
                  className="rounded-lg hover:bg-white/10 p-2 text-slate-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-8">
                <div className="bg-[#000814]/40 border border-white/5 rounded-2xl p-6 text-[13px] text-slate-200 font-medium leading-relaxed max-h-[50vh] overflow-y-auto whitespace-pre-wrap custom-scrollbar">
                  {sources.find(s => s.id === activeSourceId)?.content || 'No content available.'}
                </div>
                
                <div className="mt-8 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[#28657a]">
                    <ShieldCheck className="w-4 h-4" />
                    <span className="text-[9px] font-bold uppercase tracking-widest">Verified statutory match</span>
                  </div>
                  <Button
                    onClick={() => setIsSourceDetailModalOpen(false)}
                    className="h-11 px-8 bg-[#28657a] hover:bg-[#1e4d5d] text-white rounded-xl text-[10px] font-bold uppercase tracking-widest"
                  >
                    Close Review
                  </Button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
