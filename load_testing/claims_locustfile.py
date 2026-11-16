from locust import HttpUser, task, constant_pacing
from datetime import datetime, timedelta, timezone
import time
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

        start = time.perf_counter()

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

            run_id = data.get("run_id")

            if not run_id:
                response.failure("Missing run ID")
                return

            response.success()

        self.wait_for_completion(run_id, start)

    def record_processing(self, start, error=None):
        elapsed = (time.perf_counter() - start) * 1000

        self.environment.events.request.fire(
            request_type="RUN",
            name="End-to-end claim processing",
            response_time=elapsed,
            response_length=0,
            response=None,
            context={},
            exception=error
        )

    def wait_for_completion(self, run_id, start):
        timeout = 30
        deadline = time.perf_counter() + timeout

        while time.perf_counter() < deadline:
            try:
                with self.client.get(
                    f"/runs/{run_id}",
                    name="GET /runs/{id}",
                    catch_response=True
                ) as response:
                    if response.status_code != 200:
                        response.failure(
                            f"Run lookup returned {response.status_code}"
                        )
                        self.record_processing(
                            start,
                            RuntimeError("Run lookup failed")
                        )
                        return

                    try:
                        data = response.json()
                    except ValueError:
                        response.failure("Invalid run response")
                        self.record_processing(
                            start,
                            RuntimeError("Invalid run response")
                        )
                        return

                    response.success()

                status = data.get("status")

                if status == "completed":
                    self.record_processing(start)
                    return

                if status == "failed":
                    self.record_processing(
                        start,
                        RuntimeError("Claim processing failed")
                    )
                    return

                if status not in {"pending", "queued", "running", "processing"}:
                    self.record_processing(
                        start,
                        RuntimeError(f"Unexpected run status: {status}")
                    )
                    return

            except Exception as error:
                self.record_processing(start, error)
                return

            time.sleep(0.5)

        self.record_processing(
            start,
            TimeoutError("Claim processing exceeded 30 seconds")
        )