\
import pytest
from pydantic import ValidationError
from common.a2a_protocol import models, serialization
import json
from datetime import datetime, timezone
import base64
import uuid

# --- Fixtures ---

@pytest.fixture
def text_part_data():
    return {"type": "text", "content": "Hello, world!", "content_type": "text/plain"}

@pytest.fixture
def json_string_part_data():
    # Representing JSON data as a string within a 'text' part
    return {"type": "text", "content": '{"key": "value", "num": 123}', "content_type": "application/json"}

@pytest.fixture
def file_part_bytes_data():
    return {"type": "file", "content": b"This is binary file content.", "content_type": "application/octet-stream", "filename": "test.bin"}

@pytest.fixture
def file_part_uri_data():
    # File content can also be a URI string
    return {"type": "file", "content": "file:///path/to/resource.txt", "content_type": "text/plain", "filename": "resource.txt"}

@pytest.fixture
def sample_message_data(text_part_data, json_string_part_data, file_part_uri_data):
    # Using valid part types now
    return {
        "role": "user",
        "parts": [
            text_part_data,
            json_string_part_data, # JSON string in text part
            file_part_uri_data
        ]
        # timestamp and metadata will use defaults
    }

@pytest.fixture
def sample_artifact_data():
    # Fixed: Added required type and uri
    return {
        "type": "file",
        "uri": "file:///generated/output.txt",
        "description": "Generated output file"
        # metadata will use default
    }

@pytest.fixture
def sample_task_data(sample_message_data, sample_artifact_data):
    # Using valid message and artifact
    return {
        "id": str(uuid.uuid4()), # Generate fresh UUID for tests
        "status": "submitted",
        "history": [sample_message_data], # Use the fixture
        "artifacts": [sample_artifact_data] # Use the fixture
        # created_at, updated_at, metadata use defaults
    }

# --- Part Model Tests ---

def test_part_creation_valid(text_part_data, json_string_part_data, file_part_bytes_data, file_part_uri_data):
    """Test valid Part object creation for different types."""
    text_part = models.Part(**text_part_data)
    assert text_part.type == "text"
    assert text_part.content == text_part_data["content"]
    assert text_part.content_type == text_part_data["content_type"]
    assert text_part.filename is None

    json_part = models.Part(**json_string_part_data) # JSON string in text part
    assert json_part.type == "text"
    assert json_part.content == json_string_part_data["content"]
    assert json_part.content_type == "application/json"
    # Should be valid JSON
    assert isinstance(json.loads(json_part.content), dict)

    file_bytes_part = models.Part(**file_part_bytes_data)
    assert file_bytes_part.type == "file"
    # Content should now be correctly stored as bytes internally
    assert isinstance(file_bytes_part.content, bytes)
    assert file_bytes_part.content == file_part_bytes_data["content"]
    assert file_bytes_part.content_type == file_part_bytes_data["content_type"]
    assert file_bytes_part.filename == file_part_bytes_data["filename"]

    file_uri_part = models.Part(**file_part_uri_data)
    assert file_uri_part.type == "file"
    assert file_uri_part.content == file_part_uri_data["content"]
    assert file_uri_part.content_type == file_part_uri_data["content_type"]
    assert file_uri_part.filename == file_part_uri_data["filename"]

def test_part_creation_invalid_type():
    """Test Part creation with an invalid type."""
    # Adjust match string for Pydantic v1 Literal error format
    with pytest.raises(ValidationError, match=r"unexpected value; permitted: 'text', 'file', 'tool_code', 'tool_result'"):
        models.Part(type="invalid_type", content="abc")

def test_part_creation_missing_content():
    """Test Part creation missing required content field."""
    with pytest.raises(ValidationError, match="content"):
        models.Part(type="text")

def test_part_creation_file_missing_content_type():
    """Test File Part creation missing content_type."""
    with pytest.raises(ValueError, match="File part must have a 'content_type'"):
        models.Part(type="file", content="abc", filename="test.txt")

def test_part_creation_file_bytes_missing_filename():
    """Test File Part with bytes content missing filename."""
    # This validation now happens in the root_validator after potential decoding
    with pytest.raises(ValueError, match="File part with binary content should have a 'filename'"):
        # Inputting bytes directly
        models.Part(type="file", content=b"abc", content_type="application/octet-stream")

    # Test with base64 string input that decodes to bytes
    base64_content = base64.b64encode(b"abc").decode('utf-8')
    with pytest.raises(ValueError, match="File part with binary content should have a 'filename'"):
        models.Part(type="file", content=base64_content, content_type="application/octet-stream")

def test_part_creation_invalid_filename():
    """Test Part creation with filename on non-file type."""
    # This validation is now in the root_validator
    with pytest.raises(ValueError, match="Filename is not applicable for part type 'text'"):
        models.Part(type="text", content="abc", filename="test.txt")

