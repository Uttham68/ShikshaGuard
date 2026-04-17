import React, { useEffect, useState, useCallback } from 'react';
import { 
    FileSearch, 
    Activity, 
    BrainCircuit, 
    XCircle, 
    AlertTriangle, 
    CheckCircle2, 
    Sliders, 
    Zap,
    ChevronRight,
    Trash2
} from 'lucide-react';
import api from '../api';

const ProposalsList = () => {
    const [proposals, setProposals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [deleteState, setDeleteState] = useState({ id: null, error: null });

    const [modal, setModal] = useState({ 
        isOpen: false, loading: false, data: null, error: null, currentId: null,
        simulation: { rooms: 0, teachers: 0, delta: null, loading: false } 
    });

    const fetchProposals = useCallback(async () => {
        try {
            const response = await api.get('/my-proposals');
            setProposals(response.data.proposals || []);
        } catch (err) {
            setError(err.response?.data?.detail || "Failed to fetch proposals.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchProposals();
    }, [fetchProposals]);

    const handleValidate = async (proposal_id) => {
        setModal(prev => ({ ...prev, isOpen: true, loading: true, data: null, error: null, currentId: proposal_id, simulation: { rooms: 0, teachers: 0, delta: null, loading: false } }));
        try {
            const response = await api.post('/proposal/validate-by-id', { proposal_id });
            setModal(prev => ({ ...prev, loading: false, data: response.data }));
        } catch (err) {
            setModal(prev => ({ ...prev, loading: false, error: err.response?.data?.detail || "AI Validation failed." }));
        }
    };

    const handleDelete = async (proposal) => {
        const confirmed = window.confirm(`Delete proposal #${proposal.proposal_id} for ${proposal.school_name}? This cannot be undone.`);
        if (!confirmed) return;

        setDeleteState({ id: proposal.proposal_id, error: null });
        try {
            await api.delete(`/proposal/${proposal.proposal_id}`);
            setProposals(prev => prev.filter(p => p.proposal_id !== proposal.proposal_id));
            setDeleteState({ id: null, error: null });
        } catch (err) {
            setDeleteState({
                id: null,
                error: err.response?.data?.detail || 'Failed to delete proposal.',
            });
        }
    };

    const runSimulation = async (rooms, teachers) => {
        if (!modal.data || !modal.currentId) return;
        setModal(prev => ({ ...prev, simulation: { ...prev.simulation, loading: true, rooms, teachers } }));
        try {
            const proposal = proposals.find(p => p.proposal_id === modal.currentId);
            const response = await api.post('/simulate', null, { 
                params: { 
                    school_pseudocode: proposal.school_pseudocode,
                    classrooms_to_add: rooms,
                    teachers_to_add: teachers,
                    intervention_type: proposal.intervention_type
                }
            });
            setModal(prev => ({ ...prev, simulation: { ...prev.simulation, loading: false, delta: response.data } }));
        } catch {
            setModal(prev => ({ ...prev, simulation: { ...prev.simulation, loading: false } }));
        }
    };

    const selectedProposal = proposals.find(p => p.proposal_id === modal.currentId);
    const verdictTone = modal.data?.verdict === 'Accept' ? 'success' : 'danger';
    const predictedRisk = modal.simulation.delta?.after?.risk_score ?? modal.data?.risk_score;
    const closeValidation = () => setModal(prev => ({ ...prev, isOpen: false }));

    if (modal.isOpen) {
        return (
            <div className="validation-page animate-fade-in">
                <div className="validation-toolbar">
                    <button className="btn" onClick={closeValidation}>
                        <ChevronRight className="back-chevron" size={16} />
                        Back to Proposals
                    </button>
                    <div className="validation-toolbar-copy">
                        <span>AI validation workspace</span>
                        <strong>{selectedProposal ? `Proposal #${selectedProposal.proposal_id}` : 'Proposal review'}</strong>
                    </div>
                </div>

                <section className="validation-workspace" aria-labelledby="validation-title">
                    <header className="validation-header">
                        <div className="validation-title-row">
                            <div className="validation-icon">
                                <BrainCircuit size={22} />
                            </div>
                            <div>
                                <h2 id="validation-title">Validation Audit</h2>
                                <p>{selectedProposal ? `${selectedProposal.school_name} - ${selectedProposal.school_pseudocode}` : 'AI proposal review'}</p>
                            </div>
                        </div>
                        <button className="icon-button" onClick={closeValidation} aria-label="Close validation audit">
                            <XCircle size={20} />
                        </button>
                    </header>

                    {selectedProposal && (
                        <div className="proposal-context">
                            <div>
                                <span>Proposal</span>
                                <strong>#{selectedProposal.proposal_id}</strong>
                            </div>
                            <div>
                                <span>Category</span>
                                <strong>{selectedProposal.intervention_type}</strong>
                            </div>
                            <div>
                                <span>Fiscal Ask</span>
                                <strong>Rs. {selectedProposal.funding_requested?.toLocaleString()}</strong>
                            </div>
                        </div>
                    )}

                    {modal.loading ? (
                        <div className="validation-loading">
                            <Activity className="animate-spin" size={32} color="var(--accent-cyan)" />
                            <h3>Running validation model</h3>
                            <p>Analyzing proposal details, school baseline metrics, and risk vectors.</p>
                        </div>
                    ) : modal.error ? (
                        <div className="validation-error">
                            <AlertTriangle size={22} />
                            <span>{modal.error}</span>
                        </div>
                    ) : modal.data && (
                        <div className="validation-body">
                            <div className="validation-analysis">
                                <div className={`verdict-banner ${verdictTone}`}>
                                    <div>
                                        <span className="eyebrow">Model Verdict</span>
                                        <strong>{modal.data.verdict}</strong>
                                    </div>
                                    {modal.data.verdict === 'Accept' ? <CheckCircle2 size={26} /> : <AlertTriangle size={26} />}
                                </div>

                                <div className="validation-metrics">
                                    <div className="metric-tile">
                                        <span>Confidence</span>
                                        <strong>{(modal.data.confidence * 100).toFixed(1)}%</strong>
                                    </div>
                                    <div className="metric-tile">
                                        <span>Risk Score</span>
                                        <strong>{modal.data.risk_score?.toFixed(1) ?? '--'}</strong>
                                    </div>
                                </div>

                                <div className="reasoning-card">
                                    <span className="eyebrow">Reasoning Summary</span>
                                    <p>{modal.data.ai_explanation || 'No reasoning summary was returned for this validation.'}</p>
                                </div>
                            </div>

                            <aside className="simulation-panel">
                                <div className="section-heading">
                                    <Sliders size={18} color="var(--accent-amber)" />
                                    <h3>Impact Simulator</h3>
                                </div>

                                <div className="slider-group">
                                    <div className="slider-label">
                                        <span>Add Classrooms</span>
                                        <strong>+{modal.simulation.rooms}</strong>
                                    </div>
                                    <input
                                        type="range"
                                        min="0"
                                        max="10"
                                        step="1"
                                        value={modal.simulation.rooms}
                                        onChange={(e) => runSimulation(parseInt(e.target.value, 10), modal.simulation.teachers)}
                                    />
                                </div>

                                <div className="slider-group">
                                    <div className="slider-label">
                                        <span>Add Staff</span>
                                        <strong>+{modal.simulation.teachers}</strong>
                                    </div>
                                    <input
                                        type="range"
                                        min="0"
                                        max="10"
                                        step="1"
                                        value={modal.simulation.teachers}
                                        onChange={(e) => runSimulation(modal.simulation.rooms, parseInt(e.target.value, 10))}
                                    />
                                </div>

                                <div className="risk-preview">
                                    <span>Predicted Risk Score</span>
                                    {modal.simulation.loading ? (
                                        <Activity className="animate-spin" size={28} color="var(--warning)" />
                                    ) : (
                                        <strong>{typeof predictedRisk === 'number' ? predictedRisk.toFixed(1) : '--'}</strong>
                                    )}
                                    <p>{modal.simulation.delta?.impact?.recommendation || 'Move the sliders to preview how added resources may change local risk.'}</p>
                                </div>
                            </aside>
                        </div>
                    )}
                </section>
            </div>
        );
    }

    return (
        <div className="animate-fade-in">
            <header style={{ marginBottom: '3rem' }}>
                <h1 style={{ marginBottom: '0.25rem' }}>Proposals</h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>Review and validate infrastructural requests.</p>
            </header>

            {deleteState.error && (
                <div className="inline-error" style={{ marginBottom: '1rem' }}>
                    <AlertTriangle size={18} /> {deleteState.error}
                </div>
            )}

            {loading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '40vh' }}>
                    <Activity className="animate-spin" size={32} color="var(--accent-blue)" />
                </div>
            ) : error ? (
                <div style={{ color: 'var(--danger)', fontSize: '0.875rem' }}><AlertTriangle size={18} /> {error}</div>
            ) : proposals.length === 0 ? (
                <div className="glass-panel" style={{ textAlign: 'center', padding: '5rem 2rem' }}>
                    <FileSearch size={48} style={{ opacity: 0.1, margin: '0 auto 1.5rem auto' }} />
                    <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>No proposals found.</h3>
                    <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>New submissions will appear here after metadata processing.</p>
                </div>
            ) : (
                <div className="glass-panel" style={{ overflow: 'hidden' }}>
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Institution</th>
                                <th>Category</th>
                                <th>Fiscal Ask</th>
                                <th>AI Risk</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {proposals.map(p => (
                                <tr key={p.proposal_id}>
                                    <td style={{ fontWeight: 600, color: 'var(--text-muted)' }}>#{p.proposal_id}</td>
                                    <td>
                                        <div style={{ fontWeight: 600 }}>{p.school_name}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{p.school_pseudocode}</div>
                                    </td>
                                    <td>
                                        <span className="badge badge-neutral">{p.intervention_type}</span>
                                    </td>
                                    <td style={{ fontWeight: 700 }}>₹{p.funding_requested?.toLocaleString()}</td>
                                    <td>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                            <div style={{ flex: 1, minWidth: '60px', height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px' }}>
                                                <div style={{ width: `${p.risk_score || 0}%`, height: '100%', background: p.risk_score > 70 ? 'var(--danger)' : 'var(--accent-blue)' }} />
                                            </div>
                                            <span style={{ fontWeight: 700, fontSize: '0.875rem' }}>{p.risk_score?.toFixed(1) || '-'}</span>
                                        </div>
                                    </td>
                                    <td>
                                        <div className="proposal-actions">
                                            <button className="btn btn-primary" onClick={() => handleValidate(p.proposal_id)}>
                                                <BrainCircuit size={16} /> Validate
                                            </button>
                                            <button
                                                className="btn btn-danger"
                                                onClick={() => handleDelete(p)}
                                                disabled={deleteState.id === p.proposal_id}
                                            >
                                                <Trash2 size={16} />
                                                {deleteState.id === p.proposal_id ? 'Deleting...' : 'Delete'}
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Validation Modal */}
            {modal.isOpen && (
                <div className="validation-overlay" onClick={() => setModal(prev => ({ ...prev, isOpen: false }))}>
                    <div className="validation-backdrop" />

                    <section className="validation-modal animate-fade-in" onClick={e => e.stopPropagation()} aria-modal="true" role="dialog" aria-labelledby="validation-title">
                        <header className="validation-header">
                            <div className="validation-title-row">
                                <div className="validation-icon">
                                    <BrainCircuit size={22} />
                                </div>
                                <div>
                                    <h2 id="validation-title">Validation Audit</h2>
                                    <p>{selectedProposal ? `${selectedProposal.school_name} · ${selectedProposal.school_pseudocode}` : 'AI proposal review'}</p>
                                </div>
                            </div>
                            <button className="icon-button" onClick={() => setModal(prev => ({ ...prev, isOpen: false }))} aria-label="Close validation audit">
                                <XCircle size={20} />
                            </button>
                        </header>

                        {selectedProposal && (
                            <div className="proposal-context">
                                <div>
                                    <span>Proposal</span>
                                    <strong>#{selectedProposal.proposal_id}</strong>
                                </div>
                                <div>
                                    <span>Category</span>
                                    <strong>{selectedProposal.intervention_type}</strong>
                                </div>
                                <div>
                                    <span>Fiscal Ask</span>
                                    <strong>₹{selectedProposal.funding_requested?.toLocaleString()}</strong>
                                </div>
                            </div>
                        )}

                        {modal.loading ? (
                            <div className="validation-loading">
                                <Activity className="animate-spin" size={32} color="var(--accent-cyan)" />
                                <h3>Running validation model</h3>
                                <p>Analyzing proposal details, school baseline metrics, and risk vectors.</p>
                            </div>
                        ) : modal.error ? (
                            <div className="validation-error">
                                <AlertTriangle size={22} />
                                <span>{modal.error}</span>
                            </div>
                        ) : modal.data && (
                            <div className="validation-body">
                                <div className="validation-analysis">
                                    <div className={`verdict-banner ${verdictTone}`}>
                                        <div>
                                            <span className="eyebrow">Model Verdict</span>
                                            <strong>{modal.data.verdict}</strong>
                                        </div>
                                        {modal.data.verdict === 'Approve' ? <CheckCircle2 size={26} /> : <AlertTriangle size={26} />}
                                    </div>

                                    <div className="validation-metrics">
                                        <div className="metric-tile">
                                            <span>Confidence</span>
                                            <strong>{(modal.data.confidence * 100).toFixed(1)}%</strong>
                                        </div>
                                        <div className="metric-tile">
                                            <span>Risk Score</span>
                                            <strong>{modal.data.risk_score?.toFixed(1) ?? '--'}</strong>
                                        </div>
                                    </div>

                                    <div className="reasoning-card">
                                        <span className="eyebrow">Reasoning Summary</span>
                                        <p>{modal.data.ai_explanation || 'No reasoning summary was returned for this validation.'}</p>
                                    </div>
                                </div>

                                <aside className="simulation-panel">
                                    <div className="section-heading">
                                        <Sliders size={18} color="var(--accent-amber)" />
                                        <h3>Impact Simulator</h3>
                                    </div>

                                    <div className="slider-group">
                                        <div className="slider-label">
                                            <span>Add Classrooms</span>
                                            <strong>+{modal.simulation.rooms}</strong>
                                        </div>
                                        <input 
                                            type="range"
                                            min="0"
                                            max="10"
                                            step="1"
                                            value={modal.simulation.rooms}
                                            onChange={(e) => runSimulation(parseInt(e.target.value, 10), modal.simulation.teachers)}
                                        />
                                    </div>

                                    <div className="slider-group">
                                        <div className="slider-label">
                                            <span>Add Staff</span>
                                            <strong>+{modal.simulation.teachers}</strong>
                                        </div>
                                        <input 
                                            type="range"
                                            min="0"
                                            max="10"
                                            step="1"
                                            value={modal.simulation.teachers}
                                            onChange={(e) => runSimulation(modal.simulation.rooms, parseInt(e.target.value, 10))}
                                        />
                                    </div>

                                    <div className="risk-preview">
                                        <span>Predicted Risk Score</span>
                                        {modal.simulation.loading ? (
                                            <Activity className="animate-spin" size={28} color="var(--warning)" />
                                        ) : (
                                            <strong>{typeof predictedRisk === 'number' ? predictedRisk.toFixed(1) : '--'}</strong>
                                        )}
                                        <p>{modal.simulation.delta?.impact?.recommendation || 'Move the sliders to preview how added resources may change local risk.'}</p>
                                    </div>
                                </aside>
                            </div>
                        )}
                    </section>
                </div>
            )}
        </div>
    );
};

export default ProposalsList;
