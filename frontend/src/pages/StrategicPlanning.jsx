import React, { useEffect, useState } from 'react';
import { Target, AlertTriangle, Activity, Coins, ChevronRight, BarChart3, Info, PieChart } from 'lucide-react';
import api from '../api';

const StrategicPlanning = () => {
    const [gapData, setGapData] = useState(null);
    const [priorityList, setPriorityList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedSchool, setExpandedSchool] = useState(null);

    useEffect(() => {
        const fetchPlanningData = async () => {
            try {
                const [gapRes, priorityRes] = await Promise.all([
                    api.get('/planning/gap-analysis'),
                    api.get('/planning/prioritize?top_n=15')
                ]);
                setGapData(gapRes.data);
                setPriorityList(priorityRes.data.top_priority || []);
            } catch (err) {
                setError(err.response?.data?.detail || "Failed to load predictive planning data.");
            } finally {
                setLoading(false);
            }
        };
        fetchPlanningData();
    }, []);

    if (loading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
            <Activity className="animate-spin" size={32} color="var(--accent-blue)" />
        </div>
    );

    if (error) return (
        <div className="glass-panel animate-fade-in" style={{ padding: '2rem', color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <AlertTriangle size={20} />
            {error}
        </div>
    );

    return (
        <div className="animate-fade-in">
            <header style={{ marginBottom: '3rem' }}>
                <h1 style={{ marginBottom: '0.25rem' }}>Strategic Planning</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>Data-driven resource allocation and gap analysis framework.</p>
            </header>

            {/* Fiscal Analysis Grid */}
            {gapData && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '3rem' }}>
                    <div className="glass-panel" style={{ padding: '1.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Estimated Fiscal Requirement</span>
                            <Coins size={16} color="var(--success)" />
                        </div>
                        <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>
                            ₹{(gapData.estimated_cost?.total_estimated / 100000).toFixed(1)}L
                        </div>
                        <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>Based on Samagra SOR</div>
                    </div>

                    <div className="glass-panel" style={{ padding: '1.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Classroom Demand</span>
                            <PieChart size={16} color="var(--accent-blue)" />
                        </div>
                        <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>
                            {gapData.demand?.classrooms_needed || 0}
                        </div>
                        <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>Units missing statewide</div>
                    </div>

                    <div className="glass-panel" style={{ padding: '1.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase' }}>Critical Vacancies</span>
                            <AlertTriangle size={16} color="var(--danger)" />
                        </div>
                        <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>
                            {gapData.demand?.schools_missing_girls_toilet || 0}
                        </div>
                        <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                           Sanitation Gaps
                        </div>
                    </div>
                </div>
            )}

            {/* Detailed Feed Layer */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2rem' }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <Target size={20} color="var(--accent-purple)" />
                        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>High Priority Interventions</h2>
                    </div>
                    
                    <div className="glass-panel" style={{ overflow: 'hidden' }}>
                        <table style={{ borderBottom: 'none' }}>
                            <thead>
                                <tr>
                                    <th>Institution</th>
                                    <th>Level</th>
                                    <th>Urgency</th>
                                    <th>Risk</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                                {priorityList.map((school) => {
                                    const isExpanded = expandedSchool === school.pseudocode;
                                    return (
                                        <React.Fragment key={school.pseudocode}>
                                            <tr>
                                                <td>
                                                    <div className="school-identity">
                                                        <span className="school-identity-name">{school.school_name || `School ${school.pseudocode}`}</span>
                                                        <span className="school-identity-code">UDISE {school.pseudocode}</span>
                                                    </div>
                                                </td>
                                                <td>{school.school_level}</td>
                                                <td>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                        <div style={{ width: '60px', height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px' }}>
                                                            <div style={{ width: `${school.urgency_score}%`, height: '100%', background: 'var(--accent-purple)' }} />
                                                        </div>
                                                        <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>{school.urgency_score}</span>
                                                    </div>
                                                </td>
                                                <td>
                                                    <span className={`badge ${school.risk_level === 'High' ? 'badge-danger' : 'badge-success'}`}>
                                                        {school.risk_level}
                                                    </span>
                                                </td>
                                                <td>
                                                    <button
                                                        className={`row-icon-button ${isExpanded ? 'open' : ''}`}
                                                        onClick={() => setExpandedSchool(isExpanded ? null : school.pseudocode)}
                                                        aria-label={`Show urgency issues for ${school.school_name || school.pseudocode}`}
                                                    >
                                                        <ChevronRight size={14} />
                                                    </button>
                                                </td>
                                            </tr>
                                            {isExpanded && (
                                                <tr className="priority-detail-row">
                                                    <td colSpan="5">
                                                        <div className="priority-detail-panel">
                                                            <div>
                                                                <span className="eyebrow">Urgency Issues To Clear</span>
                                                                <div className="issue-chip-list">
                                                                    {(school.missing_items?.length ? school.missing_items : ['No missing infrastructure items reported']).map((item) => (
                                                                        <span className="issue-chip" key={item}>{item}</span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                            <div className="priority-metrics">
                                                                <span>PTR {school.ptr}</span>
                                                                <span>{school.ptr_status}</span>
                                                                <span>{school.students_per_room} students/room</span>
                                                                <span>Priority {school.priority_score}</span>
                                                            </div>
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </React.Fragment>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                        <BarChart3 size={20} color="var(--accent-blue)" />
                        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>Demand Hierarchy</h2>
                    </div>
                    
                    <div className="glass-panel demand-hierarchy-panel">
                        {gapData?.top_gaps?.map((gap, i) => (
                            <div className="demand-row" key={i}>
                                <div className="demand-row-header">
                                    <span className="demand-name">{gap.item}</span>
                                    <span className="demand-count">{gap.schools_affected} Institutions</span>
                                </div>
                                <div className="demand-track">
                                    <div
                                        className="demand-fill"
                                        style={{
                                            width: `${Math.min(100, Math.max(0, (gap.schools_affected / gapData.total_schools) * 100))}%`,
                                            background: i === 0 ? 'var(--accent-blue)' : 'var(--accent-purple)',
                                        }}
                                    />
                                </div>
                            </div>
                        ))}
                        
                        <div style={{ marginTop: '1rem', padding: '1rem', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.05)', color: 'var(--text-secondary)', fontSize: '0.75rem', lineHeight: 1.5, display: 'flex', gap: '0.75rem' }}>
                            <Info size={14} style={{ flexShrink: 0 }} />
                            <span>Fiscal estimates are recalculated based on active intervention-aware cost modeling.</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default StrategicPlanning;
