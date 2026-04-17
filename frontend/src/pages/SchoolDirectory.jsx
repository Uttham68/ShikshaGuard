import React, { useState } from 'react';
import { Search, Building, Users, AlertTriangle, GraduationCap, MapPin, TrendingUp, Clock, Calculator, BarChart2 } from 'lucide-react';
import api from '../api';

const SchoolDirectory = () => {
    const [query, setQuery] = useState('');
    const [school, setSchool] = useState(null);
    const [forecast, setForecast] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError(null);
        
        try {
            const [schoolRes, forecastRes] = await Promise.all([
                api.get(`/school/${query.trim()}`),
                api.post('/forecast', { 
                    total_students: 0, 
                    school_pseudocode: query.trim(),
                    years_ahead: 5
                }).catch(() => null)
            ]);
            
            setSchool(schoolRes.data);
            setForecast(forecastRes?.data);
        } catch (err) {
            setError(err.response?.data?.detail || "Institution profile not found in database.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="animate-fade-in">
            <header style={{ marginBottom: '3rem' }}>
                <h1 style={{ marginBottom: '0.25rem' }}>Institution Search</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>Lookup school baselines and enrollment projections.</p>
            </header>

            {/* Search Input */}
            <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '3rem' }}>
                <form onSubmit={handleSearch} style={{ display: 'flex', gap: '1rem' }}>
                    <div style={{ flex: 1, position: 'relative' }}>
                        <Search style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} size={18} />
                        <input 
                            className="input-field" 
                            style={{ paddingLeft: '3rem' }}
                            placeholder="Enter 7-digit UDISE code (e.g. 1003076)"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                        />
                    </div>
                    <button type="submit" className="btn btn-primary" disabled={loading}>
                        {loading ? 'Searching...' : 'Search AI Base'}
                    </button>
                </form>
            </div>

            {error && (
                <div style={{ background: 'rgba(239, 68, 68, 0.05)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.1)', color: 'var(--danger)', display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '2rem', fontSize: '0.875rem' }}>
                    <AlertTriangle size={18} /> {error}
                </div>
            )}

            {school && !loading && (
                <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '3rem' }}>
                    
                    {/* Institution Profile */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2rem' }}>
                        <div className="glass-panel" style={{ padding: '2rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', marginBottom: '2rem' }}>
                                <div style={{ width: '48px', height: '48px', background: 'var(--bg-secondary)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-blue)' }}>
                                    <Building size={24} />
                                </div>
                                <div>
                                    <h2 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>{school.school_name}</h2>
                                    <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: '0.25rem 0 0 0' }}>{school.pseudocode} • {school.school_level}</p>
                                </div>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.5rem' }}>Active Enrollment</div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                        <Users size={20} color="var(--accent-blue)" /> {school.total_students}
                                    </div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.5rem' }}>Resources</div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                        <Calculator size={20} color="var(--accent-purple)" /> {school.total_tch} Staff
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="glass-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '1rem' }}>AI Threat Index</div>
                            <div style={{ fontSize: '3rem', fontWeight: 800, color: school.risk_score > 70 ? 'var(--danger)' : 'var(--text-primary)', letterSpacing: '-0.05em' }}>
                                {school.risk_score?.toFixed(1)}
                            </div>
                            <div style={{ marginTop: '0.5rem' }}>
                                <span className={`badge ${school.risk_level === 'High' ? 'badge-danger' : 'badge-success'}`}>
                                    {school.risk_level} Priority
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Forecast Section */}
                    {forecast && (
                        <div className="glass-panel" style={{ padding: '2rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
                                <BarChart2 size={20} color="var(--accent-purple)" />
                                <h3 style={{ fontSize: '1.125rem', fontWeight: 700, margin: 0 }}>Enrollment Projections (5-Year AI Forecast)</h3>
                            </div>
                            
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
                                {forecast.projected_enrollment.map((proj, i) => (
                                    <div key={i} style={{ padding: '1.25rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', textAlign: 'center' }}>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Year {proj.year}</div>
                                        <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{proj.projected_students}</div>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--success)', marginTop: '0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.2rem' }}>
                                            <TrendingUp size={10}/> +{((proj.projected_students / school.total_students - 1) * 100).toFixed(0)}%
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div style={{ background: 'rgba(59, 130, 246, 0.05)', padding: '1.25rem', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>Capacity Exhaustion Oracle</div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>Predicted requirements for Year {forecast.final_year_projection.year}</div>
                                </div>
                                <div style={{ display: 'flex', gap: '2rem' }}>
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{ fontSize: '1rem', fontWeight: 700 }}>+{forecast.final_year_projection.classrooms_needed}</div>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Rooms</div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{ fontSize: '1rem', fontWeight: 700 }}>+{forecast.final_year_projection.teachers_needed}</div>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Staff</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default SchoolDirectory;
