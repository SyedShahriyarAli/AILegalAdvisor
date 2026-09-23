
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { motion } from 'framer-motion';
import { User, Bot, Sparkles, Copy, ThumbsUp, ThumbsDown, Scale } from 'lucide-react';
import { cn } from '@/lib/utils';
import { CitationCard } from './CitationCard';
import { Button } from '@/components/ui/button';
import { parseLegalAdvisorJson } from '@/lib/legalAdvisorJson';
import { resolveApiHref } from '@/lib/apiBase';
import { buildSourceSubtitle, formatDocumentName } from '@/lib/legalSourceLabels';

// Types (to be centralized)
interface Source {
    document: string;
    article: string;
    title: string;
    relevance_score: number;
    pdf_link?: string;
    chapter?: string | null;
    part?: string | null;
}

interface Case {
    citation: string;
    title: string;
    court: string;
    date: string;
    summary: string;
    pdf_link?: string;
    relevance_score: number;
    cyber_law_reason?: string | null;
    cyber_law_triggers_json?: string | null;
}

interface Message {
    role: 'user' | 'assistant';
    content: string;
    sources?: Source[];
    cases?: Case[];
    generationTime?: number;
    timestamp?: Date;
}

interface ChatMessageProps {
    message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
    const isUser = message.role === 'user';
    const advisorJson = !isUser ? parseLegalAdvisorJson(message.content) : null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
                "flex w-full min-w-0 max-w-full gap-4 md:gap-6",
                isUser ? "flex-row-reverse" : "flex-row"
            )}
        >
            {/* Avatar */}
            <div className={cn(
                "w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-lg mt-1 transition-all",
                isUser
                    ? "bg-primary text-white shadow-primary/20"
                    : "bg-white border border-border text-primary shadow-slate-200/50"
            )}>
                {isUser ? (
                    <User className="w-5 h-5" />
                ) : (
                    <Bot className="w-5 h-5" />
                )}
            </div>

            {/* Content Bubble */}
            <div
                className={cn(
                    // basis-0 + min-w-0: flex item may shrink to row width minus avatar (fixes overflow past main column).
                    "min-w-0 flex-1 basis-0 max-w-[min(85%,calc(100%-3.5rem))] md:max-w-[min(85%,calc(100%-4rem))]",
                    isUser ? "text-right" : "text-left"
                )}
            >
                {/* Header Name/Time */}
                <div className={cn("flex items-center gap-2 mb-2", isUser ? "justify-end" : "justify-start")}>
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                        {isUser ? 'User' : 'Legal Advisor'}
                    </span>
                    {message.timestamp && (
                        <span className="text-[9px] text-slate-400 font-medium">
                            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                    )}
                </div>

                {/* Message Body */}
                <div
                    className={cn(
                        "group relative min-w-0 max-w-full transition-all",
                        isUser
                            ? "rounded-[2rem] rounded-tr-sm bg-primary px-8 py-5 text-white shadow-xl shadow-primary/10"
                            : "bg-transparent text-foreground"
                    )}
                >
                    {isUser ? (
                        <p className="text-left text-[15px] font-medium leading-relaxed break-words whitespace-pre-wrap [overflow-wrap:anywhere]">
                            {message.content}
                        </p>
                    ) : (
                        <div className="space-y-6">
                            {advisorJson ? (
                                <div className="rounded-[1.75rem] border border-border bg-white/80 p-6 sm:p-8 shadow-sm space-y-6 text-left">
                                    <section>
                                        <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-primary mb-2">Direct answer</h3>
                                        <p className="text-[15px] leading-relaxed font-medium text-foreground/90">{advisorJson.directAnswer}</p>
                                    </section>
                                    {advisorJson.legalBasis.length > 0 && (
                                        <section>
                                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-primary mb-2">Legal basis</h3>
                                            <ul className="space-y-3 list-none pl-0">
                                                {advisorJson.legalBasis.map((lb, i) => (
                                                    <li key={i} className="text-[14px] leading-relaxed border-l-4 border-primary/30 pl-4">
                                                        <span className="font-bold text-foreground">{lb.citation}</span>
                                                        <span className="text-muted-foreground"> — {lb.explanation}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </section>
                                    )}
                                    {advisorJson.whatThisMeans && (
                                        <section>
                                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-primary mb-2">What this means</h3>
                                            <p className="text-[14px] leading-relaxed font-medium text-foreground/85">{advisorJson.whatThisMeans}</p>
                                        </section>
                                    )}
                                    {advisorJson.nextSteps.length > 0 && (
                                        <section>
                                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-primary mb-2">Next steps</h3>
                                            <ul className="list-disc pl-5 space-y-1 text-[14px] text-foreground/85">
                                                {advisorJson.nextSteps.map((s, i) => (
                                                    <li key={i}>{s}</li>
                                                ))}
                                            </ul>
                                        </section>
                                    )}
                                    {advisorJson.disclaimer && (
                                        <p className="text-[11px] text-muted-foreground italic border-t border-border pt-4">{advisorJson.disclaimer}</p>
                                    )}
                                </div>
                            ) : (
                                <div className="prose prose-sm max-w-none min-w-0 break-words
                                    prose-headings:font-heading prose-headings:font-black prose-headings:text-foreground prose-headings:mt-8 prose-headings:mb-4
                                    prose-p:text-foreground/90 prose-p:leading-relaxed prose-p:font-medium prose-p:text-[15px]
                                    prose-strong:text-primary prose-strong:font-black
                                    prose-ul:my-4 prose-ul:text-foreground/80
                                    prose-li:my-2 prose-li:marker:text-primary
                                    prose-blockquote:border-l-4 prose-blockquote:border-primary prose-blockquote:bg-indigo-50/50 prose-blockquote:py-5 prose-blockquote:px-8 prose-blockquote:rounded-r-[2rem] prose-blockquote:italic prose-blockquote:text-foreground prose-blockquote:font-bold
                                    prose-code:text-primary prose-code:bg-indigo-50 prose-code:px-2 prose-code:py-1 prose-code:rounded-lg prose-code:font-mono prose-code:text-[13px] prose-code:before:content-none prose-code:after:content-none">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {message.content}
                                    </ReactMarkdown>
                                </div>
                            )}

                            {/* Sources Grid — API retrieval with PDF links */}
                            {message.sources && message.sources.length > 0 && (
                                <div className="pt-6 border-t border-border">
                                    <div className="flex items-center gap-2 mb-4">
                                        <Sparkles className="w-3.5 h-3.5 text-primary" />
                                        <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em]">Applicable statutes (PDF)</span>
                                    </div>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        {message.sources.map((source, idx) => {
                                            const subtitle = buildSourceSubtitle(
                                                source.title,
                                                source.chapter,
                                                source.part,
                                            );
                                            return (
                                                <CitationCard
                                                    key={idx}
                                                    type="source"
                                                    title={`${formatDocumentName(source.document)} · ${source.article}`}
                                                    subtitle={subtitle}
                                                    relevance={source.relevance_score}
                                                    link={resolveApiHref(source.pdf_link)}
                                                    compact
                                                />
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {message.cases && message.cases.length > 0 && (
                                <div className="pt-6 border-t border-border">
                                    <div className="flex items-center gap-2 mb-4">
                                        <Scale className="w-3.5 h-3.5 text-amber-600" />
                                        <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em]">Related cases</span>
                                    </div>
                                    <div className="grid grid-cols-1 gap-4">
                                        {message.cases.map((c, idx) => (
                                            <CitationCard
                                                key={idx}
                                                type="case"
                                                title={c.title || c.citation}
                                                subtitle={c.citation}
                                                summary={c.summary}
                                                date={c.date}
                                                relevance={c.relevance_score}
                                                link={resolveApiHref(c.pdf_link)}
                                                caseInclusionNote={c.cyber_law_reason ?? undefined}
                                            />
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Action Bar (Only for AI) */}
                            <div className="flex items-center gap-2 pt-4 opacity-0 group-hover:opacity-100 transition-all duration-500">
                                <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl text-slate-400 hover:text-primary hover:bg-slate-50">
                                    <Copy className="w-4 h-4" />
                                </Button>
                                <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl text-slate-400 hover:text-emerald-500 hover:bg-emerald-50">
                                    <ThumbsUp className="w-4 h-4" />
                                </Button>
                                <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl text-slate-400 hover:text-rose-500 hover:bg-rose-50">
                                    <ThumbsDown className="w-4 h-4" />
                                </Button>
                                <div className="ml-auto flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 border border-border">
                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                    <span className="text-[9px] text-slate-500 font-bold uppercase tracking-widest">
                                        {message.generationTime?.toFixed(2)}s Verification
                                    </span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </motion.div>
    );
};
