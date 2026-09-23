import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, ArrowLeft, ShieldCheck, AlertCircle, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { authService } from '@/lib/authService';
import { APP_BASE } from '@/lib/appPaths';
import type { User } from '@/lib/authService';

export default function ChangeEmail() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [newEmail, setNewEmail] = useState('');
  const [confirmEmail, setConfirmEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    if (!currentUser) {
      navigate('/login');
      return;
    }
    setUser(currentUser);
  }, [navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newEmail !== confirmEmail) {
      setError("Email addresses do not match.");
      return;
    }

    if (!user) return;

    setIsLoading(true);
    const result = await authService.updateEmail(user.email, newEmail);
    if (result.success) {
      setSuccess(true);
      setTimeout(() => navigate(`${APP_BASE}/profile`), 2000);
    } else {
      setError(result.error || 'Failed to update email.');
      setIsLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="flex-1 h-full bg-background flex items-center justify-center p-6 overflow-y-auto custom-scrollbar">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md relative z-10"
      >
        <div className="bg-white border border-border p-10 rounded-[3rem] shadow-2xl shadow-slate-200/50">
          <div className="flex items-center gap-4 mb-8">
             <Link to={`${APP_BASE}/profile`} className="w-10 h-10 rounded-xl hover:bg-slate-50 flex items-center justify-center transition-colors">
                <ArrowLeft className="w-5 h-5 text-slate-400" />
             </Link>
             <h1 className="text-2xl font-black text-foreground uppercase tracking-tight">Identity Update</h1>
          </div>

          {success ? (
            <div className="py-10 text-center space-y-6">
              <div className="w-20 h-20 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-10 h-10" />
              </div>
              <h2 className="text-2xl font-black text-foreground uppercase tracking-tight">Update Success</h2>
              <p className="text-muted-foreground font-medium">Your primary identity has been updated. Redirecting to profile...</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-8">
              <div className="p-5 rounded-2xl bg-indigo-50/50 border border-indigo-100/50">
                 <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-1">Current Identifier</p>
                 <p className="text-sm font-bold text-foreground">{user.email}</p>
              </div>

              {error && (
                <div className="p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-center gap-3 text-rose-600 text-xs font-bold">
                  <AlertCircle className="w-4 h-4" />
                  {error}
                </div>
              )}

              <div className="space-y-6">
                <div className="space-y-2">
                  <label className="text-[11px] font-black text-foreground/70 uppercase tracking-widest ml-1">New Email Address</label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                      <Mail className="w-5 h-5 text-slate-300 group-focus-within:text-primary transition-colors" />
                    </div>
                    <input 
                      required
                      type="email" 
                      value={newEmail}
                      onChange={e => setNewEmail(e.target.value)}
                      className="w-full bg-slate-50 border border-border rounded-2xl py-4 pl-14 pr-6 outline-none focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all text-sm font-bold"
                      placeholder="new@firm.com"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-[11px] font-black text-foreground/70 uppercase tracking-widest ml-1">Verify New Email</label>
                  <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                      <Mail className="w-5 h-5 text-slate-300 group-focus-within:text-primary transition-colors" />
                    </div>
                    <input 
                      required
                      type="email" 
                      value={confirmEmail}
                      onChange={e => setConfirmEmail(e.target.value)}
                      className="w-full bg-slate-50 border border-border rounded-2xl py-4 pl-14 pr-6 outline-none focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all text-sm font-bold"
                      placeholder="new@firm.com"
                    />
                  </div>
                </div>
              </div>

              <Button 
                type="submit"
                disabled={isLoading}
                className="w-full py-8 rounded-[1.5rem] text-[13px] font-black uppercase tracking-[0.2em] shadow-xl shadow-primary/20 group"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    Confirm Identity Change
                    <ShieldCheck className="ml-3 w-5 h-5 group-hover:scale-110 transition-transform" />
                  </>
                )}
              </Button>
            </form>
          )}

          <p className="mt-8 text-center text-[10px] text-muted-foreground font-bold uppercase tracking-widest leading-relaxed">
            Note: Changing your email will update your <br /> global login credentials across the studio.
          </p>
        </div>
      </motion.div>
    </div>
  );
}
