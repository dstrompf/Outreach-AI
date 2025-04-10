import { useAuth } from '../hooks/useAuth';
import { auth, db } from '../firebase';
import { signOut } from 'firebase/auth';
import { useState, useEffect } from 'react';
import { doc, getDoc, setDoc } from 'firebase/firestore';
import Settings from './Settings';
import { generateKnowledgeBaseSuggestion } from '../api/openai';

function Dashboard() {
  const { user } = useAuth();
  const [knowledgeBase, setKnowledgeBase] = useState('');
  const [loadingSuggestion, setLoadingSuggestion] = useState(false);

  useEffect(() => {
    // Fetch knowledge base data from Firestore on mount
    const fetchKnowledgeBase = async () => {
      if (user) {
        const docRef = doc(db, 'users', user.uid);
        const docSnap = await getDoc(docRef);
        if (docSnap.exists()) {
          setKnowledgeBase(docSnap.data().knowledgeBase || '');
        }
      }
    };
    fetchKnowledgeBase();
  }, [user]);

  const saveKnowledgeBase = async () => {
    if (user) {
      try {
        await setDoc(doc(db, 'users', user.uid), { knowledgeBase });
        alert('Knowledge base saved!');
      } catch (error) {
        console.error('Error saving knowledge base:', error);
        alert('There was an error saving your knowledge base.');
      }
    }
  };

  async function handleAIAssist() {
    if (!knowledgeBase.trim()) {
      alert('Please type something first!');
      return;
    }
    try {
      setLoadingSuggestion(true);
      const aiSuggestion = await generateKnowledgeBaseSuggestion(
        `Improve these instructions: ${knowledgeBase}`
      );
      setKnowledgeBase(aiSuggestion);
    } catch (error) {
      console.error('Error generating AI suggestion:', error);
      alert('There was an error generating suggestions.');
    } finally {
      setLoadingSuggestion(false);
    }
  }

  return (
    <div>
      <h1>Dashboard</h1>
      <p>Logged in as: {user?.email}</p>
      <textarea
        value={knowledgeBase}
        onChange={(e) => setKnowledgeBase(e.target.value)}
        placeholder="Enter your knowledge base instructions here..."
        rows={10}
        className="w-full border border-gray-300 rounded px-3 py-2 mt-4"
      />
      <div className="flex space-x-2 mt-2">
        <button
          onClick={saveKnowledgeBase}
          className="bg-blue-500 text-white px-4 py-2 rounded"
        >
          Save
        </button>

        <button
          onClick={handleAIAssist}
          className="bg-purple-500 text-white px-4 py-2 rounded"
          disabled={loadingSuggestion}
        >
          {loadingSuggestion ? 'Thinking...' : 'Help Me Write'}
        </button>
      </div>
      <button onClick={() => signOut(auth)} className="mt-4">
        Sign Out
      </button>
      <Settings />
    </div>
  );
}

export default Dashboard;