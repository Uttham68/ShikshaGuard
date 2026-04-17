import React, { useEffect, useState } from 'react';
import { 
    Activity, 
    School, 
    FileText, 
    CheckCircle, 
    Bell, 
    AlertTriangle, 
    TrendingDown, 
    Target,
    Zap,
    TrendingUp,
    ShieldAlert
} from 'lucide-react';
import api from '../api';

const Dashboard = () => {
    const [stats, setStats] = useState(null);
    const [alerts, setAlerts] = useState(null);
    const [loading, setLoading] = useState(true);
    const [issueDrilldown, setIssueDrilldown] = useState({ loading: false, data: null, error: null });

    useEffect(() => {
        const fetchData = async () => {
            try {
                const userRole = localStorage.getItem('role');
                
                let dashboardRes;
                if (userRole === 'principal') {
                    // For principals: fetch their profile and proposals
                    const profileRes = await api.get('/auth/me').catch(e => { 
                        return { data: null };
                    });
                    const proposalsRes = await api.get('/my-proposals').catch(e => { 
                        return { data: { proposals: [] } };
                    });
                    
                    // Compute stats from principal's data
                    const profile = profileRes.data;
                    const school = profile?.school;
                    const proposals = proposalsRes.data?.proposals || [];
                    
                    // Calculate risk score from proposals
                    let totalRisk = 0;
                    let totalConfidence = 0;
                    let riskCount = 0;
                    let confidenceCount = 0;
                    
                    proposals.forEach(p => {
                        if (p.risk_score !== null && p.risk_score !== undefined) {
                            totalRisk += p.risk_score;
                            riskCount++;
                        }
                        if (p.confidence !== null && p.confidence !== undefined) {
                            totalConfidence += p.confidence;
                            confidenceCount++;
                        }
                    });
                    
                    dashboardRes = {
                        data: {
                            summary: {
                                total_schools: school ? 1 : (proposals.length > 0 ? 1 : 0),
                                total_proposals: proposals.length,
                                validated: riskCount,
                            },
                            averages: {
                                risk_score: riskCount > 0 ? (totalRisk / riskCount).toFixed(1) : (school?.risk_score || 0),
                                confidence: confidenceCount > 0 ? (totalConfidence / confidenceCount).toFixed(4) : 0,
                            },
                            top_risk_schools: (school || proposals.length > 0) ? [{
                                pseudocode: school?.pseudocode || proposals[0]?.school_pseudocode || 'N/A',
                                school_name: profile?.full_name || proposals[0]?.school_name || `School ${school?.pseudocode}`,
                                risk_score: school?.risk_score || proposals[0]?.risk_score || 0,
                                ptr: school?.ptr || 'N/A',
                            }] : [],
                        }
                    };
                } else {
                    // For admins: fetch full dashboard
                    dashboardRes = await api.get('/dashboard').catch(() => ({ data: { summary: {}, results: [] } }));
                }
                
                const alertsRes = await api.get('/planning/alerts').catch(() => ({ data: { alerts: [] } }));
                
                setStats(dashboardRes.data);
                setAlerts(alertsRes.data);
            } catch (err) {
                console.error("Dashboard intel failure", err);
                setStats(null);
                setAlerts({ alerts: [] });
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const handleIssueClick = async (alert) => {
        setIssueDrilldown({ loading: true, data: null, error: null });
        try {
            const response = await api.get(`/planning/issue-schools/${alert.code}`);
            setIssueDrilldown({ loading: false, data: response.data, error: null });
        } catch (err) {
            setIssueDrilldown({
                loading: false,
                data: null,
                error: err.response?.data?.detail || "Failed to load schools for this issue.",
            });
        }
    };

    if (loading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
            <Activity className="animate-spin" size={32} color="var(--accent-blue)" />
        </div>
    );

    const userRole = localStorage.getItem('role');
    
    return (
        <div className="animate-fade-in">
            <header style={{ marginBottom: '3rem' }}>
                <h1 style={{ marginBottom: '0.25rem' }}>Overview</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>
                    {userRole === 'principal' ? 'Your school intelligence and performance metrics.' : 'Active intelligence and systemic health metrics.'}
                </p>
            </header>

            {/* Metrics Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.5rem', marginBottom: '3rem' }}>
                <div className="glass-panel" style={{ padding: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>
                            {userRole === 'principal' ? 'Your School' : 'Total Institutions'}
                        </span>
                        <School size={16} color="var(--accent-blue)" />
                    </div>
                    <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>{stats?.summary?.total_schools || 0}</div>
                    <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <TrendingUp size={12} /> Live Sync
                    </div>
                </div>

                <div className="glass-panel" style={{ padding: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Systemic Risk</span>
                        <Target size={16} color="var(--accent-purple)" />
                    </div>
                    <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>{stats?.averages?.risk_score || 0}%</div>
                    <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>Average risk index</div>
                </div>

                <div className="glass-panel" style={{ padding: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Proposals</span>
                        <FileText size={16} color="var(--accent-indigo)" />
                    </div>
                    <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>{stats?.summary?.total_proposals || 0}</div>
                    <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>Total submissions</div>
                </div>

                <div className="glass-panel" style={{ padding: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>AI Confidence</span>
                        <CheckCircle size={16} color="var(--success)" />
                    </div>
                    <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>{(stats?.averages?.confidence * 100 || 0).toFixed(1)}%</div>
                    <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>XGBoost reliability</div>
                </div>
            </div>

            {/* Alert & Priority Feed */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2rem' }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <Bell size={20} color="var(--accent-purple)" />
                        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Active Alerts</h2>
                    </div>
                    
                    <div className="glass-panel" style={{ padding: '0.5rem' }}>
                        {alerts?.alerts?.length === 0 ? (
                            <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                                <ShieldAlert size={32} style={{ opacity: 0.2, marginBottom: '1rem' }} />
                                <p>No critical anomalies detected in the system pulse.</p>
                            </div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                                {alerts?.alerts?.map((alert, i) => (
                                    <button key={i} className="alert-drilldown-row" onClick={() => handleIssueClick(alert)} style={{ 
                                        padding: '1.25rem', 
                                        borderBottom: i === alerts.alerts.length - 1 ? 'none' : '1px solid var(--border-light)',
                                        display: 'flex',
                                        gap: '1.25rem'
                                    }}>
                                        <div style={{ color: alert.type === 'CRITICAL' ? 'var(--danger)' : 'var(--warning)', marginTop: '0.25rem' }}>
                                            <AlertTriangle size={24} />
                                        </div>
                                        <div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
                                                <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>{alert.code}</span>
                                                <span className={`badge ${alert.type === 'CRITICAL' ? 'badge-danger' : 'badge-warning'}`}>{alert.type}</span>
                                            </div>
                                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.5 }}>{alert.message}</p>
                                            <div style={{ color: 'var(--accent-cyan)', fontSize: '0.75rem', fontWeight: 700 }}>View affected schools</div>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {(issueDrilldown.loading || issueDrilldown.error || issueDrilldown.data) && (
                        <div className="glass-panel issue-drilldown-panel">
                            {issueDrilldown.loading ? (
                                <div className="issue-loading">
                                    <Activity className="animate-spin" size={22} color="var(--accent-cyan)" />
                                    Loading affected schools...
                                </div>
                            ) : issueDrilldown.error ? (
                                <div className="inline-error">
                                    <AlertTriangle size={18} /> {issueDrilldown.error}
                                </div>
                            ) : (
                                <>
                                    <div className="issue-drilldown-header">
                                        <div>
                                            <span className="eyebrow">{issueDrilldown.data.code}</span>
                                            <h3>{issueDrilldown.data.title}</h3>
                                            <p>{issueDrilldown.data.description}</p>
                                        </div>
                                        <span className="badge badge-warning">{issueDrilldown.data.count} Schools</span>
                                    </div>
                                    <div className="issue-school-list">
                                        {issueDrilldown.data.schools.map((school) => (
                                            <div className="issue-school-row" key={school.pseudocode}>
                                                <div className="school-identity">
                                                    <span className="school-identity-name">{school.school_name}</span>
                                                    <span className="school-identity-code">UDISE {school.pseudocode}</span>
                                                </div>
                                                <div className="issue-school-meta">
                                                    <span>Risk {school.risk_score}</span>
                                                    <span>PTR {school.ptr}</span>
                                                    <span>{school.school_level}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>

                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <TrendingDown size={20} color="var(--danger)" />
                        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>High Risk Targets</h2>
                    </div>
                    <div className="glass-panel" style={{ padding: '1rem' }}>
                        {stats?.top_risk_schools?.map((s, i) => (
                            <div key={i} style={{ 
                                display: 'flex', 
                                justifyContent: 'space-between', 
                                alignItems: 'center', 
                                padding: '1rem',
                                borderBottom: i === stats.top_risk_schools.length - 1 ? 'none' : '1px solid var(--border-light)'
                            }}>
                                <div className="school-identity">
                                    <span className="school-identity-name">{s.school_name || `School ${s.pseudocode}`}</span>
                                    <span className="school-identity-code">UDISE {s.pseudocode}</span>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <div style={{ width: '100px', height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px' }}>
                                        <div style={{ width: `${s.risk_score}%`, height: '100%', background: 'var(--danger)' }} />
                                    </div>
                                    <span style={{ fontWeight: 700, color: 'var(--danger)', fontSize: '0.875rem' }}>{s.risk_score.toFixed(1)}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
