import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import InsureesPage from './pages/InsureesPage';
import FilesPage from './pages/FilesPage';
import ReviewPage from './pages/ReviewPage';
import SubmissionsPage from './pages/SubmissionsPage';
import ReportsPage from './pages/ReportsPage';
import './App.css';

const navItems = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/insurees', label: 'Insurees' },
  { path: '/files', label: 'Files' },
  { path: '/review', label: 'Review' },
  { path: '/submissions', label: 'Submissions' },
  { path: '/reports', label: 'Reports' },
];

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <nav className="sidebar">
          <h2 className="sidebar-title">Endorsements</h2>
          <ul className="nav-list">
            {navItems.map(({ path, label }) => (
              <li key={path}>
                <NavLink
                  to={path}
                  className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                >
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/insurees" element={<InsureesPage />} />
            <Route path="/files" element={<FilesPage />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/submissions" element={<SubmissionsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