def test_part_text_with_bytes_content():
    """Test Text Part creation with bytes content (invalid)."""
    with pytest.raises(ValueError, match="Text part content cannot be bytes"):
        models.Part(type="text", content=b"abc")

def test_part_json_invalid_string_content():
    """Test Part type 'text' with invalid JSON string content when content_type is application/json."""
    json_str = '{"key": "value"' # Missing closing brace
    with pytest.raises(ValueError, match="Content for application/json must be a valid JSON string"):
        models.Part(type="text", content=json_str, content_type="application/json")


# --- Message Model Tests ---

def test_message_creation(sample_message_data):
    """Test basic Message object creation."""
    # Manually create parts as models first
    parts = [models.Part(**p_data) for p_data in sample_message_data["parts"]]
    message = models.Message(role=sample_message_data["role"], parts=parts)

    assert message.role == sample_message_data["role"]
    assert len(message.parts) == len(sample_message_data["parts"])
    assert isinstance(message.timestamp, datetime)
    assert message.metadata == {} # Default

def test_message_creation_invalid_role():
    """Test Message creation with invalid role."""
    # Adjust match string for Pydantic v1 Literal error format
    with pytest.raises(ValidationError, match=r"unexpected value; permitted: 'user', 'agent', 'system'"):
        models.Message(role="invalid_role", parts=[models.Part(type="text", content="hi")])

# --- Artifact Model Tests ---

def test_artifact_creation(sample_artifact_data):
    """Test basic Artifact object creation."""
    # Using the fixed fixture
    artifact = models.Artifact(**sample_artifact_data)
    assert artifact.type == sample_artifact_data["type"]
    assert artifact.uri == sample_artifact_data["uri"]
    assert artifact.description == sample_artifact_data["description"]
    assert artifact.metadata == {} # Default

def test_artifact_creation_invalid_type():
    """Test Artifact creation with invalid type."""
    # Adjust match string for Pydantic v1 Literal error format
    with pytest.raises(ValidationError, match=r"unexpected value; permitted: 'file', 'url', 'tool_result', 'message_id'"):
        models.Artifact(type="invalid", uri="http://example.com")

def test_artifact_creation_missing_uri():
    """Test Artifact creation missing required uri."""
    with pytest.raises(ValidationError, match="uri"):
        models.Artifact(type="url")


# --- Task Model Tests ---

def test_task_creation(sample_task_data):
    """Test basic Task object creation."""
    # Need to construct Message objects first
    history = []
    for msg_data in sample_task_data["history"]:
        parts = [models.Part(**p_data) for p_data in msg_data["parts"]]
        history.append(models.Message(role=msg_data["role"], parts=parts))

    # Need to construct Artifact objects
    artifacts = [models.Artifact(**a_data) for a_data in sample_task_data["artifacts"]]

    task = models.Task(
        id=sample_task_data["id"],
        status=sample_task_data["status"],
        history=history,
        artifacts=artifacts
    )

    assert task.id == sample_task_data["id"]
    assert task.status == sample_task_data["status"]
    assert len(task.history) == len(sample_task_data["history"])
    assert len(task.artifacts) == len(sample_task_data["artifacts"])
    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)
    assert task.metadata == {} # Default

def test_task_creation_invalid_status():
    """Test Task creation with invalid status."""
    # Adjust match string for Pydantic v1 Literal error format
    with pytest.raises(ValidationError, match=r"unexpected value; permitted: 'submitted', 'in_progress', 'completed', 'failed', 'cancelled'"):
        models.Task(status="invalid_status")

def test_task_id_default():
    """Test Task ID defaults to a UUID string."""
    task = models.Task()
    assert isinstance(task.id, str)
    # Basic check for UUID format
    assert len(task.id) == 36
    assert task.id.count('-') == 4

def test_task_timestamps_default():
    """Test Task timestamps default correctly."""
    task = models.Task()
    # Use timezone.utc for comparison
    now = datetime.now(timezone.utc)
    assert isinstance(task.created_at, datetime)
    assert isinstance(task.updated_at, datetime)
    # Check they are recent (within a small delta)
    assert abs((now - task.created_at).total_seconds()) < 5
    assert abs((now - task.updated_at).total_seconds()) < 5 # Check updated_at too

# --- Serialization/Deserialization Tests ---

