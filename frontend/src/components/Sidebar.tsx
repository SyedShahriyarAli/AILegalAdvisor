import { useState, useEffect } from 'react';
import {
  BarChart3,
  MessageSquare,
  FileText,
  User,
  LogIn,
  LogOut,
  History,
  Scale,
  CreditCard,
  Copy,
  Trash2,
  Gavel,
  X,
  CheckCircle2,
  Info,
} from 'lucide-react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { authService } from '@/lib/authService';
import type { User as UserType, CaseAnalyzerSession } from '@/lib/authService';
import { APP_BASE } from '@/lib/appPaths';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';

const NAV_ITEMS = [
  { icon: BarChart3, label: 'Case Analyzer', path: APP_BASE, sublabel: 'Intake & Audit' },
  { icon: MessageSquare, label: 'Legal Assistant', path: `${APP_BASE}/chat`, sublabel: 'AI Consultation' },
  { icon: FileText, label: 'Knowledge Base', path: `${APP_BASE}/documents`, sublabel: 'Documents' },
  { icon: Gavel, label: 'Browse Cases', path: `${APP_BASE}/cases`, sublabel: 'Court Precedents' },
];

export function Sidebar({ isOpen: _isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [user, setUser] = useState<UserType | null>(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showPlansModal, setShowPlansModal] = useState(false);
  const [caseSessions, setCaseSessions] = useState<CaseAnalyzerSession[]>([]);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const activeCaseSessionId = searchParams.get('session');

  useEffect(() => {
    setUser(authService.getCurrentUser());
  }, [location]);

  useEffect(() => {
    if (!user) { setCaseSessions([]); return; }
    const data = authService.loadUserData(user.id);
    setCaseSessions(data.caseAnalyzerSessions || []);
  }, [user, location]);

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleLogout = async () => {
    await authService.logout();
    navigate('/login');
  };

  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (user && confirm('Delete this analysis?')) {
      authService.deleteCaseAnalyzerSession(user.id, sessionId);
    }
  };

  const handleDeleteAllSessions = () => {
    if (user && confirm('Purge all case history?')) {
      authService.deleteAllCaseAnalyzerSessions(user.id);
    }
  };

  return (
    <>
      <div className={cn(
        'fixed inset-y-0 left-0 z-[60] w-[280px] flex flex-col',
        'bg-[#eff4ff] border-r border-[#c4c6cf]/30 shadow-xl'
      )}>

        {/* ── Brand Header ── */}
        <div className="h-20 flex items-center justify-between px-6 border-b border-[#c4c6cf]/30 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#002045] flex items-center justify-center shadow-sm">
              <Scale className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="font-['Geist',sans-serif] text-[13px] font-bold text-[#002045] leading-tight">AI Legal Advisor</p>
              <p className="text-[9px] font-semibold text-[#74777f] uppercase tracking-[0.1em]">Cyber-Legal Platform</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-4 py-6 flex flex-col min-h-0 overflow-hidden gap-1">
          <p className="text-[11px] font-bold text-[#74777f] uppercase tracking-[0.18em] px-3 mb-3">Navigation</p>

          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => window.innerWidth < 768 && onClose()}
                className={cn(
                  'flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 group',
                  isActive
                    ? 'bg-[#abe5fe]/40 text-[#002045] border border-[#28657a]/20'
                    : 'text-[#43474e] hover:bg-[#e5eeff] hover:text-[#002045] border border-transparent'
                )}
              >
                <div className={cn(
                  'w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors',
                  isActive ? 'bg-[#002045] text-white' : 'bg-[#dce9ff] text-[#43474e] group-hover:bg-[#002045] group-hover:text-white'
                )}>
                  <item.icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-bold leading-tight truncate">{item.label}</p>
                  <p className="text-[11px] text-[#74777f] font-medium">{item.sublabel}</p>
                </div>
                {isActive && (
                  <div className="w-1.5 h-1.5 rounded-full bg-[#28657a]" />
                )}
              </Link>
            );
          })}

          {/* ── Case History ── */}
          {user && (
            <div className="mt-6 pt-5 border-t border-[#c4c6cf]/30 flex-1 min-h-0 flex flex-col gap-2">
              <div className="flex items-center justify-between px-3 shrink-0">
                <div className="flex items-center gap-2">
                  <History className="w-3.5 h-3.5 text-[#28657a]" />
                  <span className="text-[11px] font-bold uppercase tracking-[0.18em] text-[#74777f]">Case Analyses</span>
                </div>
                {caseSessions.length > 0 && (
                  <button
                    onClick={handleDeleteAllSessions}
                    className="p-1 hover:bg-[#ffdad6] rounded-md transition-colors group/trash"
                  >
                    <Trash2 className="w-3 h-3 text-[#74777f] group-hover/trash:text-[#ba1a1a]" />
                  </button>
                )}
              </div>
              <div className="flex-1 min-h-0 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
                {caseSessions.length === 0 ? (
                  <p className="text-[12px] text-[#74777f] px-3 py-2 leading-relaxed">
                    Run an analysis to save it here.
                  </p>
                ) : (
                  caseSessions.map((s) => {
                    const isActive = activeCaseSessionId === s.id && location.pathname === APP_BASE;
                    return (
                      <div key={s.id} className="group relative">
                        <button
                          type="button"
                          onClick={() => {
                            navigate(`${APP_BASE}?session=${encodeURIComponent(s.id)}`);
                            if (window.innerWidth < 768) onClose();
                          }}
                          className={cn(
                            'w-full text-left px-3 py-2.5 rounded-xl transition-colors border pr-10',
                            isActive
                              ? 'bg-[#abe5fe]/30 border-[#28657a]/20 text-[#002045]'
                              : 'hover:bg-[#e5eeff] text-[#43474e] border-transparent'
                          )}
                        >
                          <span className="block text-[13px] font-semibold truncate">{s.title || 'Untitled analysis'}</span>
                          <span className="block text-[11px] text-[#74777f] mt-0.5">
                            {(() => {
                              try {
                                const d = new Date(s.createdAt);
                                return isNaN(d.getTime()) ? '' : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
                              } catch { return ''; }
                            })()}
                          </span>
                        </button>
                        <button
                          onClick={(e) => handleDeleteSession(e, s.id)}
                          className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg flex items-center justify-center text-[#74777f] hover:text-[#ba1a1a] hover:bg-[#ffdad6] opacity-0 group-hover:opacity-100 transition-all"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </nav>

        {/* ── Bottom CTA / User ── */}
        <div className="px-4 pb-4 pt-3 border-t border-[#c4c6cf]/30 shrink-0 space-y-3">

          {user ? (
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-[#e5eeff] transition-colors border border-transparent hover:border-[#c4c6cf]/30"
              >
                <div className="w-8 h-8 rounded-full bg-[#1a365d] text-white flex items-center justify-center text-[11px] font-bold shrink-0">
                  {user.name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div className="flex-1 min-w-0 text-left">
                  <p className="text-[11px] font-bold text-[#0b1c30] truncate">{user.name}</p>
                  <p className="text-[9px] text-[#74777f] truncate">{user.firmName || 'Independent'}</p>
                </div>
              </button>

              {showUserMenu && (
                <div className="absolute bottom-full left-0 w-full mb-2 bg-white border border-[#c4c6cf]/40 rounded-xl shadow-xl overflow-hidden z-50">
                  <Link to={`${APP_BASE}/profile`} onClick={() => setShowUserMenu(false)}>
                    <button className="w-full flex items-center gap-3 px-4 py-3 text-[11px] font-semibold text-[#43474e] hover:bg-[#eff4ff] transition-colors">
                      <User className="w-4 h-4" /> View Profile
                    </button>
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-3 px-4 py-3 text-[11px] font-semibold text-[#ba1a1a] hover:bg-[#ffdad6] transition-colors border-t border-[#c4c6cf]/20"
                  >
                    <LogOut className="w-4 h-4" /> Sign Out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link to="/login" className="w-full">
              <button className="w-full flex items-center justify-center gap-3 py-3 rounded-xl bg-[#002045] text-white
                                 text-[11px] font-bold hover:bg-[#1a365d] transition-colors">
                <LogIn className="w-4 h-4" /> Sign In
              </button>
            </Link>
          )}

          {/* Footer labels / View Plans */}
          {/* <div className="flex items-center justify-around pt-1">
            <button
              onClick={() => setShowPlansModal(true)}
              className="text-[9px] text-[#28657a] hover:text-[#002045] uppercase tracking-[0.15em] font-bold flex items-center gap-1"
            >
              <CreditCard className="w-3 h-3" /> View Plans
            </button>
            <span className="text-[9px] text-[#74777f] uppercase tracking-[0.1em] font-semibold">Support</span>
          </div> */}
        </div>
      </div>

      {/* ── Plans / Bank Details Modal ── */}
      <AnimatePresence>
        {showPlansModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowPlansModal(false)}
              className="absolute inset-0 bg-[#002045]/60 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.98, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.98, y: 10 }}
              className="relative w-full max-w-md bg-white rounded-3xl shadow-2xl overflow-hidden border border-[#c4c6cf]/30"
            >
              <div className="px-8 py-6 border-b border-[#c4c6cf]/30 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-[#eff4ff] flex items-center justify-center border border-[#dce9ff]">
                    <CreditCard className="w-5 h-5 text-[#002045]" />
                  </div>
                  <div>
                    <h2 className="text-[16px] font-bold text-[#002045] tracking-tight">Subscription Plans</h2>
                    <p className="text-[9px] text-[#74777f] font-bold uppercase tracking-widest">Enterprise Access & Payment Details</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowPlansModal(false)}
                  className="rounded-lg hover:bg-[#eff4ff] p-2 text-[#74777f] hover:text-[#002045]"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-8 space-y-6">
                <div className="bg-[#eff4ff] rounded-2xl p-5 border border-[#dce9ff]">
                  <p className="text-[10px] font-bold text-[#28657a] uppercase tracking-widest mb-3">Direct Bank Transfer</p>

                  <div className="space-y-4">
                    <div className="flex items-center justify-between group cursor-pointer" onClick={() => copyToClipboard('Ashhad Ahmed Kamran', 'name')}>
                      <div>
                        <p className="text-[9px] font-bold text-[#74777f] uppercase tracking-widest">Account Name</p>
                        <p className="text-[13px] font-bold text-[#002045]">Ashhad Ahmed Kamran</p>
                      </div>
                      {copiedField === 'name' ? <CheckCircle2 className="w-4 h-4 text-[#28657a]" /> : <Copy className="w-4 h-4 text-[#c4c6cf] group-hover:text-[#002045]" />}
                    </div>

                    <div className="flex items-center justify-between group cursor-pointer" onClick={() => copyToClipboard('ash.ahm170@nayapay', 'nayapay')}>
                      <div>
                        <p className="text-[9px] font-bold text-[#74777f] uppercase tracking-widest">NayaPay ID</p>
                        <p className="text-[13px] font-bold text-[#002045]">ash.ahm170@nayapay</p>
                      </div>
                      {copiedField === 'nayapay' ? <CheckCircle2 className="w-4 h-4 text-[#28657a]" /> : <Copy className="w-4 h-4 text-[#c4c6cf] group-hover:text-[#002045]" />}
                    </div>

                    <div className="flex items-center justify-between group cursor-pointer" onClick={() => copyToClipboard('03322575977', 'number')}>
                      <div>
                        <p className="text-[9px] font-bold text-[#74777f] uppercase tracking-widest">Account Number</p>
                        <p className="text-[13px] font-bold text-[#002045]">03322575977</p>
                      </div>
                      {copiedField === 'number' ? <CheckCircle2 className="w-4 h-4 text-[#28657a]" /> : <Copy className="w-4 h-4 text-[#c4c6cf] group-hover:text-[#002045]" />}
                    </div>

                    <div className="flex items-center justify-between group cursor-pointer" onClick={() => copyToClipboard('PK88NAYA1234503322575977', 'iban')}>
                      <div>
                        <p className="text-[9px] font-bold text-[#74777f] uppercase tracking-widest">IBAN</p>
                        <p className="text-[13px] font-bold text-[#002045]">PK88NAYA1234503322575977</p>
                      </div>
                      {copiedField === 'iban' ? <CheckCircle2 className="w-4 h-4 text-[#28657a]" /> : <Copy className="w-4 h-4 text-[#c4c6cf] group-hover:text-[#002045]" />}
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-4 bg-[#f8f9ff] rounded-xl border border-[#c4c6cf]/20">
                  <Info className="w-4 h-4 text-[#28657a] shrink-0" />
                  <p className="text-[10px] text-[#43474e] leading-relaxed">
                    Once the payment is completed, please share the screenshot with our support team to activate your enterprise license.
                  </p>
                </div>

                <Button
                  onClick={() => setShowPlansModal(false)}
                  className="w-full h-12 bg-[#002045] hover:bg-[#1a365d] text-white rounded-xl text-[10px] font-bold uppercase tracking-widest shadow-lg shadow-[#002045]/10"
                >
                  Close Window
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
