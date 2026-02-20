import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';

const navItems = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/insurees', label: 'Insurees' },
  { path: '/files', label: 'Files' },
  { path: '/review', label: 'Review' },
  { path: '/submissions', label: 'Submissions' },
  { path: '/reports', label: 'Reports' },
];

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
      <p className="mt-2 text-sm text-gray-500">This page is not yet implemented.</p>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-gray-100">
        {/* Sidebar */}
        <nav className="w-60 shrink-0 bg-[#1a1a2e] text-white flex flex-col px-4 py-6">
          <h2 className="text-lg font-bold tracking-wide mb-8 px-2">Endorsements</h2>
          <ul className="space-y-1">
            {navItems.map(({ path, label }) => (
              <li key={path}>
                <NavLink
                  to={path}
                  className={({ isActive }) =>
                    `block px-3 py-2 rounded-md text-sm transition-colors ${
                      isActive
                        ? 'bg-[#0f3460] text-white font-semibold'
                        : 'text-gray-400 hover:bg-white/10 hover:text-white'
                    }`
                  }
                >
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"   element={<PlaceholderPage title="Dashboard" />} />
            <Route path="/insurees"    element={<PlaceholderPage title="Insurees" />} />
            <Route path="/files"       element={<PlaceholderPage title="File Queue" />} />
            <Route path="/review"      element={<PlaceholderPage title="Review" />} />
            <Route path="/submissions" element={<PlaceholderPage title="Submissions" />} />
            <Route path="/reports"     element={<PlaceholderPage title="Reports" />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
