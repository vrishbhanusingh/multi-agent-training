import json
import base64
from typing import Any, Type, TypeVar
from .models import Task, Message, Artifact, Part
from pydantic import ValidationError, BaseModel

# Define a TypeVar for Pydantic models
T = TypeVar('T', bound=BaseModel) # Pydantic dataclasses inherit from BaseModel

def _default_serializer(obj):
    """Default JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode('utf-8')
    # Add other custom serializers here if needed
    # E.g., for datetime:
    # if isinstance(obj, datetime):
    #     return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def serialize(data: Any, indent: int | None = 2) -> str:
    """Serializes Pydantic A2A model objects or other data to JSON strings,
       ensuring bytes are base64 encoded.

    Args:
        data: The Pydantic model instance or other data.
        indent: JSON indentation level (default: 2).

    Returns:
        A JSON string representation of the data.

    Raises:
        TypeError: If the data cannot be serialized.
    """
    try:
        # Use json.dumps with a custom default handler for bytes
        # Pydantic models are dict-like, so this should work.
        # We rely on Pydantic's __dict__ or iteration for structure.
        # For Pydantic models, converting to dict first might be safer:
        if isinstance(data, BaseModel):
             # Use .dict() to get a dictionary representation respecting aliases etc.
             data_dict = data.dict()
             return json.dumps(data_dict, default=_default_serializer, indent=indent)
        else:
             # Fallback for non-Pydantic objects
             return json.dumps(data, default=_default_serializer, indent=indent)
    except TypeError as e:
        print(f"Serialization Error: {e}")
        raise TypeError(f"Failed to serialize object of type {type(data)}") from e
    except Exception as e:
        # Catch other potential errors
        print(f"Unexpected Serialization Error: {e}")
        raise TypeError(f"Failed to serialize object of type {type(data)}") from e

def deserialize(json_str: str, model_type: Type[T]) -> T:
    """Deserializes JSON strings back into specified Pydantic A2A model objects.

    Args:
        json_str: The JSON string to deserialize.
        model_type: The Pydantic model class (e.g., Task, Message) to deserialize into.

    Returns:
        An instance of the specified Pydantic model.

    Raises:
        ValueError: If the JSON string is invalid or doesn't match the model structure.
    """
    try:
        # Use Pydantic's parse_raw() method for deserialization and validation
        return model_type.parse_raw(json_str)
    except ValidationError as e:
        print(f"Pydantic Deserialization/Validation Error: {e}")
        # Raise ValueError as per previous logic, which tests now expect
        raise ValueError(f"JSON data does not match {model_type.__name__} schema") from e
    except json.JSONDecodeError as e:
        print(f"Invalid JSON format: {e}")
        # Raise ValueError for invalid JSON, which tests now expect
        raise ValueError("Invalid JSON format") from e
    except Exception as e:
        # Catch other potential errors during parsing
        print(f"Unexpected Deserialization Error: {e}")
        raise ValueError(f"Failed to deserialize JSON into {model_type.__name__}") from e

# Example Usage (can be moved to tests)
if __name__ == '__main__':
    # Create a sample Task object (assuming models.py is adjacent)
    sample_task = Task(id="task-123", status="submitted")
    sample_message = Message(role='user', parts=[Part(type='text', content='Test message')])
    sample_task.history.append(sample_message)

    print("Original Task:", sample_task)

    # Serialize the task
    try:
        serialized_json = serialize(sample_task)
        print("\nSerialized JSON:")
        print(serialized_json)

        # Deserialize back into a Task object
        deserialized_task = deserialize(serialized_json, Task)
        print("\nDeserialized Task:", deserialized_task)

        # Verify equality (Pydantic dataclasses should support equality checks)
        assert deserialized_task == sample_task
        print("\nSerialization and Deserialization successful!")

    except (TypeError, ValueError) as e:
        print(f"\nError during example: {e}")

    # Example with invalid JSON
    invalid_json = '{"id": "task-abc", "status": "invalid-status"}'
    try:
        deserialize(invalid_json, Task)
    except ValueError as e:
        print(f"\nCaught expected error for invalid status: {e}")

    # Example with non-serializable type
    try:
        serialize(lambda x: x) # Function is not directly serializable
    except TypeError as e:
        print(f"\nCaught expected error for non-serializable type: {e}")
