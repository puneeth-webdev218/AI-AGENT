/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#08111f',
          900: '#101a2d',
          800: '#18233a',
        },
        signal: {
          100: '#eefdf7',
          400: '#2dd4bf',
          500: '#14b8a6',
          700: '#0f766e',
        },
        ember: {
          400: '#fb7185',
          500: '#f43f5e',
          700: '#be123c',
        },
        sun: {
          300: '#fde68a',
          400: '#fbbf24',
        },
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(45, 212, 191, 0.18), 0 20px 60px rgba(4, 10, 22, 0.35)',
      },
      backgroundImage: {
        'hero-grid': 'radial-gradient(circle at top left, rgba(45,212,191,.18), transparent 28%), radial-gradient(circle at top right, rgba(251,191,36,.18), transparent 22%), linear-gradient(135deg, rgba(8,17,31,.96), rgba(16,26,45,.92))',
      },
    },
  },
  plugins: [],
};
