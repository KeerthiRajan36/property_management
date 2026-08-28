def _setup_unit_tenant(client, headers, suffix=""):
    prop = client.post(
        "/api/v1/properties",
        json={
            "property_name": f"P{suffix}",
            "property_type": "Apartment",
            "address": "x",
            "city": "x",
            "state": "x",
            "total_area": 100,
            "total_units": 1,
        },
        headers=headers,
    ).json()
    building = client.post(
        "/api/v1/buildings",
        json={"property_id": prop["id"], "building_name": f"B{suffix}", "number_of_floors": 1, "total_units": 1},
        headers=headers,
    ).json()
    unit = client.post(
        "/api/v1/units",
        json={
            "building_id": building["id"],
            "unit_number": f"U{suffix}",
            "floor_number": 1,
            "unit_type": "1BHK",
            "area": 400,
            "monthly_rent": 8000,
        },
        headers=headers,
    ).json()
    tenant = client.post(
        "/api/v1/tenants",
        json={
            "full_name": f"Tenant{suffix}",
            "email": f"tenant{suffix}@test.com",
            "phone": "9000000000",
            "identification_number": f"ID{suffix}",
        },
        headers=headers,
    ).json()
    return unit, tenant


def test_maintenance_assignment_requires_maintenance_role(client, admin_headers):
    unit, tenant = _setup_unit_tenant(client, admin_headers, "M1")

    # register a tenant-role user (wrong role for assignment)
    reg = client.post(
        "/api/v1/auth/register",
        json={"full_name": "WrongRole", "email": "wrongrole@test.com", "password": "password123", "role": "tenant"},
    )
    wrong_staff_id = reg.json()["id"]

    request = client.post(
        "/api/v1/maintenance/requests",
        json={"tenant_id": tenant["id"], "unit_id": unit["id"], "category": "Electrical", "description": "No power"},
        headers=admin_headers,
    ).json()

    resp = client.put(
        f"/api/v1/maintenance/requests/{request['id']}/assign",
        json={"assigned_staff_id": wrong_staff_id},
        headers=admin_headers,
    )
    assert resp.status_code == 422  # BusinessRuleError: wrong role


def test_maintenance_assignment_and_status_flow(client, admin_headers):
    unit, tenant = _setup_unit_tenant(client, admin_headers, "M2")
    staff = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Staffer",
            "email": "staffer@test.com",
            "password": "password123",
            "role": "maintenance_staff",
        },
    ).json()

    request = client.post(
        "/api/v1/maintenance/requests",
        json={
            "tenant_id": tenant["id"],
            "unit_id": unit["id"],
            "category": "Plumbing",
            "description": "Leaky pipe",
            "priority": "High",
        },
        headers=admin_headers,
    ).json()

    assign = client.put(
        f"/api/v1/maintenance/requests/{request['id']}/assign",
        json={"assigned_staff_id": staff["id"]},
        headers=admin_headers,
    )
    assert assign.status_code == 200
    assert assign.json()["status"] == "Assigned"

    resolve = client.put(
        f"/api/v1/maintenance/requests/{request['id']}/status",
        json={"status": "Resolved", "actual_cost": 250},
        headers=admin_headers,
    )
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "Resolved"
    assert resolve.json()["actual_cost"] == 250

    history = client.get(f"/api/v1/maintenance/requests/{request['id']}/history", headers=admin_headers)
    assert history.status_code == 200
    assert len(history.json()) >= 3  # created, assigned, resolved


def test_facility_booking_capacity_enforced(client, admin_headers):
    _, tenant = _setup_unit_tenant(client, admin_headers, "F1")
    facility = client.post(
        "/api/v1/facilities",
        json={"facility_name": "Small Gym", "facility_type": "Gym", "capacity": 1},
        headers=admin_headers,
    ).json()

    book1 = client.post(
        f"/api/v1/facilities/{facility['id']}/book",
        json={"tenant_id": tenant["id"], "booking_date": "2026-09-10", "start_time": "08:00:00", "end_time": "09:00:00"},
        headers=admin_headers,
    )
    assert book1.status_code == 201

    # overlapping slot beyond capacity
    book2 = client.post(
        f"/api/v1/facilities/{facility['id']}/book",
        json={"tenant_id": tenant["id"], "booking_date": "2026-09-10", "start_time": "08:30:00", "end_time": "09:30:00"},
        headers=admin_headers,
    )
    assert book2.status_code == 409

    # cancelling releases the slot
    cancel = client.put(f"/api/v1/facilities/bookings/{book1.json()['id']}/cancel", headers=admin_headers)
    assert cancel.status_code == 200

    book3 = client.post(
        f"/api/v1/facilities/{facility['id']}/book",
        json={"tenant_id": tenant["id"], "booking_date": "2026-09-10", "start_time": "08:30:00", "end_time": "09:30:00"},
        headers=admin_headers,
    )
    assert book3.status_code == 201


def test_utility_reading_rejects_lower_current_reading(client, admin_headers):
    unit, _ = _setup_unit_tenant(client, admin_headers, "U1")
    resp = client.post(
        "/api/v1/utilities/readings",
        json={
            "unit_id": unit["id"],
            "utility_type": "Water",
            "previous_reading": 100,
            "current_reading": 50,
            "rate": 5,
            "billing_month": "2026-05",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_utility_invoice_calculation(client, admin_headers):
    unit, _ = _setup_unit_tenant(client, admin_headers, "U2")
    reading = client.post(
        "/api/v1/utilities/readings",
        json={
            "unit_id": unit["id"],
            "utility_type": "Water",
            "previous_reading": 100,
            "current_reading": 130,
            "rate": 5,
            "billing_month": "2026-05",
        },
        headers=admin_headers,
    ).json()
    invoice = client.post("/api/v1/utilities/invoices", json={"reading_id": reading["id"]}, headers=admin_headers)
    assert invoice.status_code == 201
    assert invoice.json()["total_amount"] == 150  # 30 units * rate 5
