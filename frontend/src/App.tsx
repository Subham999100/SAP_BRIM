import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ChatPage } from './pages/ChatPage';
import { Layers, Loader2 } from 'lucide-react';

const MainApp: React.FC = () => {
  const { user, loading } = useAuth();

  const [authView, setAuthView] =
    useState<'login' | 'register'>('login');

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          width: '100%',
          background: '#090d16',
          color: '#ffffff',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'Arial, sans-serif',
        }}
      >
        <div
          style={{
            width: '56px',
            height: '56px',
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #075985, #0284c7, #38bdf8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '16px',
          }}
        >
          <Layers size={28} />
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: '#94a3b8',
            fontSize: '13px',
          }}
        >
          <Loader2
            size={16}
            style={{
              animation: 'spin 1s linear infinite',
            }}
          />

          <span>
            Connecting to SAP Knowledge Assistant...
          </span>
        </div>
      </div>
    );
  }

  if (!user) {
    if (authView === 'login') {
      return (
        <LoginPage
          onSwitchToRegister={() =>
            setAuthView('register')
          }
        />
      );
    }

    return (
      <RegisterPage
        onSwitchToLogin={() =>
          setAuthView('login')
        }
      />
    );
  }

  return <ChatPage />;
};

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}