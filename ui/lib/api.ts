import { Node, Edge } from 'reactflow';
import { 
    Query, 
    DAG, 
    Task, 
    SystemHealthStatus, 
    QueryListResponse,
    QueryRequest,
    TaskStatusUpdate,
    APIError 
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Error handling utility for API responses
 */
async function handleAPIResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error ${response.status}: ${errorText}`);
    }
    return response.json();
}

/**
 * Get system health status
 */
export async function getSystemHealth(): Promise<SystemHealthStatus> {
    const response = await fetch(`${API_BASE_URL}/health`);
    return handleAPIResponse<SystemHealthStatus>(response);
}

/**
 * Get all queries (Note: This endpoint may not exist yet, using mock for now)
 */
export async function getQueries(): Promise<Query[]> {
    // TODO: Implement when API endpoint is available
    // For now, return empty array as the API doesn't have a list endpoint yet
    return [];
}

/**
 * Get available tasks for execution
 */
export async function getAvailableTasks(capability?: string): Promise<Task[]> {
    const url = new URL(`${API_BASE_URL}/api/tasks/available`);
    if (capability) {
        url.searchParams.append('capability', capability);
    }
    
    const response = await fetch(url.toString());
    return handleAPIResponse<Task[]>(response);
}

/**
 * Create a new query
 */
export async function createQuery(content: string): Promise<Query> {
    const response = await fetch(`${API_BASE_URL}/api/queries`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            content,
            metadata: {},
            sync: true,
        }),
    });

    return handleAPIResponse<Query>(response);
}

export async function getQuery(queryId: string): Promise<Query> {
    const response = await fetch(`${API_BASE_URL}/api/queries/${queryId}`);
    return handleAPIResponse<Query>(response);
}

export async function getQueryDAG(queryId: string): Promise<DAG> {
    const response = await fetch(`${API_BASE_URL}/api/queries/${queryId}/dag`);
    return handleAPIResponse<DAG>(response);
}

export function convertDAGToFlowElements(dag: DAG): { nodes: Node[]; edges: Edge[] } {
    const nodes: Node[] = dag.tasks.map((task, index) => ({
        id: task.id,
        type: index === 0 ? 'input' : index === dag.tasks.length - 1 ? 'output' : 'default',
        data: {
            label: task.name,
            description: task.description,
            status: task.status,
            complexity: task.estimated_complexity,
        },
        position: { x: 250, y: index * 100 },
    }));

    const edges: Edge[] = dag.tasks.flatMap(task =>
        task.downstream_tasks.map(targetId => ({
            id: `${task.id}-${targetId}`,
            source: task.id,
            target: targetId,
        }))
    );

    return { nodes, edges };
} 