def test_lab_controller_create(client):
    response = client.post("/api/lab_controllers", json={
            "fqdn": "lab1.example.com"
        })
    assert response.json()["fqdn"] == "lab1.example.com"

def test_system_create(client):
    response = client.post("/api/systems", json={
          "fqdn": "host1.example.com",
          "location": "Westford, MA",
          "lender": "IBM",
          "vender": "IBM",
          "model": "Z230",
          "serial": "A12345678",
          "lab_controller": "lab1.example.com"
    })
    assert response.json()["fqdn"] == "host1.example.com"
    assert response.json()["status"] == "unavailable"

def test_system_fail(client):
    response = client.post("/api/systems", json={
          "fqdn": "host4.example.com",
          "location": "Westford, MA",
          "lender": "IBM",
          "vender": "IBM",
          "model": "Z230",
          "serial": "A12345678",
          "lab_controller": "nolab.example.com"
    })
    assert response.status_code == 406
