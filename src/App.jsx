
import { useState } from 'react';
import SignIn from './components/SignIn';
import SignUp from './components/SignUp';
import { useAuth } from './hooks/useAuth';

function App() {
  const { user, logOut } = useAuth();
  const [isSignUp, setIsSignUp] = useState(false);

  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center h-screen">
        {isSignUp ? <SignUp /> : <SignIn />}
        <button
          onClick={() => setIsSignUp(!isSignUp)}
          style={{ marginTop: '1rem', color: '#0097FB', textDecoration: 'underline' }}
        >
          {isSignUp ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center h-screen">
      <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>
        Welcome, {user.email}!
      </h1>
      <button
        onClick={logOut}
        style={{
          padding: '0.5rem 1rem',
          backgroundColor: '#0097FB',
          color: 'white',
          borderRadius: '0.25rem'
        }}
      >
        Sign Out
      </button>
    </div>
  );
}

export default App;
