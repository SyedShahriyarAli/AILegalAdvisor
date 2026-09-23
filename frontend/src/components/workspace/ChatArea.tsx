import React, { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Bot, Loader2, Sparkles, ShieldCheck } from 'lucide-react';
import TextareaAutosize from 'react-textarea-autosize';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ChatMessage } from '@/components/chat/ChatMessage';
import legalFacts from '@/data/legal_facts.json';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
}

interface ChatAreaProps {
  messages: Message[];
  input: string;
  setInput: (val: string) => void;
  onSend: () => void;
  isPending: boolean;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  input,
  setInput,
  onSend,
  isPending
}) => {
  const [currentFactIndex, setCurrentFactIndex] = useState(0);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isPending) {
      setCurrentFactIndex(Math.floor(Math.random() * legalFacts.length));
      interval = setInterval(() => {
        setCurrentFactIndex(prev => (prev + 1) % legalFacts.length);
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [isPending]);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const root = scrollContainerRef.current;
    if (!root) return;
    const pinToBottom = () => {
      root.scrollTo({ top: root.scrollHeight - root.clientHeight, behavior: 'auto' });
    };
    requestAnimationFrame(() => requestAnimationFrame(pinToBottom));
  }, [messages, isPending]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="relative flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-[#f8f9ff]">

      {/* ── Background decoration ── */}
      <div className="absolute inset-0 pointer-events-none opacity-20">
        <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-[#dce9ff] blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-[#eff4ff] blur-[120px] rounded-full" />
      </div>

      {/* ── Messages Feed ── */}
      <div className="relative z-10 flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <div
          ref={scrollContainerRef}
          className="custom-scrollbar min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-hidden px-6 scroll-pt-8 scroll-pb-4 lg:px-10 lg:scroll-pt-10"
        >
          <div className="mx-auto w-full min-w-0 max-w-3xl pb-40 pt-14">
            {messages.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col items-center justify-center min-h-[60vh] text-center"
              >
                <div className="w-16 h-16 rounded-2xl bg-[#eff4ff] flex items-center justify-center border border-[#dce9ff] mb-8">
                  <Sparkles className="w-8 h-8 text-[#002045]" />
                </div>
                <div className="space-y-6">
                  <div className="space-y-3">
                    <div className="flex items-center justify-center gap-3 text-[#28657a] font-bold uppercase tracking-[0.2em] text-[8px]">
                      <div className="w-6 h-[1px] bg-[#28657a]" />
                      <span>Interactive Advisory</span>
                      <div className="w-6 h-[1px] bg-[#28657a]" />
                    </div>
                    <h2 className="text-[28px] font-bold text-[#002045] tracking-tight">
                      Legal Assistant AI
                    </h2>
                    <p className="text-[#74777f] max-w-sm text-[12px] leading-relaxed font-medium mx-auto">
                      Provide case context or request statutory drafting guidance.
                      My analysis is grounded in PECA 2025 protocols.
                    </p>
                  </div>
                </div>
              </motion.div>
            )}

            <div className="min-w-0 space-y-10">
              <AnimatePresence initial={false}>
                {messages.map((msg, idx) => (
                  <ChatMessage key={idx} message={msg as any} />
                ))}
              </AnimatePresence>

              {isPending && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-5"
                >
                  <div className="w-10 h-10 rounded-xl bg-[#002045] flex items-center justify-center shrink-0 shadow-lg shadow-[#002045]/10">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center gap-3 text-[#002045] bg-white px-5 py-4 rounded-2xl border border-[#c4c6cf]/30 shadow-sm">
                      <Loader2 className="w-4 h-4 animate-spin text-[#28657a]" />
                      <span className="text-[10px] font-bold uppercase tracking-wider">Processing Legal Query...</span>
                    </div>

                    {/* Random Facts Loader */}
                    <motion.div
                      key={currentFactIndex}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="flex items-center gap-2 px-1"
                    >
                      <ShieldCheck className="w-3 h-3 text-[#28657a]" />
                      <p className="text-[12px] text-[#28657a] font-bold uppercase tracking-widest leading-relaxed max-w-md">
                        Regulatory Context: {legalFacts[currentFactIndex]}
                      </p>
                    </motion.div>
                  </div>
                </motion.div>
              )}
            </div>

            <div className="h-4 shrink-0" aria-hidden />
          </div>
        </div>
      </div>

      {/* ── Floating Input Area ── */}
      <div className="absolute bottom-8 left-0 right-0 px-6 lg:px-10 z-20">
        <div className="max-w-2xl mx-auto">
          <div className="relative">
            <div className="absolute -inset-2 bg-[#002045]/5 rounded-[2.5rem] blur-xl opacity-0 group-focus-within:opacity-100 transition-all duration-500" />
            <div className="relative flex items-end gap-2 bg-white/80 backdrop-blur-xl border border-[#c4c6cf]/40 p-2.5 rounded-[2rem] shadow-2xl shadow-[#002045]/5 transition-all">

              <TextareaAutosize
                ref={inputRef}
                minRows={1}
                maxRows={8}
                placeholder="Ask about PECA compliance, drafting strategies..."
                className="flex-1 bg-transparent border-0 resize-none outline-none text-[#002045] placeholder:text-[#c4c6cf] py-3.5 px-6 text-[14px] leading-relaxed font-medium"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isPending}
              />

              <Button
                onClick={onSend}
                disabled={!input.trim() || isPending}
                size="icon"
                className={cn(
                  "h-12 w-12 rounded-2xl transition-all duration-500",
                  input.trim()
                    ? "bg-[#002045] hover:bg-[#1a365d] text-white shadow-lg shadow-[#002045]/20"
                    : "bg-[#eff4ff] text-[#c4c6cf]"
                )}
              >
                <Send className="w-5 h-5" />
              </Button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};
