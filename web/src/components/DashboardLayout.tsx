import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import MobileNavigation from "./MobileNavigation";

export default function DashboardLayout() {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Desktop Sidebar */}
      <div className="print:hidden">
        <Sidebar />
      </div>

      {/* Mobile Sidebar Navigation Drawer */}
      <div className="print:hidden">
        <MobileNavigation isOpen={isMobileOpen} onClose={() => setIsMobileOpen(false)} />
      </div>

      {/* Main Layout Area */}
      <div className="lg:pl-64 flex flex-col min-h-screen print:pl-0">
        {/* Topbar navigation */}
        <div className="print:hidden">
          <Topbar onMenuClick={() => setIsMobileOpen(true)} />
        </div>

        {/* Content View Area */}
        <main className="flex-1 overflow-y-auto bg-slate-950 p-6 md:p-8 print:bg-white print:p-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
