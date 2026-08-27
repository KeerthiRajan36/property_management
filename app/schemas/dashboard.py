from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_properties: int
    total_buildings: int
    total_units: int
    occupied_units: int
    available_units: int
    total_tenants: int
    active_leases: int
    monthly_rent_collection: float
    pending_rent: float
    overdue_rent: float
    maintenance_expenses: float
    utility_revenue: float
    parking_occupancy: float
