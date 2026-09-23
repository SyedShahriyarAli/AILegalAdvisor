import React from 'react';
import { cn } from '@/lib/utils';
import { FileText, Scale, ExternalLink, Calendar, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';

interface CitationCardProps {
    type: 'source' | 'case';
    title: string;
    subtitle?: string; // e.g., Citation or Article number
    summary?: string;
    relevance?: number;
    link?: string;
    date?: string;
    /** Why this case was included (e.g. cyber-law metadata filter explanation) */
    caseInclusionNote?: string;
    onClick?: () => void;
    compact?: boolean;
}

export const CitationCard: React.FC<CitationCardProps> = ({
    type,
    title,
    subtitle,
    summary,
    relevance,
    link,
    date,
    caseInclusionNote,
    onClick,
    compact = false
}) => {
    const isCase = type === 'case';
    const Icon = isCase ? Scale : FileText;

    const CardContent = (
        <div
            onClick={(e) => {
                if (onClick) onClick();
                if (!link) e.preventDefault();
            }}
            className={cn(
                "group relative flex flex-col items-start gap-3 rounded-2xl border transition-all duration-300 cursor-pointer overflow-hidden bg-white/50 backdrop-blur-md",
                isCase ? "border-[#28657a]/20 hover:border-[#28657a]/50" : "border-[#002045]/10 hover:border-[#002045]/30",
                compact ? "p-3.5" : "p-5 hover:shadow-xl hover:shadow-[#002045]/5 hover:-translate-y-0.5"
            )}
        >
            <div className="flex items-start justify-between w-full gap-4">
                <div className="flex items-start gap-3.5 min-w-0">
                    <div className={cn(
                      "p-2 rounded-xl shrink-0 transition-colors", 
                      isCase ? "bg-[#eff4ff] text-[#28657a]" : "bg-[#f8f9ff] text-[#002045]",
                      "group-hover:bg-[#002045] group-hover:text-white"
                    )}>
                        <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex flex-col min-w-0">
                        {subtitle && (
                            <span className={cn(
                              "text-[9px] font-bold tracking-[0.15em] uppercase mb-0.5", 
                              isCase ? "text-[#28657a]" : "text-[#74777f]"
                            )}>
                                {subtitle}
                            </span>
                        )}
                        <h4 className={cn(
                          "text-[9px] font-bold text-[#002045] pr-2 transition-colors", 
                          compact ? "truncate" : "leading-tight"
                        )}>
                            {title}
                        </h4>
                    </div>
                </div>
                {link && !compact && (
                    <ExternalLink className="w-3.5 h-3.5 text-[#c4c6cf] group-hover:text-[#002045] transition-colors shrink-0" />
                )}
            </div>

            {!compact && (
                <>
                    {summary && (
                        <p className="text-[8px] text-[#43474e] line-clamp-2 leading-relaxed pl-3 border-l-2 border-[#dce9ff] group-hover:border-[#28657a] transition-colors font-medium">
                            {summary}
                        </p>
                    )}
                    {isCase && caseInclusionNote && (
                        <div className="flex items-start gap-2 bg-[#f8f9ff] p-2 rounded-lg border border-[#dce9ff]">
                           <ShieldCheck className="w-2.5 h-2.5 text-[#28657a] shrink-0 mt-0.5" />
                           <p className="text-[8px] text-[#28657a] font-bold leading-snug">
                               {caseInclusionNote}
                           </p>
                        </div>
                    )}

                    <div className="flex items-center gap-4 mt-2 w-full">
                        {date && (
                            <div className="flex items-center gap-1.5 text-[9px] font-bold text-[#74777f] uppercase tracking-wider">
                                <Calendar className="w-3 h-3" />
                                <span>{date}</span>
                            </div>
                        )}
                        {relevance && (
                            <div className="flex items-center gap-3 ml-auto">
                                <div className="h-1 w-12 bg-[#eff4ff] rounded-full overflow-hidden shadow-inner">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${relevance * 100}%` }}
                                        transition={{ duration: 1, ease: "easeOut" }}
                                        className={cn("h-full rounded-full", isCase ? "bg-[#28657a]" : "bg-[#002045]")}
                                    />
                                </div>
                                <span className="text-[7px] font-black text-[#002045] uppercase tracking-widest">{Math.round(relevance * 100)}% MATCH</span>
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );

    if (link) {
        return (
            <a href={link} target="_blank" rel="noopener noreferrer" className="block w-full no-underline">
                {CardContent}
            </a>
        );
    }

    return CardContent;
};
