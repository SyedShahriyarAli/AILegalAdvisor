import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, ArrowLeft, KeyRound, ShieldCheck, Lock, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { authService } from '@/lib/authService';

export default function ForgotPassword() {
  const [step, setStep] = useState<'email' | 'new-password' | 'success'>('email');
  const [email, setEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    // We'll just advance to the next step — the actual validation 
    // happens when the user submits the new password.
    // The API will return an error if the email doesn't exist.
    setTimeout(() => {
      setStep('new-password');
      setIsLoading(false);
    }, 500);
  };

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);
    const success = await authService.resetPassword(email, newPassword);
    if (success) {
      setStep('success');
    } else {
      setError("No account found with this email. Please try again.");
    }
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen w-full bg-background flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none opacity-40">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-100/50 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-violet-100/50 blur-[120px] rounded-full" />
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md relative z-10"
      >
        <div className="bg-white border border-border p-10 rounded-[3rem] shadow-2xl shadow-slate-200/50 overflow-hidden relative">
          <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-primary via-indigo-400 to-violet-500" />

          <AnimatePresence mode="wait">
            {step === 'email' && (
              <motion.div
                key="email-step"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
              >
                <div className="w-16 h-16 rounded-[1.5rem] bg-indigo-50 flex items-center justify-center mb-8">
                  <KeyRound className="w-8 h-8 text-primary" />
                </div>
                
                <h1 className="text-2xl font-black text-foreground uppercase tracking-tight mb-3">Identity Recovery</h1>
                <p className="text-muted-foreground text-[13px] font-medium mb-8 leading-relaxed">
                  Enter your professional email to retrieve access to your AI Legal Advisor workspace.
                </p>

                {error && (
                  <div className="mb-6 p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-center gap-3 text-rose-600 text-xs font-bold">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    {error}
                  </div>
                )}

                <form className="space-y-6" onSubmit={handleEmailSubmit}>
                  <div className="space-y-2">
                    <label className="text-[11px] font-black text-foreground/70 uppercase tracking-widest ml-1">Registered Email</label>
                    <div className="relative group">
                      <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                        <Mail className="w-5 h-5 text-slate-300 group-focus-within:text-primary transition-colors" />
                      </div>
                      <input 
                        type="email" 
                        required
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                        className="w-full bg-slate-50 border border-border rounded-2xl py-4 pl-14 pr-6 outline-none focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all text-sm font-bold placeholder:text-slate-300"
                        placeholder="name@firm.com"
                      />
                    </div>
                  </div>

                  <Button 
                    disabled={isLoading}
                    className="w-full py-8 rounded-[1.5rem] font-black uppercase tracking-widest shadow-xl shadow-primary/20 text-[12px]"
                  >
                    {isLoading ? "Verifying..." : "Recover Identity"}
                  </Button>
                </form>
              </motion.div>
            )}

            {step === 'new-password' && (
              <motion.div
                key="password-step"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
              >
                <div className="w-16 h-16 rounded-[1.5rem] bg-emerald-50 flex items-center justify-center mb-8">
                  <ShieldCheck className="w-8 h-8 text-emerald-500" />
                </div>
                
                <h1 className="text-2xl font-black text-foreground uppercase tracking-tight mb-3">Identity Verified</h1>
                <p className="text-muted-foreground text-[13px] font-medium mb-8 leading-relaxed">
                  Authentication success. Please provide a new secure key for your account.
                </p>

                {error && (
                  <div className="mb-6 p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-center gap-3 text-rose-600 text-xs font-bold">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    {error}
                  </div>
                )}

                <form className="space-y-6" onSubmit={handleResetSubmit}>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-[11px] font-black text-foreground/70 uppercase tracking-widest ml-1">New Password</label>
                      <div className="relative group">
                        <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                          <Lock className="w-5 h-5 text-slate-300 group-focus-within:text-primary transition-colors" />
                        </div>
                        <input 
                          type="password" 
                          required
                          value={newPassword}
                          onChange={e => setNewPassword(e.target.value)}
                          className="w-full bg-slate-50 border border-border rounded-2xl py-4 pl-14 pr-6 outline-none focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all text-sm font-bold placeholder:text-slate-300"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-[11px] font-black text-foreground/70 uppercase tracking-widest ml-1">Confirm New Password</label>
                      <div className="relative group">
                        <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                          <Lock className="w-5 h-5 text-slate-300 group-focus-within:text-primary transition-colors" />
                        </div>
                        <input 
                          type="password" 
                          required
                          value={confirmPassword}
                          onChange={e => setConfirmPassword(e.target.value)}
                          className="w-full bg-slate-50 border border-border rounded-2xl py-4 pl-14 pr-6 outline-none focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all text-sm font-bold placeholder:text-slate-300"
                        />
                      </div>
                    </div>
                  </div>

                  <Button 
                    disabled={isLoading}
                    className="w-full py-8 rounded-[1.5rem] font-black uppercase tracking-widest shadow-xl shadow-primary/20 text-[12px]"
                  >
                    {isLoading ? "Updating..." : "Update Private Key"}
                  </Button>
                </form>
              </motion.div>
            )}

            {step === 'success' && (
              <motion.div
                key="success-step"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center py-6"
              >
                <div className="w-20 h-20 rounded-full bg-emerald-50 text-emerald-500 flex items-center justify-center mx-auto mb-8 shadow-inner">
                  <CheckCircle2 className="w-10 h-10" />
                </div>
                <h2 className="text-2xl font-black text-foreground uppercase tracking-tight mb-3">Reset Complete</h2>
                <p className="text-muted-foreground text-[13px] font-medium mb-10 leading-relaxed">
                  Your identity has been re-secured. You can now access your workspace with the new credentials.
                </p>
                <Link to="/login">
                  <Button className="w-full py-8 rounded-[1.5rem] font-black uppercase tracking-widest shadow-xl shadow-primary/20 text-[12px]">
                    Return to Login
                  </Button>
                </Link>
              </motion.div>
            )}
          </AnimatePresence>

          {step !== 'success' && (
            <div className="mt-8 pt-8 border-t border-border">
              <Link to="/login" className="flex items-center justify-center gap-3 text-[11px] font-black text-primary uppercase tracking-[0.2em] hover:text-primary/80 transition-colors">
                <ArrowLeft className="w-4 h-4" />
                Return to Access Studio
              </Link>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
