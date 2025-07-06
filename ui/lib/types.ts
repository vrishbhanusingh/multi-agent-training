/**
 * Type definitions for the Orchestrator Management UI
 * 
 * This file contains all TypeScript interface definitions used throughout
 * the dashboard components for type safety and consistency.
 */

import { Node, Edge } from 'reactflow';

// Core entity types from the orchestrator API
export interface Query {
    query_id: string;
    status: string;
    dag_id: string | null;
    created_at: string | null;
    updated_at: string | null;
}

export interface Task {
    id: string;
    name: string;
    description: string;
    task_type: string;
    parameters: Record<string, any>;
    status: string;
    assigned_to?: string | null;
    estimated_complexity: number;
    required_capabilities: string[];
    created_at: string | null;
    updated_at: string | null;
    result?: Record<string, any> | null;
    error?: string | null;
    upstream_tasks: string[];
    downstream_tasks: string[];
    duration?: number; // Task execution duration in seconds
    progress?: number; // Task progress percentage (0-100)
}

export interface DAG {
    id: string;
    name: string;
    description: string;
    created_at: string;
    updated_at: string;
    version: number;
    tasks: Task[];
}

// System health and monitoring types
export interface ComponentHealth {
    status: 'healthy' | 'unhealthy' | 'unknown';
    error?: string;
}

export interface SystemHealthStatus {
    status: 'healthy' | 'degraded' | 'unhealthy';
    version: string;
    components: {
        database: ComponentHealth;
        rabbitmq: ComponentHealth;
        [key: string]: ComponentHealth;
    };
}

// API request/response types
export interface QueryRequest {
    content: string;
    metadata?: Record<string, any>;
    sync?: boolean;
}

export interface TaskStatusUpdate {
    status: string;
    result?: Record<string, any>;
    error?: string;
}

// UI-specific types
export interface QueryListResponse {
    queries: Query[];
    total: number;
}

export interface DAGFlowElements {
    nodes: Node[];
    edges: Edge[];
}

// Dashboard component props
export interface SystemHealthProps {
    health: SystemHealthStatus | null;
}

export interface QueryManagerProps {
    queries?: Query[];
    selectedQuery?: Query | null;
    onQuerySelect?: (query: Query) => void;
    onQuerySubmit: (content: string) => Promise<void>;
    loading?: boolean;
}

export interface DAGVisualizationProps {
    dag: DAG | null;
    query: Query | null;
}

export interface TaskMonitorProps {
    tasks: Task[];
    selectedDAG?: DAG | null;
}

export interface AnalyticsProps {
    queries: Query[];
    tasks: Task[];
    systemHealth: SystemHealthStatus | null;
}

// Analytics and metrics types
export interface WorkflowMetrics {
    totalQueries: number;
    completedQueries: number;
    failedQueries: number;
    averageExecutionTime: number;
    totalTasks: number;
    completedTasks: number;
    failedTasks: number;
    pendingTasks: number;
}

export interface PerformanceData {
    timestamp: string;
    cpuUsage: number;
    memoryUsage: number;
    taskThroughput: number;
    errorRate: number;
}

// Error handling types
export interface APIError {
    message: string;
    status?: number;
    details?: any;
}

// Node types for ReactFlow
export interface TaskNodeData {
    label: string;
    description: string;
    status: string;
    complexity: number;
    taskType: string;
    assignedTo?: string;
    result?: Record<string, any>;
    error?: string;
}

export interface CustomNodeProps {
    data: TaskNodeData;
    selected: boolean;
}

// Filter and sort options
export interface QueryFilter {
    status?: string[];
    dateRange?: {
        start: Date;
        end: Date;
    };
    searchTerm?: string;
}

export interface TaskFilter {
    status?: string[];
    capability?: string[];
    complexity?: {
        min: number;
        max: number;
    };
    assignedTo?: string[];
}

// Real-time update types
export interface LiveUpdate {
    type: 'query_update' | 'task_update' | 'dag_update' | 'system_health';
    data: any;
    timestamp: string;
}

export type SortOrder = 'asc' | 'desc';

export interface SortOption {
    field: string;
    order: SortOrder;
}
