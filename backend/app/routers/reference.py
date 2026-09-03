from fastapi import APIRouter, Depends

from app.dependencies import require_role
from app.models.enums import UserRole
from app.services.currency import SUPPORTED_CURRENCIES

# Same gating as the employees/salary-records routers: only the roles that
# can actually create a SalaryRecord need the currency allowlist.
router = APIRouter(
    prefix="/reference",
    tags=["reference"],
    dependencies=[Depends(require_role(UserRole.admin, UserRole.hr_manager))],
)


@router.get("/currencies", response_model=list[str])
def get_supported_currencies():
    return sorted(SUPPORTED_CURRENCIES)