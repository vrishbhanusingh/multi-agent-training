"""
Tests for the domain models.
"""
import unittest
from uuid import UUID, uuid4

from agents.orchestrator_agent.domain.models import Task, DAG, Query, TaskStatus

class TestDomainModels(unittest.TestCase):
    """Test cases for the domain models."""
    
    def test_task_creation(self):
        """Test task creation and properties."""
        task = Task(name="Test Task", description="A test task")
        
        self.assertIsNotNone(task.id)
        self.assertEqual(task.name, "Test Task")
        self.assertEqual(task.description, "A test task")
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertIsNone(task.assigned_to)
        self.assertIsNone(task.result)
        self.assertIsNone(task.error)
    
    def test_dag_creation_and_task_addition(self):
        """Test DAG creation and adding tasks."""
        dag = DAG(name="Test DAG", description="A test DAG")
        task1 = Task(name="Task 1")
        task2 = Task(name="Task 2")
        
        dag.add_task(task1)
        dag.add_task(task2)
        
        self.assertEqual(len(dag.tasks), 2)
        self.assertIn(task1.id, dag.tasks)
        self.assertIn(task2.id, dag.tasks)
    
    def test_dag_dependencies(self):
        """Test adding dependencies between tasks in a DAG."""
        dag = DAG(name="Test DAG")
        task1 = Task(name="Task 1")
        task2 = Task(name="Task 2")
        task3 = Task(name="Task 3")
        
        dag.add_task(task1)
        dag.add_task(task2)
        dag.add_task(task3)
        
        dag.add_dependency(task1.id, task2.id)
        dag.add_dependency(task2.id, task3.id)
        
        self.assertIn(task2.id, task1._downstream_tasks)
        self.assertIn(task1.id, task2._upstream_tasks)
        self.assertIn(task3.id, task2._downstream_tasks)
        self.assertIn(task2.id, task3._upstream_tasks)
    
    def test_ready_tasks(self):
        """Test detection of ready tasks in a DAG."""
        dag = DAG(name="Test DAG")
        task1 = Task(name="Task 1")
        task2 = Task(name="Task 2")
        task3 = Task(name="Task 3")
        
        dag.add_task(task1)
        dag.add_task(task2)
        dag.add_task(task3)
        
        dag.add_dependency(task1.id, task2.id)
        dag.add_dependency(task1.id, task3.id)
        
        # Only task1 should be ready initially
        ready_tasks = dag.get_ready_tasks()
        self.assertEqual(len(ready_tasks), 1)
        self.assertEqual(ready_tasks[0].id, task1.id)
        
        # Complete task1, task2 and task3 should now be ready
        dag.update_task_status(task1.id, TaskStatus.COMPLETED)
        ready_tasks = dag.get_ready_tasks()
        self.assertEqual(len(ready_tasks), 2)
        
    def test_dag_validation(self):
        """Test DAG validation for cycles."""
        dag = DAG(name="Test DAG")
        task1 = Task(name="Task 1")
        task2 = Task(name="Task 2")
        task3 = Task(name="Task 3")
        
        dag.add_task(task1)
        dag.add_task(task2)
        dag.add_task(task3)
        
        # Create a valid DAG
        dag.add_dependency(task1.id, task2.id)
        dag.add_dependency(task2.id, task3.id)
        
        self.assertTrue(dag.validate())
        
        # Create a cycle
        dag.add_dependency(task3.id, task1.id)
        
        self.assertFalse(dag.validate())
    
    def test_query_creation(self):
        """Test query creation and properties."""
        query = Query(content="Test query", user_id="user123", meta={"key": "value"})
        
        self.assertIsNotNone(query.id)
        self.assertEqual(query.content, "Test query")
        self.assertEqual(query.user_id, "user123")
        self.assertEqual(query.meta, {"key": "value"})
        self.assertEqual(query.status, "pending")
        self.assertIsNone(query.dag_id)


if __name__ == "__main__":
    unittest.main()
