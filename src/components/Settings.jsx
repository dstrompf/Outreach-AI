import { useState } from 'react';
import { updateEmail, updatePassword, EmailAuthProvider, reauthenticateWithCredential } from 'firebase/auth';
import { useAuth } from '../hooks/useAuth';

function Settings() {
  const { user } = useAuth();
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [message, setMessage] = useState({ text: '', isError: false });

  async function handleEmailUpdate(e) {
    e.preventDefault();
    try {
      await updateEmail(user, newEmail);
      setMessage({ text: 'Email updated successfully!', isError: false });
      setNewEmail('');
    } catch (error) {
      setMessage({ text: error.message, isError: true });
    }
  }

  async function reauthenticate() {
    const password = prompt('Please enter your current password to continue');
    if (!password) return false;
    
    const credential = EmailAuthProvider.credential(user.email, password);
    try {
      await reauthenticateWithCredential(user, credential);
      return true;
    } catch (error) {
      setMessage({ text: 'Authentication failed. Please try again.', isError: true });
      return false;
    }
  }

  async function handlePasswordUpdate(e) {
    e.preventDefault();
    try {
      const lastSignInTime = new Date(user.metadata.lastSignInTime).getTime();
      if (Date.now() - lastSignInTime > 300000) {
        if (!(await reauthenticate())) return;
      }
      await updatePassword(user, newPassword);
      setMessage({ text: 'Password updated successfully!', isError: false });
      setNewPassword('');
    } catch (error) {
      setMessage({ text: error.message, isError: true });
    }
  }

  return (
    <div style={{ marginBottom: '24px' }}>
      <h2 style={{ fontSize: '20px', marginBottom: '16px' }}>Settings</h2>

      {message.text && (
        <div style={{ 
          padding: '8px', 
          marginBottom: '16px',
          backgroundColor: message.isError ? '#fee2e2' : '#dcfce7',
          color: message.isError ? '#dc2626' : '#16a34a',
          borderRadius: '4px'
        }}>
          {message.text}
        </div>
      )}

      <form onSubmit={handleEmailUpdate} style={{ marginBottom: '16px' }}>
        <input
          type="email"
          value={newEmail}
          onChange={(e) => setNewEmail(e.target.value)}
          placeholder="New Email"
          style={{
            width: '100%',
            padding: '8px',
            marginBottom: '8px',
            border: '1px solid #ccc',
            borderRadius: '4px'
          }}
        />
        <button
          type="submit"
          style={{
            backgroundColor: '#0097FB',
            color: 'white',
            padding: '8px 16px',
            borderRadius: '4px',
            border: 'none',
            cursor: 'pointer'
          }}
        >
          Update Email
        </button>
      </form>

      <form onSubmit={handlePasswordUpdate}>
        <input
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          placeholder="New Password"
          style={{
            width: '100%',
            padding: '8px',
            marginBottom: '8px',
            border: '1px solid #ccc',
            borderRadius: '4px'
          }}
        />
        <button
          type="submit"
          style={{
            backgroundColor: '#0097FB',
            color: 'white',
            padding: '8px 16px',
            borderRadius: '4px',
            border: 'none',
            cursor: 'pointer'
          }}
        >
          Update Password
        </button>
      </form>
    </div>
  );
}

export default Settings;