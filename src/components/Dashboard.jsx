
import { useAuth } from '../hooks/useAuth';
import { auth, db } from '../firebase';
import { signOut } from 'firebase/auth';
import { useState, useEffect } from 'react';
import { doc, getDoc, setDoc } from 'firebase/firestore';

function Dashboard() {
  const { user } = useAuth();
  const [trialDaysLeft, setTrialDaysLeft] = useState(null);
  const [knowledgeBase, setKnowledgeBase] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTrial() {
      if (!user) return;
      const userDoc = await getDoc(doc(db, 'users', user.uid));
      if (userDoc.exists()) {
        const data = userDoc.data();
        const trialStart = data.trialStart?.toDate();
        const today = new Date();
        const daysPassed = Math.floor((today - trialStart) / (1000 * 60 * 60 * 24));
        const daysLeft = 30 - daysPassed;
        setTrialDaysLeft(daysLeft > 0 ? daysLeft : 0);
        setKnowledgeBase(data.knowledgeBase || '');
      } else {
        await setDoc(doc(db, 'users', user.uid), {
          trialStart: new Date(),
          knowledgeBase: ''
        });
        setTrialDaysLeft(30);
      }
      setLoading(false);
    }
    fetchTrial();
  }, [user]);

  async function saveKnowledgeBase() {
    if (!user) return;
    await setDoc(doc(db, 'users', user.uid), {
      knowledgeBase
    }, { merge: true });
    alert('Knowledge Base saved!');
  }

  function handleLogout() {
    signOut(auth);
  }

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>Loading...</div>;
  }

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>Welcome, {user.email}</h1>
        <button
          onClick={handleLogout}
          style={{
            backgroundColor: '#ff4444',
            color: 'white',
            padding: '8px 16px',
            borderRadius: '4px',
            border: 'none',
            cursor: 'pointer'
          }}
        >
          Logout
        </button>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>Trial Days Left: {trialDaysLeft}</h2>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>Knowledge Base</h2>
        <textarea
          value={knowledgeBase}
          onChange={(e) => setKnowledgeBase(e.target.value)}
          style={{
            width: '100%',
            border: '1px solid #ccc',
            borderRadius: '4px',
            padding: '8px',
            minHeight: '200px'
          }}
        />
        <button
          onClick={saveKnowledgeBase}
          style={{
            marginTop: '8px',
            backgroundColor: '#0097FB',
            color: 'white',
            padding: '8px 16px',
            borderRadius: '4px',
            border: 'none',
            cursor: 'pointer'
          }}
        >
          Save
        </button>
      </div>

      <div style={{ marginTop: '32px' }}>
        <button 
          style={{ color: '#0097FB', textDecoration: 'underline', background: 'none', border: 'none', cursor: 'pointer' }}
          onClick={() => window.location.href = 'mailto:support@aiformreply.com'}
        >
          Report a Problem
        </button>
      </div>
    </div>
  );
}

export default Dashboard;
