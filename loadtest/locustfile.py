"""Test de charge : critère "50 utilisateurs simultanés" et "dashboard < 3 s".

pip install locust
locust -f loadtest/locustfile.py --host https://localhost --users 50 --spawn-rate 10 --run-time 2m --headless
Regarder le 95e percentile (colonne 95%) : il doit rester sous 3000 ms.
"""
from locust import HttpUser, between, task


class Citizen(HttpUser):
    wait_time = between(1, 4)

    def on_start(self):
        self.client.verify = False   # certificat auto-signé en local

    @task(3)
    def dashboard(self):
        self.client.get("/api/kpis")
        self.client.get("/api/measurements/latest")
        self.client.get("/api/measurements/history?pollutant=pm25&hours=24")

    @task(1)
    def forecast(self):
        self.client.get("/api/forecast")
        self.client.get("/api/recommendations")
