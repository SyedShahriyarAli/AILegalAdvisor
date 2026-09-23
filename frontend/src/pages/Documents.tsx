import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  Search,
  Filter,
  Grid,
  List as ListIcon,
  BookOpen,
  X,
  Scale,
  ChevronRight,
  ExternalLink
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const PDF_FILES = [
  { name: 'PECA Act, 2016.pdf', category: 'Cyber Law', size: '388 KB', lastModified: '2024-02-10' },
  { name: 'PECA Amendment, 2025.pdf', category: 'Cyber Law', size: '231 KB', lastModified: '2025-01-05' },
  { name: 'Pakistan Penal Code.pdf', category: 'Criminal Law', size: '457 KB', lastModified: '2024-01-15' },
  { name: 'The Electronic Transactions Ordinance, 2002.pdf', category: 'Electronic Ops', size: '372 KB', lastModified: '2023-11-20' },
  { name: 'Telecom Regulations.pdf', category: 'Regulations', size: '509 KB', lastModified: '2024-03-05' },
  { name: 'Pakistan Telecom Rules.pdf', category: 'Regulations', size: '2.0 MB', lastModified: '2024-02-28' },
];

export default function Documents() {
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [search, setSearch] = useState('');
  const [selectedPdf, setSelectedPdf] = useState<string | null>(null);

  const filteredFiles = PDF_FILES.filter(f =>
    f.name.toLowerCase().includes(search.toLowerCase()) ||
    f.category.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex-1 h-full bg-[#f8f9ff] p-6 lg:p-10 overflow-y-auto custom-scrollbar">
      <div className="max-w-[1400px] mx-auto space-y-10">

        {/* ── Header Section ── */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-3">
            <div className="flex items-center gap-3 text-[#28657a] font-bold uppercase tracking-[0.2em] text-[7px]">
              <div className="w-8 h-[1px] bg-[#28657a]" />
              <span>Statutory Repository</span>
            </div>
            <h1 className="text-[22px] font-bold text-[#002045] tracking-tight">Law Documents</h1>
            <p className="text-[10px] text-[#43474e] font-medium leading-relaxed">Official primary sources and legislative acts for Pakistani cyber law.</p>
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
              placeholder="Search documents by name or category..."
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

        {/* ── Files Display ── */}
        {view === 'grid' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredFiles.map((file, idx) => (
              <motion.div
                key={file.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.03 }}
                className="group bg-white border border-[#c4c6cf]/30 hover:border-[#28657a]/40 p-5 rounded-2xl transition-all hover:shadow-lg hover:shadow-[#002045]/5 relative overflow-hidden"
              >
                <div className="w-10 h-10 rounded-xl bg-[#eff4ff] flex items-center justify-center mb-5 group-hover:scale-105 transition-transform">
                  <FileText className="w-5 h-5 text-[#002045]" />
                </div>

                <h3 className="text-[11px] font-bold text-[#002045] mb-2 truncate leading-tight" title={file.name}>
                  {file.name}
                </h3>
                <div className="flex items-center gap-2 mb-5">
                  <span className="text-[8px] font-bold text-[#28657a] bg-[#eff4ff] px-2 py-0.5 rounded-md uppercase tracking-wider border border-[#dce9ff]">
                    {file.category}
                  </span>
                  <span className="text-[8px] text-[#74777f] font-bold uppercase tracking-widest">
                    {file.size}
                  </span>
                </div>

                <Button
                  onClick={() => setSelectedPdf(file.name)}
                  className="w-full rounded-xl h-10 bg-[#002045] hover:bg-[#1a365d] text-white text-[9px] font-bold uppercase tracking-widest transition-all"
                >
                  View Document
                </Button>
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="bg-white border border-[#c4c6cf]/30 rounded-2xl overflow-hidden shadow-sm">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#f8f9ff] border-b border-[#c4c6cf]/30">
                  <th className="px-6 py-4 text-[8px] font-bold text-[#74777f] uppercase tracking-[0.15em]">Document Name</th>
                  <th className="px-6 py-4 text-[8px] font-bold text-[#74777f] uppercase tracking-[0.15em]">Category</th>
                  <th className="px-6 py-4 text-[8px] font-bold text-[#74777f] uppercase tracking-[0.15em]">Size</th>
                  <th className="px-6 py-4 text-[8px] font-bold text-[#74777f] uppercase tracking-[0.15em] text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#c4c6cf]/20">
                {filteredFiles.map((file) => (
                  <tr key={file.name} className="hover:bg-[#eff4ff]/30 transition-colors group">
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-[#eff4ff] flex items-center justify-center shrink-0 border border-[#dce9ff]">
                          <FileText className="w-4 h-4 text-[#002045]" />
                        </div>
                        <span className="font-bold text-[#002045] text-[10px]">{file.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-3.5">
                      <span className="text-[8px] font-bold text-[#28657a] bg-[#eff4ff] px-2.5 py-0.5 rounded-md uppercase tracking-wider border border-[#dce9ff]">
                        {file.category}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-[9px] text-[#43474e] font-bold">{file.size}</td>
                    <td className="px-6 py-3.5 text-right">
                      <Button
                        variant="ghost"
                        onClick={() => setSelectedPdf(file.name)}
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

        {filteredFiles.length === 0 && (
          <div className="py-20 text-center space-y-4">
            <div className="w-14 h-14 bg-[#eff4ff] rounded-full flex items-center justify-center mx-auto mb-4">
              <Search className="w-7 h-7 text-[#c4c6cf]" />
            </div>
            <h3 className="text-[14px] font-bold text-[#002045]">No documents found</h3>
            <p className="text-[#74777f] text-[10px] max-w-sm mx-auto font-medium">
              Try adjusting your search or filters to find the statutory documents you're looking for.
            </p>
          </div>
        )}
      </div>

      {/* ── PDF Viewer Modal ── */}
      <AnimatePresence>
        {selectedPdf && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 sm:p-10">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedPdf(null)}
              className="absolute inset-0 bg-[#002045]/80 backdrop-blur-sm"
            />

            <motion.div
              initial={{ opacity: 0, scale: 0.98, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98, y: 10 }}
              className="relative w-full h-[80vh] max-w-[1000px] bg-white rounded-3xl shadow-2xl overflow-hidden flex flex-col border border-[#c4c6cf]/30"
            >
              {/* Modal Header */}
              <div className="px-6 py-4 border-b border-[#c4c6cf]/30 flex items-center justify-between bg-white sticky top-0 z-10">
                <div className="flex items-center gap-4">
                  <div className="w-9 h-9 rounded-xl bg-[#eff4ff] flex items-center justify-center border border-[#dce9ff]">
                    <Scale className="w-4 h-4 text-[#002045]" />
                  </div>
                  <div>
                    <h2 className="text-[14px] font-bold text-[#002045] tracking-tight">{selectedPdf}</h2>
                    <p className="text-[8px] text-[#74777f] font-bold uppercase tracking-widest">Official Statutory Version • Non-Downloadable</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedPdf(null)}
                  className="rounded-lg hover:bg-[#eff4ff] p-2 text-[#74777f] hover:text-[#002045] transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* PDF Frame */}
              <div className="flex-1 bg-[#43474e] relative">
                <iframe
                  src={`/pdfs/${encodeURIComponent(selectedPdf)}#toolbar=0`}
                  className="w-full h-full border-none"
                  title="PDF Viewer"
                />
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-3.5 bg-[#f8f9ff] border-t border-[#c4c6cf]/30 flex items-center justify-between">
                <div className="flex items-center gap-2 text-[8px] font-bold text-[#74777f] uppercase tracking-widest">
                  <BookOpen className="w-3.5 h-3.5 text-[#28657a]" />
                  Statutory Reader Mode Active
                </div>
                <div className="flex items-center gap-4">
                  <button className="text-[8px] font-bold text-[#002045] uppercase tracking-widest flex items-center gap-1 hover:underline">
                    <ExternalLink className="w-3 h-3" /> External Source
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