def test_serialization_deserialization_task(sample_task_data):
    """Test serializing and deserializing a Task object."""
    # --- Create the Task object ---
    history = []
    for msg_data in sample_task_data["history"]:
        parts = [models.Part(**p_data) for p_data in msg_data["parts"]]
        history.append(models.Message(role=msg_data["role"], parts=parts))
    artifacts = [models.Artifact(**a_data) for a_data in sample_task_data["artifacts"]]
    original_task = models.Task(
        id=sample_task_data["id"],
        status=sample_task_data["status"],
        history=history,
        artifacts=artifacts
    )

    # Add a part with bytes to test its serialization
    bytes_part_data = {"type": "file", "content": b"binary data", "content_type": "application/octet-stream", "filename": "data.bin"}
    bytes_part = models.Part(**bytes_part_data)
    original_task.history[0].parts.append(bytes_part)

    # --- Serialize ---
    json_string = serialization.serialize(original_task)
    assert isinstance(json_string, str)

    # --- Verify Serialized Bytes ---
    # Check that the bytes part was base64 encoded in the JSON string
    serialized_data = json.loads(json_string)
    # Find the bytes part we added (assuming it's the last one in the first message)
    serialized_bytes_part = serialized_data['history'][0]['parts'][-1]
    assert serialized_bytes_part['type'] == 'file'
    assert serialized_bytes_part['filename'] == 'data.bin'
    expected_base64 = base64.b64encode(b"binary data").decode('utf-8')
    assert serialized_bytes_part['content'] == expected_base64 # Compare with base64 string

    # --- Deserialize ---
    deserialized_task = serialization.deserialize(json_string)

    # --- Verify Deserialized Object ---
    assert isinstance(deserialized_task, models.Task)
    assert deserialized_task.id == original_task.id
    assert deserialized_task.status == original_task.status
    assert len(deserialized_task.history) == len(original_task.history)
    assert len(deserialized_task.artifacts) == len(original_task.artifacts)

    # Verify the deserialized bytes part content
    deserialized_bytes_part = deserialized_task.history[0].parts[-1]
    assert deserialized_bytes_part.type == 'file'
    assert deserialized_bytes_part.filename == 'data.bin'
    assert isinstance(deserialized_bytes_part.content, bytes) # Should be bytes now
    assert deserialized_bytes_part.content == b"binary data" # Compare with original bytes

    # Compare other parts (simple comparison might work if order is preserved)
    # For more robust comparison, might need to compare field by field or sort lists
    assert deserialized_task.history[0].role == original_task.history[0].role
    assert deserialized_task.artifacts[0].uri == original_task.artifacts[0].uri

def test_serialization_bytes(file_part_bytes_data):
    """Test serialization specifically handles bytes correctly (base64 encoding)."""
    part = models.Part(**file_part_bytes_data)
    # Use the model's .json() method which utilizes the Config
    json_string = part.json()
    serialized_data = json.loads(json_string)

    expected_base64 = base64.b64encode(file_part_bytes_data["content"]).decode('utf-8')
    assert serialized_data["content"] == expected_base64 # Check against base64 string
    assert serialized_data["type"] == file_part_bytes_data["type"]
    assert serialized_data["content_type"] == file_part_bytes_data["content_type"]
    assert serialized_data["filename"] == file_part_bytes_data["filename"]

def test_deserialization_bytes_base64(file_part_bytes_data):
    """Test deserialization handles base64 encoded strings for bytes content."""
    original_bytes = file_part_bytes_data["content"]
    base64_content = base64.b64encode(original_bytes).decode('utf-8')

    # Create JSON string with base64 content
    json_data = {
        "type": file_part_bytes_data["type"],
        "content": base64_content, # Use the base64 string here
        "content_type": file_part_bytes_data["content_type"],
        "filename": file_part_bytes_data["filename"]
    }
    json_string = json.dumps(json_data)

    # Deserialize using Pydantic's parse_raw which triggers validation
    deserialized_part = models.Part.parse_raw(json_string)

    assert deserialized_part.type == file_part_bytes_data["type"]
    assert isinstance(deserialized_part.content, bytes) # Content should be decoded to bytes
    assert deserialized_part.content == original_bytes # Compare with original bytes
    assert deserialized_part.content_type == file_part_bytes_data["content_type"]
    assert deserialized_part.filename == file_part_bytes_data["filename"]

def test_deserialization_invalid_json():
    """Test deserialization with invalid JSON string."""
    invalid_json = "{\"key\": \"value\"" # Malformed JSON
    # Expect ValueError from our deserialize function
    with pytest.raises(ValueError, match="Invalid JSON format"):
        serialization.deserialize(invalid_json, models.Task)

def test_deserialization_validation_error(sample_task_data):
    """Test deserialization raises ValueError for invalid data structure."""
    # Create a valid Task object first
    history = [models.Message(**msg_data) for msg_data in sample_task_data["history"]]
    artifacts = [models.Artifact(**a_data) for a_data in sample_task_data["artifacts"]]
    task = models.Task(
        id=sample_task_data["id"],
        status=sample_task_data["status"],
        history=history,
        artifacts=artifacts
    )
    valid_json_string = serialization.serialize(task)
    valid_data = json.loads(valid_json_string)

    # Introduce an error (e.g., invalid status)
    valid_data["status"] = "invalid_status_value"
    invalid_json_string = json.dumps(valid_data)

    # Expect ValueError from our deserialize function wrapping ValidationError
    with pytest.raises(ValueError, match=f"JSON data does not match {models.Task.__name__} schema"):
        serialization.deserialize(invalid_json_string, models.Task)
