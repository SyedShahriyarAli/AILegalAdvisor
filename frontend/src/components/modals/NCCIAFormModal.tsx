
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldCheck,
  X,
  ExternalLink,
  User,
  CreditCard,
  Phone,
  Mail,
  MapPin,
  Building2,
  AlertCircle,
  CheckCircle2,
  Lock,
  Sparkles
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { authService } from '@/lib/authService';
import { apiUrl } from '@/lib/apiBase';

interface NCCIAFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  analysisData: any;
  narrative: string;
}

export const NCCIAFormModal: React.FC<NCCIAFormModalProps> = ({
  isOpen,
  onClose,
  analysisData: _analysisData,
  narrative
}) => {
  const [formData, setFormData] = useState({
    fullName: '',
    cnic: '',
    gender: '',
    mobileNumber: '',
    emailAddress: '',
    occupation: '',
    postalAddress: '',
    city: '',
    crimeCategory: 'Cybercrime (Hacking, Electronic Frauds, Cyber Stalking, Online Defamation, Hate Speech and Other)',
    crimeDetails: ''
  });
  const [isGenerating, setIsGenerating] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [showSmartPasteInfo, setShowSmartPasteInfo] = useState(false);

  const user = authService.getCurrentUser();

  useEffect(() => {
    if (isOpen) {
      setFormData(prev => ({
        ...prev,
        fullName: user?.name || '',
        emailAddress: user?.email || '',
        crimeDetails: prev.crimeDetails || narrative.substring(0, 3400)
      }));
    }
  }, [isOpen, narrative, user]);

  const generateCrimeDetails = async () => {
    setIsGenerating(true);
    setGenerationError(null);
    try {
      const response = await fetch(apiUrl('/api/draft/nccia'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          narrative: narrative,
          template_id: 'nccia'
        })
      });
      const data = await response.json();
      if (data.success) {
        setFormData(prev => ({ ...prev, crimeDetails: data.body_markdown }));
      } else {
        setGenerationError(data.error || 'Backend couldnt generate response');
      }
    } catch (error) {
      console.error("LLM Generation failed", error);
      setGenerationError('Backend connection failed');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    // Copy to clipboard with structured payload for smart paste
    const smartPayload = {
      fullName: formData.fullName,
      cnic: formData.cnic,
      mobile: formData.mobileNumber,
      email: formData.emailAddress,
      city: formData.city,
      category: formData.crimeCategory,
      details: formData.crimeDetails
    };
    navigator.clipboard.writeText(JSON.stringify(smartPayload));

    setTimeout(() => {
      setIsSubmitting(false);
      setShowSmartPasteInfo(true);

      setTimeout(() => {
        window.open('https://complaint.nccia.gov.pk/', '_blank');
        onClose();
        setShowSmartPasteInfo(false);
      }, 4000);
    }, 1500);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 md:p-8 overflow-y-auto">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-slate-950/40 backdrop-blur-md"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative w-full max-w-4xl bg-white rounded-[2rem] shadow-2xl border border-border overflow-hidden flex flex-col max-h-[90vh]"
          >
            {/* Header */}
            <div className="sticky top-0 z-20 bg-white border-b border-border p-6 sm:p-8 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-200">
                  <ShieldCheck className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-black text-foreground uppercase tracking-tight">Draft NCCIA Complaint</h2>
                  <p className="text-[9px] text-muted-foreground font-bold uppercase tracking-widest mt-0.5">Pre-filing Protocol Alpha-01</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="rounded-xl hover:bg-slate-100"
              >
                <X className="w-5 h-5 text-slate-400" />
              </Button>
            </div>

            {/* Form Content */}
            <div className="flex-1 overflow-y-auto p-6 sm:p-8 custom-scrollbar">
              {isSuccess ? (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="h-full flex flex-col items-center justify-center text-center space-y-6 py-20"
                >
                  <div className="w-24 h-24 rounded-full bg-emerald-50 flex items-center justify-center mb-4">
                    <CheckCircle2 className="w-12 h-12 text-emerald-500" />
                  </div>
                  <h3 className="text-2xl font-black text-foreground uppercase tracking-tight">Draft Prepared Successfully</h3>
                  <p className="text-slate-500 max-w-md mx-auto font-medium">
                    Your details have been compiled. We are now redirecting you to the official NCCIA portal to finalize the submission.
                  </p>
                  <div className="flex items-center gap-2 text-primary font-black uppercase tracking-widest text-xs">
                    <span className="w-2 h-2 bg-primary rounded-full animate-ping" />
                    Redirecting in 2 seconds...
                  </div>
                </motion.div>
              ) : showSmartPasteInfo ? (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="flex-1 flex flex-col items-center justify-center p-12 text-center space-y-8"
                >
                  <div className="w-24 h-24 rounded-[2.5rem] bg-indigo-50 flex items-center justify-center shadow-2xl shadow-indigo-100/50 animate-bounce">
                    <Sparkles className="w-12 h-12 text-primary" />
                  </div>
                  <div className="space-y-4">
                    <h3 className="text-3xl font-black text-foreground uppercase tracking-tight">Smart Paste Ready</h3>
                    <p className="text-muted-foreground max-w-sm mx-auto text-sm font-medium leading-relaxed">
                      We've copied all fields to your clipboard. Once the NCCIA portal opens, press <kbd className="bg-slate-100 px-2 py-1 rounded text-primary border border-border">Ctrl+V</kbd> to automatically fill the entire form.
                    </p>
                  </div>
                  <div className="flex items-center gap-3 bg-slate-50 px-6 py-3 rounded-2xl border border-border">
                    <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Redirecting to Statutory Portal...</span>
                  </div>
                </motion.div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-10">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Personal Info Section */}
                    <div className="space-y-6">
                      <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                        <User className="w-4 h-4 text-primary" />
                        <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Personal Identification</h4>
                      </div>

                      <div className="space-y-4">
                        <div className="space-y-2">
                          <label className="text-[10px] font-black uppercase tracking-widest text-foreground/70 ml-1">Full Name *</label>
                          <div className="relative">
                            <User className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300" />
                            <input
                              required
                              name="fullName"
                              value={formData.fullName}
                              onChange={handleInputChange}
                              className="w-full h-12 bg-slate-50/50 border border-border rounded-xl pl-12 pr-4 text-sm font-bold focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all"
                              placeholder="As per CNIC"
                            />
                          </div>
                        </div>

                        <div className="space-y-2">
                          <label className="text-[10px] font-black uppercase tracking-widest text-foreground/70 ml-1">CNIC Number *</label>
                          <div className="relative">
                            <CreditCard className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300" />
                            <input
                              required
                              name="cnic"
                              value={formData.cnic}
                              onChange={handleInputChange}
                              className="w-full h-12 bg-slate-50/50 border border-border rounded-xl pl-12 pr-4 text-sm font-bold focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all"
                              placeholder="e.g. 42101-1234567-1"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <label className="text-[10px] font-black uppercase tracking-widest text-foreground/70 ml-1">Gender *</label>
                            <select
                              required
                              name="gender"
                              value={formData.gender}
                              onChange={handleInputChange}
                              className="w-full h-12 bg-slate-50/50 border border-border rounded-xl px-4 text-sm font-bold focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all appearance-none cursor-pointer"
                            >
                              <option value="">Select</option>
                              <option value="Male">Male</option>
                              <option value="Female">Female</option>
                              <option value="Other">Other</option>
                            </select>
                          </div>
                          <div className="space-y-2">
                            <label className="text-[10px] font-black uppercase tracking-widest text-foreground/70 ml-1">Mobile *</label>
                            <div className="relative">
                              <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300" />
                              <input
                                required
                                name="mobileNumber"
                                value={formData.mobileNumber}
                                onChange={handleInputChange}
                                className="w-full h-12 bg-slate-50/50 border border-border rounded-xl pl-12 pr-4 text-sm font-bold focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all"
                                placeholder="03xx-xxxxxxx"
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Contact & Professional Section */}
                    <div className="space-y-6">
                      <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                        <Mail className="w-4 h-4 text-primary" />
                        <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Contact & Professional</h4>
                      </div>

                      <div className="space-y-4">
                        <div className="space-y-2">
                          <label className="text-[10px] font-black uppercase tracking-widest text-foreground/70 ml-1">Email Address</label>
                          <div className="relative">
                            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300" />
                            <input
                              name="emailAddress"
                              value={formData.emailAddress}
                              onChange={handleInputChange}
                              className="w-full h-12 bg-slate-50/50 border border-border rounded-xl pl-12 pr-4 text-sm font-bold focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all"
                              placeholder="name@example.com"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <label className="text-[10px] font-black uppercase tracking-widest text-foreground/70 ml-1">Occupation</label>
                            <div className="relative">
                              <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300" />
                              <input
                                name="occupation"
                                value={formData.occupation}
                                onChange={handleInputChange}
                                className="w-full h-12 bg-slate-50/50 border border-border rounded-xl pl-12 pr-4 text-sm font-bold focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all"
                                placeholder="e.g. Lawyer"
                              />
                            </div>
                          </div>
                          <div className="space-y-2">
                            <label className="text-[10px] font-black uppercase tracking-widest text-foreground/70 ml-1">City *</label>
                            <div className="relative">
                              <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300" />
                              <input
                                required
                                name="city"
                                value={formData.city}
                                onChange={handleInputChange}
                                className="w-full h-12 bg-slate-50/50 border border-border rounded-xl pl-12 pr-4 text-sm font-bold focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all"
                                placeholder="e.g. Islamabad"
                              />
                            </div>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <label className="text-[10px] font-black uppercase tracking-widest text-foreground/70 ml-1">Postal Address</label>
                          <textarea
                            name="postalAddress"
                            value={formData.postalAddress}
                            onChange={handleInputChange}
                            rows={2}
                            className="w-full bg-slate-50/50 border border-border rounded-xl p-4 text-sm font-bold focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all resize-none"
                            placeholder="Current residential or office address"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Crime Details Section */}
                  <div className="space-y-6">
                    <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
                      <AlertCircle className="w-4 h-4 text-rose-500" />
                      <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Incident Specifications</h4>
                    </div>

                    <div className="space-y-4">
                      <div className="space-y-2">
                        <select
                          required
                          name="crimeCategory"
                          value={formData.crimeCategory}
                          onChange={handleInputChange}
                          className="w-full h-12 bg-slate-50/50 border border-border rounded-xl px-4 text-xs font-bold focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all appearance-none cursor-pointer"
                        >
                          <option value="Cybercrime (Hacking, Electronic Frauds, Cyber Stalking, Online Defamation, Hate Speech and Other)">Cybercrime (Hacking, Electronic Frauds, Cyber Stalking, Online Defamation, Hate Speech and Other)</option>
                        </select>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between ml-1">
                          <label className="text-[10px] font-black uppercase tracking-widest text-foreground/70">Crime Details *</label>
                          <div className="flex items-center gap-2">
                            <Button
                              type="button"
                              onClick={generateCrimeDetails}
                              disabled={isGenerating}
                              variant="ghost"
                              className="h-6 px-2 text-[9px] font-black uppercase tracking-widest text-primary hover:bg-primary/10"
                            >
                              {isGenerating ? 'Drafting...' : generationError ? generationError : 'Generate with LLM'}
                            </Button>
                            <span className={cn(
                              "text-[9px] font-black uppercase tracking-widest",
                              formData.crimeDetails.length > 3000 ? "text-rose-500" : "text-slate-400"
                            )}>
                              {formData.crimeDetails.length} / 3400
                            </span>
                          </div>
                        </div>
                        <textarea
                          required
                          name="crimeDetails"
                          value={formData.crimeDetails}
                          onChange={handleInputChange}
                          maxLength={3400}
                          rows={6}
                          className="w-full bg-slate-50/50 border border-border rounded-[1.5rem] p-6 text-sm font-medium leading-relaxed focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all resize-none"
                          placeholder="Provide a chronological account of the incident..."
                        />
                      </div>
                    </div>
                  </div>

                  {/* Footer / Affirmation */}
                  <div className="p-8 rounded-[2rem] bg-slate-950 text-white relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-transparent pointer-events-none" />
                    <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-6">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center backdrop-blur-md shrink-0">
                          <Lock className="w-5 h-5 text-indigo-400" />
                        </div>
                        <p className="text-[10px] font-medium text-slate-300 max-w-sm leading-relaxed">
                          By proceeding, I affirm that all information provided is correct to the best of my knowledge. This portal serves as a drafting aid for the official NCCIA system.
                        </p>
                      </div>
                      <Button
                        type="submit"
                        disabled={isSubmitting}
                        className="w-full md:w-auto h-14 px-10 bg-white text-slate-900 hover:bg-slate-100 rounded-xl font-black uppercase tracking-widest shadow-xl shadow-white/5 disabled:opacity-50"
                      >
                        {isSubmitting ? (
                          <div className="flex items-center gap-3">
                            <div className="w-4 h-4 border-2 border-slate-900/30 border-t-slate-900 rounded-full animate-spin" />
                            Finalizing...
                          </div>
                        ) : (
                          <>
                            Generate & Open Portal
                            <ExternalLink className="ml-3 w-4 h-4" />
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </form>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

function cn(...classes: any[]) {
  return classes.filter(Boolean).join(' ');
}
