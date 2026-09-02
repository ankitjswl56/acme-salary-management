"""Generates correlated employee + salary history data for the seed script.

Salary is derived from reference tables (country/department/level), not
generated independently at random, so aggregate numbers stay internally
consistent (see reference_data.py for the full rationale).
"""

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from faker import Faker

from app.models.enums import ChangeType, EmployeeStatus, Gender
from app.reference_data import COUNTRIES, DEPARTMENTS, LEVELS, Country, Department, level_title

SEED = 42

GENDER_CHOICES = [Gender.female, Gender.male, Gender.other, Gender.prefer_not_to_say, None]
GENDER_WEIGHTS = [0.47, 0.47, 0.02, 0.02, 0.02]

STATUS_CHOICES = [EmployeeStatus.active, EmployeeStatus.inactive]
STATUS_WEIGHTS = [0.92, 0.08]

RAISE_CHANGE_TYPES = [ChangeType.raise_, ChangeType.promotion, ChangeType.cola]
RAISE_CHANGE_WEIGHTS = [0.55, 0.25, 0.20]

HIRE_WINDOW_DAYS = 8 * 365
MIN_TENURE_DAYS = 30
HISTORY_RATE = 0.18
HISTORY_MIN_TENURE_DAYS = 400
FUTURE_RAISE_RATE_OF_HISTORY = 0.20


@dataclass
class GeneratedEmployee:
    id: int
    name: str
    email: str
    country: Country
    department: Department
    role: str
    gender: Gender | None
    hire_date: date
    status: EmployeeStatus
    current_target_usd: float

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "country": self.country.code,
            "department": self.department.name,
            "role": self.role,
            "gender": self.gender.value if self.gender else None,
            "hire_date": self.hire_date,
            "status": self.status.value,
        }


def _pick(rng: random.Random, options: list, weights: list):
    return rng.choices(options, weights=weights, k=1)[0]


def _usd_to_local(amount_usd: float, country: Country) -> float:
    return round(amount_usd / country.fx_rate_to_usd, 2)


def _local_to_usd(amount_local: float, country: Country) -> float:
    return round(amount_local * country.fx_rate_to_usd, 2)


def generate_employees(count: int, today: date, seed: int = SEED) -> list[GeneratedEmployee]:
    rng = random.Random(seed)
    faker = Faker()
    Faker.seed(seed)

    countries = [c.weight for c in COUNTRIES]
    departments = [d.weight for d in DEPARTMENTS]
    levels = [l.weight for l in LEVELS]

    used_emails: set[str] = set()
    employees: list[GeneratedEmployee] = []

    for i in range(1, count + 1):
        country = _pick(rng, COUNTRIES, countries)
        department = _pick(rng, DEPARTMENTS, departments)
        level = _pick(rng, LEVELS, levels)

        variance = rng.uniform(0.85, 1.15)
        current_target_usd = level.base_usd * department.salary_multiplier * country.salary_multiplier * variance

        name = faker.name()
        base_email = "".join(ch for ch in name.lower() if ch.isalnum() or ch == " ").replace(" ", ".")
        email = f"{base_email}@acme-corp.example"
        suffix = 2
        while email in used_emails:
            email = f"{base_email}{suffix}@acme-corp.example"
            suffix += 1
        used_emails.add(email)

        hire_date = today - timedelta(days=rng.randint(MIN_TENURE_DAYS, HIRE_WINDOW_DAYS))

        employees.append(
            GeneratedEmployee(
                id=i,
                name=name,
                email=email,
                country=country,
                department=department,
                role=level_title(level.code, department),
                gender=_pick(rng, GENDER_CHOICES, GENDER_WEIGHTS),
                hire_date=hire_date,
                status=_pick(rng, STATUS_CHOICES, STATUS_WEIGHTS),
                current_target_usd=current_target_usd,
            )
        )

    return employees


def generate_salary_records(
    employees: list[GeneratedEmployee], today: date, seed: int = SEED
) -> list[dict]:
    rng = random.Random(seed + 1)  # separate stream from employee generation
    records: list[dict] = []
    next_id = 1

    def add_record(employee: GeneratedEmployee, amount_usd: float, effective_date: date, change_type: ChangeType) -> None:
        nonlocal next_id
        amount_local = _usd_to_local(amount_usd, employee.country)
        records.append(
            {
                "id": next_id,
                "employee_id": employee.id,
                "amount": amount_local,
                "currency": employee.country.currency,
                "amount_usd_snapshot": _local_to_usd(amount_local, employee.country),
                "fx_rate_to_usd": employee.country.fx_rate_to_usd,
                "effective_date": effective_date,
                "change_type": change_type.value,
                "created_at": datetime.combine(effective_date, datetime.min.time()),
            }
        )
        next_id += 1

    for employee in employees:
        tenure_days = (today - employee.hire_date).days
        has_history = tenure_days >= HISTORY_MIN_TENURE_DAYS and rng.random() < HISTORY_RATE

        if not has_history:
            add_record(employee, employee.current_target_usd, employee.hire_date, ChangeType.hire)
            continue

        num_raises = rng.choice([1, 2])
        hire_amount = employee.current_target_usd * rng.uniform(0.72, 0.88)
        add_record(employee, hire_amount, employee.hire_date, ChangeType.hire)

        checkpoints = sorted(
            employee.hire_date + timedelta(days=rng.randint(180, max(181, tenure_days - 30)))
            for _ in range(num_raises)
        )
        last_amount = hire_amount
        for idx, effective_date in enumerate(checkpoints):
            is_last = idx == len(checkpoints) - 1
            amount = employee.current_target_usd if is_last else last_amount + (
                employee.current_target_usd - last_amount
            ) * rng.uniform(0.4, 0.7)
            add_record(employee, amount, effective_date, _pick(rng, RAISE_CHANGE_TYPES, RAISE_CHANGE_WEIGHTS))
            last_amount = amount

        if rng.random() < FUTURE_RAISE_RATE_OF_HISTORY:
            future_date = today + timedelta(days=rng.randint(30, 180))
            future_amount = employee.current_target_usd * rng.uniform(1.03, 1.08)
            add_record(employee, future_amount, future_date, _pick(rng, RAISE_CHANGE_TYPES, RAISE_CHANGE_WEIGHTS))

    return records