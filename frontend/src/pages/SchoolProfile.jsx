import React, { useState } from 'react';
import { Search, Building, AlertTriangle, CheckCircle, ShieldAlert, Zap, BookOpen, Activity, Crosshair } from 'lucide-react';
import api from '../api';

const SchoolProfile = () => {
    const [query, setQuery] = useState('');
    const [schoolData, setSchoolData] = useState(null);
    const [riskData, setRiskData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError(null);
        
        try {
            const schoolRes = await api.get(`/school/${query.trim()}`);
            setSchoolData(schoolRes.data);

            const riskRes = await api.post('/risk-score', { 
                school_pseudocode: schoolRes.data.pseudocode,
                total_students: schoolRes.data.total_students,
                total_tch: schoolRes.data.total_tch,
                classrooms_total: schoolRes.data.classrooms_total,
                school_level: schoolRes.data.school_level,
                has_girls_toilet: schoolRes.data.has_girls_toilet,
                has_ramp: schoolRes.data.has_ramp,
                has_electricity: schoolRes.data.has_electricity,
                has_handwash: schoolRes.data.has_handwash,
                has_boundary_wall: schoolRes.data.has_boundary_wall,
                infrastructure_gap: schoolRes.data.infrastructure_gap
            });
            setRiskData(riskRes.data);
            
        } catch (err) {
            setError(err.response?.data?.detail || "Institution profile not found locally or in remote DB.");
            setSchoolData(null);
            setRiskData(null);
        } finally {
            setLoading(false);
        }
    };

    const MetricCard = ({ title, value, icon }) => (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', borderBottom: '1px solid var(--border-light)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{ width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-secondary)', borderRadius: '6px', color: 'var(--text-muted)' }}>
                    {icon}
                </div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{title}</div>
            </div>
            <div>
                {value === 1 ? <CheckCircle size={18} color="var(--success)" /> : value === 0 ? <AlertTriangle size={18} color="var(--danger)" /> : <span style={{ fontWeight: 700, fontSize: '1rem' }}>{value}</span>}
            </div>
        </div>
    );

    return (
        <div className="animate-fade-in">
            <header style={{ marginBottom: '3rem' }}>
                <h1 style={{ marginBottom: '0.25rem' }}>Institution Deep-Dive</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>Comprehensive UDISE+ baseline and automated risk teardown.</p>
            </header>

            <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '3rem' }}>
                <form onSubmit={handleSearch} style={{ display: 'flex', gap: '1rem' }}>
                    <div style={{ flex: 1, position: 'relative' }}>
                        <Search style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} size={18} />
                        <input 
                            className="input-field" 
                            style={{ paddingLeft: '3rem' }}
                            placeholder="Enter 11-digit UDISE code (e.g. 1003076)"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                        />
                    </div>
                    <button type="submit" className="btn btn-primary" disabled={loading}>
                        {loading ? 'Compiling Profile...' : 'Extract Analytics'}
                    </button>
                </form>
            </div>

            {error && (
                <div style={{ background: 'rgba(239, 68, 68, 0.05)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.1)', color: 'var(--danger)', display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '2rem', fontSize: '0.875rem' }}>
                    <AlertTriangle size={18} /> {error}
                </div>
            )}

            {schoolData && riskData && (
                <div className="animate-fade-in" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.5fr)', gap: '2rem' }}>
                    
                    {/* Left Col: UDISE Structural Baseline */}
                    <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
                        <div style={{ padding: '2rem', borderBottom: '1px solid var(--border-light)', background: 'linear-gradient(180deg, rgba(255,255,255,0.03) 0%, transparent 100%)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
                                <Building size={24} color="var(--accent-blue)" />
                                <h2 style={{ fontSize: '1.5rem', margin: 0, fontWeight: 800 }}>Profile Baseline</h2>
                            </div>
                            <div style={{ color: 'var(--text-primary)', fontSize: '0.95rem', fontWeight: 700, marginLeft: '2.5rem' }}>{schoolData.school_name || `School ${schoolData.pseudocode}`}</div>
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginLeft: '2.5rem', marginTop: '0.2rem' }}>UDISE {schoolData.pseudocode}</div>
                        </div>

                        <div style={{ padding: '1rem' }}>
                            <MetricCard title="Total Students" value={schoolData.total_students} icon={<BookOpen size={16} />} />
                            <MetricCard title="Available Staff" value={schoolData.total_tch} icon={<BookOpen size={16} />} />
                            <MetricCard title="Student-Teacher Ratio" value={schoolData.ptr?.toFixed(1) || '-'} icon={<Activity size={16} />} />
                            <MetricCard title="Classrooms Active" value={schoolData.classrooms_total} icon={<Building size={16} />} />
                            <MetricCard title="Girls Toilet Facilities" value={schoolData.has_girls_toilet} icon={<ShieldAlert size={16} />} />
                            <MetricCard title="Boys Toilet Facilities" value={schoolData.has_boys_toilet} icon={<ShieldAlert size={16} />} />
                            <MetricCard title="Handwash Available" value={schoolData.has_handwash} icon={<Zap size={16} />} />
                            <MetricCard title="Ramp Access" value={schoolData.has_ramp} icon={<Crosshair size={16} />} />
                            <MetricCard title="Electricity Grid Connected" value={schoolData.has_electricity} icon={<Zap size={16} />} />
                        </div>
                    </div>

                    {/* Right Col: Risk Engine Details */}
                    <div>
                        <div className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
                                <ShieldAlert size={24} color="var(--warning)" />
                                <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Vulnerability Scoring Engine</h3>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
                                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '12px', textAlign: 'center', border: `1px solid ${riskData.risk_score > 70 ? 'var(--danger)' : 'var(--border-light)'}`}}>
                                    <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.5rem' }}>Aggregate Risk Score</div>
                                    <div style={{ fontSize: '3rem', fontWeight: 800, color: riskData.risk_score > 70 ? 'var(--danger)' : 'white' }}>{riskData.risk_score.toFixed(1)}</div>
                                </div>
                                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '12px', textAlign: 'center' }}>
                                    <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.5rem' }}>Urgency Index</div>
                                    <div style={{ fontSize: '3rem', fontWeight: 800, color: 'var(--accent-purple)' }}>{riskData.urgency_score.toFixed(1)}</div>
                                </div>
                            </div>

                            <div style={{ marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 600 }}>Risk Breakdown Vectors</div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                {Object.entries(riskData.breakdown).map(([factor, score]) => (
                                    <div key={factor}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                                            <span style={{ color: 'var(--text-secondary)' }}>{factor.replace(/_/g, ' ').toUpperCase()}</span>
                                            <span style={{ fontWeight: 600 }}>{score.toFixed(1)} / 100</span>
                                        </div>
                                        <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px' }}>
                                            <div style={{ height: '100%', borderRadius: '3px', width: `${score}%`, background: score > 50 ? 'var(--danger)' : 'var(--accent-blue)' }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="glass-panel" style={{ padding: '2rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
                                <Activity size={20} color="var(--success)" />
                                <h3 style={{ fontSize: '1.125rem', fontWeight: 700, margin: 0 }}>Key Anomalies / Indicators</h3>
                            </div>
                            
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {Object.entries(riskData.key_metrics).map(([metric, val]) => (
                                    val === true || typeof val === 'number' && val > 0 ? (
                                        <div key={metric} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem', background: 'rgba(239, 68, 68, 0.05)', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.1)' }}>
                                            <AlertTriangle size={16} color="var(--danger)" />
                                            <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                                                {metric.replace(/_/g, ' ').toUpperCase()}: <span style={{ fontWeight: 700 }}>{val}</span>
                                            </span>
                                        </div>
                                    ) : null
                                ))}
                                {!Object.values(riskData.key_metrics).some(v => v === true || (typeof v === 'number' && v > 0)) && (
                                    <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>No critical localized anomalies detected for this UDISE base.</div>
                                )}
                            </div>
                        </div>
                    </div>

                </div>
            )}
        </div>
    );
};

export default SchoolProfile;
