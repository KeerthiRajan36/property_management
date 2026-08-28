def _make_property(client, headers):
    resp = client.post(
        "/api/v1/properties",
        json={
            "property_name": "Test Towers",
            "property_type": "Apartment",
            "address": "1 Test St",
            "city": "TestCity",
            "state": "TS",
            "total_area": 1000,
            "total_units": 5,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _make_building(client, headers, property_id):
    resp = client.post(
        "/api/v1/buildings",
        json={"property_id": property_id, "building_name": "B1", "number_of_floors": 3, "total_units": 5},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def test_create_and_list_property(client, admin_headers):
    prop = _make_property(client, admin_headers)
    resp = client.get(f"/api/v1/properties/{prop['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["property_name"] == "Test Towers"

    listing = client.get("/api/v1/properties?city=TestCity", headers=admin_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1


def test_property_requires_admin_role(client):
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Plain", "email": "plain@test.com", "password": "password123", "role": "tenant"},
    )
    login = client.post("/api/v1/auth/login", json={"email": "plain@test.com", "password": "password123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = client.post(
        "/api/v1/properties",
        json={
            "property_name": "Should Fail",
            "property_type": "Apartment",
            "address": "x",
            "city": "x",
            "state": "x",
            "total_area": 100,
            "total_units": 1,
        },
        headers=headers,
    )
    assert resp.status_code == 403


def test_unit_number_unique_within_building(client, admin_headers):
    prop = _make_property(client, admin_headers)
    building = _make_building(client, admin_headers, prop["id"])

    unit_payload = {
        "building_id": building["id"],
        "unit_number": "U-1",
        "floor_number": 1,
        "unit_type": "1BHK",
        "area": 500,
        "monthly_rent": 5000,
    }
    r1 = client.post("/api/v1/units", json=unit_payload, headers=admin_headers)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/units", json=unit_payload, headers=admin_headers)
    assert r2.status_code == 409


def test_unit_filtering_by_rent_range(client, admin_headers):
    prop = _make_property(client, admin_headers)
    building = _make_building(client, admin_headers, prop["id"])
    client.post(
        "/api/v1/units",
        json={
            "building_id": building["id"],
            "unit_number": "CHEAP",
            "floor_number": 1,
            "unit_type": "Studio",
            "area": 300,
            "monthly_rent": 2000,
        },
        headers=admin_headers,
    )
    client.post(
        "/api/v1/units",
        json={
            "building_id": building["id"],
            "unit_number": "EXPENSIVE",
            "floor_number": 2,
            "unit_type": "3BHK",
            "area": 1500,
            "monthly_rent": 50000,
        },
        headers=admin_headers,
    )
    resp = client.get("/api/v1/units?min_rent=1000&max_rent=3000", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["monthly_rent"] <= 3000 for item in body["items"])
