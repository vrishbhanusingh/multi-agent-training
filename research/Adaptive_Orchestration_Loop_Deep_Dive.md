# Deep Dive: The Adaptive Orchestration Loop

**Objective:** To create a multi-agent system that not only executes tasks but actively learns from its mistakes. This system is designed for resilience and self-improvement, treating errors not as failures, but as training data.

---

## 1. Core Philosophy: From Execution to Resilience

Traditional workflow systems are brittle; they succeed or they fail. This architecture is designed to be **resilient**. The core principle is that the most valuable learning occurs when the system encounters an unexpected problem, diagnoses it, formulates a solution, and verifies the fix.

The system operates on a continuous **Observe -> Orient -> Decide -> Act (OODA)** loop, but with an integrated learning step:

1.  **Observe:** The `OrchestratorAgent` monitors the state of all tasks in Postgres.
2.  **Orient:** When a failure is observed, the orchestrator gathers all context: the original goal, the failed task's description, and the precise error message from the `feedback_notes`.
3.  **Decide:** It enters "Correction Mode" and formulates a new plan to solve the specific error.
4.  **Act:** It dispatches the new corrective tasks.
5.  **Learn (Post-Act):** The outcome (a large bonus reward for a successful fix) is used to update the orchestrator's internal policy, making it less likely to repeat the same category of mistake in the future.

---

## 2. Detailed Component Specification

### **Postgres `tasks` Table Schema**

This table is the central source of truth for the entire system. The `feedback_notes` column is especially critical, as it provides the structured data needed for the `OrchestratorAgent` to understand failures.

**Example `feedback_notes` Structures:**

*   **For a successful code execution:**
    ```json
    {
      "status": "success",
      "notes": "Execution completed.",
      "stdout": "Hello World\n",
      "stderr": ""
    }
    ```
*   **For a failed Python script (e.g., `ModuleNotFoundError`):**
    ```json
    {
      "status": "failed",
      "error_type": "ModuleNotFoundError",
      "error_message": "No module named 'non_existent_package'",
      "traceback": "Traceback (most recent call last):\n  File \"/app/executor.py\", line 15, in execute_task\n    import non_existent_package\nModuleNotFoundError: No module named 'non_existent_package'"
    }
    ```
*   **For a failed file operation (e.g., file not found):**
    ```json
    {
        "status": "failed",
        "error_type": "FileNotFoundError",
        "error_message": "No such file or directory: '/app/data/missing_file.txt'",
        "details": {
            "operation": "read",
            "path": "/app/data/missing_file.txt"
        }
    }
    ```

```sql
CREATE TABLE workflows (
    workflow_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_prompt TEXT NOT NULL,
    creation_timestamp TIMESTAMPTZ DEFAULT NOW(),
    final_status VARCHAR(20) DEFAULT 'in_progress',
    total_reward FLOAT DEFAULT 0.0
);

CREATE TABLE tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(workflow_id),
    parent_id UUID REFERENCES tasks(task_id), -- For sub-task relationships
    task_order INT NOT NULL, -- Defines the original sequence
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, dispatched, in_progress, success, failed, paused
    dependencies UUID[], -- Array of task_ids this task depends on
    executor_type VARCHAR(50) NOT NULL, -- e.g., 'code_executor', 'file_writer'
    reward FLOAT NOT NULL DEFAULT 0.0,
    feedback_notes JSONB, -- Stores structured error/success data
    retries INT NOT NULL DEFAULT 0,
    creation_timestamp TIMESTAMPTZ DEFAULT NOW(),
    last_update_timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_workflow_id ON tasks(workflow_id);
```

### **RabbitMQ Topology**

-   **Exchange:** `agent_exchange` (Type: `direct`)
-   **Queues:**
    -   `task_dispatch_queue`: For the orchestrator to send out new tasks.
    -   `task_results_queue`: For executors to report back their results.
-   **Bindings:**
    -   The `OrchestratorAgent` publishes to the `task_dispatch_queue`.
    -   Each `ExecutorAgent` subscribes to the `task_dispatch_queue`.
    -   All `ExecutorAgent`s publish their results to the `task_results_queue`.
    -   The `EvaluatorAgent` subscribes to the `task_results_queue`.

### **`ExecutorAgent` Logic**

```python
# Pseudo-code for the main loop of an ExecutorAgent
import json
import traceback

def main_loop():
    connection = connect_to_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue='task_dispatch_queue')

    def callback(ch, method, properties, body):
        task = json.loads(body)
        task_id = task['task_id']
        result = {}
        try:
            # Core task execution logic
            output = execute_task(task['description'])
            result = {
                "task_id": task_id,
                "status": "success",
                "data": output
            }
        except Exception as e:
            # Detailed error capture
            result = {
                "task_id": task_id,
                "status": "failed",
                "error_details": {
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc()
                }
            }
        finally:
            # Publish result regardless of outcome
            channel.basic_publish(
                exchange='',
                routing_key='task_results_queue',
                body=json.dumps(result)
            )

    channel.basic_consume(queue='task_dispatch_queue', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()
```

### **`EvaluatorAgent` Logic**

The `EvaluatorAgent` acts as the impartial judge. Its role is to translate the raw output from executors into structured feedback and a quantitative reward signal.

A key function within the evaluator is `validate_output`. Its logic would be dispatched based on the task's `executor_type`.

