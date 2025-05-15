"""
End-to-end test for the orchestrator-executor system.

This script:
1. Creates a test DAG with multiple tasks
2. Submits the DAG to the orchestrator
3. Monitors the execution
4. Verifies the results

Usage:
    python e2e_test.py --orchestrator-url http://localhost:8000
"""
import argparse
import asyncio
import aiohttp
import uuid
import json
import time
import sys
from typing import Dict, List, Any


class OrchestratorClient:
    """Client for communicating with the orchestrator API."""
    
    def __init__(self, base_url: str, username: str = None, password: str = None):
        """Initialize the client with the orchestrator URL and optional auth."""
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        if self.username and self.password:
            await self._authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _authenticate(self):
        """Authenticate with the orchestrator API."""
        auth_url = f"{self.base_url}/token"
        form_data = {
            "username": self.username,
            "password": self.password
        }
        
        async with self.session.post(auth_url, data=form_data) as response:
            if response.status != 200:
                raise RuntimeError(f"Authentication failed: {await response.text()}")
            
            auth_data = await response.json()
            self.token = auth_data.get("access_token")
            
            if not self.token:
                raise ValueError("No access token received")
    
    async def _get_headers(self):
        """Get request headers with authentication if available."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        return headers
    
    async def submit_dag(self, dag_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a DAG to the orchestrator."""
        url = f"{self.base_url}/api/dags"
        headers = await self._get_headers()
        
        async with self.session.post(url, json=dag_data, headers=headers) as response:
            if response.status != 201:
                raise RuntimeError(f"Failed to submit DAG: {await response.text()}")
            
            return await response.json()
    
    async def submit_query(self, query: str) -> Dict[str, Any]:
        """Submit a query to the orchestrator to generate a DAG."""
        url = f"{self.base_url}/api/queries"
        headers = await self._get_headers()
        
        payload = {
            "query": query,
            "parameters": {}
        }
        
        async with self.session.post(url, json=payload, headers=headers) as response:
            if response.status != 201:
                raise RuntimeError(f"Failed to submit query: {await response.text()}")
            
            return await response.json()
    
    async def get_dag_status(self, dag_id: str) -> Dict[str, Any]:
        """Get the status of a DAG."""
        url = f"{self.base_url}/api/dags/{dag_id}"
        headers = await self._get_headers()
        
        async with self.session.get(url, headers=headers) as response:
            if response.status != 200:
                raise RuntimeError(f"Failed to get DAG status: {await response.text()}")
            
            return await response.json()
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a specific task."""
        url = f"{self.base_url}/api/tasks/{task_id}"
        headers = await self._get_headers()
        
        async with self.session.get(url, headers=headers) as response:
            if response.status != 200:
                raise RuntimeError(f"Failed to get task status: {await response.text()}")
            
            return await response.json()


def create_test_dag() -> Dict[str, Any]:
    """Create a test DAG with multiple tasks."""
    dag_id = str(uuid.uuid4())
    
    # Create a simple sequence of tasks:
    # 1. Generate a message
    # 2. Transform the message to uppercase
    # 3. Verify the result
    
    task1_id = str(uuid.uuid4())
    task2_id = str(uuid.uuid4())
    task3_id = str(uuid.uuid4())
    
    dag = {
        "id": dag_id,
        "name": "E2E Test DAG",
        "description": "DAG for end-to-end testing",
        "tasks": [
            {
                "id": task1_id,
                "task_type": "echo",
                "parameters": {
                    "message": "This is a test message for end-to-end testing"
                },
                "dependencies": []
            },
            {
                "id": task2_id,
                "task_type": "transform",
                "parameters": {
                    "transform": "uppercase",
                    "data": "${" + task1_id + ".result.message}"
                },
                "dependencies": [task1_id]
            },
            {
                "id": task3_id,
                "task_type": "echo", 
                "parameters": {
                    "message": "Verification complete: ${" + task2_id + ".result.result}"
                },
                "dependencies": [task2_id]
            }
        ]
    }
    
    return dag


async def run_e2e_test(orchestrator_url: str, username: str = None, password: str = None):
    """Run the end-to-end test."""
    print(f"Starting end-to-end test with orchestrator at {orchestrator_url}")
    
    # Create a test DAG
    test_dag = create_test_dag()
    print(f"Created test DAG with ID {test_dag['id']}")
    
    async with OrchestratorClient(orchestrator_url, username, password) as client:
        # Submit the DAG
        print("Submitting DAG to orchestrator...")
        result = await client.submit_dag(test_dag)
        dag_id = result["id"]
        print(f"DAG submitted successfully with ID: {dag_id}")
        
        # Wait for DAG execution to complete
        print("Waiting for DAG execution to complete...")
        complete = False
        max_wait_time = 60  # seconds
        start_time = time.time()
        
        while not complete and (time.time() - start_time) < max_wait_time:
            # Get DAG status
            dag_status = await client.get_dag_status(dag_id)
            status = dag_status.get("status", "")
            
            if status == "completed":
                complete = True
                print("DAG execution completed successfully!")
                break
            elif status == "failed":
                raise RuntimeError(f"DAG execution failed: {dag_status.get('error', 'Unknown error')}")
            
            print(f"DAG status: {status}. Waiting...")
            await asyncio.sleep(2)
        
        if not complete:
            raise TimeoutError(f"DAG execution did not complete within {max_wait_time} seconds")
        
        # Verify task results
        print("Verifying task results...")
        for task in test_dag["tasks"]:
            task_id = task["id"]
            task_status = await client.get_task_status(task_id)
            
            print(f"Task {task_id} ({task['task_type']}):")
            print(f"  Status: {task_status.get('status')}")
            print(f"  Result: {json.dumps(task_status.get('result', {}), indent=2)}")
            
            if task_status.get("status") != "completed":
                print(f"  Error: {task_status.get('error', 'No error information')}")
                raise RuntimeError(f"Task {task_id} did not complete successfully")
        
        print("\nAll tasks completed successfully!")
        print("\nTest DAG execution verified successfully.")
        return True


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="End-to-end test for orchestrator-executor system")
    parser.add_argument("--orchestrator-url", type=str, default="http://localhost:8000",
                       help="URL of the orchestrator API")
    parser.add_argument("--username", type=str, help="Username for API authentication")
    parser.add_argument("--password", type=str, help="Password for API authentication")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    try:
        asyncio.run(run_e2e_test(
            orchestrator_url=args.orchestrator_url,
            username=args.username,
            password=args.password
        ))
        print("End-to-end test completed successfully!")
        sys.exit(0)
    except Exception as e:
        print(f"Error during end-to-end test: {e}")
        sys.exit(1)
