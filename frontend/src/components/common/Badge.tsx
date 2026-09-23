import React from 'react';

interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'gold' | 'navy';
  children: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ variant = 'default', children, className = '' }) => {
  const variantStyles = {
    default: 'bg-gray-800 text-gray-300 border-gray-700',
    success: 'bg-emerald-950/70 text-emerald-400 border-emerald-800/80',
    warning: 'bg-amber-950/70 text-amber-400 border-amber-800/80',
    danger: 'bg-rose-950/70 text-rose-400 border-rose-800/80',
    gold: 'bg-darkroom-goldLight text-darkroom-gold border-darkroom-gold/40',
    navy: 'bg-blue-950/60 text-blue-300 border-blue-800/60',
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium border ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  );
};
