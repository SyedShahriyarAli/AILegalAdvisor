import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, LogIn, Scale, AlertCircle, Shield } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { authService } from '@/lib/authService';
import { APP_BASE } from '@/lib/appPaths';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    const result = await authService.login(email, password);
    if (result.success) {
      navigate(APP_BASE);
    } else {
      setError(result.error || 'Login failed');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f9ff] flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Ambient blobs */}
      <div className="absolute -top-[20%] -right-[15%] w-[50rem] h-[50rem] bg-gradient-to-br from-[#dce9ff] via-[#eff4ff]/60 to-transparent rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-[20%] -left-[10%] w-[40rem] h-[40rem] bg-gradient-to-tr from-[#abe5fe]/20 to-transparent rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="w-full max-w-md relative z-10"
      >
        {/* Logo + heading */}
        <div className="flex flex-col items-center mb-10 text-center">
          <div className="w-14 h-14 rounded-2xl bg-[#002045] flex items-center justify-center shadow-lg shadow-[#002045]/20 mb-5">
            <Scale className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-black text-[#002045] uppercase tracking-tight">
            Access Studio
          </h1>
          <p className="text-[10px] text-[#74777f] font-semibold uppercase tracking-[0.25em] mt-1.5">
            AI Legal Advisor Workspace
          </p>
        </div>

        {/* Card */}
        <div className="bg-white/90 border border-[#c4c6cf]/40 p-8 rounded-3xl shadow-xl shadow-[#002045]/5 backdrop-blur-sm">
          {error && (
            <div className="mb-6 p-3.5 bg-[#ffdad6] border border-[#ba1a1a]/20 rounded-xl flex items-center gap-3 text-[#93000a] text-[12px] font-semibold">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-5">
            {/* Email */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-bold text-[#43474e] uppercase tracking-widest ml-0.5">
                Email Address
              </label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Mail className="w-4.5 h-4.5 text-[#c4c6cf] group-focus-within:text-[#28657a] transition-colors" />
                </div>
                <input
                  required
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full bg-[#f8f9ff] border border-[#c4c6cf]/60 rounded-xl py-3.5 pl-11 pr-5 outline-none focus:ring-2 focus:ring-[#28657a]/20 focus:border-[#28657a] transition-all text-[14px] font-medium text-[#0b1c30] placeholder:text-[#c4c6cf]"
                  placeholder="name@firm.com"
                />
              </div>
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center ml-0.5">
                <label className="text-[11px] font-bold text-[#43474e] uppercase tracking-widest">
                  Password
                </label>
                <Link
                  to="/forgot-password"
                  className="text-[10px] font-bold text-[#28657a] uppercase tracking-widest hover:text-[#002045] hover:underline underline-offset-4 transition-colors"
                >
                  Lost Key?
                </Link>
              </div>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Lock className="w-4.5 h-4.5 text-[#c4c6cf] group-focus-within:text-[#28657a] transition-colors" />
                </div>
                <input
                  required
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full bg-[#f8f9ff] border border-[#c4c6cf]/60 rounded-xl py-3.5 pl-11 pr-5 outline-none focus:ring-2 focus:ring-[#28657a]/20 focus:border-[#28657a] transition-all text-[14px] font-medium text-[#0b1c30] placeholder:text-[#c4c6cf]"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full py-6 rounded-xl bg-[#002045] hover:bg-[#1a365d] text-white font-bold uppercase tracking-[0.18em] text-[12px] shadow-lg shadow-[#002045]/20 hover:-translate-y-0.5 transition-all group"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Authenticate
                  <LogIn className="w-4 h-4 ml-3 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-[#c4c6cf]/30 text-center">
            <p className="text-[11px] text-[#74777f] font-semibold uppercase tracking-widest">
              New to the Advisor?{' '}
              <Link
                to="/register"
                className="text-[#28657a] font-bold hover:text-[#002045] hover:underline underline-offset-4 transition-colors"
              >
                Create Profile
              </Link>
            </p>
          </div>
        </div>

        <p className="text-center mt-6 text-[10px] text-[#74777f] font-semibold uppercase tracking-widest flex items-center justify-center gap-2">
          <Shield className="w-3.5 h-3.5 text-[#28657a]" />
          End-to-End Statutory Protection Enabled
        </p>
      </motion.div>
    </div>
  );
}
