import '../styles/globals.css'
import type { AppProps } from 'next/app'
import { useEffect } from 'react'

export default function App({ Component, pageProps }: AppProps) {
    useEffect(() => {
        // Check for saved dark mode preference or default to false
        const isDarkMode = localStorage.getItem('darkMode') === 'true';
        
        // Apply dark mode class to document element
        if (isDarkMode) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    }, []);

    return <Component {...pageProps} />
} 