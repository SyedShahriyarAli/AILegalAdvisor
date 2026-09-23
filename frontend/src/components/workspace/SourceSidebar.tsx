import React from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  FileSearch,
  Image as ImageIcon,
  File,
  X,
  Plus,
  Upload,
  Database,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

export interface Source {
  id: string;
  type: 'text' | 'pdf' | 'image';
  title: string;
  content: string;
  status: 'indexed' | 'processing';
  timestamp: Date;
}

interface SourceSidebarProps {
  sources: Source[];
  activeSourceId?: string;
  onSourceSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onDeleteAll: () => void;
  onAddText: () => void;
  onUploadFile: () => void;
}

export const SourceSidebar: React.FC<SourceSidebarProps> = ({
  sources,
  activeSourceId,
  onSourceSelect,
  onDelete,
  onDeleteAll,
  onAddText,
  onUploadFile
}) => {
  return (
    <div className="w-80 h-full bg-white border-r border-[#c4c6cf]/30 flex flex-col overflow-hidden relative shadow-[4px_0_24px_rgba(0,0,0,0.02)] z-30">
      <div className="flex flex-col h-full overflow-hidden">
        {/* ── Header ── */}
        <div className="p-6 border-b border-[#c4c6cf]/30 shrink-0">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-[#002045] flex items-center justify-center shadow-sm shrink-0">
                <Database className="w-4 h-4 text-white" />
              </div>
              <h2 className="text-[14px] font-bold text-[#002045] uppercase tracking-tight">Added Sources</h2>
            </div>
            {sources.length > 0 && (
              <button
                onClick={(e) => { e.stopPropagation(); onDeleteAll(); }}
                className="text-[9px] font-bold text-[#ba1a1a] hover:text-[#ba1a1a]/80 uppercase tracking-widest px-2 py-1 rounded-lg transition-colors"
              >
                Reset
              </button>
            )}
          </div>

          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Button
                variant="outline"
                onClick={onAddText}
                className="h-10 px-3 bg-[#f8f9ff] border-[#dce9ff] text-[#002045] text-[10px] font-bold uppercase tracking-widest rounded-xl flex items-center gap-2 hover:bg-[#eff4ff] transition-all"
              >
                <Plus className="w-3.5 h-3.5" />
                Text
              </Button>
              <Button
                variant="outline"
                onClick={onUploadFile}
                className="h-10 px-3 bg-[#f8f9ff] border-[#dce9ff] text-[#002045] text-[10px] font-bold uppercase tracking-widest rounded-xl flex items-center gap-2 hover:bg-[#eff4ff] transition-all"
              >
                <Upload className="w-3.5 h-3.5" />
                Upload
              </Button>
            </div>
          </div>

        </div>

        {/* ── Source List ── */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
          {sources.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center space-y-4 opacity-40">
              <div className="w-12 h-12 rounded-2xl bg-[#eff4ff] flex items-center justify-center">
                <FileSearch className="w-6 h-6 text-[#002045]" />
              </div>
              <p className="text-[9px] text-[#74777f] font-bold uppercase tracking-[0.2em]">
                Empty Pipeline
              </p>
            </div>
          ) : (
            sources.map((source) => (
              <motion.div
                key={source.id}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative group"
              >
                <button
                  onClick={() => onSourceSelect(source.id)}
                  className={cn(
                    "w-full text-left p-3.5 rounded-2xl border transition-all duration-300 relative overflow-hidden",
                    activeSourceId === source.id
                      ? "bg-[#eff4ff] border-[#002045]/20 shadow-sm"
                      : "bg-white border-transparent hover:bg-[#f8f9ff] hover:border-[#c4c6cf]/20"
                  )}
                >
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-all",
                      activeSourceId === source.id ? "bg-[#002045] text-white" : "bg-[#f8f9ff] text-[#74777f] group-hover:bg-[#002045] group-hover:text-white"
                    )}>
                      {source.status === 'processing' ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          {source.type === 'text' && <FileText className="w-4 h-4" />}
                          {source.type === 'pdf' && <File className="w-4 h-4" />}
                          {source.type === 'image' && <ImageIcon className="w-4 h-4" />}
                        </>
                      )}
                    </div>

                    <div className="flex-1 min-w-0 pr-4">
                      <p className={cn(
                        "text-[12px] font-bold truncate transition-colors",
                        activeSourceId === source.id ? "text-[#002045]" : "text-[#43474e]"
                      )}>
                        {source.title}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[8px] font-bold text-[#74777f] uppercase tracking-widest">{source.type}</span>
                        <div className="w-1 h-1 rounded-full bg-[#c4c6cf]" />
                        <span className="text-[8px] font-bold text-[#28657a] uppercase tracking-widest">
                          {source.status === 'processing' ? 'Encrypting...' : 'Indexed'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Skeleton Loading Effect for Processing */}
                  {source.status === 'processing' && (
                    <motion.div
                      initial={{ x: '-100%' }}
                      animate={{ x: '100%' }}
                      transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                      className="absolute inset-0 bg-gradient-to-r from-transparent via-[#002045]/5 to-transparent pointer-events-none"
                    />
                  )}
                </button>

                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(source.id); }}
                  className="absolute top-1/2 -translate-y-1/2 right-3 w-7 h-7 rounded-lg bg-white border border-[#c4c6cf]/30 flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-[#ba1a1a] hover:text-white hover:border-[#ba1a1a] transition-all z-10 shadow-sm"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </motion.div>
            ))
          )}
        </div>

      </div>
    </div>
  );
};
