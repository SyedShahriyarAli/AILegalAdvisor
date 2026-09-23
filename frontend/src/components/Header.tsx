import { useState, useEffect } from 'react';
import { LogOut, User, Settings } from 'lucide-react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { authService } from '@/lib/authService';
import { APP_BASE } from '@/lib/appPaths';
import type { User as UserType } from '@/lib/authService';

interface HeaderProps {
    onToggleSidebar: () => void;
}

export function Header({ onToggleSidebar: _onToggleSidebar }: HeaderProps) {
    const location = useLocation();
    const navigate = useNavigate();
    const [user, setUser] = useState<UserType | null>(null);
    const [showMenu, setShowMenu] = useState(false);

    useEffect(() => {
        setUser(authService.getCurrentUser());
    }, [location]);

    const handleLogout = async () => {
        await authService.logout();
        navigate('/login');
    };

    return (
        <header
            className="h-20 bg-[#f8f9ff]/80 backdrop-blur-xl px-8
                       flex items-center justify-between z-[55] shrink-0 sticky top-0"
        >
            {/* Left: empty (icon removed) */}
            <div className="flex items-center gap-5">
            </div>

            {/* Right: user menu */}
            <div className="flex items-center gap-4">
                {user ? (
                    <div className="relative">
                        <button
                            onClick={() => setShowMenu(!showMenu)}
                            className="w-10 h-10 rounded-full bg-[#1a365d] text-white flex items-center justify-center
                                       text-sm font-bold hover:opacity-90 transition-opacity border-2 border-[#adc7f7]/30"
                        >
                            {user.name?.charAt(0).toUpperCase() || 'U'}
                        </button>
                        {showMenu && (
                            <div className="absolute right-0 top-full mt-2 w-56 bg-white border border-[#c4c6cf]/40 rounded-xl shadow-xl
                                            shadow-[rgba(0,32,69,0.08)] overflow-hidden z-50">
                                <div className="px-4 py-3 border-b border-[#c4c6cf]/20">
                                    <p className="text-[11px] font-bold text-[#0b1c30] truncate">{user.name}</p>
                                    <p className="text-[10px] text-[#74777f] truncate">{user.email}</p>
                                </div>
                                <Link to={`${APP_BASE}/profile`} onClick={() => setShowMenu(false)}>
                                    <button className="w-full flex items-center gap-3 px-4 py-3 text-[11px] font-semibold text-[#43474e]
                                                       hover:bg-[#eff4ff] hover:text-[#002045] transition-colors">
                                        <User className="w-4 h-4" /> View Profile
                                    </button>
                                </Link>
                                <Link to={`${APP_BASE}/profile`} onClick={() => setShowMenu(false)}>
                                    <button className="w-full flex items-center gap-3 px-4 py-3 text-[11px] font-semibold text-[#43474e]
                                                       hover:bg-[#eff4ff] hover:text-[#002045] transition-colors">
                                        <Settings className="w-4 h-4" /> Settings
                                    </button>
                                </Link>
                                <button
                                    onClick={handleLogout}
                                    className="w-full flex items-center gap-3 px-4 py-3 text-[11px] font-semibold text-[#ba1a1a]
                                               hover:bg-[#ffdad6] transition-colors border-t border-[#c4c6cf]/20"
                                >
                                    <LogOut className="w-4 h-4" /> Sign Out
                                </button>
                            </div>
                        )}
                    </div>
                ) : (
                    <Link to="/login">
                        <button className="h-9 px-5 bg-[#002045] text-white text-[11px] font-bold rounded-lg
                                           hover:bg-[#1a365d] transition-colors tracking-wide">
                            Sign In
                        </button>
                    </Link>
                )}
            </div>
        </header>
    );
}
