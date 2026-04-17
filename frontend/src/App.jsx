import React from 'react';
import { Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Search, 
  PlusCircle, 
  ClipboardList, 
  BarChart3, 
  Settings, 
  LogOut,
  ChevronRight,
  ChevronLeft,
  ShieldCheck,
  Building,
  TrendingUp,
  Menu,
  Users
} from 'lucide-react';

import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import SchoolSearch from './pages/SchoolDirectory';
import NewProposal from './pages/ProposalForm';
import MyProposals from './pages/ProposalsList';
import StrategicPlanning from './pages/StrategicPlanning';
import AiControlCenter from './pages/AiControlPanel';
import Forecaster from './pages/Forecaster';
import SchoolProfile from './pages/SchoolProfile';
import DataManagement from './pages/DataManagement';
import PrincipalManagement from './pages/PrincipalManagement';

const Sidebar = ({ role, onLogout }) => {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);
  
  const navItems = [
    { path: '/', label: 'Overview', icon: <LayoutDashboard size={18} />, roles: ['admin', 'principal'] },
    { path: '/search', label: 'School Search', icon: <Search size={18} />, roles: ['admin', 'principal'] },
    { path: '/school-profile', label: 'Risk Profiler', icon: <Building size={18} />, roles: ['admin'] },
    { path: '/new-proposal', label: 'New Proposal', icon: <PlusCircle size={18} />, roles: ['principal'] },
    { path: '/proposals', label: 'Proposals', icon: <ClipboardList size={18} />, roles: ['admin', 'principal'] },
    { path: '/planning', label: 'Strategic Planning', icon: <BarChart3 size={18} />, roles: ['admin'] },
    { path: '/forecaster', label: 'AI Forecaster', icon: <TrendingUp size={18} />, roles: ['admin'] },
    { path: '/principals', label: 'Principal Management', icon: <Users size={18} />, roles: ['admin'] },
    { path: '/data', label: 'Dataset & Models', icon: <Settings size={18} />, roles: ['admin'] },
    { path: '/ai-control', label: 'AI Control', icon: <ShieldCheck size={18} />, roles: ['admin'] },
  ];

  // Mobile Header
  const MobileHeader = () => (
    <div className="mobile-header">
      <div className="mobile-header-logo">
        <img src="/SG.png" alt="ShikshaGuard" style={{ width: '32px', height: '32px' }} />
        <span>ShikshaGuard</span>
      </div>
      <div className="mobile-header-actions">
        <button 
          className="mobile-logout-btn" 
          onClick={onLogout}
          aria-label="Sign out"
          title="Sign out"
        >
          <LogOut size={20} />
        </button>
        <button 
          className="mobile-menu-btn" 
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? '✕' : '☰'}
        </button>
      </div>
    </div>
  );

  return (
    <>
      <MobileHeader />
      <aside className={`sidebar ${mobileMenuOpen ? 'mobile-open' : ''} ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-brand">
          <div className="brand-lockup">
            <div className="brand-mark">
              <img src="/SG.png" alt="ShikshaGuard" style={{ width: '32px', height: '32px', objectFit: 'contain' }} />
            </div>
            <div>
              <span className="brand-title">ShikshaGuard</span>
              <span className="brand-subtitle">Infrastructure intelligence</span>
            </div>
          </div>
          <button 
            className="sidebar-toggle-btn" 
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label="Toggle sidebar"
          >
            {sidebarCollapsed ? <Menu size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>
        
        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navItems.filter(item => item.roles.includes(role)).map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-link ${isActive ? 'active' : ''}`}
                aria-current={isActive ? 'page' : undefined}
                onClick={() => setMobileMenuOpen(false)}
              >
                <div className="nav-link-label">
                  {item.icon}
                  <span>{item.label}</span>
                </div>
                {isActive && <ChevronRight size={14} className="nav-chevron" />}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="role-card">
            <div className="role-label">Current Role</div>
            <div className="role-value">
               <span className="status-dot" />
               {role}
            </div>
          </div>
          <button 
            onClick={onLogout} 
            className="logout-button"
            title="Sign Out"
            aria-label="Sign Out"
          >
            <LogOut size={18} />
            Sign Out
          </button>
        </div>
      </aside>
    </>
  );
};

function App() {
  const [user, setUser] = React.useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  React.useEffect(() => {
    const token = localStorage.getItem('token');
    const role = localStorage.getItem('role');
    const school = localStorage.getItem('school_pseudocode');
    if (token && role) {
      setUser({ role, school });
    } else if (location.pathname !== '/login') {
      navigate('/login');
    }
  }, [location.pathname, navigate]);

  const handleLogin = (userData) => {
    setUser(userData);
    navigate('/');
  };

  const handleLogout = () => {
    localStorage.clear();
    setUser(null);
    navigate('/login');
  };

  if (!user && location.pathname !== '/login') return null;

  return (
    <div className="app-container">
      {user && location.pathname !== '/login' && <Sidebar role={user.role} onLogout={handleLogout} />}
      <main className="main-content">
        <Routes>
          <Route path="/login" element={<Login onLoginSuccess={handleLogin} />} />
          <Route path="/" element={<Dashboard />} />
          <Route path="/search" element={<SchoolSearch />} />
          <Route path="/new-proposal" element={<NewProposal />} />
          <Route path="/proposals" element={<MyProposals />} />
          <Route path="/planning" element={<StrategicPlanning />} />
          <Route path="/forecaster" element={<Forecaster />} />
          <Route path="/school-profile" element={<SchoolProfile />} />
          <Route path="/principals" element={<PrincipalManagement />} />
          <Route path="/data" element={<DataManagement />} />
          <Route path="/ai-control" element={<AiControlCenter />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
