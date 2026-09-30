/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: '#0A0D10',
        surface: '#10151A',
        elevated: '#161C22',
        'elevated-2': '#1C232B',
        border: {
          DEFAULT: '#232B32',
          strong: '#2E3944',
        },
        text: {
          primary: '#E6EDF2',
          secondary: '#8A97A0',
          muted: '#5A6570',
        },
        accent: {
          DEFAULT: '#35B8D9',
          dim: '#1E5A69',
          bright: '#6ED4EC',
        },
        warning: {
          DEFAULT: '#E8A23F',
          dim: '#5C4322',
        },
        critical: {
          DEFAULT: '#E5484D',
          dim: '#4D2224',
        },
        healthy: {
          DEFAULT: '#3FB97E',
          dim: '#1D4A34',
        },
        predicted: {
          DEFAULT: '#8B7FE8',
          dim: '#332E5C',
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      backgroundImage: {
        'grid-texture':
          'linear-gradient(rgba(53,184,217,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(53,184,217,0.035) 1px, transparent 1px)',
      },
      backgroundSize: {
        grid: '28px 28px',
      },
      boxShadow: {
        panel: '0 0 0 1px rgba(53,184,217,0.04)',
      },
      keyframes: {
        pulseDot: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.35 },
        },
        dashFlow: {
          to: { strokeDashoffset: -24 },
        },
        packetFlow: {
          '0%': { offsetDistance: '0%', opacity: 0 },
          '10%': { opacity: 1 },
          '90%': { opacity: 1 },
          '100%': { offsetDistance: '100%', opacity: 0 },
        },
      },
      animation: {
        pulseDot: 'pulseDot 2s ease-in-out infinite',
        dashFlow: 'dashFlow 1.2s linear infinite',
      },
    },
  },
  plugins: [],
};