**`validate_output` Dispatch Logic:**
```python
def validate_output(task_type, data):
    if task_type == 'code_executor':
        # For code, "success" just means it ran.
        # A more advanced validator could check for specific outputs or artifacts.
        return True # Assume success if no exception was thrown
    elif task_type == 'file_writer':
        # Verify that the file was actually created and contains the expected content.
        file_path = data.get('path')
        expected_content = data.get('content')
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return f.read() == expected_content
        return False
    elif task_type == 'api_caller':
        # Check for a successful HTTP status code.
        return 200 <= data.get('status_code', 500) < 300
    else:
        return False # Default to invalid for unknown types
```

```python
# Pseudo-code for the EvaluatorAgent
import json

def main_loop():
    # ... connect to RabbitMQ and Postgres ...

    def callback(ch, method, properties, body):
        result = json.loads(body)
        task_id = result['task_id']
        
        # Get current task state from DB to check retries
        db_cursor.execute("SELECT retries FROM tasks WHERE task_id = %s", (task_id,))
        current_retries = db_cursor.fetchone()[0]

        reward = 0.0
        feedback = {}

        if result['status'] == 'success':
            # Simple validation for now, can be expanded
            is_valid = validate_output(result['data'])
            if is_valid:
                reward = 1.5 if current_retries > 0 else 1.0 # Bonus for fixing!
                feedback = {"notes": "Validation passed."}
            else:
                reward = -0.5 # Penalty for incorrect success
                feedback = {"notes": "Output failed validation.", "details": "..."}
        else: # status == 'failed'
            reward = -1.0 - (0.1 * current_retries) # Penalty + cost for retrying
            feedback = result['error_details']

        # Update the database with the outcome
        db_cursor.execute(
            "UPDATE tasks SET status = %s, reward = %s, feedback_notes = %s, last_update_timestamp = NOW() WHERE task_id = %s",
            (result['status'], reward, json.dumps(feedback), task_id)
        )
        db_connection.commit()

    # ... start consuming from 'task_results_queue' ...
```

### **`OrchestratorAgent` Logic: The Correction Mode Deep Dive**

This is the most critical component. When a task fails, the orchestrator's ability to understand the error and formulate a precise solution is what drives the entire learning loop.

1.  **State Monitoring:**
    ```sql
    -- The query the orchestrator runs periodically
    SELECT task_id, status FROM tasks WHERE workflow_id = 'current_workflow_uuid';
    ```

2.  **Triggering Correction Mode:** When the above query returns a task with `status = 'failed'`, the orchestrator halts dispatching new tasks from the original plan and executes the following logic.

3.  **Information Gathering & Self-Prompting:**
    ```python
    # Pseudo-code for the orchestrator's correction logic
    def handle_failed_task(task_id):
        # 1. Get all context from the database
        db_cursor.execute("SELECT t.description, t.feedback_notes, w.user_prompt FROM tasks t JOIN workflows w ON t.workflow_id = w.workflow_id WHERE t.task_id = %s", (task_id,))
        failed_task_desc, feedback, user_prompt = db_cursor.fetchone()
        
        # ... get successful tasks history for the workflow ...

        # 2. Engineer the detailed, structured prompt for the internal LLM
        # THIS IS THE CORE OF THE SELF-REFLECTION PROCESS
        correction_prompt = f"""
        {{
            "request_type": "generate_correction_plan",
            "context": {{
                "overall_goal": "{user_prompt}",
                "failed_task": {{
                    "id": "{task_id}",
                    "description": "{failed_task_desc}",
                    "error_details": {json.dumps(feedback, indent=2)}
                }},
                "history": {{
                    "successful_prior_tasks": [
                        {{ "id": "...", "description": "..." }}
                    ]
                }}
            }},
            "instructions": {{
                "goal": "Analyze the error in the 'failed_task' and generate a sequence of precise, executable sub-tasks to fix it. The final sub-task must be to retry the original failed task.",
                "response_format": {{
                    "type": "array",
                    "items": {{
                        "task": {{
                            "description": "A clear, single-action command for an executor.",
                            "executor_type": "The specific type of agent required (e.g., 'code_executor', 'file_writer').",
                            "rationale": "A brief explanation of why this step is necessary to fix the error."
                        }}
                    }}
                }},
                "constraints": [
                    "Be specific. If a file needs editing, the task should be to write the complete, corrected file.",
                    "If a command needs to be run, provide the exact command.",
                    "The plan must directly address the 'error_message' from the context.",
                    "The final step MUST be a retried version of the original failed task description."
                ]
            }}
        }}
        """

        # 3. Call its own LLM to get the plan
        corrective_plan_str = self.llm.generate(correction_prompt)
        corrective_plan = json.loads(corrective_plan_str)

        # 4. Perform DAG Surgery
        insert_corrective_plan_into_db(failed_task_id, corrective_plan)
    ```

4.  **DAG Surgery Logic:** This process involves atomically pausing the failed task, inserting the new corrective tasks, and rewiring the dependencies to ensure the new plan is executed before the original task is retried.

    **Example Scenario:** Task #3 fails. The orchestrator generates a 2-step corrective plan.

    **Before DAG Surgery:**
    | task_id | description              | dependencies | status    |
    |---------|--------------------------|--------------|-----------|
    | 1       | ...                      | {}           | success   |
    | 2       | ...                      | {1}          | success   |
    | **3**   | **Run python script.py** | **{2}**      | **failed**|
    | 4       | ...                      | {3}          | pending   | 

    **After DAG Surgery:**
    | task_id | description                         | dependencies | status      |
    |---------|-------------------------------------|--------------|-------------|
    | 1       | ...                                 | {}           | success     |
    | 2       | ...                                 | {1}          | success     |
    | **3**   | **Run python script.py**            | **{3.2}**    | **paused**  |
    | 4       | ...                     
