
from locust import HttpUser, task, between


class PassengerAPIUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def check_runs(self):
        self.client.get("/runs/count", name="GET /runs/count")

    @task(1)
    def check_health(self):
        self.client.get("/health", name="GET /health")
