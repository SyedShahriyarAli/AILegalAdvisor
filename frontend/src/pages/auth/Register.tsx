import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, User, Building, ArrowRight, Scale, AlertCircle, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { authService } from '@/lib/authService';

export default function Register() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    firmName: ''
  });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);

    const result = await authService.register({
      name: formData.name,
      email: formData.email,
      password: formData.password,
      organization: formData.firmName,
    });

    if (result.success) {
      setSuccess(true);
      setTimeout(() => navigate('/login'), 2000);
    } else {
      setError(result.error || 'Registration failed');
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  /* Shared input class */
  const inputCls =
    'w-full bg-[#f8f9ff] border border-[#c4c6cf]/60 rounded-xl py-3.5 pl-11 pr-5 outline-none focus:ring-2 focus:ring-[#28657a]/20 focus:border-[#28657a] transition-all text-[14px] font-medium text-[#0b1c30] placeholder:text-[#c4c6cf]';

  return (
    <div className="min-h-screen bg-[#f8f9ff] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Ambient blobs */}
      <div className="absolute -top-[20%] -right-[10%] w-[50rem] h-[50rem] bg-gradient-to-br from-[#dce9ff] via-[#eff4ff]/60 to-transparent rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-[20%] -left-[10%] w-[45rem] h-[45rem] bg-gradient-to-tr from-[#abe5fe]/20 to-transparent rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.45 }}
        className="w-full max-w-xl relative z-10"
      >
        {/* Logo + heading */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[#002045] shadow-lg shadow-[#002045]/20 mb-5">
            <Scale className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-black text-[#002045] uppercase tracking-tight">
            User Registration
          </h1>
          <p className="text-[10px] text-[#74777f] font-semibold uppercase tracking-[0.25em] mt-1.5">
            Create your professional advisor profile
          </p>
        </div>

        {/* Card */}
        <div className="bg-white/90 border border-[#c4c6cf]/40 p-8 rounded-3xl shadow-xl shadow-[#002045]/5 backdrop-blur-sm">
          {success ? (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="py-12 text-center space-y-5"
            >
              <div className="w-20 h-20 bg-[#eff4ff] text-[#28657a] rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-10 h-10" />
              </div>
              <h2 className="text-2xl font-black text-[#002045] uppercase tracking-tight">
                Account Created!
              </h2>
              <p className="text-[#43474e] font-medium text-[14px]">
                Redirecting you to the secure login terminal…
              </p>
            </motion.div>
          ) : (
            <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {error && (
                <div className="md:col-span-2 p-3.5 bg-[#ffdad6] border border-[#ba1a1a]/20 rounded-xl flex items-center gap-3 text-[#93000a] text-[12px] font-semibold">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {error}
                </div>
              )}

              {/* Full name */}
              <div className="space-y-1.5 col-span-1">
                <label className="text-[11px] font-bold text-[#43474e] uppercase tracking-widest ml-0.5">
                  Full Legal Name
                </label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <User className="w-4.5 h-4.5 text-[#c4c6cf] group-focus-within:text-[#28657a] transition-colors" />
                  </div>
                  <input
                    required
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    className={inputCls}
                    placeholder="Adv. Ahmed Khan"
                  />
                </div>
              </div>

              {/* Organization */}
              <div className="space-y-1.5 col-span-1">
                <label className="text-[11px] font-bold text-[#43474e] uppercase tracking-widest ml-0.5">
                  Organization / Role
                </label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Building className="w-4.5 h-4.5 text-[#c4c6cf] group-focus-within:text-[#28657a] transition-colors" />
                  </div>
                  <input
                    required
                    name="firmName"
                    value={formData.firmName}
                    onChange={handleChange}
                    className={inputCls}
                    placeholder="e.g. Legal Consultant"
                  />
                </div>
              </div>

              {/* Email */}
              <div className="space-y-1.5 md:col-span-2">
                <label className="text-[11px] font-bold text-[#43474e] uppercase tracking-widest ml-0.5">
                  Professional Email
                </label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Mail className="w-4.5 h-4.5 text-[#c4c6cf] group-focus-within:text-[#28657a] transition-colors" />
                  </div>
                  <input
                    required
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    className={inputCls}
                    placeholder="ahmed@firm.com"
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-1.5 col-span-1">
                <label className="text-[11px] font-bold text-[#43474e] uppercase tracking-widest ml-0.5">
                  Secure Password
                </label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Lock className="w-4.5 h-4.5 text-[#c4c6cf] group-focus-within:text-[#28657a] transition-colors" />
                  </div>
                  <input
                    required
                    type="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    className={inputCls}
                    placeholder="••••••••"
                  />
                </div>
              </div>

              {/* Confirm password */}
              <div className="space-y-1.5 col-span-1">
                <label className="text-[11px] font-bold text-[#43474e] uppercase tracking-widest ml-0.5">
                  Verify Identity
                </label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Lock className="w-4.5 h-4.5 text-[#c4c6cf] group-focus-within:text-[#28657a] transition-colors" />
                  </div>
                  <input
                    required
                    type="password"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    className={inputCls}
                    placeholder="••••••••"
                  />
                </div>
              </div>

              {/* Submit */}
              <div className="md:col-span-2 pt-2">
                <Button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-6 rounded-xl bg-[#002045] hover:bg-[#1a365d] text-white font-bold uppercase tracking-[0.18em] text-[12px] shadow-lg shadow-[#002045]/20 hover:-translate-y-0.5 transition-all group"
                >
                  {isLoading ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      Complete Registration
                      <ArrowRight className="ml-3 w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </>
                  )}
                </Button>
              </div>
            </form>
          )}

          {!success && (
            <div className="mt-6 pt-6 border-t border-[#c4c6cf]/30 text-center">
              <p className="text-[11px] text-[#74777f] font-semibold uppercase tracking-widest">
                Already registered?{' '}
                <Link
                  to="/login"
                  className="text-[#28657a] font-bold hover:text-[#002045] hover:underline underline-offset-4 transition-colors"
                >
                  Return to Access Studio
                </Link>
              </p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
