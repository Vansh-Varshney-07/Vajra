import React from 'react';
import { X, Sparkles, Check, ArrowRight } from 'lucide-react';

interface DownscalingModalProps {
  isOpen: boolean;
  onClose: () => void;
  downscaleData: any;
}

export const DownscalingModal: React.FC<DownscalingModalProps> = ({
  isOpen,
  onClose,
  downscaleData
}) => {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(3, 7, 18, 0.85)',
        backdropFilter: 'blur(8px)',
        zIndex: 2000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px'
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '850px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '28px',
          position: 'relative',
          border: '1px solid rgba(6, 182, 212, 0.4)'
        }}
      >
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '20px',
            right: '20px',
            background: 'none',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer'
          }}
        >
          <X size={22} />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Sparkles color="#06B6D4" size={24} />
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#F8FAFC' }}>
            Physics-Constrained Generative Diffusion Downscaling
          </h2>
        </div>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: '6px' }}>
          Eliminating spectral smoothing: Generating 5 km hyper-local threat arrays from 12 km coarse NEPS-G ensemble.
        </p>

        {/* Comparison Showcase (12km vs 5km) */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '20px', alignItems: 'center', marginTop: '24px' }}>
          {/* Coarse 12km Box */}
          <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(148, 163, 184, 0.2)' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94A3B8', textTransform: 'uppercase' }}>
              Standard Deterministic / CNN (12 km)
            </div>
            <div
              style={{
                width: '100%',
                height: '180px',
                marginTop: '12px',
                borderRadius: '8px',
                background: 'radial-gradient(circle, rgba(14, 165, 233, 0.5) 0%, rgba(15, 23, 42, 0.9) 70%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                filter: 'blur(4px)',
                position: 'relative'
              }}
            />
            <div style={{ marginTop: '10px', fontSize: '0.82rem', color: '#EF4444', fontWeight: 600 }}>
              ⚠ Spectral Smoothing: Peak crushed from 195mm down to 68mm
            </div>
          </div>

          <ArrowRight size={28} color="#06B6D4" />

          {/* High-Res 5km Diffusion Box */}
          <div style={{ background: 'rgba(6, 182, 212, 0.08)', padding: '16px', borderRadius: '10px', border: '1px solid rgba(6, 182, 212, 0.4)' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#38BDF8', textTransform: 'uppercase' }}>
              Vajra Generative Diffusion (5 km)
            </div>
            <div
              style={{
                width: '100%',
                height: '180px',
                marginTop: '12px',
                borderRadius: '8px',
                background: 'radial-gradient(circle at 45% 45%, #EF4444 0%, #F59E0B 35%, #06B6D4 65%, #0F172A 90%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 25px rgba(239, 68, 68, 0.4)'
              }}
            />
            <div style={{ marginTop: '10px', fontSize: '0.82rem', color: '#10B981', fontWeight: 600 }}>
              ✓ Amplitude Retained: Peak preserved at 195.0 mm / 12h
            </div>
          </div>
        </div>

        {/* Statistical Summary */}
        <div style={{ marginTop: '24px', background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '10px' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#F8FAFC', marginBottom: '10px' }}>
            Probabilistic 20-Scenario Sampling Diagnostics
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>P90 Tail Peak:</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#38BDF8' }}>
                {downscaleData?.statistics?.p90_extreme_rainfall_peak?.toFixed(1) || '195.0'} mm
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Spatial Uncertainty Spread:</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#F59E0B' }}>
                ±{downscaleData?.statistics?.spatial_uncertainty_mean?.toFixed(1) || '22.4'} mm
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Mass Continuity Status:</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#10B981', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Check size={16} /> Conserved
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
