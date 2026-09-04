from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_current_user, require_role
from app.models import User
from app.models.enums import UserRole
from app.schemas.user import UserCreate, UserRead, UserRoleUpdate
from app.services import user as user_service

# Admin only — this is the one capability CLAUDE.md gives admin over
# hr_manager. hr_manager and executive_viewer get 403 on every route here.
router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_role(UserRole.admin))],
)


@router.get("", response_model=list[UserRead])
def list_users(session: Session = Depends(get_session)):
    return user_service.list_users(session)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, session: Session = Depends(get_session)):
    try:
        return user_service.create_user(session, data)
    except user_service.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )


@router.patch("/{user_id}", response_model=UserRead)
def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Guard against an admin locking themselves (and possibly everyone) out
    # of user management by demoting their own account.
    if user_id == current_user.id and data.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't change your own role away from admin",
        )
    user = user_service.set_user_role(session, user_id, data.role)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can't delete your own account",
        )
    if not user_service.delete_user(session, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")