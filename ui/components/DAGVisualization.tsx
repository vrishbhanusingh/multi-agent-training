/**
 * DAGVisualization Component
 * 
 * Renders DAG workflows using ReactFlow for visual representation
 */

import React from 'react';
import ReactFlow, { Node, Edge, Controls, Background } from 'reactflow';
import { DAGVisualizationProps } from '../lib/types';
import { convertDAGToFlowElements } from '../lib/api';

export const DAGVisualization: React.FC<DAGVisualizationProps> = ({ dag, query }) => {
    if (!dag) {
        return (
            <div className="bg-white dark:bg-dark-surface rounded-lg shadow-lg dark:shadow-gray-900/20 p-6 h-96 transition-colors duration-200">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 transition-colors duration-200">DAG Visualization</h2>
                <div className="flex items-center justify-center h-64 text-gray-400 dark:text-gray-500 transition-colors duration-200">
                    {query ? 'No DAG available for this query' : 'Select a query to view its DAG'}
                </div>
            </div>
        );
    }

    const { nodes, edges } = convertDAGToFlowElements(dag);

    return (
        <div className="bg-white dark:bg-dark-surface rounded-lg shadow-lg dark:shadow-gray-900/20 p-6 h-96 transition-colors duration-200">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 transition-colors duration-200">
                DAG Visualization - {dag.name}
            </h2>
            <div className="h-80 rounded-lg overflow-hidden bg-gray-50 dark:bg-dark-elevated transition-colors duration-200">
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    fitView
                    attributionPosition="bottom-left"
                    className="dark:bg-dark-elevated"
                >
                    <Background 
                        color="#94a3b8" 
                        className="dark:opacity-20"
                    />
                    <Controls 
                        className="dark:bg-dark-surface dark:border-gray-700"
                    />
                </ReactFlow>
            </div>
        </div>
    );
};
