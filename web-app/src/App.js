import React, { useState, useEffect } from 'react';
import { StytchProvider, useStytchUser, useStytch } from '@stytch/react';
import { StytchUIClient } from '@stytch/vanilla-js';
import './App.css';

// Initialize Stytch client
const stytch = new StytchUIClient(
  process.env.REACT_APP_STYTCH_PUBLIC_TOKEN || 'public-token-live-b58a2742-33c6-4356-a083-879416574e5e'
);

function ApiKeyManagement() {
  const { user } = useStytchUser();
  const stytchClient = useStytch();
  const [apiKey, setApiKey] = useState('');
  const [currentApiKey, setCurrentApiKey] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginMessage, setLoginMessage] = useState('');
  const [isSignup, setIsSignup] = useState(false);
  const [oauthRedirectUrl, setOauthRedirectUrl] = useState(null);

  // Handle OAuth redirect parameter
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const redirectUrl = params.get('redirect');

    if (redirectUrl) {
      console.log('[DEBUG] OAuth redirect URL detected:', redirectUrl);
      setOauthRedirectUrl(redirectUrl);
    }
  }, []);

  useEffect(() => {
    if (user) {
      // If we have an OAuth redirect URL, complete the OAuth flow
      if (oauthRedirectUrl) {
        handleOAuthRedirect();
      } else {
        // Load current API key from backend
        fetchCurrentApiKey();
      }
    }
  }, [user, oauthRedirectUrl]);

  const handleOAuthRedirect = async () => {
    try {
      const tokens = stytchClient.session.getTokens();
      console.log('[DEBUG] OAuth redirect - Tokens:', tokens);

      if (!tokens || !tokens.session_token) {
        console.error('No valid session token for OAuth redirect. Tokens:', tokens);
        setLoginMessage('Error: Authentication failed. No session token.');
        return;
      }

      // Redirect back to MCP OAuth server with session token
      const separator = oauthRedirectUrl.includes('?') ? '&' : '?';
      const redirectWithToken = `${oauthRedirectUrl}${separator}stytch_token=${tokens.session_token}`;

      console.log('[DEBUG] Redirecting to:', redirectWithToken);
      window.location.href = redirectWithToken;
    } catch (error) {
      console.error('Failed to complete OAuth redirect:', error);
      setLoginMessage(`Error: ${error.message}`);
    }
  };

  const fetchCurrentApiKey = async () => {
    try {
      const tokens = stytchClient.session.getTokens();
      console.log('[DEBUG] Tokens:', tokens);

      if (!tokens || !tokens.session_token) {
        console.error('No valid session token found. Tokens:', tokens);
        return;
      }

      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/user/api-key`, {
        headers: {
          'Authorization': `Bearer ${tokens.session_token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentApiKey(data.quendoo_api_key);
      }
    } catch (error) {
      console.error('Failed to fetch API key:', error);
    }
  };

  const handleSaveApiKey = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const tokens = stytchClient.session.getTokens();
      console.log('[DEBUG] Save API Key - Tokens:', tokens);

      if (!tokens || !tokens.session_token) {
        setMessage('Error: No valid session. Please log in again.');
        setLoading(false);
        return;
      }

      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/user/api-key`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${tokens.session_token}`
        },
        body: JSON.stringify({
          quendoo_api_key: apiKey
        })
      });

      if (response.ok) {
        setMessage('API key saved successfully!');
        setCurrentApiKey(apiKey);
        setApiKey('');
      } else {
        const error = await response.json();
        setMessage(`Error: ${error.error || 'Failed to save API key'}`);
      }
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await stytchClient.session.revoke();
  };

  if (!user) {
    const handleAuth = async (e) => {
      e.preventDefault();
      setLoginLoading(true);
      setLoginMessage('');

      try {
        if (isSignup) {
          // Sign up with email/password
          await stytchClient.passwords.create({
            email: email,
            password: password,
            session_duration_minutes: 60
          });
          setLoginMessage('Account created successfully! You are now logged in.');
        } else {
          // Login with email/password
          await stytchClient.passwords.authenticate({
            email: email,
            password: password,
            session_duration_minutes: 60
          });
          setLoginMessage('Login successful!');
        }
        setEmail('');
        setPassword('');
      } catch (error) {
        console.error('Auth error:', error);
        setLoginMessage(`Error: ${error.error_message || error.message || 'Authentication failed'}`);
      } finally {
        setLoginLoading(false);
      }
    };

    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>Quendoo MCP</h1>
          {oauthRedirectUrl ? (
            <p>🔐 Sign in to authorize Claude Desktop access</p>
          ) : (
            <p>{isSignup ? 'Create an account' : 'Sign in to manage your API keys'}</p>
          )}

          <form onSubmit={handleAuth}>
            <div className="form-group">
              <label htmlFor="email">Email Address</label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                required
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                minLength="8"
                className="form-input"
              />
              <small>Password must be at least 8 characters</small>
            </div>

            <button
              type="submit"
              disabled={loginLoading || !email || !password}
              className="primary-button"
            >
              {loginLoading ? (isSignup ? 'Creating account...' : 'Signing in...') : (isSignup ? 'Sign Up' : 'Sign In')}
            </button>
          </form>

          <div className="auth-toggle">
            <button
              type="button"
              onClick={() => {
                setIsSignup(!isSignup);
                setLoginMessage('');
              }}
              className="link-button"
            >
              {isSignup ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
            </button>
          </div>

          {loginMessage && (
            <div className={`message ${loginMessage.includes('Error') ? 'error' : 'success'}`}>
              {loginMessage}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>Quendoo MCP Dashboard</h1>
        <div className="user-info">
          <span>{user.emails[0]?.email}</span>
          <button onClick={handleLogout} className="secondary-button">
            Logout
          </button>
        </div>
      </header>

      <main className="dashboard-main">
        <div className="card">
          <h2>API Key Management</h2>

          {currentApiKey && (
            <div className="current-key-info">
              <p><strong>Current API Key:</strong></p>
              <code>{currentApiKey.substring(0, 20)}...{currentApiKey.substring(currentApiKey.length - 4)}</code>
            </div>
          )}

          <form onSubmit={handleSaveApiKey}>
            <div className="form-group">
              <label htmlFor="apiKey">Quendoo API Key</label>
              <input
                type="text"
                id="apiKey"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your Quendoo PMS API key"
                required
                className="form-input"
              />
              <small>
                Find your API key in your Quendoo PMS dashboard under Settings → API
              </small>
            </div>

            <button
              type="submit"
              disabled={loading || !apiKey}
              className="primary-button"
            >
              {loading ? 'Saving...' : 'Save API Key'}
            </button>
          </form>

          {message && (
            <div className={`message ${message.includes('Error') ? 'error' : 'success'}`}>
              {message}
            </div>
          )}
        </div>

        <div className="card info-card">
          <h3>How to use</h3>
          <ol>
            <li>Get your Quendoo PMS API key from your Quendoo dashboard</li>
            <li>Enter it in the form above and click "Save API Key"</li>
            <li>Open Claude Desktop and connect to the Quendoo MCP server</li>
            <li>Your API key will be loaded automatically!</li>
          </ol>

          <h3>MCP Server URL</h3>
          <code className="server-url">
            https://quendoo-mcp-server-880871219885.us-central1.run.app/sse
          </code>
        </div>
      </main>
    </div>
  );
}

function App() {
  return (
    <StytchProvider stytch={stytch}>
      <ApiKeyManagement />
    </StytchProvider>
  );
}

export default App;
