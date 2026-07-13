import { AuthProvider, useAuth } from './context/AuthContext';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import './styles/tokens.css';
import './styles/global.css';

function Shell() {
  const { user, loading } = useAuth();
  if (loading) return <div className="boot-loading">{'Loading\u2026'}</div>;
  return user ? <DashboardPage /> : <AuthPage />;
}

export default function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  );
}
