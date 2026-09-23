import React from 'react';

interface ProgressBarProps {
  progress: number;
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  showPercentage?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  label,
  size = 'md',
  showPercentage = true,
}) => {
  const clamped = Math.max(0, Math.min(100, progress));

  const sizeClasses = {
    sm: 'h-1.5',
    md: 'h-2.5',
    lg: 'h-4',
  };

  return (
    <div className="w-full">
      {(label || showPercentage) && (
        <div className="flex justify-between text-xs font-mono mb-1 text-gray-400">
          <span>{label}</span>
          {showPercentage && <span className="text-darkroom-gold font-medium">{clamped}%</span>}
        </div>
      )}
      <div className={`w-full bg-gray-800 rounded-full overflow-hidden border border-gray-700/60 ${sizeClasses[size]}`}>
        <div
          className="bg-gradient-to-r from-darkroom-navy via-darkroom-gold to-emerald-400 h-full transition-all duration-300 rounded-full"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
};
