import unittest
from fastapi.testclient import TestClient
from api.main import app


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("Cascabel", data["message"])

    def test_start_simulation(self):
        """Test starting a new simulation"""
        simulation_request = {
            "border_config": {
                "num_queues": 2,
                "nodes_per_queue": [2, 2],
                "arrival_rate": 1.0,
                "service_rates": [2.0, 1.5, 2.5, 1.8],
                "queue_assignment": "shortest",
                "safe_distance": 8.0,
                "max_queue_length": 50,
            },
            "simulation_config": {
                "max_simulation_time": 60.0,
                "time_factor": 1.0,
                "enable_telemetry": True,
                "enable_position_tracking": True,
            },
            "phone_config": {
                "sampling_rate": 10,
                "gps_noise": {"horizontal_accuracy": 5.0, "vertical_accuracy": 3.0},
                "accelerometer_noise": 0.01,
                "gyro_noise": 0.001,
                "device_orientation": "portrait",
            },
        }

        response = self.client.post("/simulate", json=simulation_request)
        if response.status_code != 200:
            print("Response:", response.text)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("simulation_id", data)
        self.assertIn("status", data)
        self.assertEqual(data["status"], "running")
        self.assertIn("websocket_url", data)

        # Store simulation_id for other tests
        self.simulation_id = data["simulation_id"]

    def test_get_simulation_status(self):
        """Test getting simulation status"""
        # First start a simulation
        self.test_start_simulation()

        response = self.client.get(f"/simulation/{self.simulation_id}/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("simulation_id", data)
        self.assertIn("status", data)
        self.assertIn("progress", data)
        self.assertIn("current_time", data)

    def test_get_simulation_status_not_found(self):
        """Test getting status for non-existent simulation"""
        response = self.client.get("/simulation/non-existent-id/status")
        self.assertEqual(response.status_code, 404)

    def test_get_simulation_telemetry_csv(self):
        """Test downloading telemetry as CSV"""
        # First start a simulation
        self.test_start_simulation()

        # Wait a bit for simulation to generate data (mock this)
        response = self.client.get(
            f"/simulation/{self.simulation_id}/telemetry", params={"format": "csv"}
        )
        # May return 404 if no data yet, which is acceptable for test
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            self.assertEqual(response.headers["content-type"], "text/csv")

    def test_get_simulation_telemetry_json(self):
        """Test getting telemetry as JSON"""
        # First start a simulation
        self.test_start_simulation()

        response = self.client.get(
            f"/simulation/{self.simulation_id}/telemetry", params={"format": "json"}
        )
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            data = response.json()
            self.assertIn("telemetry", data)

    def test_list_simulations(self):
        """Test listing simulations"""
        response = self.client.get("/simulations")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("simulations", data)
        self.assertIn("total", data)

    def test_cancel_simulation(self):
        """Test canceling a simulation"""
        # First start a simulation
        self.test_start_simulation()

        response = self.client.delete(f"/simulation/{self.simulation_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("simulation_id", data)
        self.assertIn("status", data)

    def test_cancel_non_existent_simulation(self):
        """Test canceling non-existent simulation"""
        response = self.client.delete("/simulation/non-existent-id")
        self.assertEqual(response.status_code, 404)

    def test_add_car_to_simulation(self):
        """Test adding a car to running simulation"""
        # First start a simulation
        self.test_start_simulation()

        phone_config = {
            "sampling_rate": 10,
            "gps_noise": {"horizontal_accuracy": 5.0, "vertical_accuracy": 3.0},
            "accelerometer_noise": 0.01,
            "gyro_noise": 0.001,
            "device_orientation": "portrait",
        }

        response = self.client.post(
            f"/simulation/{self.simulation_id}/add_car", json=phone_config
        )
        self.assertIn(response.status_code, [200, 400])  # May fail if queue full

        if response.status_code == 200:
            data = response.json()
            self.assertIn("car_id", data)
            self.assertIn("queue_id", data)

    def test_update_service_node_rate(self):
        """Test updating service node rate"""
        # First start a simulation
        self.test_start_simulation()

        response = self.client.put(
            f"/simulation/{self.simulation_id}/service_node/q0_n0", json={"rate": 3.0}
        )
        self.assertIn(response.status_code, [200, 404])

        if response.status_code == 200:
            data = response.json()
            self.assertIn("node_id", data)
            self.assertIn("new_rate", data)

    def test_get_simulation_state(self):
        """Test getting simulation state for visualization"""
        # First start a simulation
        self.test_start_simulation()

        response = self.client.get(f"/simulation/{self.simulation_id}/state")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("simulation_id", data)
        self.assertIn("status", data)
        self.assertIn("cars", data)
        self.assertIn("service_nodes", data)

    def test_advance_simulation(self):
        """Test manually advancing simulation time"""
        # First start a simulation
        self.test_start_simulation()

        response = self.client.post(
            f"/simulation/{self.simulation_id}/advance", json={"dt": 1.0}
        )
        self.assertIn(response.status_code, [200, 400])

        if response.status_code == 200:
            data = response.json()
            self.assertIn("advanced_by", data)
            self.assertIn("completed_cars", data)

    def test_get_simulation_visualization_data(self):
        """Test getting visualization data for simulation"""
        # First start a simulation
        self.test_start_simulation()

        response = self.client.get(
            f"/simulation/{self.simulation_id}/visualization-data"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("cars", data)
        self.assertIn("service_nodes", data)
        self.assertIn("statistics", data)
        self.assertIn("timestamp", data)
        self.assertIn("simulation_id", data)

        # Check structure
        self.assertIsInstance(data["cars"], list)
        self.assertIsInstance(data["service_nodes"], list)
        self.assertIsInstance(data["statistics"], dict)


if __name__ == "__main__":
    unittest.main()
