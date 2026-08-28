#!/bin/bash
set -e
BASE=http://127.0.0.1:8000/api/v1

echo "== register admin (idempotent-ish; ignore failure if exists) =="
curl -s -X POST $BASE/auth/register -H "Content-Type: application/json" -d '{"full_name":"Admin User","email":"admin@example.com","password":"admin123","role":"super_admin"}'; echo

echo "== login as admin =="
LOGIN=$(curl -s -X POST $BASE/auth/login -H "Content-Type: application/json" -d '{"email":"admin@example.com","password":"admin123"}')
echo $LOGIN
ACCESS=$(echo $LOGIN | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $ACCESS"

echo "== create property =="
PROP=$(curl -s -X POST $BASE/properties -H "$AUTH" -H "Content-Type: application/json" -d '{"property_name":"Sunrise Apartments","property_type":"Apartment","address":"123 Main St","city":"Chennai","state":"TN","total_area":5000,"total_units":10}')
echo $PROP
PROP_ID=$(echo $PROP | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "== create building =="
BLD=$(curl -s -X POST $BASE/buildings -H "$AUTH" -H "Content-Type: application/json" -d "{\"property_id\":$PROP_ID,\"building_name\":\"Tower A\",\"number_of_floors\":5,\"total_units\":10}")
echo $BLD
BLD_ID=$(echo $BLD | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "== create unit =="
UNIT=$(curl -s -X POST $BASE/units -H "$AUTH" -H "Content-Type: application/json" -d "{\"building_id\":$BLD_ID,\"unit_number\":\"101\",\"floor_number\":1,\"unit_type\":\"2BHK\",\"area\":900,\"monthly_rent\":15000}")
echo $UNIT
UNIT_ID=$(echo $UNIT | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "== duplicate unit number should fail with 409 =="
curl -s -o /dev/null -w "%{http_code}\n" -X POST $BASE/units -H "$AUTH" -H "Content-Type: application/json" -d "{\"building_id\":$BLD_ID,\"unit_number\":\"101\",\"floor_number\":1,\"unit_type\":\"2BHK\",\"area\":900,\"monthly_rent\":15000}"

echo "== create tenant =="
TEN=$(curl -s -X POST $BASE/tenants -H "$AUTH" -H "Content-Type: application/json" -d '{"full_name":"John Doe","email":"john@example.com","phone":"9999999999","identification_number":"ID12345"}')
echo $TEN
TEN_ID=$(echo $TEN | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "== create lease (Active) =="
LEASE=$(curl -s -X POST $BASE/leases -H "$AUTH" -H "Content-Type: application/json" -d "{\"tenant_id\":$TEN_ID,\"unit_id\":$UNIT_ID,\"start_date\":\"2026-01-01\",\"end_date\":\"2026-12-31\",\"monthly_rent\":15000,\"security_deposit\":30000,\"lease_status\":\"Active\"}")
echo $LEASE
LEASE_ID=$(echo $LEASE | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "== check unit status became Occupied =="
curl -s $BASE/units/$UNIT_ID -H "$AUTH"; echo

echo "== overlapping lease on same unit should fail with 409 =="
curl -s -o /dev/null -w "%{http_code}\n" -X POST $BASE/leases -H "$AUTH" -H "Content-Type: application/json" -d "{\"tenant_id\":$TEN_ID,\"unit_id\":$UNIT_ID,\"start_date\":\"2026-06-01\",\"end_date\":\"2026-08-31\",\"monthly_rent\":15000,\"security_deposit\":30000,\"lease_status\":\"Active\"}"

echo "== generate rent invoice =="
INV=$(curl -s -X POST $BASE/rent/invoices/generate -H "$AUTH" -H "Content-Type: application/json" -d "{\"lease_id\":$LEASE_ID,\"billing_month\":\"2026-08\",\"late_fee\":0,\"discount\":0,\"due_date\":\"2026-08-05\"}")
echo $INV
INV_ID=$(echo $INV | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "== duplicate invoice for same month should fail with 409 =="
curl -s -o /dev/null -w "%{http_code}\n" -X POST $BASE/rent/invoices/generate -H "$AUTH" -H "Content-Type: application/json" -d "{\"lease_id\":$LEASE_ID,\"billing_month\":\"2026-08\",\"late_fee\":0,\"discount\":0,\"due_date\":\"2026-08-05\"}"

echo "== pay invoice partially =="
curl -s -X POST $BASE/rent/pay/$INV_ID -H "$AUTH" -H "Content-Type: application/json" -d '{"amount_paid":10000,"payment_method":"UPI"}'; echo

echo "== overpay remaining should fail with 422 =="
curl -s -o /dev/null -w "%{http_code}\n" -X POST $BASE/rent/pay/$INV_ID -H "$AUTH" -H "Content-Type: application/json" -d '{"amount_paid":10000,"payment_method":"UPI"}'

echo "== pay remaining exactly =="
curl -s -X POST $BASE/rent/pay/$INV_ID -H "$AUTH" -H "Content-Type: application/json" -d '{"amount_paid":5000,"payment_method":"UPI"}'; echo

echo "== invoice should now be Paid =="
curl -s $BASE/rent/invoices/$INV_ID -H "$AUTH"; echo

echo "== download PDF receipt =="
curl -s -o /home/claude/receipt.pdf -w "HTTP %{http_code}, size: %{size_download} bytes\n" $BASE/rent/invoices/$INV_ID/receipt -H "$AUTH"
file /home/claude/receipt.pdf

echo "== create maintenance staff user =="
STAFF=$(curl -s -X POST $BASE/auth/register -H "Content-Type: application/json" -d '{"full_name":"Mike Fixit","email":"mike@example.com","password":"mike1234","role":"maintenance_staff"}')
echo $STAFF
STAFF_ID=$(echo $STAFF | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "== create maintenance request =="
MAINT=$(curl -s -X POST $BASE/maintenance/requests -H "$AUTH" -H "Content-Type: application/json" -d "{\"tenant_id\":$TEN_ID,\"unit_id\":$UNIT_ID,\"category\":\"Plumbing\",\"description\":\"Leaking tap\",\"priority\":\"Emergency\"}")
echo $MAINT
MREQ_ID=$(echo $MAINT | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "== assign staff =="
curl -s -X PUT $BASE/maintenance/requests/$MREQ_ID/assign -H "$AUTH" -H "Content-Type: application/json" -d "{\"assigned_staff_id\":$STAFF_ID}"; echo

echo "== update status to Resolved =="
curl -s -X PUT $BASE/maintenance/requests/$MREQ_ID/status -H "$AUTH" -H "Content-Type: application/json" -d '{"status":"Resolved","actual_cost":500,"note":"Fixed the tap washer"}'; echo

echo "== maintenance history =="
curl -s $BASE/maintenance/requests/$MREQ_ID/history -H "$AUTH"; echo

echo "== utility reading (bad: current < previous) should fail with 422 =="
curl -s -o /dev/null -w "%{http_code}\n" -X POST $BASE/utilities/readings -H "$AUTH" -H "Content-Type: application/json" -d "{\"unit_id\":$UNIT_ID,\"utility_type\":\"Electricity\",\"previous_reading\":500,\"current_reading\":400,\"rate\":8,\"billing_month\":\"2026-08\"}"

echo "== utility reading (good) =="
UREAD=$(curl -s -X POST $BASE/utilities/readings -H "$AUTH" -H "Content-Type: application/json" -d "{\"unit_id\":$UNIT_ID,\"utility_type\":\"Electricity\",\"previous_reading\":500,\"current_reading\":650,\"rate\":8,\"billing_month\":\"2026-08\"}")
echo $UREAD
UREAD_ID=$(echo $UREAD | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "== utility invoice (should be 150*8=1200) =="
curl -s -X POST $BASE/utilities/invoices -H "$AUTH" -H "Content-Type: application/json" -d "{\"reading_id\":$UREAD_ID}"; echo

echo "== visitor create + checkin + checkout =="
VIS=$(curl -s -X POST $BASE/visitors -H "$AUTH" -H "Content-Type: application/json" -d "{\"visitor_name\":\"Guest One\",\"phone\":\"8888888888\",\"tenant_id\":$TEN_ID,\"unit_id\":$UNIT_ID,\"purpose\":\"Personal\"}")
echo $VIS
VIS_ID=$(echo $VIS | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X PUT $BASE/visitors/$VIS_ID/checkin -H "$AUTH"; echo
curl -s -X PUT $BASE/visitors/$VIS_ID/checkout -H "$AUTH"; echo

echo "== parking: create + assign =="
PARK=$(curl -s -X POST $BASE/parking -H "$AUTH" -H "Content-Type: application/json" -d "{\"property_id\":$PROP_ID,\"parking_number\":\"P-01\"}")
echo $PARK
PARK_ID=$(echo $PARK | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST $BASE/parking/$PARK_ID/assign -H "$AUTH" -H "Content-Type: application/json" -d "{\"tenant_id\":$TEN_ID,\"vehicle_number\":\"TN01AB1234\",\"vehicle_type\":\"Car\"}"; echo

echo "== facility: create + book + overlap capacity check =="
FAC=$(curl -s -X POST $BASE/facilities -H "$AUTH" -H "Content-Type: application/json" -d '{"facility_name":"Gym Room","facility_type":"Gym","capacity":1}')
echo $FAC
FAC_ID=$(echo $FAC | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST $BASE/facilities/$FAC_ID/book -H "$AUTH" -H "Content-Type: application/json" -d "{\"tenant_id\":$TEN_ID,\"booking_date\":\"2026-09-01\",\"start_time\":\"09:00:00\",\"end_time\":\"10:00:00\"}"; echo
echo "== overlapping booking beyond capacity should fail with 409 =="
curl -s -o /dev/null -w "%{http_code}\n" -X POST $BASE/facilities/$FAC_ID/book -H "$AUTH" -H "Content-Type: application/json" -d "{\"tenant_id\":$TEN_ID,\"booking_date\":\"2026-09-01\",\"start_time\":\"09:30:00\",\"end_time\":\"10:30:00\"}"

echo "== dashboard summary =="
curl -s $BASE/dashboard/summary -H "$AUTH"; echo

echo "== unit occupancy excel export =="
curl -s -o /home/claude/occupancy.xlsx -w "HTTP %{http_code}, size: %{size_download} bytes\n" $BASE/dashboard/reports/unit-occupancy/export -H "$AUTH"
file /home/claude/occupancy.xlsx

echo "== pagination/filtering test =="
curl -s "$BASE/units?unit_type=2BHK&page=1&limit=5" -H "$AUTH"; echo

echo "ALL SMOKE TESTS COMPLETED"
