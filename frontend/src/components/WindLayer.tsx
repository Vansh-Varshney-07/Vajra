import React, { useEffect, useRef } from 'react';

interface WindParticle {
  x: number;
  y: number;
  speed: number;
  angle: number;
  age: number;
  maxAge: number;
}

interface WindLayerProps {
  visible: boolean;
  intensity?: number;
}

export const WindLayer: React.FC<WindLayerProps> = ({ visible, intensity = 1.0 }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!visible) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    const width = (canvas.width = canvas.parentElement?.clientWidth || 800);
    const height = (canvas.height = canvas.parentElement?.clientHeight || 600);

    const particles: WindParticle[] = [];
    const numParticles = 120;

    // Cyclone vortex center
    const cx = width * 0.65;
    const cy = height * 0.45;

    for (let i = 0; i < numParticles; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        speed: (1.5 + Math.random() * 3) * intensity,
        angle: 0,
        age: Math.random() * 50,
        maxAge: 40 + Math.random() * 40,
      });
    }

    const render = () => {
      ctx.fillStyle = 'rgba(15, 23, 42, 0.08)';
      ctx.fillRect(0, 0, width, height);

      ctx.strokeStyle = 'rgba(56, 189, 248, 0.65)';
      ctx.lineWidth = 1.5;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        const dx = p.x - cx;
        const dy = p.y - cy;
        const dist = Math.sqrt(dx * dx + dy * dy);

        // Cyclonic counter-clockwise inward spiral
        const tangentAngle = Math.atan2(dy, dx) - Math.PI / 2 - 0.25;
        p.x += Math.cos(tangentAngle) * p.speed;
        p.y += Math.sin(tangentAngle) * p.speed;
        p.age++;

        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(
          p.x - Math.cos(tangentAngle) * p.speed * 2.5,
          p.y - Math.sin(tangentAngle) * p.speed * 2.5
        );
        ctx.stroke();

        if (p.age > p.maxAge || dist < 20 || p.x < 0 || p.x > width || p.y < 0 || p.y > height) {
          particles[i] = {
            x: cx + (Math.random() - 0.5) * width * 0.8,
            y: cy + (Math.random() - 0.5) * height * 0.8,
            speed: (1.5 + Math.random() * 3) * intensity,
            angle: 0,
            age: 0,
            maxAge: 40 + Math.random() * 40,
          };
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [visible, intensity]);

  if (!visible) return null;

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 pointer-events-none z-10 w-full h-full"
    />
  );
};
