import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { MapPin, Package, Truck, Activity, Boxes, Wrench, AlertOctagon, Radio } from 'lucide-react';
import { OfflineSyncIndicator } from '../features/control-tower/components/OfflineSyncIndicator';
import { OfflineSyncDrawer } from '../features/control-tower/components/OfflineSyncDrawer';
import { useVisitorSession } from '../lib/hooks/useVisitorSession';

const COMMAND_NAV_ITEMS = [
  { to: '/control-tower', label: 'Control Tower', Icon: Radio },
];

const LOGISTICS_NAV_ITEMS = [
  { to: '/locations', label: 'Locations',  Icon: MapPin  },
  { to: '/cargo',     label: 'Cargo',      Icon: Package },
  { to: '/transport', label: 'Transport',  Icon: Truck   },
];

const OPERATIONS_NAV_ITEMS = [
  { to: '/inventory', label: 'Inventory',            Icon: Boxes        },
  { to: '/assets',    label: 'Assets & Maintenance', Icon: Wrench       },
  { to: '/incidents', label: 'Incident Response',    Icon: AlertOctagon },
];

interface Props {
  children: React.ReactNode;
}

export function AppLayout({ children }: Props) {
  const [isSyncDrawerOpen, setIsSyncDrawerOpen] = useState(false);
  useVisitorSession();

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      {/* Sidebar */}
      <aside
        className="w-60 shrink-0 border-r border-slate-800 flex flex-col"
        aria-label="Main navigation"
      >
        {/* Logo / wordmark */}
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" aria-hidden="true" />
            <span className="font-semibold text-slate-100 tracking-tight text-sm">
              CRYOS
            </span>
          </div>
          <p className="text-[10px] text-slate-500 font-mono mt-0.5 uppercase tracking-widest">
            SIH26062 · Track B
          </p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-4 overflow-y-auto" aria-label="Workspaces">
          <div>
            <p className="px-2 mb-2 text-[10px] font-mono text-slate-500 uppercase tracking-widest">
              Command
            </p>
            <div className="space-y-1">
              {COMMAND_NAV_ITEMS.map(({ to, label, Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                      isActive
                        ? 'bg-cyan-900/40 text-cyan-300 border border-cyan-800/60'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`}
                        aria-hidden="true"
                      />
                      {label}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>

          <div>
            <p className="px-2 mb-2 text-[10px] font-mono text-slate-500 uppercase tracking-widest">
              Logistics
            </p>
            <div className="space-y-1">
              {LOGISTICS_NAV_ITEMS.map(({ to, label, Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                      isActive
                        ? 'bg-cyan-900/40 text-cyan-300 border border-cyan-800/60'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`}
                        aria-hidden="true"
                      />
                      {label}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>

          <div>
            <p className="px-2 mb-2 text-[10px] font-mono text-slate-500 uppercase tracking-widest">
              Operations
            </p>
            <div className="space-y-1">
              {OPERATIONS_NAV_ITEMS.map(({ to, label, Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                      isActive
                        ? 'bg-cyan-900/40 text-cyan-300 border border-cyan-800/60'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`}
                        aria-hidden="true"
                      />
                      {label}
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        </nav>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-800">
          <p className="text-[10px] text-slate-600 font-mono">
            Data: [SYNTHETIC/DEMO]
          </p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {/* Top bar */}
        <header className="sticky top-0 z-10 px-6 py-3 border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm flex items-center justify-between">
          <OfflineSyncIndicator onOpenDrawer={() => setIsSyncDrawerOpen(true)} />
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 font-mono">
              Antarctic Expedition Logistics Platform
            </span>
          </div>
        </header>

        <div className="px-6 py-6">
          {children}
        </div>

        {/* Platform-wide Offline Sync Drawer */}
        <OfflineSyncDrawer
          isOpen={isSyncDrawerOpen}
          onClose={() => setIsSyncDrawerOpen(false)}
        />
      </main>
    </div>
  );
}
