/**
 * Main Dashboard Component for Orchestrator Management UI
 * 
 * This component provides a comprehensive interface for monitoring and managing
 * the orchestrator agent workflow execution system. It includes:
 * 
 * 1. Real-time system health monitoring
 * 2. Query submission and management
 * 3. DAG visualization and execution tracking
 * 4. Task status monitoring
 * 5. Analytics and performance metrics
 * 6. Dark mode toggle for improved user experience
 */

import React, { useState, useEffect, useCallback } from 'react';
import { SystemHealth } from './SystemHealth';
import { QueryManager } from './QueryManager';
import { DAGVisualization } from './DAGVisualization';
import { TaskMonitor } from './TaskMonitor';
import { Analytics } from './Analytics';
import { Query, DAG, Task, SystemHealthStatus } from '../lib/types';
import { 
    getSystemHealth, 
    getQueries, 
    getAvailableTasks,
    createQuery,
    getQueryDAG 
} from '../lib/api';

type TabType = 'overview' | 'queries' | 'tasks' | 'analytics';

export const Dashboard: React.FC = () => {
    // State management for different dashboard sections
    const [activeTab, setActiveTab] = useState<TabType>('overview');
    const [systemHealth, setSystemHealth] = useState<SystemHealthStatus | null>(null);
    const [queries, setQueries] = useState<Query[]>([]);
    const [availableTasks, setAvailableTasks] = useState<Task[]>([]);
    const [selectedQuery, setSelectedQuery] = useState<Query | null>(null);
    const [selectedDAG, setSelectedDAG] = useState<DAG | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Dark mode state
    const [isDarkMode, setIsDarkMode] = useState(false);

    // Auto-refresh interval for real-time updates
    const [refreshInterval, setRefreshInterval] = useState(5000); // 5 seconds
    const [autoRefresh, setAutoRefresh] = useState(true);

    /**
     * Initialize dark mode from localStorage
     */
    useEffect(() => {
        const savedDarkMode = localStorage.getItem('darkMode');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const shouldUseDark = savedDarkMode ? JSON.parse(savedDarkMode) : prefersDark;
        
        setIsDarkMode(shouldUseDark);
        updateDarkModeClass(shouldUseDark);
    }, []);

    /**
     * Update document class and localStorage when dark mode changes
     */
    const updateDarkModeClass = (dark: boolean) => {
        if (dark) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    };

    /**
     * Toggle dark mode
     */
    const toggleDarkMode = () => {
        const newDarkMode = !isDarkMode;
        setIsDarkMode(newDarkMode);
        localStorage.setItem('darkMode', JSON.stringify(newDarkMode));
        updateDarkModeClass(newDarkMode);
    };

    /**
     * Fetch system health status from orchestrator API
     */
    const fetchSystemHealth = useCallback(async () => {
        try {
            const health = await getSystemHealth();
            setSystemHealth(health);
        } catch (err) {
            console.error('Failed to fetch system health:', err);
            setError('Failed to fetch system health');
        }
    }, []);

    /**
     * Fetch all queries from orchestrator API
     */
    const fetchQueries = useCallback(async () => {
        try {
            const queriesData = await getQueries();
            setQueries(queriesData);
        } catch (err) {
            console.error('Failed to fetch queries:', err);
            setError('Failed to fetch queries');
        }
    }, []);

    /**
     * Fetch available tasks from orchestrator API
     */
    const fetchAvailableTasks = useCallback(async () => {
        try {
            const tasks = await getAvailableTasks();
            setAvailableTasks(tasks);
        } catch (err) {
            console.error('Failed to fetch available tasks:', err);
            setError('Failed to fetch available tasks');
        }
    }, []);

    /**
     * Handle query submission from the UI
     */
    const handleQuerySubmit = async (content: string) => {
        setLoading(true);
        try {
            const newQuery = await createQuery(content);
            setSelectedQuery(newQuery);
            
            // Refresh queries list
            await fetchQueries();
            
            // If DAG is available, fetch it
            if (newQuery.dag_id) {
                try {
                    const dag = await getQueryDAG(newQuery.query_id);
                    setSelectedDAG(dag);
                } catch (dagError) {
                    console.error('Failed to fetch DAG:', dagError);
                }
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create query');
        } finally {
            setLoading(false);
        }
    };

    /**
     * Handle query selection for detailed view
     */
    const handleQuerySelect = async (query: Query) => {
        setSelectedQuery(query);
        
        if (query.dag_id) {
            try {
                const dag = await getQueryDAG(query.query_id);
                setSelectedDAG(dag);
            } catch (err) {
                console.error('Failed to fetch DAG for query:', err);
                setSelectedDAG(null);
            }
        } else {
            setSelectedDAG(null);
        }
    };

    /**
     * Refresh all dashboard data
     */
    const refreshDashboard = useCallback(async () => {
        await Promise.all([
            fetchSystemHealth(),
            fetchQueries(),
            fetchAvailableTasks()
        ]);
    }, [fetchSystemHealth, fetchQueries, fetchAvailableTasks]);

    // Initial data load
    useEffect(() => {
        refreshDashboard();
    }, [refreshDashboard]);

    // Auto-refresh setup
    useEffect(() => {
        if (!autoRefresh) return;

        const interval = setInterval(refreshDashboard, refreshInterval);
        return () => clearInterval(interval);
    }, [autoRefresh, refreshInterval, refreshDashboard]);

    /**
     * Clear error messages after a delay
     */
    useEffect(() => {
        if (error) {
            const timer = setTimeout(() => setError(null), 5000);
            return () => clearTimeout(timer);
        }
    }, [error]);

    const tabs = [
        { id: 'overview', label: 'Overview', icon: '📊' },
        { id: 'queries', label: 'Queries', icon: '🔍' },
        { id: 'tasks', label: 'Tasks', icon: '⚙️' },
        { id: 'analytics', label: 'Analytics', icon: '📈' }
    ] as const;

    return (
        <div className="h-screen w-full flex flex-col bg-gray-50 dark:bg-dark-bg transition-colors duration-200">
            {/* Header */}
            <header className="bg-white dark:bg-dark-surface shadow-sm border-b border-gray-200 dark:border-gray-700 transition-colors duration-200">
                <div className="px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900 dark:text-white transition-colors duration-200">
                                Orchestrator Management Dashboard
                            </h1>
                            <p className="text-sm text-gray-600 dark:text-gray-300 transition-colors duration-200">
                                Multi-Agent Workflow Orchestration System
                            </p>
                        </div>
                        
                        <div className="flex items-center space-x-4">
                            {/* Dark Mode Toggle */}
                            <button
                                onClick={toggleDarkMode}
                                className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-all duration-200 group"
                                title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                            >
                                {isDarkMode ? (
                                    <svg className="w-5 h-5 text-yellow-500 group-hover:text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                                    </svg>
                                ) : (
                                    <svg className="w-5 h-5 text-gray-700 group-hover:text-gray-900" fill="currentColor" viewBox="0 0 20 20">
                                        <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                                    </svg>
                                )}
                            </button>
                            
                            {/* Auto-refresh toggle */}
                            <div className="flex items-center space-x-2">
                                <label htmlFor="auto-refresh" className="text-sm text-gray-600 dark:text-gray-300 transition-colors duration-200">
                                    Auto-refresh
                                </label>
                                <input
                                    id="auto-refresh"
                                    type="checkbox"
                                    checked={autoRefresh}
                                    onChange={(e) => setAutoRefresh(e.target.checked)}
                                    className="rounded border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-blue-400 focus:ring-blue-500 dark:focus:ring-blue-400 transition-colors duration-200"
                                />
                                <select
                                    value={refreshInterval}
                                    onChange={(e) => setRefreshInterval(Number(e.target.value))}
                                    className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-white transition-colors duration-200"
                                    disabled={!autoRefresh}
                                >
                                    <option value={1000}>1s</option>
                                    <option value={5000}>5s</option>
                                    <option value={10000}>10s</option>
                                    <option value={30000}>30s</option>
                                </select>
                            </div>
                            
                            {/* Manual refresh button */}
                            <button
                                onClick={refreshDashboard}
                                className="px-3 py-1 bg-blue-500 dark:bg-blue-600 text-white rounded hover:bg-blue-600 dark:hover:bg-blue-700 text-sm transition-colors duration-200 disabled:opacity-50"
                                disabled={loading}
                            >
                                🔄 Refresh
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Error Display */}
            {error && (
                <div className="bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 mx-6 mt-4 rounded transition-colors duration-200">
                    <strong>Error:</strong> {error}
                </div>
            )}

            {/* Tab Navigation */}
            <div className="bg-white dark:bg-dark-surface border-b border-gray-200 dark:border-gray-700 transition-colors duration-200">
                <nav className="px-6">
                    <div className="flex space-x-8">
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                                    activeTab === tab.id
                                        ? 'border-blue-500 dark:border-blue-400 text-blue-600 dark:text-blue-400'
                                        : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:border-gray-300 dark:hover:border-gray-600'
                                }`}
                            >
                                <span className="mr-2">{tab.icon}</span>
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </nav>
            </div>

            {/* Main Content */}
            <main className="flex-1 overflow-hidden bg-gray-50 dark:bg-dark-bg transition-colors duration-200">
                {activeTab === 'overview' && (
                    <div className="h-full p-6">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
                            <div className="space-y-6">
                                <SystemHealth health={systemHealth} />
                                <QueryManager 
                                    onQuerySubmit={handleQuerySubmit}
                                    loading={loading}
                                />
                            </div>
                            <div>
                                <DAGVisualization 
                                    dag={selectedDAG}
                                    query={selectedQuery}
                                />
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'queries' && (
                    <div className="h-full p-6">
                        <QueryManager 
                            queries={queries}
                            selectedQuery={selectedQuery}
                            onQuerySelect={handleQuerySelect}
                            onQuerySubmit={handleQuerySubmit}
                            loading={loading}
                        />
                    </div>
                )}

                {activeTab === 'tasks' && (
                    <div className="h-full p-6">
                        <TaskMonitor 
                            tasks={availableTasks}
                            selectedDAG={selectedDAG}
                        />
                    </div>
                )}

                {activeTab === 'analytics' && (
                    <div className="h-full p-6">
                        <Analytics 
                            queries={queries}
                            tasks={availableTasks}
                            systemHealth={systemHealth}
                        />
                    </div>
                )}
            </main>
        </div>
    );
};

export default Dashboard;
