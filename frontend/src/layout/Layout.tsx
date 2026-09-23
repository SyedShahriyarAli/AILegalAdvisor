import { Outlet } from 'react-router-dom';
import { Sidebar } from '../components/Sidebar';

export default function Layout() {
    return (
        <div className="flex h-screen w-full bg-background overflow-hidden font-sans antialiased text-foreground selection:bg-primary/10 selection:text-primary">
            {/* Sidebar is now persistent and non-closable */}
            <Sidebar isOpen={true} onClose={() => { }} />

            <div className="flex flex-col flex-1 h-full min-w-0 pl-[280px]">
                <main className="flex-1 overflow-hidden relative">
                    <div className="h-full w-full">
                        <Outlet />
                    </div>
                </main>
            </div>
        </div>
    );
}
