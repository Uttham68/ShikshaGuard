import React, { useState } from 'react';
import { LineChart, BarChart } from 'lucide-react'; // Mocking icons for visualization
import { Search, TrendingUp, AlertTriangle, Download, Database, Users, GraduationCap } from 'lucide-react';
import api from '../api';

const Forecaster = () => {
    const [query, setQuery] = useState('');
    const [years, setYears] = useState(5);
    const [forecast, setForecast] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSimulationRequest = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setError(null);
        
        try {
            // First we need school data to pass into forecast accurately. Wait, forecast endpoint takes total_students and school_pseudocode. 
            // In the backend: forecast(req: ForecastRequest) needs total_students, total_tch, classrooms_total, school_level.
            // Let's fetch school first:
            const schoolRes = await api.get(`/school/${query.trim()}`);
            const school = schoolRes.data;

            const forecastRes = await api.post('/forecast', { 
                school_pseudocode: query.trim(),
                total_students: school.total_students,
                total_tch: school.total_tch,
                classrooms_total: school.classrooms_total,
                school_level: school.school_level,
                years_ahead: Number(years)
            });
            
            setForecast({ ...forecastRes.data, school });
        } catch (err) {
            setError(err.response?.data?.detail || "Algorithm failed to resolve predictive paths for this UDISE.");
            setForecast(null);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="animate-fade-in">
            <header style={{ marginBottom: '3rem' }}>
                <h1 style={{ marginBottom: '0.25rem' }}>Dynamic Forecaster</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>XGBoost-powered multi-year infrastructure projections.</p>
            </header>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 2.5fr)', gap: '2rem' }}>
                
                {/* Control Panel Sidebar */}
                <div className="glass-panel" style={{ padding: '2rem', height: 'fit-content' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
                        <Database size={20} color="var(--accent-blue)" />
                        <h2 style={{ fontSize: '1.125rem', fontWeight: 700, margin: 0 }}>Projection Parameters</h2>
                    </div>

                    <form onSubmit={handleSimulationRequest}>
                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>School Pseudocode (UDISE)</label>
                            <div style={{ position: 'relative' }}>
                                <Search style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} size={16} />
                                <input 
                                    className="input-field" 
                                    style={{ paddingLeft: '2.5rem' }}
                                    placeholder="1003076"
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    required
                                />
                            </div>
                        </div>

                        <div style={{ marginBottom: '2rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                <label style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Timeline (Years Ahead)</label>
                                <span style={{ fontWeight: 700, color: 'var(--accent-purple)' }}>+{years} Yrs</span>
                            </div>
                            <input 
                                type="range" 
                                min="3" 
                                max="10" 
                                step="1" 
                                style={{ width: '100%', cursor: 'pointer' }}
                                value={years}
                                onChange={(e) => setYears(e.target.value)}
                            />
                        </div>

                        <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
                            {loading ? 'Simulating...' : 'Run Projection Model'}
                        </button>
                    </form>

                    {error && (
                        <div style={{ marginTop: '1.5rem', background: 'rgba(239, 68, 68, 0.05)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.1)', color: 'var(--danger)', fontSize: '0.875rem' }}>
                            <AlertTriangle size={16} style={{ marginBottom: '0.25rem' }} /> {error}
                        </div>
                    )}
                </div>

                {/* Dashboard Output */}
                <div>
                    {!forecast && !loading ? (
                        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '400px', textAlign: 'center', padding: '2rem' }}>
                            <TrendingUp size={48} style={{ opacity: 0.1, marginBottom: '1.5rem' }} />
                            <h3 style={{ fontSize: '1.25rem', margin: 0, fontWeight: 700 }}>Awaiting Parameters</h3>
                            <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>Enter a UDISE code to generate long-term structural demand models.</p>
                        </div>
                    ) : loading ? (
                        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '400px', textAlign: 'center' }}>
                            <TrendingUp size={48} className="animate-spin" color="var(--accent-purple)" style={{ opacity: 0.5, marginBottom: '1.5rem' }} />
                            <p style={{ color: 'var(--text-muted)' }}>Calculating temporal trajectories...</p>
                        </div>
                    ) : forecast && (
                        <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                            
                            <div className="glass-panel" style={{ padding: '2rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
                                    <div>
                                        <h2 style={{ fontSize: '1.5rem', margin: '0 0 0.25rem 0', fontWeight: 800 }}>{forecast.school.school_name}</h2>
                                        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.875rem' }}>{forecast.school.pseudocode} • {forecast.school.school_level} Level</p>
                                    </div>
                                    <div className="badge badge-success" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
                                        <TrendingUp size={14} /> Model Active ({forecast.assumptions.annual_growth_rate} Growth Assumed)
                                    </div>
                                </div>

                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
                                    <div className="glass-card" style={{ padding: '1.25rem' }}>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.5rem' }}>Base Enrollment</div>
                                        <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>{forecast.current_students}</div>
                                    </div>
                                    <div className="glass-card" style={{ padding: '1.25rem', borderColor: 'var(--accent-purple)' }}>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.5rem' }}>Projected Year {forecast.final_year_projection.year}</div>
                                        <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--accent-purple)' }}>{forecast.final_year_projection.students}</div>
                                    </div>
                                    <div className="glass-card" style={{ padding: '1.25rem' }}>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.5rem' }}>Model Delta</div>
                                        <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--warning)' }}>+{forecast.final_year_projection.students - forecast.current_students}</div>
                                    </div>
                                </div>
                            </div>
                            
                            {/* Graphical Chart Proxy (CSS Grid Bars) */}
                            <div className="glass-panel" style={{ padding: '2rem' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem' }}>
                                    <BarChart size={20} color="var(--accent-blue)" />
                                    <h3 style={{ fontSize: '1.125rem', fontWeight: 700, margin: 0 }}>Temporal Enrollment Distribution</h3>
                                </div>

                                <div style={{ display: 'flex', alignItems: 'flex-end', gap: '1rem', height: '240px', paddingBottom: '2rem', borderBottom: '1px solid var(--border-light)' }}>
                                    {forecast.projected_enrollment.map((proj, idx) => {
                                        const maxVal = forecast.projected_enrollment[forecast.projected_enrollment.length - 1].projected_students;
                                        const heightPct = (proj.projected_students / maxVal) * 100;
                                        return (
                                            <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', height: '100%', position: 'relative' }}>
                                                <div style={{ fontSize: '0.75rem', fontWeight: 600, position: 'absolute', top: `calc(100% - ${heightPct}% - 24px)` }}>{proj.projected_students}</div>
                                                <div style={{ 
                                                    width: '100%', 
                                                    maxWidth: '60px', 
                                                    height: `${heightPct}%`, 
                                                    background: idx === forecast.projected_enrollment.length - 1 ? 'linear-gradient(180deg, var(--accent-purple) 0%, rgba(139, 92, 246, 0.2) 100%)' : 'linear-gradient(180deg, var(--accent-blue) 0%, rgba(59, 130, 246, 0.2) 100%)',
                                                    borderRadius: '4px 4px 0 0',
                                                    border: '1px solid rgba(255,255,255,0.1)',
                                                    borderBottom: 'none'
                                                }} />
                                                <div style={{ position: 'absolute', bottom: '-2rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Yr {proj.year}</div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Exhaustion Alert */}
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                                <div className="glass-panel" style={{ padding: '1.5rem', background: forecast.final_year_projection.classrooms_needed > 0 ? 'rgba(239, 68, 68, 0.05)' : 'rgba(16, 185, 129, 0.05)' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                                        <Database size={18} color="var(--text-muted)" />
                                        <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>Infrastructure Gap Oracle</div>
                                    </div>
                                    <div style={{ fontSize: '2rem', fontWeight: 800 }}>+{forecast.final_year_projection.classrooms_needed} <span style={{ fontSize: '1rem', color: 'var(--text-muted)', fontWeight: 500 }}>Classrooms</span></div>
                                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Required by year {forecast.final_year_projection.year} based on a density threshold of {forecast.assumptions.target_classroom_density} per room.</p>
                                </div>
                                <div className="glass-panel" style={{ padding: '1.5rem', background: forecast.final_year_projection.teachers_needed > 0 ? 'rgba(239, 68, 68, 0.05)' : 'rgba(16, 185, 129, 0.05)' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                                        <Users size={18} color="var(--text-muted)" />
                                        <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>Staffing Gap Oracle</div>
                                    </div>
                                    <div style={{ fontSize: '2rem', fontWeight: 800 }}>+{forecast.final_year_projection.teachers_needed} <span style={{ fontSize: '1rem', color: 'var(--text-muted)', fontWeight: 500 }}>Teachers</span></div>
                                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Required by year {forecast.final_year_projection.year} based on state PTR norm ({forecast.final_year_projection.ptr_threshold}:1).</p>
                                </div>
                            </div>

                        </div>
                    )}
                </div>

            </div>
        </div>
    );
};

export default Forecaster;
