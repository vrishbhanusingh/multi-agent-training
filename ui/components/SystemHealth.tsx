/**
 * SystemHealth Component
 * 
 * Displays real-time system health information including:
 * - Overall system status
 * - Individual component health (database, RabbitMQ, etc.)
 * - Version information
 * - Health indicators with visual status
 */

import React from 'react';
import { SystemHealthProps } from '../lib/types';

export const SystemHealth: React.FC<SystemHealthProps> = ({ health }) => {
    if (!health) {
        return (
            <div className="bg-white dark:bg-dark-surface rounded-lg shadow-lg dark:shadow-gray-900/20 p-6 transition-colors duration-200">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 transition-colors duration-200">System Health</h2>
                <div className="text-center py-8">
                    <div className="text-gray-400 dark:text-gray-500 transition-colors duration-200">Loading system health...</div>
                </div>
            </div>
        );
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'healthy':
                return 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30';
            case 'degraded':
                return 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30';
            case 'unhealthy':
                return 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30';
            default:
                return 'text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'healthy':
                return '✅';
            case 'degraded':
                return '⚠️';
            case 'unhealthy':
                return '❌';
            default:
                return '❓';
        }
    };

    return (
        <div className="bg-white dark:bg-dark-surface rounded-lg shadow-lg dark:shadow-gray-900/20 p-6 transition-colors duration-200">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 transition-colors duration-200">System Health</h2>
            
            {/* Overall Status */}
            <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300 transition-colors duration-200">Overall Status</span>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium transition-colors duration-200 ${getStatusColor(health.status)}`}>
                        {getStatusIcon(health.status)} {health.status.toUpperCase()}
                    </span>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
                    Version: {health.version}
                </div>
            </div>

            {/* Component Status */}
            <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 transition-colors duration-200">Components</h3>
                {Object.entries(health.components).map(([component, status]) => (
                    <div key={component} className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-dark-elevated rounded transition-colors duration-200">
                        <div className="flex items-center space-x-3">
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 capitalize transition-colors duration-200">
                                {component}
                            </span>
                        </div>
                        <div className="flex items-center space-x-2">
                            <span className={`px-2 py-1 rounded text-xs font-medium transition-colors duration-200 ${getStatusColor(status.status)}`}>
                                {getStatusIcon(status.status)} {status.status}
                            </span>
                        </div>
                    </div>
                ))}
            </div>

            {/* Error Details */}
            {Object.entries(health.components).some(([, status]) => status.error) && (
                <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800 transition-colors duration-200">
                    <h4 className="text-sm font-medium text-red-800 dark:text-red-300 mb-2 transition-colors duration-200">Error Details</h4>
                    <div className="space-y-1">
                        {Object.entries(health.components)
                            .filter(([, status]) => status.error)
                            .map(([component, status]) => (
                                <div key={component} className="text-xs text-red-700 dark:text-red-400 transition-colors duration-200">
                                    <strong>{component}:</strong> {status.error}
                                </div>
                            ))}
                    </div>
                </div>
            )}

            {/* Last Updated */}
            <div className="mt-4 text-xs text-gray-400 dark:text-gray-500 text-center transition-colors duration-200">
                Last updated: {new Date().toLocaleTimeString()}
            </div>
        </div>
    );
};
