import React, { useState, useEffect } from 'react';
import { Send, AlertTriangle, CheckCircle, BrainCircuit, Calculator, ShieldCheck } from 'lucide-react';
import api from '../api';

const ProposalForm = () => {
    const userRole = localStorage.getItem('role');
    const userSchool = localStorage.getItem('school_pseudocode');

    const [formData, setFormData] = useState({
        school_pseudocode: userSchool || '',
        school_name: '',
        intervention_type: 'New_Classrooms',
        classrooms_requested: 0,
        funding_requested: 0,
        proposal_letter: '',
        udise_data_verified: false,
        dynamic_fields: {
            // Sanitation fields
            toilet_seats_requested: 0,
            has_girls_toilet: false,
            has_boys_toilet: false,
            has_handwash: false,
            has_drinking_water: false,
            // Digital fields
            devices_requested: 0,
            teacher_ict_trained: false,
            // Lab fields
            lab_type: '',
            // Repairs fields
            repair_scope: '',
            structural_urgency: 'medium',
            // New_Classrooms fields
            construction_type: '',
            land_available: ''
        }
    });

    const [status, setStatus] = useState({ loading: false, result: null, error: null });
    
    // Budget Estimation specific state
    const [budgetEstimate, setBudgetEstimate] = useState(null);
    const [budgetLoading, setBudgetLoading] = useState(false);

    // Debounced trigger for budget estimation
    useEffect(() => {
        const fetchBudgetEstimate = async () => {
            if (!formData.intervention_type || formData.classrooms_requested <= 0) {
                setBudgetEstimate(null);
                return;
            }
            setBudgetLoading(true);
            try {
                const response = await api.post('/budget-estimate', {
                    school_pseudocode: formData.school_pseudocode,
                    intervention_type: formData.intervention_type,
                    funding_requested: Number(formData.funding_requested),
                    dynamic_fields: { classrooms_requested: Number(formData.classrooms_requested) }
                });
                setBudgetEstimate(response.data);
            } catch (err) {
                console.error("Budget estimation failed", err);
            } finally {
                setBudgetLoading(false);
            }
        };

        const timeoutId = setTimeout(() => {
            fetchBudgetEstimate();
        }, 600);

        return () => clearTimeout(timeoutId);
    }, [formData.intervention_type, formData.classrooms_requested, formData.funding_requested, formData.school_pseudocode]);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        
        // Handle nested dynamic_fields
        if (name.startsWith('dynamic_')) {
            const fieldName = name.replace('dynamic_', '');
            setFormData(prev => ({
                ...prev,
                dynamic_fields: {
                    ...prev.dynamic_fields,
                    [fieldName]: type === 'checkbox' ? checked : (type === 'number' ? Number(value) : value)
                }
            }));
        } else {
            // Handle regular fields
            setFormData(prev => ({ 
                ...prev, 
                [name]: type === 'checkbox' ? checked : (name === 'classrooms_requested' || name === 'funding_requested' ? Number(value) : value)
            }));
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setStatus({ loading: true, result: null, error: null });
        try {
            const response = await api.post('/proposal/submit', formData);
            setStatus({ loading: false, result: response.data, error: null });
        } catch (err) {
            setStatus({ loading: false, result: null, error: err.response?.data?.detail || err.message });
        }
    };

    return (
        <div className="animate-fade-in">
            <header style={{ marginBottom: '3rem' }}>
                <h1 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '0.5rem' }}>New Proposal</h1>
                <p style={{ color: 'var(--text-muted)' }}>Submit a structured infrastructural proposal for AI underwriting.</p>
            </header>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.5fr) minmax(0, 1fr)', gap: '2rem' }}>
                
                {/* Form column */}
                <div>
                    <form onSubmit={handleSubmit} className="glass-panel" style={{ padding: '2rem' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                                    School Pseudocode (UDISE) {userRole === 'principal' && userSchool && <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>(Fixed - Registered School)</span>}
                                </label>
                                <input 
                                    className="input-field" 
                                    type="text" 
                                    name="school_pseudocode" 
                                    required 
                                    value={formData.school_pseudocode} 
                                    onChange={handleChange} 
                                    placeholder="e.g. 1003076" 
                                    readOnly={userRole === 'principal' && userSchool}
                                    disabled={userRole === 'principal' && userSchool}
                                    style={{ opacity: (userRole === 'principal' && userSchool) ? 0.6 : 1, cursor: (userRole === 'principal' && userSchool) ? 'not-allowed' : 'text' }} 
                                />
                                {userRole === 'principal' && userSchool && (
                                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Principals can only submit proposals for their registered school.</p>
                                )}
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>School Name</label>
                                <input className="input-field" type="text" name="school_name" required value={formData.school_name} onChange={handleChange} placeholder="Govt High School..." />
                            </div>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Intervention Type</label>
                                <select className="input-field" name="intervention_type" value={formData.intervention_type} onChange={handleChange}>
                                    <option value="New_Classrooms">New Classrooms</option>
                                    <option value="Repairs">Repairs</option>
                                    <option value="Sanitation">Sanitation</option>
                                    <option value="Lab">Lab</option>
                                    <option value="Digital">Digital Infrastructure</option>
                                </select>
                            </div>
                            <div>
                                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Classrooms / Units Requested</label>
                                <input className="input-field" type="number" name="classrooms_requested" value={formData.classrooms_requested} onChange={handleChange} min="0" />
                            </div>
                        </div>

                        {/* Sanitation-Specific Fields */}
                        {formData.intervention_type === 'Sanitation' && (
                            <div style={{ 
                                marginBottom: '1.5rem', 
                                padding: '1.25rem', 
                                backgroundColor: 'rgba(52, 211, 153, 0.05)',
                                border: '1px solid rgba(52, 211, 153, 0.2)',
                                borderRadius: '8px'
                            }}>
                                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--success)', marginBottom: '1rem' }}>Sanitation Items Requested</h3>
                                
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                                        <input 
                                            type="checkbox" 
                                            id="has_girls_toilet" 
                                            name="dynamic_has_girls_toilet"
                                            checked={formData.dynamic_fields.has_girls_toilet}
                                            onChange={handleChange}
                                            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                                        />
                                        <label htmlFor="has_girls_toilet" style={{ cursor: 'pointer', fontSize: '0.875rem' }}>Girls Toilet</label>
                                    </div>
                                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                                        <input 
                                            type="checkbox" 
                                            id="has_boys_toilet"
                                            name="dynamic_has_boys_toilet"
                                            checked={formData.dynamic_fields.has_boys_toilet}
                                            onChange={handleChange}
                                            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                                        />
                                        <label htmlFor="has_boys_toilet" style={{ cursor: 'pointer', fontSize: '0.875rem' }}>Boys Toilet</label>
                                    </div>
                                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                                        <input 
                                            type="checkbox" 
                                            id="has_handwash"
                                            name="dynamic_has_handwash"
                                            checked={formData.dynamic_fields.has_handwash}
                                            onChange={handleChange}
                                            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                                        />
                                        <label htmlFor="has_handwash" style={{ cursor: 'pointer', fontSize: '0.875rem' }}>Handwash Stations</label>
                                    </div>
                                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                                        <input 
                                            type="checkbox" 
                                            id="has_drinking_water"
                                            name="dynamic_has_drinking_water"
                                            checked={formData.dynamic_fields.has_drinking_water}
                                            onChange={handleChange}
                                            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                                        />
                                        <label htmlFor="has_drinking_water" style={{ cursor: 'pointer', fontSize: '0.875rem' }}>Drinking Water System</label>
                                    </div>
                                </div>
                                
                                <div>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Toilet Seats to Install</label>
                                    <input 
                                        className="input-field" 
                                        type="number" 
                                        name="dynamic_toilet_seats_requested"
                                        value={formData.dynamic_fields.toilet_seats_requested}
                                        onChange={handleChange}
                                        min="0"
                                        placeholder="e.g., 4"
                                    />
                                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Total number of toilet seats (typically 2-4 per toilet block)</p>
                                </div>
                            </div>
                        )}

                        {/* Digital-Specific Fields */}
                        {formData.intervention_type === 'Digital' && (
                            <div style={{ 
                                marginBottom: '1.5rem', 
                                padding: '1.25rem', 
                                backgroundColor: 'rgba(168, 85, 247, 0.05)',
                                border: '1px solid rgba(168, 85, 247, 0.2)',
                                borderRadius: '8px'
                            }}>
                                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-purple)', marginBottom: '1rem' }}>Digital Infrastructure</h3>
                                
                                <div>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Devices Requested</label>
                                    <input 
                                        className="input-field" 
                                        type="number" 
                                        name="dynamic_devices_requested"
                                        value={formData.dynamic_fields.devices_requested}
                                        onChange={handleChange}
                                        min="0"
                                        placeholder="e.g., 30 computers/tablets"
                                    />
                                </div>
                                
                                <div style={{ marginTop: '1rem' }}>
                                    <label style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', cursor: 'pointer', fontSize: '0.875rem', fontWeight: 600 }}>
                                        <input 
                                            type="checkbox" 
                                            name="dynamic_teacher_ict_trained"
                                            checked={formData.dynamic_fields.teacher_ict_trained}
                                            onChange={handleChange}
                                            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                                        />
                                        Teachers have ICT training
                                    </label>
                                </div>
                            </div>
                        )}

                        {/* Lab-Specific Fields */}
                        {formData.intervention_type === 'Lab' && (
                            <div style={{ 
                                marginBottom: '1.5rem', 
                                padding: '1.25rem', 
                                backgroundColor: 'rgba(139, 92, 246, 0.05)',
                                border: '1px solid rgba(139, 92, 246, 0.2)',
                                borderRadius: '8px'
                            }}>
                                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#8b5cf6', marginBottom: '1rem' }}>Laboratory Details</h3>
                                
                                <div style={{ marginBottom: '1rem' }}>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Lab Type</label>
                                    <select 
                                        className="input-field" 
                                        name="dynamic_lab_type"
                                        value={formData.dynamic_fields.lab_type}
                                        onChange={handleChange}
                                        required
                                    >
                                        <option value="">-- Select Lab Type --</option>
                                        <option value="Science">Science Lab</option>
                                        <option value="Computer">Computer Lab</option>
                                        <option value="Mathematics">Mathematics Lab</option>
                                        <option value="Language">Language Lab</option>
                                        <option value="Geography">Geography Lab</option>
                                    </select>
                                </div>
                                
                                <div>
                                    <label style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', cursor: 'pointer', fontSize: '0.875rem', fontWeight: 600 }}>
                                        <input 
                                            type="checkbox" 
                                            name="dynamic_teacher_ict_trained"
                                            checked={formData.dynamic_fields.teacher_ict_trained}
                                            onChange={handleChange}
                                            style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                                        />
                                        Teachers have relevant training
                                    </label>
                                </div>
                            </div>
                        )}

                        {/* Repairs-Specific Fields */}
                        {formData.intervention_type === 'Repairs' && (
                            <div style={{ 
                                marginBottom: '1.5rem', 
                                padding: '1.25rem', 
                                backgroundColor: 'rgba(251, 146, 60, 0.05)',
                                border: '1px solid rgba(251, 146, 60, 0.2)',
                                borderRadius: '8px'
                            }}>
                                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fb923c', marginBottom: '1rem' }}>Repair Details</h3>
                                
                                <div style={{ marginBottom: '1rem' }}>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Structural Urgency</label>
                                    <select 
                                        className="input-field" 
                                        name="dynamic_structural_urgency"
                                        value={formData.dynamic_fields.structural_urgency}
                                        onChange={handleChange}
                                    >
                                        <option value="low">Low - Maintenance</option>
                                        <option value="medium">Medium - Important</option>
                                        <option value="high">High - Urgent</option>
                                        <option value="critical">Critical - Safety Risk</option>
                                    </select>
                                </div>
                                
                                <div>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Repair Scope / Description</label>
                                    <textarea 
                                        className="input-field" 
                                        name="dynamic_repair_scope"
                                        value={formData.dynamic_fields.repair_scope}
                                        onChange={handleChange}
                                        rows="3"
                                        placeholder="e.g., Roof leakage in main building, classroom walls cracked, foundation issues..."
                                    />
                                </div>
                            </div>
                        )}

                        {/* New Classrooms-Specific Fields */}
                        {formData.intervention_type === 'New_Classrooms' && (
                            <div style={{ 
                                marginBottom: '1.5rem', 
                                padding: '1.25rem', 
                                backgroundColor: 'rgba(59, 130, 246, 0.05)',
                                border: '1px solid rgba(59, 130, 246, 0.2)',
                                borderRadius: '8px'
                            }}>
                                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-blue)', marginBottom: '1rem' }}>Construction Details</h3>
                                
                                <div style={{ marginBottom: '1rem' }}>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Construction Type</label>
                                    <select 
                                        className="input-field" 
                                        name="dynamic_construction_type"
                                        value={formData.dynamic_fields.construction_type}
                                        onChange={handleChange}
                                        required
                                    >
                                        <option value="">-- Select Construction Type --</option>
                                        <option value="Pucca">Pucca (Permanent)</option>
                                        <option value="Semi-pucca">Semi-pucca</option>
                                        <option value="Prefab">Prefab/Modular</option>
                                    </select>
                                </div>
                                
                                <div>
                                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Land Availability</label>
                                    <select 
                                        className="input-field" 
                                        name="dynamic_land_available"
                                        value={formData.dynamic_fields.land_available}
                                        onChange={handleChange}
                                        required
                                    >
                                        <option value="">-- Select Land Status --</option>
                                        <option value="Yes">Land available at school</option>
                                        <option value="No">Land not available</option>
                                    </select>
                                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Construction cannot proceed without confirmed land availability</p>
                                </div>
                            </div>
                        )}

                        <div style={{ marginBottom: '1.5rem' }}>
                            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Funding Requested (₹)</label>
                            <input className="input-field" type="number" name="funding_requested" value={formData.funding_requested} onChange={handleChange} min="0" required />
                        </div>

                        <div style={{ marginBottom: '2rem' }}>
                            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Proposal Letter (Optional - For AI Extraction)</label>
                            <textarea className="input-field" name="proposal_letter" rows="4" value={formData.proposal_letter} onChange={handleChange} placeholder="We desperately need physical space as PTR is exceeding 45..."></textarea>
                        </div>

                        <div style={{ 
                            marginBottom: '2rem', 
                            padding: '1rem', 
                            backgroundColor: 'rgba(34, 211, 238, 0.05)', 
                            border: '1px solid rgba(34, 211, 238, 0.2)',
                            borderRadius: '8px' 
                        }}>
                            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                                <input 
                                    type="checkbox" 
                                    id="udise_verified" 
                                    name="udise_data_verified" 
                                    checked={formData.udise_data_verified}
                                    onChange={handleChange}
                                    required
                                    style={{ marginTop: '4px', cursor: 'pointer', width: '18px', height: '18px' }}
                                />
                                <label htmlFor="udise_verified" style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', cursor: 'pointer', flex: 1 }}>
                                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>✓ UDISE Data Verified</span>
                                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                                        I confirm that school details have been verified against the UDISE+ dashboard and are accurate. 
                                        All DBT funding disbursement requires UDISE verification.
                                    </p>
                                </label>
                            </div>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                            <button 
                                type="submit" 
                                className="btn btn-primary" 
                                disabled={status.loading || !formData.udise_data_verified || (budgetEstimate?.cost_anomaly && budgetEstimate?.fraud_flag)}
                                title={!formData.udise_data_verified ? "Please verify UDISE data to submit" : ""}
                            >
                                {status.loading ? 'Submitting...' : <><Send size={18} /> Submit Proposal</>}
                            </button>
                        </div>
                    </form>

                    {status.error && (
                        <div className="glass-card" style={{ borderColor: 'var(--danger-light)', backgroundColor: 'rgba(239, 68, 68, 0.1)', marginTop: '2rem' }}>
                            <h3 style={{ color: 'var(--danger)', display: 'flex', gap: '0.5rem', alignItems: 'center' }}><AlertTriangle size={20} /> Error Submitting Proposal</h3>
                            <p style={{ marginTop: '0.5rem' }}>{typeof status.error === 'string' ? status.error : JSON.stringify(status.error)}</p>
                        </div>
                    )}

                    {status.result && (
                        <div className="glass-card animate-fade-in" style={{ borderColor: 'var(--success-light)', backgroundColor: 'rgba(16, 185, 129, 0.1)', marginTop: '2rem' }}>
                            <h3 style={{ color: 'var(--success)', display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '1rem' }}><CheckCircle size={20} /> Successfully Submitted</h3>
                            <div style={{ display: 'grid', gap: '0.5rem', fontSize: '0.9rem' }}>
                                <p><strong>Proposal ID:</strong> {status.result.proposal_id}</p>
                                <p><strong>Status:</strong> {status.result.status}</p>
                                {status.result.ai_summary && (
                                    <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
                                        <p style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-purple)', fontWeight: 600, marginBottom: '0.5rem' }}><BrainCircuit size={16} /> AI Summary Extract</p>
                                        <p style={{ fontStyle: 'italic', color: 'var(--text-secondary)' }}>{status.result.ai_summary}</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* AI Cost Estimation Sidebar */}
                <div>
                    <div className="glass-panel" style={{ padding: '2rem', position: 'sticky', top: '2rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
                            <Calculator size={20} color="var(--accent-purple)" />
                            <h2 style={{ fontSize: '1.125rem', fontWeight: 700, margin: 0 }}>Predicted Budget Envelope</h2>
                        </div>

                        {!budgetEstimate && !budgetLoading && (
                            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem 1rem' }}>
                                <ShieldCheck size={32} style={{ opacity: 0.2, margin: '0 auto 1rem auto' }} />
                                <p style={{ fontSize: '0.875rem' }}>Enter intervention details and unit request to calculate AI budget envelope.</p>
                            </div>
                        )}

                        {budgetLoading && (
                            <div style={{ padding: '2rem', textAlign: 'center' }}>
                                <BrainCircuit size={24} className="animate-spin" color="var(--accent-blue)" style={{ margin: '0 auto 1rem auto' }} />
                                <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Calibrating SOR norms...</div>
                            </div>
                        )}

                        {budgetEstimate && !budgetLoading && (
                            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                                <div className="glass-card" style={{ padding: '1rem' }}>
                                    <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.25rem' }}>Expected Base Cost</div>
                                    <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>₹{budgetEstimate.total_expected_cost?.toLocaleString()}</div>
                                    <div style={{ fontSize: '0.75rem', color: 'var(--accent-blue)', marginTop: '0.25rem' }}>Based on local district weight.</div>
                                </div>
                                <div className="glass-card" style={{ padding: '1rem' }}>
                                    <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.25rem' }}>Computed Envelope</div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <div style={{ fontSize: '1.125rem', fontWeight: 600 }}>₹{(budgetEstimate.total_expected_cost * 0.9)?.toLocaleString()}</div>
                                        <div style={{ color: 'var(--text-muted)' }}>—</div>
                                        <div style={{ fontSize: '1.125rem', fontWeight: 600 }}>₹{(budgetEstimate.total_expected_cost * 1.2)?.toLocaleString()}</div>
                                    </div>
                                </div>

                                {formData.funding_requested > 0 && (
                                    <div style={{ 
                                        padding: '1rem', 
                                        borderRadius: '8px', 
                                        backgroundColor: budgetEstimate.fraud_flag ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                                        border: `1px solid ${budgetEstimate.fraud_flag ? 'var(--danger)' : 'var(--success)'}`,
                                        marginTop: '1rem'
                                    }}>
                                        <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: budgetEstimate.fraud_flag ? 'var(--danger)' : 'var(--success)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                            {budgetEstimate.fraud_flag ? <AlertTriangle size={14} /> : <CheckCircle size={14} />}
                                            AI Verdict
                                        </div>
                                        <div style={{ fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                                            Requested amount ({formData.funding_requested.toLocaleString()}) is 
                                            {budgetEstimate.fraud_flag ? " exceeding algorithmic bounds by an anomalous margin. Approval unlikely without verification." : " within expected statistical parameters."}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProposalForm;
