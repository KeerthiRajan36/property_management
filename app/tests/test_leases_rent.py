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


def test_lease_activation_marks_unit_occupied(client, admin_headers):
    unit, tenant = _setup_unit_tenant(client, admin_headers, "L1")
    resp = client.post(
        "/api/v1/leases",
        json={
            "tenant_id": tenant["id"],
            "unit_id": unit["id"],
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "monthly_rent": 8000,
            "security_deposit": 16000,
            "lease_status": "Active",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    unit_check = client.get(f"/api/v1/units/{unit['id']}", headers=admin_headers).json()
    assert unit_check["status"] == "Occupied"


def test_overlapping_lease_rejected(client, admin_headers):
    unit, tenant = _setup_unit_tenant(client, admin_headers, "L2")
    payload = {
        "tenant_id": tenant["id"],
        "unit_id": unit["id"],
        "start_date": "2026-01-01",
        "end_date": "2026-06-30",
        "monthly_rent": 8000,
        "security_deposit": 16000,
        "lease_status": "Active",
    }
    r1 = client.post("/api/v1/leases", json=payload, headers=admin_headers)
    assert r1.status_code == 201

    payload2 = dict(payload, start_date="2026-04-01", end_date="2026-10-31")
    r2 = client.post("/api/v1/leases", json=payload2, headers=admin_headers)
    assert r2.status_code == 409


def test_lease_start_after_end_rejected(client, admin_headers):
    unit, tenant = _setup_unit_tenant(client, admin_headers, "L3")
    resp = client.post(
        "/api/v1/leases",
        json={
            "tenant_id": tenant["id"],
            "unit_id": unit["id"],
            "start_date": "2026-12-31",
            "end_date": "2026-01-01",
            "monthly_rent": 8000,
            "security_deposit": 16000,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_rent_invoice_and_payment_flow(client, admin_headers):
    unit, tenant = _setup_unit_tenant(client, admin_headers, "L4")
    lease = client.post(
        "/api/v1/leases",
        json={
            "tenant_id": tenant["id"],
            "unit_id": unit["id"],
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "monthly_rent": 8000,
            "security_deposit": 16000,
            "lease_status": "Active",
        },
        headers=admin_headers,
    ).json()

    invoice = client.post(
        "/api/v1/rent/invoices/generate",
        json={"lease_id": lease["id"], "billing_month": "2026-05", "late_fee": 200, "discount": 0, "due_date": "2026-05-05"},
        headers=admin_headers,
    )
    assert invoice.status_code == 201
    invoice_body = invoice.json()
    assert invoice_body["total_amount"] == 8200  # rent + late fee

    # duplicate month invoice should fail
    dup = client.post(
        "/api/v1/rent/invoices/generate",
        json={"lease_id": lease["id"], "billing_month": "2026-05", "late_fee": 0, "discount": 0, "due_date": "2026-05-05"},
        headers=admin_headers,
    )
    assert dup.status_code == 409

    # overpay should fail
    overpay = client.post(
        f"/api/v1/rent/pay/{invoice_body['id']}",
        json={"amount_paid": 999999},
        headers=admin_headers,
    )
    assert overpay.status_code == 422

    # correct full payment
    pay = client.post(
        f"/api/v1/rent/pay/{invoice_body['id']}",
        json={"amount_paid": 8200, "payment_method": "Cash"},
        headers=admin_headers,
    )
    assert pay.status_code == 201

    check = client.get(f"/api/v1/rent/invoices/{invoice_body['id']}", headers=admin_headers).json()
    assert check["status"] == "Paid"

    # paying again should now fail (already paid)
    again = client.post(
        f"/api/v1/rent/pay/{invoice_body['id']}",
        json={"amount_paid": 100},
        headers=admin_headers,
    )
    assert again.status_code == 409
