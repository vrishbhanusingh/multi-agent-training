/**
 * Analytics Component
 * 
 * Displays analytics and metrics
 */

import React from 'react';
import { AnalyticsProps } from '../lib/types';

export const Analytics: React.FC<AnalyticsProps> = ({ queries, tasks, systemHealth }) => {
    // Calculate analytics metrics
    const totalQueries = queries.length;
    const completedQueries = queries.filter(q => q.status === 'completed').length;
    const failedQueries = queries.filter(q => q.status === 'failed').length;
    const processingQueries = queries.filter(q => q.status === 'processing').length;
    
    const totalTasks = tasks.length;
    const completedTasks = tasks.filter(t => t.status === 'completed').length;
    const runningTasks = tasks.filter(t => t.status === 'running').length;
    const failedTasks = tasks.filter(t => t.status === 'failed').length;
    
    const successRate = totalQueries > 0 ? ((completedQueries / totalQueries) * 100).toFixed(1) : '0';
    const taskCompletionRate = totalTasks > 0 ? ((completedTasks / totalTasks) * 100).toFixed(1) : '0';

    const MetricCard = ({ title, value, subtitle, color = 'blue' }: { 
        title: string; 
        value: string | number; 
        subtitle?: string; 
        color?: 'blue' | 'green' | 'red' | 'yellow' | 'gray' 
    }) => {
        const colorClasses = {
            blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400',
            green: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400',
            red: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400',
            yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400',
            gray: 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-300'
        };

        return (
            <div className="bg-gray-50 dark:bg-dark-elevated p-4 rounded-lg transition-colors duration-200">
                <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1 transition-colors duration-200">
                    {title}
                </div>
                <div className={`text-2xl font-bold mb-1 ${colorClasses[color]} px-2 py-1 rounded transition-colors duration-200`}>
                    {value}
                </div>
                {subtitle && (
                    <div className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
                        {subtitle}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="bg-white dark:bg-dark-surface rounded-lg shadow-lg dark:shadow-gray-900/20 p-6 transition-colors duration-200">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 transition-colors duration-200">Analytics Dashboard</h2>
            
            {/* Query Analytics */}
            <div className="mb-8">
                <h3 className="text-md font-medium text-gray-800 dark:text-gray-200 mb-4 transition-colors duration-200">Query Analytics</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <MetricCard title="Total Queries" value={totalQueries} color="blue" />
                    <MetricCard title="Completed" value={completedQueries} color="green" />
                    <MetricCard title="Processing" value={processingQueries} color="yellow" />
                    <MetricCard title="Failed" value={failedQueries} color="red" />
                </div>
                <div className="mt-4">
                    <MetricCard 
                        title="Success Rate" 
                        value={`${successRate}%`} 
                        subtitle={`${completedQueries} of ${totalQueries} queries completed successfully`}
                        color={parseFloat(successRate) >= 80 ? 'green' : parseFloat(successRate) >= 60 ? 'yellow' : 'red'}
                    />
                </div>
            </div>

            {/* Task Analytics */}
            <div className="mb-8">
                <h3 className="text-md font-medium text-gray-800 dark:text-gray-200 mb-4 transition-colors duration-200">Task Analytics</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <MetricCard title="Total Tasks" value={totalTasks} color="blue" />
                    <MetricCard title="Completed" value={completedTasks} color="green" />
                    <MetricCard title="Running" value={runningTasks} color="yellow" />
                    <MetricCard title="Failed" value={failedTasks} color="red" />
                </div>
                <div className="mt-4">
                    <MetricCard 
                        title="Completion Rate" 
                        value={`${taskCompletionRate}%`} 
                        subtitle={`${completedTasks} of ${totalTasks} tasks completed`}
                        color={parseFloat(taskCompletionRate) >= 80 ? 'green' : parseFloat(taskCompletionRate) >= 60 ? 'yellow' : 'red'}
                    />
                </div>
            </div>

            {/* System Health Summary */}
            {systemHealth && (
                <div>
                    <h3 className="text-md font-medium text-gray-800 dark:text-gray-200 mb-4 transition-colors duration-200">System Health Summary</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-gray-50 dark:bg-dark-elevated p-4 rounded-lg transition-colors duration-200">
                            <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2 transition-colors duration-200">
                                Overall Status
                            </div>
                            <div className={`text-lg font-semibold px-3 py-1 rounded-full inline-block transition-colors duration-200 ${
                                systemHealth.status === 'healthy' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400' :
                                systemHealth.status === 'degraded' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400' :
                                'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400'
                            }`}>
                                {systemHealth.status.toUpperCase()}
                            </div>
                        </div>
                        
                        <div className="bg-gray-50 dark:bg-dark-elevated p-4 rounded-lg transition-colors duration-200">
                            <div className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2 transition-colors duration-200">
                                Component Health
                            </div>
                            <div className="space-y-1">
                                {Object.entries(systemHealth.components).map(([component, status]) => (
                                    <div key={component} className="flex justify-between items-center text-sm">
                                        <span className="text-gray-700 dark:text-gray-300 capitalize transition-colors duration-200">
                                            {component}
                                        </span>
                                        <span className={`px-2 py-0.5 rounded text-xs font-medium transition-colors duration-200 ${
                                            status.status === 'healthy' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400' :
                                            'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400'
                                        }`}>
                                            {status.status}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Performance Insights */}
            <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-400 dark:border-blue-500 transition-colors duration-200">
                <h4 className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2 transition-colors duration-200">Performance Insights</h4>
                <div className="text-sm text-blue-700 dark:text-blue-400 space-y-1 transition-colors duration-200">
                    {totalQueries === 0 && (
                        <div>• Start by submitting your first query to see analytics</div>
                    )}
                    {totalQueries > 0 && parseFloat(successRate) < 70 && (
                        <div>• Query success rate is below 70% - check for common failure patterns</div>
                    )}
                    {totalTasks > 0 && parseFloat(taskCompletionRate) < 80 && (
                        <div>• Task completion rate could be improved - review failed tasks</div>
                    )}
                    {systemHealth?.status !== 'healthy' && (
                        <div>• System health is degraded - check component status for issues</div>
                    )}
                    {totalQueries > 0 && parseFloat(successRate) >= 80 && (
                        <div>• Great performance! Query success rate is {successRate}%</div>
                    )}
                </div>
            </div>
        </div>
    );
};
