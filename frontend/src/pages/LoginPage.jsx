import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/login.css';
import { API_URL } from '../config';

const Login = ({ isSignup = false }) => {
  const [view, setView] = useState(isSignup ? 'signup' : 'login');
  
  const [formData, setFormData] = useState({
    username: '',
    full_name: '',
    email: '',
    password: '',
    new_password: ''
  });
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    sessionStorage.clear();
    localStorage.clear(); 
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    setLoading(true);

    let endpoint = '';
    let body = {};

    if (view === 'reset') {
        endpoint = '/api/password-reset';
        body = { 
            username: formData.username, 
            email: formData.email, 
            new_password: formData.new_password 
        };

    } else if (view === 'signup') {
        endpoint = '/api/signup';
        body = formData;
    } else {
        endpoint = '/api/login';
        body = { username: formData.username, password: formData.password };
    }
    
    try {
      const res = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      
      const data = await res.json();

      if (res.ok) {
        if (view === 'signup') {
          alert("Account created! Please log in.");
          setView('login');
          setFormData(prev => ({ ...prev, password: '' })); 
        } else if (view === 'reset') {
          setSuccessMsg("Password reset successfully! Please log in.");
          setView('login');
          setFormData({ ...formData, password: '', new_password: '' });
        } else {
          // Login Success
          sessionStorage.setItem('username', formData.username);
          sessionStorage.setItem('token', data.token); 
          navigate('/dashboard');
        }
      } else {
        setError(data.message || data.error || "Authentication failed");
      }
    } catch (err) {
      console.error("Login Error:", err);
      setError("Server error. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  const handleViewSwitch = (newView) => {
      setView(newView);
      setError('');
      setSuccessMsg('');
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <h2>
            {view === 'signup' ? 'Create Account' : 
             view === 'reset' ? 'Reset Password' : 'Welcome Back'}
          </h2>
          <p>
            {view === 'signup' ? 'Start tracking your portfolio today' : 
             view === 'reset' ? 'Verify your details to set a new password' : 'Login to manage your crypto assets'}
          </p>
        </div>

        {error && <div className="login-error-banner">⚠️ {error}</div>}
        {successMsg && <div className="login-error-banner" style={{color: 'var(--accent-green)', borderColor: 'var(--accent-green)', background: 'rgba(0,223,154,0.1)'}}>✅ {successMsg}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          {view === 'signup' && (
            <div className="login-form-group">
                <label>Full Name</label>
                <input 
                  type="text" 
                  name="full_name" 
                  className="login-form-input"
                  placeholder="e.g. John Doe" 
                  value={formData.full_name} 
                  onChange={handleChange} 
                  required 
                />
            </div>
          )}

          <div className="login-form-group">
            <label>Username</label>
            <input 
              type="text" 
              name="username" 
              className="login-form-input"
              placeholder="Enter your username" 
              value={formData.username} 
              onChange={handleChange} 
              required 
            />
          </div>

          {(view === 'signup' || view === 'reset') && (
            <div className="login-form-group">
                <label>Email Address</label>
                <input 
                  type="email" 
                  name="email" 
                  className="login-form-input"
                  placeholder="name@example.com" 
                  value={formData.email} 
                  onChange={handleChange} 
                  required 
                />
            </div>
          )}

          {view === 'reset' ? (
             <div className="login-form-group">
                <label>New Password</label>
                <input 
                  type="password" 
                  name="new_password" 
                  className="login-form-input"
                  placeholder="Enter new password" 
                  value={formData.new_password} 
                  onChange={handleChange} 
                  required 
                />
             </div>
          ) : (
             <div className="login-form-group">
                <label>Password</label>
                <input 
                  type="password" 
                  name="password" 
                  className="login-form-input"
                  placeholder="••••••••" 
                  value={formData.password} 
                  onChange={handleChange} 
                  required 
                />
             </div>
          )}

          <button type="submit" className="login-btn-submit" disabled={loading}>
            {loading ? 'Processing...' : (view === 'signup' ? 'Sign Up' : view === 'reset' ? 'Update Password' : 'Log In')}
          </button>
        </form>

        <div className="login-footer">
          {view === 'login' && (
              <p style={{marginBottom: '10px'}}>
                  <span onClick={() => handleViewSwitch('reset')} className="login-link-text" style={{marginLeft: 0, fontSize: '0.9rem'}}>
                      Forgot Password?
                  </span>
              </p>
          )}
          
          <p>
            {view === 'signup' ? "Already have an account?" : "Don't have an account?"} 
            <span onClick={() => handleViewSwitch(view === 'signup' ? 'login' : 'signup')} className="login-link-text">
              {view === 'signup' ? ' Log In' : ' Sign Up'}
            </span>
          </p>
          
          {view === 'reset' && (
              <p style={{marginTop: '10px'}}>
                  <span onClick={() => handleViewSwitch('login')} className="login-link-text">
                      ← Back to Login
                  </span>
              </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default Login;