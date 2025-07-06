/**
 * QueryManager Component
 * 
 * Handles query submission and management functionality:
 * - Query submission form
 * - Query list display
 * - Query status monitoring
 * - Query selection for detailed view
 */

import React, { useState } from 'react';
import { QueryManagerProps } from '../lib/types';

export const QueryManager: React.FC<QueryManagerProps> = ({ 
    queries = [], 
    selectedQuery, 
    onQuerySelect, 
    onQuerySubmit, 
    loading = false 
}) => {
    const [queryInput, setQueryInput] = useState('');
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!queryInput.trim()) return;

        setError(null);
        try {
            await onQuerySubmit(queryInput);
            setQueryInput(''); // Clear input on successful submission
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to submit query');
        }
    };

    return (
        <div className="bg-white dark:bg-dark-surface rounded-lg shadow-lg dark:shadow-gray-900/20 p-6 transition-colors duration-200">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 transition-colors duration-200">Query Manager</h2>
            
            {/* Query Submission Form */}
            <form onSubmit={handleSubmit} className="mb-6">
                <div className="space-y-4">
                    <div>
                        <label htmlFor="query-input" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 transition-colors duration-200">
                            Submit New Query
                        </label>
                        <textarea
                            id="query-input"
                            value={queryInput}
                            onChange={(e) => setQueryInput(e.target.value)}
                            placeholder="Enter your workflow query... (e.g., 'Process a data pipeline with validation and reporting')"
                            className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-dark-elevated text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 transition-colors duration-200"
                            rows={3}
                            disabled={loading}
                        />
                    </div>
                    <div className="flex justify-between items-center">
                        <div className="text-sm text-gray-500 dark:text-gray-400 transition-colors duration-200">
                            The orchestrator will generate a DAG workflow for your query
                        </div>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white rounded disabled:bg-gray-400 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors duration-200"
                            disabled={loading || !queryInput.trim()}
                        >
                            {loading ? 'Processing...' : 'Submit Query'}
                        </button>
                    </div>
                </div>
            </form>

            {/* Error Display */}
            {error && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md transition-colors duration-200">
                    <div className="text-sm text-red-700 dark:text-red-400 transition-colors duration-200">{error}</div>
                </div>
            )}

            {/* Query List */}
            {queries.length > 0 && (
                <div>
                    <h3 className="text-md font-medium text-gray-900 dark:text-white mb-3 transition-colors duration-200">Recent Queries</h3>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {queries.map((query) => (
                            <div
                                key={query.query_id}
                                className={`p-3 border rounded cursor-pointer transition-colors duration-200 ${
                                    selectedQuery?.query_id === query.query_id
                                        ? 'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20'
                                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-dark-elevated'
                                }`}
                                onClick={() => onQuerySelect?.(query)}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex-1 min-w-0">
                                        <div className="text-sm font-medium text-gray-900 dark:text-white truncate transition-colors duration-200">
                                            Query {query.query_id.substring(0, 8)}
                                        </div>
                                        <div className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">
                                            {query.created_at && new Date(query.created_at).toLocaleString()}
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <span className={`px-2 py-1 text-xs rounded-full transition-colors duration-200 ${
                                            query.status === 'completed' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400' :
                                            query.status === 'processing' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400' :
                                            query.status === 'failed' ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400' :
                                            'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-300'
                                        }`}>
                                            {query.status}
                                        </span>
                                        {query.dag_id && (
                                            <span className="text-xs text-blue-600 dark:text-blue-400 transition-colors duration-200">
                                                DAG Available
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Selected Query Details */}
            {selectedQuery && (
                <div className="mt-6 p-4 bg-gray-50 dark:bg-dark-elevated rounded-md transition-colors duration-200">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2 transition-colors duration-200">Selected Query Details</h4>
                    <div className="space-y-1 text-sm text-gray-700 dark:text-gray-300 transition-colors duration-200">
                        <div><strong>ID:</strong> {selectedQuery.query_id}</div>
                        <div><strong>Status:</strong> {selectedQuery.status}</div>
                        <div><strong>DAG ID:</strong> {selectedQuery.dag_id || 'Not generated'}</div>
                        <div><strong>Created:</strong> {selectedQuery.created_at && new Date(selectedQuery.created_at).toLocaleString()}</div>
                        <div><strong>Updated:</strong> {selectedQuery.updated_at && new Date(selectedQuery.updated_at).toLocaleString()}</div>
                    </div>
                </div>
            )}
        </div>
    );
};
