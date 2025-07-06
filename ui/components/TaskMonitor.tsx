/**
 * TaskMonitor Component
 * 
 * Displays task execution monitoring and status
 */

import React from 'react';
import { TaskMonitorProps } from '../lib/types';

export const TaskMonitor: React.FC<TaskMonitorProps> = ({ tasks, selectedDAG }) => {
    const getTaskStatusColor = (status: string) => {
        switch (status?.toLowerCase()) {
            case 'completed':
                return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400';
            case 'running':
                return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400';
            case 'pending':
                return 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-300';
            case 'failed':
                return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400';
            default:
                return 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-300';
        }
    };

    return (
        <div className="bg-white dark:bg-dark-surface rounded-lg shadow-lg dark:shadow-gray-900/20 p-6 transition-colors duration-200">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 transition-colors duration-200">Task Monitor</h2>
            
            {tasks.length > 0 ? (
                <div className="space-y-3">
                    <div className="text-sm text-gray-600 dark:text-gray-400 mb-4 transition-colors duration-200">
                        Monitoring {tasks.length} task{tasks.length !== 1 ? 's' : ''}
                        {selectedDAG && ` for DAG: ${selectedDAG.name}`}
                    </div>
                    
                    {tasks.map((task, index) => (
                        <div 
                            key={task.id || index} 
                            className="p-3 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-dark-elevated transition-colors duration-200"
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex-1">
                                    <div className="text-sm font-medium text-gray-900 dark:text-white transition-colors duration-200">
                                        {task.name || `Task ${index + 1}`}
                                    </div>
                                    <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 transition-colors duration-200">
                                        {task.description || 'No description available'}
                                    </div>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <span className={`px-2 py-1 text-xs rounded-full font-medium transition-colors duration-200 ${getTaskStatusColor(task.status)}`}>
                                        {task.status || 'unknown'}
                                    </span>
                                    {task.duration && (
                                        <span className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
                                            {task.duration}s
                                        </span>
                                    )}
                                </div>
                            </div>
                            
                            {task.error && (
                                <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-xs text-red-700 dark:text-red-400 transition-colors duration-200">
                                    <strong>Error:</strong> {task.error}
                                </div>
                            )}
                            
                            {task.progress !== undefined && (
                                <div className="mt-2">
                                    <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400 mb-1 transition-colors duration-200">
                                        <span>Progress</span>
                                        <span>{task.progress}%</span>
                                    </div>
                                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 transition-colors duration-200">
                                        <div 
                                            className="bg-blue-600 dark:bg-blue-400 h-1.5 rounded-full transition-all duration-300" 
                                            style={{ width: `${task.progress}%` }}
                                        ></div>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            ) : (
                <div className="text-center py-8">
                    <div className="text-gray-400 dark:text-gray-500 mb-2 transition-colors duration-200">
                        No tasks to monitor
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400 transition-colors duration-200">
                        Submit a query to see task execution status
                    </div>
                </div>
            )}
        </div>
    );
};
