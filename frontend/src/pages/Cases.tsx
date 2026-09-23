import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  Search,
  Filter,
  Grid,
  List as ListIcon,
  BookOpen,
  X,
  ChevronRight,
  Info,
  Gavel,
  Calendar,
  User as UserIcon,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { apiUrl, resolveApiHref } from '@/lib/apiBase';

interface CourtCase {
  id: string;
  citation: string;
  title: string;
  summary: string;
  court: string;
  date: string;
  judge: string;
  pdf_link: string;
  winner?: string;
  type: 'case';
  cyber_law_reason?: string | null;
}

export default function Cases() {
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [search, setSearch] = useState('');
  const [cases, setCases] = useState<CourtCase[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCase, setSelectedCase] = useState<CourtCase | null>(null);

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(apiUrl('/api/cases'));
      const data = await response.json();
      if (data.success) {
        setCases(data.cases);
      }
    } catch (error) {
      console.error('Error fetching cases:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredCases = cases.filter(c =>
    c.title?.toLowerCase().includes(search.toLowerCase()) ||
    c.citation?.toLowerCase().includes(search.toLowerCase()) ||
    c.court?.toLowerCase().includes(search.toLowerCase()) ||
    c.judge?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex-1 h-full bg-[#f8f9ff] p-6 lg:p-10 overflow-y-auto custom-scrollbar">
      <div className="max-w-[1400px] mx-auto space-y-10">

        {/* ── Header Section ── */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-3">
            <div className="flex items-center gap-3 text-[#28657a] font-bold uppercase tracking-[0.2em] text-[7px]">
              <div className="w-8 h-[1px] bg-[#28657a]" />
              <span>Judicial Repository</span>
            </div>
            <h1 className="text-[22px] font-bold text-[#002045] tracking-tight">Browse Cases</h1>
            <p className="text-[10px] text-[#43474e] font-medium leading-relaxed">Explore Pakistani court precedents and landmark judgments on cybercrime.</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex bg-[#eff4ff] p-1 rounded-xl border border-[#c4c6cf]/30 backdrop-blur-sm">
              <button
                onClick={() => setView('grid')}
                className={cn("p-2 rounded-lg transition-all", view === 'grid' ? "bg-white shadow-sm text-[#002045]" : "text-[#74777f] hover:text-[#002045]")}
              >
                <Grid className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setView('list')}
                className={cn("p-2 rounded-lg transition-all", view === 'list' ? "bg-white shadow-sm text-[#002045]" : "text-[#74777f] hover:text-[#002045]")}
              >
                <ListIcon className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* ── Search and Filters ── */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative group">
            <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
              <Search className="w-3.5 h-3.5 text-[#74777f] group-focus-within:text-[#002045] transition-colors" />
            </div>
            <input
              type="text"
              placeholder="Search cases by title, citation, court, or judge..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-white border border-[#c4c6cf]/40 rounded-xl py-3 px-12 pr-6 outline-none focus:ring-4 focus:ring-[#002045]/5 focus:border-[#002045] transition-all text-[10px] font-medium shadow-sm placeholder:text-[#c4c6cf]"
            />
          </div>
          <Button variant="outline" className="rounded-xl border-[#c4c6cf]/50 h-11 px-6 text-[9px] font-bold uppercase tracking-widest bg-white hover:bg-[#eff4ff] transition-all">
            <Filter className="w-3.5 h-3.5 mr-2" />
            Filters
          </Button>
        </div>

        {/* ── Loading State ── */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="bg-white border border-[#c4c6cf]/20 rounded-2xl p-5 h-48 animate-pulse">
                <div className="w-10 h-10 bg-[#eff4ff] rounded-xl mb-4" />
                <div className="h-4 bg-[#eff4ff] rounded w-3/4 mb-2" />
                <div className="h-3 bg-[#eff4ff] rounded w-1/2 mb-4" />
                <div className="h-10 bg-[#eff4ff] rounded-xl w-full" />
              </div>
            ))}
          </div>
        ) : (
          <>
            {/* ── Files Display ── */}
            {view === 'grid' ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {filteredCases.map((caseItem, idx) => (
                  <motion.div
                    key={caseItem.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    className="group bg-white border border-[#c4c6cf]/30 hover:border-[#28657a]/40 p-5 rounded-2xl transition-all hover:shadow-lg hover:shadow-[#002045]/5 relative overflow-hidden flex flex-col"
                  >
                    <div className="w-10 h-10 rounded-xl bg-[#eff4ff] flex items-center justify-center mb-5 group-hover:scale-105 transition-transform">
                      <Gavel className="w-5 h-5 text-[#002045]" />
                    </div>

                    <h3 className="text-[11px] font-bold text-[#002045] mb-2 line-clamp-2 leading-tight" title={caseItem.title}>
                      {caseItem.title}
                    </h3>
                    
                    <div className="space-y-1.5 mb-5 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-[8px] font-bold text-[#28657a] bg-[#eff4ff] px-2 py-0.5 rounded-md uppercase tracking-wider border border-[#dce9ff]">
                          {caseItem.court}
                        </span>
                        <span className="text-[8px] text-[#74777f] font-bold uppercase tracking-widest">
                          {caseItem.citation}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 text-[9px] text-[#43474e] font-medium">
                        <Calendar className="w-3 h-3 text-[#74777f]" />
                        {caseItem.date}
                      </div>
                      {caseItem.judge && (
                        <div className="flex items-center gap-1.5 text-[9px] text-[#43474e] font-medium truncate">
                          <UserIcon className="w-3 h-3 text-[#74777f]" />
                          {caseItem.judge}
                        </div>
                      )}
                    </div>

                    <Button
                      onClick={() => setSelectedCase(caseItem)}
                      className="w-full rounded-xl h-10 bg-[#002045] hover:bg-[#1a365d] text-white text-[9px] font-bold uppercase tracking-widest transition-all"
                    >
                      View Details
                    </Button>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="bg-white border border-[#c4c6cf]/30 rounded-2xl overflow-hidden shadow-sm">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-[#f8f9ff] border-b border-[#c4c6cf]/30">
                      <th className="px-6 py-4 text-[8px] font-bold text-[#74777f] uppercase tracking-[0.15em]">Parties / Citation</th>
                      <th className="px-6 py-4 text-[8px] font-bold text-[#74777f] uppercase tracking-[0.15em]">Court</th>
                      <th className="px-6 py-4 text-[8px] font-bold text-[#74777f] uppercase tracking-[0.15em]">Judge</th>
                      <th className="px-6 py-4 text-[8px] font-bold text-[#74777f] uppercase tracking-[0.15em]">Date</th>
                      <th className="px-6 py-4 text-[8px] font-bold text-[#74777f] uppercase tracking-[0.15em] text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#c4c6cf]/20">
                    {filteredCases.map((caseItem) => (
                      <tr key={caseItem.id} className="hover:bg-[#eff4ff]/30 transition-colors group">
                        <td className="px-6 py-3.5">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-[#eff4ff] flex items-center justify-center shrink-0 border border-[#dce9ff]">
                              <Gavel className="w-4 h-4 text-[#002045]" />
                            </div>
                            <div className="min-w-0">
                              <p className="font-bold text-[#002045] text-[10px] truncate max-w-[300px]">{caseItem.title}</p>
                              <p className="text-[8px] text-[#74777f] font-medium">{caseItem.citation}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-3.5">
                          <span className="text-[8px] font-bold text-[#28657a] bg-[#eff4ff] px-2.5 py-0.5 rounded-md uppercase tracking-wider border border-[#dce9ff]">
                            {caseItem.court}
                          </span>
                        </td>
                        <td className="px-6 py-3.5 text-[9px] text-[#43474e] font-bold truncate max-w-[150px]">{caseItem.judge}</td>
                        <td className="px-6 py-3.5 text-[9px] text-[#43474e] font-bold">{caseItem.date}</td>
                        <td className="px-6 py-3.5 text-right">
                          <Button
                            variant="ghost"
                            onClick={() => setSelectedCase(caseItem)}
                            className="rounded-lg h-8 px-3 text-[9px] font-bold uppercase tracking-widest text-[#002045] hover:bg-[#eff4ff]"
                          >
                            View <ChevronRight className="w-3 h-3 ml-1" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {filteredCases.length === 0 && (
              <div className="py-20 text-center space-y-4">
                <div className="w-14 h-14 bg-[#eff4ff] rounded-full flex items-center justify-center mx-auto mb-4">
                  <Search className="w-7 h-7 text-[#c4c6cf]" />
                </div>
                <h3 className="text-[14px] font-bold text-[#002045]">No cases found</h3>
                <p className="text-[#74777f] text-[10px] max-w-sm mx-auto font-medium">
                  Try adjusting your search or filters to find the court precedents you're looking for.
                </p>
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Case Details Modal ── */}
      <AnimatePresence>
        {selectedCase && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 sm:p-10">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedCase(null)}
              className="absolute inset-0 bg-[#002045]/80 backdrop-blur-sm"
            />

            <motion.div
              initial={{ opacity: 0, scale: 0.98, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98, y: 10 }}
              className="relative w-full max-w-6xl h-[90vh] bg-white rounded-3xl shadow-2xl overflow-hidden flex flex-col border border-[#c4c6cf]/30"
            >
              <div className="px-8 py-5 border-b border-[#c4c6cf]/30 flex items-center justify-between shrink-0 bg-white">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-[#eff4ff] flex items-center justify-center border border-[#dce9ff] shadow-sm">
                    <Gavel className="w-5 h-5 text-[#002045]" />
                  </div>
                  <div>
                    <h2 className="text-[14px] font-bold text-[#002045] leading-tight max-w-[500px] truncate">{selectedCase.title}</h2>
                    <div className="flex items-center gap-2 mt-0.5">
                      <p className="text-[9px] text-[#74777f] font-bold uppercase tracking-widest">{selectedCase.citation}</p>
                      <span className="w-1 h-1 rounded-full bg-[#c4c6cf]" />
                      <p className="text-[9px] text-[#28657a] font-bold uppercase tracking-widest">{selectedCase.court}</p>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setSelectedCase(null)}
                    className="p-2 rounded-xl hover:bg-[#eff4ff] text-[#74777f] hover:text-[#002045] transition-all"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>

              <div className="flex-1 flex overflow-hidden">
                {/* PDF Viewer Side */}
                <div className="flex-1 bg-[#43474e] relative">
                  {selectedCase.pdf_link ? (
                    <iframe
                      src={`${resolveApiHref(selectedCase.pdf_link)}#toolbar=1`}
                      className="w-full h-full border-none"
                      title="Case Judgment PDF"
                    />
                  ) : (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-white p-10 text-center">
                      <div className="w-16 h-16 rounded-2xl bg-white/10 flex items-center justify-center mb-6 border border-white/10">
                        <FileText className="w-8 h-8 text-white/50" />
                      </div>
                      <h3 className="text-[16px] font-bold mb-2">No PDF Document Available</h3>
                      <p className="text-[12px] text-white/60 max-w-xs leading-relaxed font-medium">
                        The digital judgment file is not currently indexed for this specific case citation.
                      </p>
                    </div>
                  )}
                </div>

                {/* Info Sidebar */}
                <div className="w-[320px] border-l border-[#c4c6cf]/30 bg-[#f8f9ff] flex flex-col shrink-0 overflow-y-auto custom-scrollbar">
                  <div className="p-6 space-y-8">
                    {/* Metadata */}
                    <div className="space-y-4">
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-4 bg-[#28657a] rounded-full" />
                        <h3 className="text-[10px] font-bold text-[#002045] uppercase tracking-widest">Case Metadata</h3>
                      </div>
                      <div className="space-y-4 p-4 bg-white rounded-2xl border border-[#c4c6cf]/20">
                        <div>
                          <p className="text-[8px] font-bold text-[#74777f] uppercase tracking-widest mb-0.5">Judge</p>
                          <p className="text-[10px] font-bold text-[#002045]">{selectedCase.judge || 'N/A'}</p>
                        </div>
                        <div>
                          <p className="text-[8px] font-bold text-[#74777f] uppercase tracking-widest mb-0.5">Date of Judgment</p>
                          <p className="text-[10px] font-bold text-[#002045]">{selectedCase.date}</p>
                        </div>
                        <div>
                          <p className="text-[8px] font-bold text-[#74777f] uppercase tracking-widest mb-0.5">Outcome</p>
                          <span className={cn(
                            "text-[8px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider inline-block mt-1",
                            selectedCase.winner?.toLowerCase().includes('accused') 
                              ? "bg-[#ffdad6] text-[#ba1a1a] border border-[#ffb4ab]" 
                              : "bg-[#eff4ff] text-[#28657a] border border-[#dce9ff]"
                          )}>
                            {selectedCase.winner || 'Pending/Other'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Summary */}
                    <div className="space-y-4">
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-4 bg-[#002045] rounded-full" />
                        <h3 className="text-[10px] font-bold text-[#002045] uppercase tracking-widest">Legal Summary</h3>
                      </div>
                      <div className="bg-white border border-[#c4c6cf]/20 rounded-2xl p-4">
                        <p className="text-[10px] text-[#43474e] leading-relaxed font-medium">
                          {selectedCase.summary || 'No summary available.'}
                        </p>
                      </div>
                    </div>

                    {/* Reasoning */}
                    {selectedCase.cyber_law_reason && (
                      <div className="space-y-4">
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-4 bg-emerald-500 rounded-full" />
                          <h3 className="text-[10px] font-bold text-[#002045] uppercase tracking-widest">Ratio Decidendi</h3>
                        </div>
                        <div className="bg-white border border-[#c4c6cf]/20 rounded-2xl p-4">
                          <p className="text-[10px] text-[#28657a] leading-relaxed font-medium italic">
                            "{selectedCase.cyber_law_reason}"
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="px-8 py-3.5 bg-white border-t border-[#c4c6cf]/30 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2 text-[8px] font-bold text-[#74777f] uppercase tracking-widest">
                  <BookOpen className="w-3.5 h-3.5 text-[#28657a]" />
                  Judicial Precedent Reader
                </div>
                <div className="flex items-center gap-2">
                  <Info className="w-3 h-3 text-[#c4c6cf]" />
                  <span className="text-[8px] text-[#c4c6cf] font-bold uppercase tracking-widest">Official Record Source</span>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
