from sqlalchemy.orm import Session
from backend.models.models import Member
from datetime import date

def get_member(db: Session, member_id: str) -> Member:
    return db.query(Member).filter(Member.id == member_id).first()

def create_member(db: Session, member_id: str, name: str, join_date: date, policy_number: str = "PLUM_OPD_2024", annual_limit: float = 50000.0, status: str = "ACTIVE") -> Member:
    db_member = Member(
        id=member_id,
        name=name,
        policy_number=policy_number,
        join_date=join_date,
        annual_limit_remaining=annual_limit,
        status=status
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

def update_member_limit(db: Session, member_id: str, new_limit: float) -> Member:
    db_member = get_member(db, member_id)
    if db_member:
        db_member.annual_limit_remaining = new_limit
        db.commit()
        db.refresh(db_member)
    return db_member
