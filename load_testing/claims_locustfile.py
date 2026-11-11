
from locust import HttpUser, task, constant_pacing
from datetime import datetime, timedelta, timezone
import uuid


class ClaimSubmissionUser(HttpUser):
    wait_time = constant_pacing(20)

    @task
    def submit_claim(self):
        booking_reference = uuid.uuid4().hex[:6].upper()

        departure = (
            datetime.now(timezone.utc) + timedelta(days=1)
        ).isoformat()

        claim = {
            "passenger_name": "Test Passenger",
            "booking_reference": booking_reference,
            "airline": "IndiGo",
            "flight_number": "6E123",
            "origin": "BLR",
            "destination": "DEL",
            "scheduled_departure": departure,
            "description": "Test claim for a delayed flight during controlled load testing.",
            "reported_disruption": "delay",
            "notice_minutes": 120,
            "block_time_minutes": 150,
            "alternate_flight_offered": False,
            "alternate_flight_accepted": False,
            "alternate_departure": None,
            "contact_details_provided": True
        }

        with self.client.post(
            "/claims",
            json=claim,
            name="POST /claims",
            catch_response=True
        ) as response:
            if response.status_code != 202:
                response.failure(
                    f"Expected 202, received {response.status_code}"
                )
                return

            try:
                data = response.json()
            except ValueError:
                response.failure("Invalid JSON response")
                return

            if not data.get("run_id"):
                response.failure("Missing run ID")
                return

            response.success()
