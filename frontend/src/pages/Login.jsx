import React, { useState } from 'react';
import { Key, User, ShieldCheck, GraduationCap, ArrowRight, AlertCircle, Loader, Eye, EyeOff } from 'lucide-react';
import api from '../api';
import '../styles/login.css';

const Login = ({ onLoginSuccess }) => {
    const [isRegisterMode, setIsRegisterMode] = useState(false);
    const [activeRole, setActiveRole] = useState('admin');
    const [showPassword, setShowPassword] = useState(false);
    const [showRegisterPassword, setShowRegisterPassword] = useState(false);
    const [showRegisterConfirmPassword, setShowRegisterConfirmPassword] = useState(false);
    const [credentials, setCredentials] = useState({
        username: '',
        password: ''
    });
    const [registerData, setRegisterData] = useState({
        full_name: '',
        school_pseudocode: '',
        username: '',
        password: '',
        confirm_password: ''
    });
    const [status, setStatus] = useState({ loading: false, error: null });
    const [focusedField, setFocusedField] = useState(null);

    const handleRoleSwitch = (role) => {
        setActiveRole(role);
        setCredentials({
            username: '',
            password: ''
        });
        setStatus({ loading: false, error: null });
    };

    const handleChange = (e) => {
        setCredentials({ ...credentials, [e.target.name]: e.target.value });
    };

    const handleRegisterChange = (e) => {
        setRegisterData({ ...registerData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setStatus({ loading: true, error: null });
        
        const formData = new URLSearchParams();
        formData.append('username', credentials.username);
        formData.append('password', credentials.password);

        try {
            const response = await api.post('/auth/login', formData, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });
            
            const { access_token, role, full_name, school_pseudocode } = response.data;
            
            localStorage.setItem('token', access_token);
            localStorage.setItem('role', role);
            if(full_name) localStorage.setItem('full_name', full_name);
            if(school_pseudocode) localStorage.setItem('school_pseudocode', school_pseudocode);

            onLoginSuccess({ role, school: school_pseudocode });
            
        } catch (err) {
            setStatus({ 
                loading: false, 
                error: err.response?.data?.detail || "Connection failed. Is the backend running?" 
            });
        }
    };

    const handleRegisterSubmit = async (e) => {
        e.preventDefault();
        setStatus({ loading: true, error: null });

        if (registerData.password !== registerData.confirm_password) {
            setStatus({ loading: false, error: 'Passwords do not match!' });
            return;
        }

        if (!registerData.school_pseudocode || !registerData.username || !registerData.password || !registerData.full_name) {
            setStatus({ loading: false, error: 'Please fill all required fields!' });
            return;
        }

        try {
            await api.post('/auth/register-principal', {
                full_name: registerData.full_name,
                school_pseudocode: registerData.school_pseudocode,
                username: registerData.username,
                password: registerData.password
            });

            setStatus({ 
                loading: false, 
                error: null 
            });
            
            // Auto-login after successful registration
            const formData = new URLSearchParams();
            formData.append('username', registerData.username);
            formData.append('password', registerData.password);

            const loginResponse = await api.post('/auth/login', formData, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });

            const { access_token, role, full_name, school_pseudocode } = loginResponse.data;
            
            localStorage.setItem('token', access_token);
            localStorage.setItem('role', role);
            localStorage.setItem('full_name', full_name);
            localStorage.setItem('school_pseudocode', school_pseudocode);

            onLoginSuccess({ role, school: school_pseudocode });
        } catch (err) {
            setStatus({ 
                loading: false, 
                error: err.response?.data?.detail || "Registration failed. Please try again." 
            });
        }
    };

    const roleOptions = [
        { id: 'admin', label: 'Administrator', icon: ShieldCheck, color: 'var(--accent-blue)' },
        { id: 'principal', label: 'Principal', icon: GraduationCap, color: 'var(--accent-purple)' }
    ];

    return (
        <div className="login-container">
            <div className="login-background" />
            
            <div className="login-content">
                {/* Left: Header Section */}
                <div className="login-left">
                    <div className="login-header">
                        <div className="login-logo-wrapper">
                            <div className="login-logo">
                                <img src="/SG.png" alt="ShikshaGuard Logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                            </div>
                        </div>
                        <h1 className="login-title">Welcome to ShikshaGaurd</h1>
                        <p className="login-subtitle">Intelligent School Infrastructure Assessment System</p>
                    </div>
                </div>

                {/* Right: Login Card */}
                <div className="login-right">
                    <div className="login-card">
                        {!isRegisterMode ? (
                            <>
                                {/* Role Selection */}
                                <div className="role-selector">
                                    {roleOptions.map((role) => {
                                        const IconComponent = role.icon;
                                        const isActive = activeRole === role.id;
                                        return (
                                            <button
                                                key={role.id}
                                                type="button"
                                                className={`role-button ${isActive ? 'active' : ''}`}
                                                onClick={() => handleRoleSwitch(role.id)}
                                            >
                                                <div className="role-button-content">
                                                    <IconComponent 
                                                        size={20} 
                                                        color={isActive ? role.color : 'var(--text-muted)'}
                                                    />
                                                    <span>{role.label}</span>
                                                </div>
                                            </button>
                                        );
                                    })}
                                </div>

                                {/* Form */}
                                <form onSubmit={handleSubmit} className="login-form">
                                    {/* Username Field */}
                                    <div className="form-group">
                                        <label className="form-label">
                                            <User size={16} />
                                            <span>Username</span>
                                        </label>
                                        <div className={`input-wrapper ${focusedField === 'username' ? 'focused' : ''}`}>
                                            <input
                                                type="text"
                                                name="username"
                                                className="login-input"
                                                placeholder="Enter your username"
                                                required
                                                value={credentials.username}
                                                onChange={handleChange}
                                                onFocus={() => setFocusedField('username')}
                                                onBlur={() => setFocusedField(null)}
                                            />
                                        </div>
                                    </div>

                                    {/* Password Field */}
                                    <div className="form-group">
                                        <label className="form-label">
                                            <Key size={16} />
                                            <span>Password</span>
                                        </label>
                                        <div className={`input-wrapper ${focusedField === 'password' ? 'focused' : ''}`}>
                                            <input
                                                type={showPassword ? 'text' : 'password'}
                                                name="password"
                                                className="login-input"
                                                placeholder="Enter your password"
                                                required
                                                value={credentials.password}
                                                onChange={handleChange}
                                                onFocus={() => setFocusedField('password')}
                                                onBlur={() => setFocusedField(null)}
                                            />
                                            <button
                                                type="button"
                                                className="password-toggle"
                                                onClick={() => setShowPassword(!showPassword)}
                                                title={showPassword ? 'Hide password' : 'Show password'}
                                            >
                                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                            </button>
                                        </div>
                                    </div>

                                    {/* Error Message */}
                                    {status.error && (
                                        <div className="error-alert">
                                            <AlertCircle size={18} />
                                            <span>{status.error}</span>
                                        </div>
                                    )}

                                    {/* Submit Button */}
                                    <button
                                        type="submit"
                                        className="login-button"
                                        disabled={status.loading}
                                    >
                                        {status.loading ? (
                                            <>
                                                <Loader size={18} className="spinner" />
                                                <span>Authenticating...</span>
                                            </>
                                        ) : (
                                            <>
                                                <span>Sign In</span>
                                                <ArrowRight size={18} />
                                            </>
                                        )}
                                    </button>

                                    {/* Register Link for Principals */}
                                    {activeRole === 'principal' && (
                                        <div className="register-footer" style={{ textAlign: 'center', marginTop: '0.8rem', paddingTop: '0.8rem', borderTop: '1px solid var(--border-light)' }}>
                                            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>New Principal?</p>
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setIsRegisterMode(true);
                                                    setStatus({ loading: false, error: null });
                                                }}
                                                style={{
                                                    background: 'transparent',
                                                    border: 'none',
                                                    color: 'var(--accent-blue)',
                                                    fontWeight: 600,
                                                    cursor: 'pointer',
                                                    fontSize: '0.95rem',
                                                    textDecoration: 'underline'
                                                }}
                                            >
                                                Create Account with UDISE
                                            </button>
                                        </div>
                                    )}
                                </form>
                            </>
                        ) : (
                            <>
                                {/* Registration Form */}
                                <div style={{ marginBottom: '1.5rem', gridColumn: '1 / -1' }}>
                                    <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>Register as Principal</h2>
                                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Create your account using your school's UDISE code</p>
                                </div>

                                <form onSubmit={handleRegisterSubmit} className="login-form">
                                    {/* Full Name */}
                                    <div className="form-group">
                                        <label className="form-label">
                                            <User size={16} />
                                            <span>Full Name</span>
                                        </label>
                                        <div className={`input-wrapper ${focusedField === 'full_name' ? 'focused' : ''}`}>
                                            <input
                                                type="text"
                                                name="full_name"
                                                className="login-input"
                                                placeholder="Your full name"
                                                required
                                                value={registerData.full_name}
                                                onChange={handleRegisterChange}
                                                onFocus={() => setFocusedField('full_name')}
                                                onBlur={() => setFocusedField(null)}
                                            />
                                        </div>
                                    </div>

                                    {/* UDISE Code */}
                                    <div className="form-group">
                                        <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                            <ShieldCheck size={16} />
                                            <span>School UDISE Code</span>
                                            <span style={{ color: 'var(--danger)', fontWeight: 700 }}>*</span>
                                        </label>
                                        <div className={`input-wrapper ${focusedField === 'school_pseudocode' ? 'focused' : ''}`}>
                                            <input
                                                type="text"
                                                name="school_pseudocode"
                                                className="login-input"
                                                placeholder="e.g., 1003076"
                                                required
                                                value={registerData.school_pseudocode}
                                                onChange={handleRegisterChange}
                                                onFocus={() => setFocusedField('school_pseudocode')}
                                                onBlur={() => setFocusedField(null)}
                                                pattern="[0-9]+"
                                                title="UDISE must be numeric"
                                            />
                                        </div>
                                        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>This UDISE will be locked in your proposals for security.</p>
                                    </div>

                                    {/* Username */}
                                    <div className="form-group">
                                        <label className="form-label">
                                            <User size={16} />
                                            <span>Username</span>
                                        </label>
                                        <div className={`input-wrapper ${focusedField === 'username' ? 'focused' : ''}`}>
                                            <input
                                                type="text"
                                                name="username"
                                                className="login-input"
                                                placeholder="Choose a username"
                                                required
                                                value={registerData.username}
                                                onChange={handleRegisterChange}
                                                onFocus={() => setFocusedField('username')}
                                                onBlur={() => setFocusedField(null)}
                                            />
                                        </div>
                                    </div>

                                    {/* Password */}
                                    <div className="form-group">
                                        <label className="form-label">
                                            <Key size={16} />
                                            <span>Password</span>
                                        </label>
                                        <div className={`input-wrapper ${focusedField === 'password' ? 'focused' : ''}`}>
                                            <input
                                                type={showRegisterPassword ? 'text' : 'password'}
                                                name="password"
                                                className="login-input"
                                                placeholder="Enter a strong password"
                                                required
                                                value={registerData.password}
                                                onChange={handleRegisterChange}
                                                onFocus={() => setFocusedField('password')}
                                                onBlur={() => setFocusedField(null)}
                                            />
                                            <button
                                                type="button"
                                                className="password-toggle"
                                                onClick={() => setShowRegisterPassword(!showRegisterPassword)}
                                                title={showRegisterPassword ? 'Hide password' : 'Show password'}
                                            >
                                                {showRegisterPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                            </button>
                                        </div>
                                    </div>

                                    {/* Confirm Password */}
                                    <div className="form-group">
                                        <label className="form-label">
                                            <Key size={16} />
                                            <span>Confirm Password</span>
                                        </label>
                                        <div className={`input-wrapper ${focusedField === 'confirm_password' ? 'focused' : ''}`}>
                                            <input
                                                type={showRegisterConfirmPassword ? 'text' : 'password'}
                                                name="confirm_password"
                                                className="login-input"
                                                placeholder="Confirm your password"
                                                required
                                                value={registerData.confirm_password}
                                                onChange={handleRegisterChange}
                                                onFocus={() => setFocusedField('confirm_password')}
                                                onBlur={() => setFocusedField(null)}
                                            />
                                            <button
                                                type="button"
                                                className="password-toggle"
                                                onClick={() => setShowRegisterConfirmPassword(!showRegisterConfirmPassword)}
                                                title={showRegisterConfirmPassword ? 'Hide password' : 'Show password'}
                                            >
                                                {showRegisterConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                            </button>
                                        </div>
                                    </div>

                                    {/* Error Message */}
                                    {status.error && (
                                        <div className="error-alert">
                                            <AlertCircle size={18} />
                                            <span>{status.error}</span>
                                        </div>
                                    )}

                                    {/* Submit Button */}
                                    <button
                                        type="submit"
                                        className="login-button"
                                        disabled={status.loading}
                                    >
                                        {status.loading ? (
                                            <>
                                                <Loader size={18} className="spinner" />
                                                <span>Creating Account...</span>
                                            </>
                                        ) : (
                                            <>
                                                <span>Register</span>
                                                <ArrowRight size={18} />
                                            </>
                                        )}
                                    </button>

                                    {/* Back to Login */}
                                    <div className="register-footer" style={{ textAlign: 'center', marginTop: '0.8rem', paddingTop: '0.8rem', borderTop: '1px solid var(--border-light)' }}>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setIsRegisterMode(false);
                                                setStatus({ loading: false, error: null });
                                                setRegisterData({
                                                    full_name: '',
                                                    school_pseudocode: '',
                                                    username: '',
                                                    password: '',
                                                    confirm_password: ''
                                                });
                                            }}
                                            style={{
                                                background: 'transparent',
                                                border: 'none',
                                                color: 'var(--accent-blue)',
                                                fontWeight: 600,
                                                cursor: 'pointer',
                                                fontSize: '0.95rem',
                                                textDecoration: 'underline'
                                            }}
                                        >
                                            Back to Login
                                        </button>
                                    </div>
                                </form>
                            </>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="login-footer">
                        <p>Secure school administration platform powered by AI</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Login;
