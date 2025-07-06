/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './pages/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
        './app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    darkMode: 'class', // Enable class-based dark mode
    theme: {
        extend: {
            colors: {
                // Custom dark mode colors
                'dark-bg': '#0f172a',
                'dark-surface': '#1e293b',
                'dark-elevated': '#334155',
            },
        },
    },
    plugins: [],
} 