import { useState } from 'react';
import SignIn from './components/SignIn';
import SignUp from './components/SignUp';
import Dashboard from './components/Dashboard';
import { useAuth } from './hooks/useAuth';

function App() {
  const { user } = useAuth();
  const [isSignUp, setIsSignUp] = useState(false);

  if (!user) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        {isSignUp ? <SignUp /> : <SignIn />}
        <button
          onClick={() => setIsSignUp(!isSignUp)}
          style={{ marginTop: '1rem', color: '#0097FB', textDecoration: 'underline', background: 'none', border: 'none', cursor: 'pointer' }}
        >
          {isSignUp ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
        </button>
      </div>
    );
  }

  return <Dashboard />;
}

export default App;