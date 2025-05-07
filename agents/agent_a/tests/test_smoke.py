def test_smoke():
    assert 1 + 1 == 2

def test_protobuf_a2a_message():
    from common.a2a_protocol.proto import a2a_message_pb2
    # Create a test message
    msg = a2a_message_pb2.AgentMessage(
        sender="test_sender",
        recipient="test_recipient",
        content="hello world",
        sent_at="2024-01-01T00:00:00Z"
    )
    # Serialize to bytes
    data = msg.SerializeToString()
    # Deserialize from bytes
    msg2 = a2a_message_pb2.AgentMessage()
    msg2.ParseFromString(data)
    assert msg2.sender == "test_sender"
    assert msg2.recipient == "test_recipient"
    assert msg2.content == "hello world"
    assert msg2.sent_at == "2024-01-01T00:00:00Z" 