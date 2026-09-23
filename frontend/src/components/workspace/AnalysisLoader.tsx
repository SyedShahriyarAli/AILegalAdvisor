
import React, { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Database, Scale, FileCheck, Cpu, CheckCircle2, Sparkles } from 'lucide-react';

const STEPS = [
  { id: 'rag', label: 'Neural Context Initialization', sublabel: 'Embedding case vectors into RAG index', icon: Cpu },
  { id: 'statutes', label: 'Statutory Retrieval', sublabel: 'Matching PECA 2016/2025 sections', icon: Database },
  { id: 'audit', label: 'Procedural Evidence Audit', sublabel: 'Cross-referencing evidence integrity', icon: FileCheck },
  { id: 'merit', label: 'Strategic Merit Projection', sublabel: 'Generating advisory recommendations', icon: Scale },
];

const RING_C = 2 * Math.PI * 44;

export const AnalysisLoader: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentStep((prev) => (prev < STEPS.length - 1 ? prev + 1 : prev));
    }, 2500);
    return () => clearInterval(timer);
  }, []);

  const progress = useMemo(() => (currentStep + 1) / STEPS.length, [currentStep]);
  const ActiveIcon = STEPS[currentStep]?.icon ?? Sparkles;

  return (
    <div className="w-full space-y-8 py-6">

      <div className="flex flex-col items-center text-center gap-2">
        <div className="inline-flex items-center gap-2 rounded-full border border-[#28657a]/30 bg-[#eff4ff] px-4 py-1.5 text-[10px] font-black uppercase tracking-[0.25em] text-[#28657a]">
          <motion.span
            animate={{ opacity: [1, 0.35, 1] }}
            transition={{ duration: 1.4, repeat: Infinity }}
            className="h-1.5 w-1.5 rounded-full bg-[#28657a]"
          />
          Statutory analysis in progress
        </div>
        <h3 className="bg-gradient-to-r from-[#002045] to-[#28657a] bg-clip-text text-2xl font-black uppercase tracking-tight text-transparent">
          Analyzing your query
        </h3>
        <p className="text-[11px] font-medium uppercase tracking-widest text-[#74777f] opacity-80">
          Synthesizing statutes, precedents, and case facts…
        </p>
      </div>

      <div className="flex w-full flex-col gap-6 lg:flex-row">

        <div className="relative min-h-[320px] flex-1 overflow-hidden rounded-2xl border border-[#c4c6cf]/40 bg-[#f8f9ff] shadow-[0_20px_50px_-12px_rgba(0,32,69,0.12)] lg:min-h-[420px]">
          <div className="pointer-events-none absolute left-[-10%] top-[-10%] h-[50%] w-[50%] rounded-full bg-[#adc7f7]/10 blur-[80px]" />
          <div className="pointer-events-none absolute bottom-[-10%] right-[-10%] h-[50%] w-[50%] rounded-full bg-[#28657a]/10 blur-[80px]" />

          <div className="absolute left-3 top-3 z-10 flex items-center gap-3 rounded-xl border border-[#c4c6cf]/30 bg-white/80 px-4 py-2 shadow-sm backdrop-blur-xl">
            <div>
              <p className="text-[9px] font-black uppercase tracking-[0.15em] text-[#74777f]">Current stage</p>
              <p className="text-[11px] font-bold text-[#002045]">{STEPS[currentStep]?.label}</p>
            </div>
            <div className="h-7 w-px bg-[#c4c6cf]/40" />
            <div className="flex items-center gap-1.5 text-[#28657a]">
              <motion.div
                animate={{ opacity: [1, 0.25, 1] }}
                transition={{ duration: 1.2, repeat: Infinity }}
                className="h-2 w-2 rounded-full bg-[#28657a]"
              />
              <span className="text-[10px] font-bold">Live</span>
            </div>
          </div>

          <div className="absolute right-3 top-3 z-10 rounded-xl border border-[#c4c6cf]/30 bg-white/80 px-3 py-1.5 shadow-sm backdrop-blur-xl">
            <p className="text-[9px] font-black uppercase tracking-wider text-[#002045]">
              Phase {currentStep + 1} / {STEPS.length}
            </p>
          </div>

          <div className="absolute inset-0 flex flex-col items-center justify-center pt-16 pb-14">
            <div className="relative flex h-[200px] w-[200px] items-center justify-center md:h-[220px] md:w-[220px]">
              <motion.div
                className="absolute inset-0 rounded-full border border-dashed border-[#28657a]/20"
                animate={{ rotate: 360 }}
                transition={{ duration: 28, repeat: Infinity, ease: 'linear' }}
              />
              <motion.div
                className="absolute inset-2 rounded-full border border-[#dce9ff]/80"
                animate={{ scale: [1, 1.04, 1], opacity: [0.6, 0.9, 0.6] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              />
              <svg className="absolute inset-0 h-full w-full -rotate-90" viewBox="0 0 100 100" aria-hidden>
                <circle cx="50" cy="50" r="44" fill="none" stroke="#eff4ff" strokeWidth="5" />
                <motion.circle
                  cx="50"
                  cy="50"
                  r="44"
                  fill="none"
                  stroke="#28657a"
                  strokeWidth="5"
                  strokeLinecap="round"
                  strokeDasharray={RING_C}
                  initial={false}
                  animate={{ strokeDashoffset: RING_C * (1 - progress) }}
                  transition={{ duration: 0.55, ease: 'easeOut' }}
                />
              </svg>
              <div className="relative flex h-[88px] w-[88px] items-center justify-center rounded-2xl bg-gradient-to-br from-[#002045] to-[#1a365d] shadow-[0_12px_40px_-8px_rgba(0,32,69,0.45)]">
                <ActiveIcon className="h-9 w-9 text-white/95" strokeWidth={1.75} />
              </div>
              <motion.div
                className="pointer-events-none absolute inset-0 rounded-full border border-[#28657a]/25"
                animate={{ scale: [1, 1.12, 1], opacity: [0.35, 0, 0.35] }}
                transition={{ duration: 2.2, repeat: Infinity, ease: 'easeOut' }}
              />
            </div>
            <p className="mt-6 max-w-xs px-4 text-center text-[11px] font-medium leading-relaxed text-[#43474e]">
              {STEPS[currentStep]?.sublabel}
            </p>
          </div>

          <div className="absolute bottom-5 left-0 right-0 flex h-9 items-end justify-center gap-1 px-10">
            {Array.from({ length: 14 }).map((_, i) => (
              <motion.div
                key={i}
                className="w-1 rounded-full bg-[#28657a]/35"
                animate={{ height: [6, 22, 6] }}
                transition={{
                  duration: 1.15 + i * 0.04,
                  repeat: Infinity,
                  ease: 'easeInOut',
                  delay: i * 0.06,
                }}
              />
            ))}
          </div>
        </div>

        <div className="flex w-full shrink-0 flex-col gap-3 lg:w-64">
          <p className="px-1 text-[9px] font-black uppercase tracking-[0.2em] text-[#74777f]">Analysis pipeline</p>

          {STEPS.map((step, index) => {
            const isActive = index === currentStep;
            const isCompleted = index < currentStep;
            const Icon = step.icon;

            return (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.08 }}
                className={`relative flex items-start gap-3 rounded-xl border p-3.5 backdrop-blur-md transition-all duration-500 ${isActive
                  ? 'scale-[1.02] border-[#28657a]/40 bg-gradient-to-br from-[#eff4ff] to-[#dce9ff] shadow-[0_8px_20px_-6px_rgba(40,101,122,0.15)]'
                  : isCompleted
                    ? 'border-[#002045]/15 bg-white/80 shadow-sm'
                    : 'border-[#c4c6cf]/20 bg-white/30 opacity-45'
                  }`}
              >
                {isActive && (
                  <motion.div
                    initial={{ width: '0%' }}
                    animate={{ width: '100%' }}
                    transition={{ duration: 2.5, ease: 'linear' }}
                    className="absolute bottom-0 left-0 h-0.5 rounded-b-xl bg-[#28657a]/40"
                  />
                )}

                {index < STEPS.length - 1 && (
                  <div className="absolute left-[1.6rem] top-full h-3 w-px bg-[#c4c6cf]/40" />
                )}

                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-all duration-500 ${isActive
                    ? 'bg-[#28657a]/15 text-[#28657a]'
                    : isCompleted
                      ? 'bg-[#002045]/10 text-[#002045]'
                      : 'bg-[#c4c6cf]/20 text-[#74777f]'
                    }`}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="h-4 w-4 text-[#002045]" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <p
                    className={`mb-0.5 text-[10px] font-black uppercase tracking-widest ${isActive ? 'text-[#28657a]' : isCompleted ? 'text-[#002045]' : 'text-[#74777f]'
                      }`}
                  >
                    Step 0{index + 1}
                  </p>
                  <p className="text-[11px] font-bold leading-tight text-[#0b1c30]">{step.label}</p>
                  {isActive && (
                    <motion.p
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="mt-1 text-[9px] font-medium leading-relaxed text-[#74777f]"
                    >
                      {step.sublabel}
                    </motion.p>
                  )}
                </div>

                {isActive && (
                  <motion.div
                    animate={{ scale: [1, 1.5, 1], opacity: [0.7, 1, 0.7] }}
                    transition={{ duration: 1.2, repeat: Infinity }}
                    className="mt-1 h-2 w-2 shrink-0 rounded-full bg-[#28657a] shadow-[0_0_8px_rgba(40,101,122,0.6)]"
                  />
                )}
              </motion.div>
            );
          })}

          <div className="mt-auto rounded-xl border border-[#c4c6cf]/30 bg-[#dce9ff]/40 p-3">
            <p className="text-[9px] font-black uppercase tracking-[0.15em] text-[#002045]">Statutory lock</p>
            <p className="mt-0.5 text-[8px] font-medium text-[#74777f]">PECA 2016/2025 • NCCIA compliant</p>
          </div>
        </div>
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-[#c4c6cf]/30 bg-white p-6 shadow-[0_4px_24px_-8px_rgba(0,32,69,0.06)]">
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 animate-pulse rounded-lg bg-[#e5eeff]" />
            <div className="space-y-1.5">
              <div className="h-2.5 w-28 animate-pulse rounded-full bg-[#dce9ff]" />
              <div className="h-2 w-20 animate-pulse rounded-full bg-[#eff4ff]" />
            </div>
          </div>
          <div className="h-7 w-20 animate-pulse rounded-full bg-[#eff4ff]" />
        </div>
        <div className="space-y-3">
          {[80, 65, 90].map((w, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="h-3 w-3 shrink-0 animate-pulse rounded-full bg-[#e5eeff]" />
              <div className="h-2 animate-pulse rounded-full bg-[#eff4ff]" style={{ width: `${w}%` }} />
            </div>
          ))}
        </div>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-white to-transparent" />
      </div>
    </div>
  );
};
