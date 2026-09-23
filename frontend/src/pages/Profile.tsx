import { useState, useEffect } from 'react';
import { 
  User, 
  Mail, 
  Building, 
  FileText, 
  MessageSquare, 
  Settings, 
  LogOut,
  Calendar,
  Scale,
  ExternalLink,
  X,
  ShieldCheck,
  Zap,
  Globe,
  Database
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { authService } from '@/lib/authService';
import { APP_BASE } from '@/lib/appPaths';
import type { User as UserType, UserData } from '@/lib/authService';

export default function Profile() {
  const navigate = useNavigate();
  const [user, setUser] = useState<UserType | null>(null);
  const [userData, setUserData] = useState<UserData>({
    sources: [],
    chatHistory: [],
    caseAnalyzerSessions: [],
  });
  const [showPaymentModal, setShowPaymentModal] = useState(false);

  useEffect(() => {
    let mounted = true;
    const run = async () => {
      const currentUser = authService.getCurrentUser();
      if (!currentUser) {
        navigate('/login');
        return;
      }
      setUser(currentUser);
      const data = await authService.getUserData(currentUser.id);
      if (mounted) {
        setUserData(data);
      }
    };
    run();
    return () => {
      mounted = false;
    };
  }, [navigate]);

  const handleLogout = async () => {
    await authService.logout();
    navigate('/login');
  };

  if (!user) return null;

  return (
    <div className="flex-1 h-full bg-[#f8f9ff] p-6 overflow-y-auto custom-scrollbar relative">
      {/* ── Background Gradients ── */}
      <div className="absolute inset-0 pointer-events-none opacity-40">
        <div className="absolute top-0 right-0 w-[50%] h-[50%] bg-gradient-to-br from-[#dce9ff] to-transparent blur-[120px]" />
        <div className="absolute bottom-0 left-0 w-[50%] h-[50%] bg-gradient-to-tr from-[#eff4ff] to-transparent blur-[120px]" />
      </div>

      <div className="max-w-4xl mx-auto space-y-6 relative z-10">
        
        {/* Profile Header */}
        <div className="bg-white border border-[#c4c6cf]/30 p-6 rounded-[1.5rem] shadow-[0_8px_30px_rgb(0,0,0,0.04)] relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-[#eff4ff] blur-[80px] rounded-full -mr-24 -mt-24" />
          
          <div className="flex flex-col md:flex-row items-center gap-6 relative z-10">
            <div className="w-20 h-20 rounded-[1.25rem] bg-[#002045] flex items-center justify-center shadow-2xl shadow-[#002045]/20">
              <User className="w-10 h-10 text-white" />
            </div>
            
            <div className="flex-1 text-center md:text-left space-y-1">
              <div className="flex flex-col md:flex-row md:items-center gap-3">
                <h1 className="text-xl font-bold text-[#002045] tracking-tight">{user.name}</h1>
                <div className="flex items-center gap-2 bg-[#eff4ff] border border-[#dce9ff] px-3 py-1 rounded-full w-fit mx-auto md:mx-0">
                  <ShieldCheck className="w-3 h-3 text-[#28657a]" />
                  <span className="text-[#28657a] text-[8px] font-bold uppercase tracking-widest">Verified Practitioner</span>
                </div>
              </div>
              <div className="flex flex-wrap justify-center md:justify-start gap-4 text-[#74777f]">
                <div className="flex items-center gap-2">
                  <Building className="w-3.5 h-3.5 text-[#002045]" />
                  <span className="text-[10px] font-bold text-[#43474e]">{user.firmName || 'Independent Practice'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Mail className="w-3.5 h-3.5 text-[#002045]" />
                  <span className="text-[10px] font-bold text-[#43474e]">{user.email}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="w-3.5 h-3.5 text-[#002045]" />
                  <span className="text-[10px] font-bold text-[#43474e]">Joined May 2024</span>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <Button 
                onClick={() => navigate(`${APP_BASE}/settings/email`)}
                variant="outline" 
                className="rounded-xl h-9 px-6 text-[9px] font-bold uppercase tracking-widest border-[#c4c6cf]/40 hover:bg-[#eff4ff] text-[#002045]"
              >
                <Settings className="w-3.5 h-3.5 mr-2" />
                Security Settings
              </Button>
              <Button 
                onClick={handleLogout}
                variant="ghost" 
                className="rounded-xl h-9 px-6 text-[9px] font-bold uppercase tracking-widest text-[#ba1a1a] hover:bg-[#ffdad6]"
              >
                <LogOut className="w-3.5 h-3.5 mr-2" />
                Sign Out
              </Button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Stats & Details */}
          <div className="lg:col-span-1 space-y-8">
            <div className="bg-white border border-[#c4c6cf]/30 p-6 rounded-[1.5rem] shadow-sm space-y-5">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-lg bg-[#eff4ff] flex items-center justify-center">
                  <Globe className="w-3.5 h-3.5 text-[#002045]" />
                </div>
                <h3 className="text-[10px] font-bold text-[#002045] uppercase tracking-[0.2em]">Network Status</h3>
              </div>
              <div className="space-y-3">
                <div className="p-3 rounded-xl bg-[#f8f9ff] border border-[#dce9ff] flex items-center justify-between">
                  <div>
                    <p className="text-[7px] font-bold text-[#74777f] uppercase tracking-widest mb-0.5">Active Region</p>
                    <p className="text-[10px] font-bold text-[#002045]">Graph-Node-01 (KHI)</p>
                  </div>
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                </div>
                <div className="p-3 rounded-xl bg-[#f8f9ff] border border-[#dce9ff]">
                  <p className="text-[7px] font-bold text-[#74777f] uppercase tracking-widest mb-0.5">Last Sync</p>
                  <p className="text-[10px] font-bold text-[#002045]">Today at {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                </div>
              </div>
            </div>

            <div className="bg-[#002045] p-6 rounded-[1.5rem] text-white shadow-xl shadow-[#002045]/10 relative overflow-hidden group cursor-pointer">
               <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
                  <Zap className="w-16 h-16" />
               </div>
               <h3 className="text-lg font-bold tracking-tight mb-2 uppercase tracking-wide">Enterprise Pro</h3>
               <p className="text-[#eff4ff]/70 text-[9px] font-medium leading-relaxed mb-6">Unlock unlimited semantic vectors and bulk case analysis.</p>
                <Button 
                  onClick={() => setShowPaymentModal(true)}
                  className="w-full bg-[#28657a] hover:bg-[#347b94] text-white text-[9px] font-bold uppercase tracking-widest rounded-xl h-10"
                >
                  View Payment Details
                </Button>
            </div>
          </div>

          {/* Activity Feed */}
          <div className="lg:col-span-2 space-y-8">
            
            {/* Evidence Repository */}
            <div className="bg-white border border-[#c4c6cf]/30 p-8 rounded-[2rem] shadow-sm">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                   <div className="w-9 h-9 rounded-xl bg-[#eff4ff] flex items-center justify-center">
                    <Database className="w-4 h-4 text-[#002045]" />
                  </div>
                  <h3 className="text-[11px] font-bold text-[#002045] uppercase tracking-[0.1em]">Evidence Repository</h3>
                </div>
                <span className="text-[7px] font-bold text-[#28657a] uppercase tracking-widest bg-[#eff4ff] px-3 py-1.5 rounded-full border border-[#dce9ff]">
                  {userData.sources.length} Documents Indexed
                </span>
              </div>
              
              <div className="space-y-3">
                {userData.sources.length === 0 ? (
                  <div className="py-10 text-center border border-dashed border-[#c4c6cf]/40 rounded-2xl">
                    <p className="text-[9px] font-bold text-[#74777f] uppercase tracking-widest">No active cases found</p>
                  </div>
                ) : (
                  userData.sources.map((source, i) => (
                    <div key={i} className="flex items-center gap-4 p-4 rounded-2xl hover:bg-[#f8f9ff] transition-colors border border-transparent hover:border-[#c4c6cf]/30">
                      <div className="w-10 h-10 rounded-xl bg-[#eff4ff] flex items-center justify-center text-[#002045]">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div className="flex-1">
                        <p className="text-[10px] font-bold text-[#002045] uppercase tracking-tight">{source.title}</p>
                        <p className="text-[8px] text-[#74777f] font-bold uppercase tracking-widest">{source.type} • Indexed on {new Date(source.timestamp).toLocaleDateString()}</p>
                      </div>
                      <Button variant="ghost" size="icon" className="text-[#c4c6cf] hover:text-[#002045] w-8 h-8">
                        <ExternalLink className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Consultation History */}
            <div className="bg-white border border-[#c4c6cf]/30 p-8 rounded-[2rem] shadow-sm">
               <div className="flex items-center gap-3 mb-6">
                 <div className="w-9 h-9 rounded-xl bg-[#eff4ff] flex items-center justify-center">
                    <MessageSquare className="w-4 h-4 text-[#002045]" />
                  </div>
                  <h3 className="text-[11px] font-bold text-[#002045] uppercase tracking-[0.1em]">Consultation History</h3>
              </div>
              
              <div className="space-y-5">
                {userData.chatHistory.length === 0 ? (
                  <div className="py-10 text-center border border-dashed border-[#c4c6cf]/40 rounded-2xl">
                    <p className="text-[9px] font-bold text-[#74777f] uppercase tracking-widest">No previous consultations</p>
                  </div>
                ) : (
                  userData.chatHistory.slice(0, 5).map((chat, i) => (
                    <div key={i} className="space-y-2">
                       <div className="flex items-center justify-between px-1">
                         <span className="text-[7px] font-bold text-[#28657a] uppercase tracking-[0.2em]">{new Date(chat.timestamp).toLocaleString()}</span>
                       </div>
                       <div className="p-5 rounded-2xl bg-[#f8f9ff] border border-[#c4c6cf]/20">
                          <p className="text-[10px] font-medium text-[#43474e] leading-relaxed italic">"{String(chat.content || chat.query || '').substring(0, 150)}..."</p>
                       </div>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>

        </div>
      </div>

      {/* Payment Modal */}
      <AnimatePresence>
        {showPaymentModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowPaymentModal(false)}
              className="absolute inset-0 bg-[#000814]/80 backdrop-blur-md"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-md bg-[#0a1528] rounded-[1.5rem] shadow-2xl border border-white/10 overflow-hidden p-6"
            >
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-[#28657a]/20 flex items-center justify-center border border-[#28657a]/30">
                    <Scale className="w-5 h-5 text-[#28657a]" />
                  </div>
                  <h3 className="text-[14px] font-bold text-white tracking-tight">Enterprise Access</h3>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setShowPaymentModal(false)} className="rounded-lg hover:bg-white/10">
                  <X className="w-5 h-5 text-slate-400" />
                </Button>
              </div>

              <div className="space-y-6">
                <div className="p-5 rounded-2xl bg-[#000814]/40 border border-white/5 space-y-4">
                  <div>
                    <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest mb-1">Account Holder</p>
                    <p className="text-[11px] font-bold text-white">Ashhad Ahmed Kamran</p>
                  </div>
                  <div>
                    <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest mb-1">NayaPay ID</p>
                    <p className="text-[11px] font-bold text-[#28657a]">ash.ahm170@nayapay</p>
                  </div>
                  <div>
                    <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest mb-1">Account Number</p>
                    <p className="text-[11px] font-bold text-white">03322575977</p>
                  </div>
                  <div>
                    <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest mb-1">IBAN</p>
                    <p className="text-[11px] font-bold text-white tabular-nums">PK88NAYA1234503322575977</p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-4 rounded-xl bg-[#000814]/40 border border-white/5 text-[8px] font-bold text-[#28657a] uppercase tracking-widest leading-relaxed">
                   <ShieldCheck className="w-4 h-4 shrink-0" />
                   Verification is required for enterprise node activation.
                </div>

                <Button 
                  onClick={() => setShowPaymentModal(false)}
                  className="w-full h-11 rounded-xl bg-[#28657a] hover:bg-[#1e4d5d] text-white text-[9px] font-bold uppercase tracking-widest shadow-lg shadow-[#28657a]/20"
                >
                  Proceed to Terminal
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
