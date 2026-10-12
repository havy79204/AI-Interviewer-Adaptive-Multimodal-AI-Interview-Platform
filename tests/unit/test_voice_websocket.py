import base64
import pytest
from starlette.websockets import WebSocketDisconnect

from fastapi.testclient import TestClient

from apps.api.main import app
from services.auth_service import issue_token
from services.user_store import UserStore


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_authenticated_voice_websocket_final_flow_and_duplicate_final(client: TestClient):
    email = "voice-websocket@example.com"
    UserStore.create(email, "password123", role="candidate")
    token = issue_token(email, "candidate")
    headers = {"Authorization": f"Bearer {token}"}
    candidate = client.post(
        "/api/v1/candidates",
        json={"name": "Voice Test Candidate", "email": email},
        headers=headers,
    )
    assert candidate.status_code == 200
    start = client.post(
        "/api/v1/interview/start",
        json={"candidate_id": candidate.json()["id"], "position": "AI Engineer"},
        headers=headers,
    )
    interview_id = start.json()["interview_id"]

    with client.websocket_connect(f"/ws/interview/{interview_id}/voice?token={token}") as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "session.ready"
        websocket.send_json({"type": "session.start"})
        assert websocket.receive_json()["type"] == "session.ready"
        websocket.send_json({"type": "audio.start", "utterance_id": "voice-utt-1"})
        websocket.send_json({
            "type": "audio.chunk",
            "utterance_id": "voice-utt-1",
            "audio_format": "pcm_s16le/16000/1",
            "audio_base64": base64.b64encode(b"pcm").decode("ascii"),
        })
        assert websocket.receive_json()["type"] == "transcript.partial"
        websocket.send_json({"type": "audio.end", "utterance_id": "voice-utt-1"})
        events = []
        while True:
            event = websocket.receive_json()
            events.append(event)
            if event["type"] == "tts.completed":
                break
        assert events[0]["type"] == "transcript.final"
        assert events[1]["type"] == "interview.question"
        assert events[2]["type"] == "tts.started"
        assert events[-1]["type"] == "tts.completed"

        websocket.send_json({"type": "audio.end", "utterance_id": "voice-utt-1"})
        duplicate_events = [websocket.receive_json() for _ in range(5)]
        assert duplicate_events[0]["type"] == "interview.question"
        assert not any(event["type"] == "transcript.final" for event in duplicate_events)


def test_unauthenticated_voice_websocket_is_rejected(client: TestClient):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/interview/missing/voice"):
            pass