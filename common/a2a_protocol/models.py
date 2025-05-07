#!/usr/bin/env python3
"""
Pydantic Models for Agent-to-Agent (A2A) Communication Protocol (Google Style)
Based on the concepts outlined for Google's A2A protocol.
Using Pydantic V1 syntax.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field, validator, root_validator, ValidationError # Added ValidationError
import base64
import json # Added json

# Define Literal types for status and role
TaskStatus = Literal["submitted", "in_progress", "completed", "failed", "cancelled"]
MessageRole = Literal["user", "agent", "system"]
PartType = Literal["text", "file", "tool_code", "tool_result"]
ArtifactType = Literal["file", "url", "tool_result", "message_id"]

# Custom validator for base64 encoding/decoding bytes
def encode_bytes_to_base64(v: Any) -> Optional[str]:
    """Encode bytes to base64 string if present."""
    if isinstance(v, bytes):
        return base64.b64encode(v).decode('utf-8')
    return v

def decode_base64_to_bytes(v: Any) -> Any:
    """Decode base64 string back to bytes if it looks like base64."""
    if isinstance(v, str):
        try:
            # Basic check if it might be base64
            base64.b64decode(v, validate=True)
            return base64.b64decode(v)
        except (ValueError, TypeError):
            # Not valid base64, return original string
            pass
    return v

# --- Model Definitions ---

class Part(BaseModel): # Changed to BaseModel
    """Represents a part of a message, like text or a file."""
    type: PartType = Field(..., description="The type of the part (text, file, etc.).")
    content: Union[str, bytes] = Field(..., description="The content of the part (text or binary data).")
    content_type: Optional[str] = Field(None, description="MIME type for file content (e.g., 'text/plain', 'image/jpeg').")
    filename: Optional[str] = Field(None, description="Filename for file parts.")

    @root_validator(pre=False) # Runs after individual field validation
    def check_and_decode_content(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure attributes match the part type and decode base64 content if necessary."""
        part_type = values.get('type')
        content = values.get('content') # This might be str or bytes initially
        filename = values.get('filename')
        content_type = values.get('content_type')

        is_content_bytes_after_decode = isinstance(content, bytes)

        # --- Potential Base64 Decoding for Input Flexibility ---
        # If content is a string and type suggests binary (file), try decoding
        if part_type == 'file' and isinstance(content, str):
            try:
                decoded_bytes = base64.b64decode(content, validate=True)
                values['content'] = decoded_bytes # Update the dict for final object
                content = decoded_bytes # Update local var for checks below
                is_content_bytes_after_decode = True
            except (ValueError, TypeError):
                # Not valid base64, keep it as a string (might be a URI or plain text)
                is_content_bytes_after_decode = False
        # --- Attribute Checks (using potentially updated 'content' and 'is_content_bytes_after_decode') ---

        # Check for text part with bytes content (using the final state)
        if part_type == 'text' and is_content_bytes_after_decode:
             raise ValueError("Text part content cannot be bytes.")

        # Check filename requirement for non-file types
        if part_type != 'file' and filename:
             raise ValueError(f"Filename is not applicable for part type '{part_type}'.")

        # Check content_type requirement for file types
        if part_type == 'file' and not content_type:
            raise ValueError("File part must have a 'content_type'.")

        # Check filename requirement *after* potential decoding confirms content is bytes
        if part_type == 'file' and is_content_bytes_after_decode and not filename:
            raise ValueError("File part with binary content should have a 'filename'.")

        # --- JSON Content Validation ---
        # Check only if content is still a string
        if content_type == 'application/json' and isinstance(content, str):
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError("Content for application/json must be a valid JSON string.") from e

        return values

    class Config:
        # Pydantic V1 config
        json_encoders = {
            # This handles encoding bytes to base64 during serialization (.json())
            bytes: lambda b: base64.b64encode(b).decode('utf-8')
        }
        # Allow arbitrary types needed for Union[str, bytes]
        arbitrary_types_allowed = True
        validate_assignment = True


class Message(BaseModel): # Changed to BaseModel
    """Represents a single message in the task history."""
    role: MessageRole = Field(..., description="The role of the sender (user, agent, system).")
    parts: List[Part] = Field(..., description="List of parts comprising the message content.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the message was created.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata associated with the message.")

    class Config:
        json_encoders = {
            # Ensure bytes in nested Parts are encoded
            bytes: lambda b: base64.b64encode(b).decode('utf-8')
        }
        arbitrary_types_allowed = True
        validate_assignment = True


class Artifact(BaseModel): # Changed to BaseModel
    """Represents an artifact related to the task (e.g., generated file, URL)."""
    type: ArtifactType = Field(..., description="The type of the artifact.")
    uri: str = Field(..., description="URI pointing to the artifact resource (e.g., file path, URL, message ID).")
    description: Optional[str] = Field(None, description="Optional description of the artifact.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata associated with the artifact.")


class Task(BaseModel): # Changed to BaseModel
    """Represents the overall task being processed."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the task.")
    status: TaskStatus = Field(default="submitted", description="Current status of the task.")
    history: List[Message] = Field(default_factory=list, description="Chronological list of messages exchanged.")
    artifacts: List[Artifact] = Field(default_factory=list, description="List of artifacts related to the task.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata associated with the task.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the task was created.")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the task was last updated.")

    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v, values):
        """Automatically update the updated_at timestamp."""
        # In Pydantic V1, validators run even if the field isn't provided,
        # but we only want to update if the object is being modified.
        # A better approach might be outside the model, e.g., before saving.
        # For simplicity here, we just set it to now.
        return datetime.now(timezone.utc)

    class Config:
        # Pydantic V1 config
        json_encoders = {
            # Ensure bytes in nested Parts are encoded
            bytes: lambda b: base64.b64encode(b).decode('utf-8')
        }
        # Allow arbitrary types for bytes handling during validation
        arbitrary_types_allowed = True
        validate_assignment = True # Re-validate on attribute assignment
