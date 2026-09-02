"""Reference tables the seed generator derives correlated salaries from.

Salary for a given employee is computed as:

    base_usd(level) * department_multiplier * country_multiplier * variance

then converted into the employee's local currency using the country's fixed
FX rate. This keeps aggregate numbers internally consistent (Engineering >
Support, US > lower-cost-tier countries) instead of independently random.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    code: str
    name: str
    currency: str
    fx_rate_to_usd: float  # USD value of 1 unit of local currency
    salary_multiplier: float
    weight: float  # share of total headcount


@dataclass(frozen=True)
class Department:
    name: str
    salary_multiplier: float
    base_title: str
    weight: float  # share of total headcount


@dataclass(frozen=True)
class Level:
    code: str
    base_usd: float
    weight: float  # share of total headcount (org pyramid shape)


COUNTRIES: list[Country] = [
    Country("US", "United States", "USD", 1.00, 1.00, 0.35),
    Country("IN", "India", "INR", 0.012, 0.35, 0.20),
    Country("UK", "United Kingdom", "GBP", 1.27, 0.95, 0.10),
    Country("DE", "Germany", "EUR", 1.09, 0.92, 0.08),
    Country("CA", "Canada", "CAD", 0.74, 0.88, 0.07),
    Country("AU", "Australia", "AUD", 0.66, 0.90, 0.05),
    Country("PL", "Poland", "PLN", 0.25, 0.45, 0.05),
    Country("PH", "Philippines", "PHP", 0.018, 0.30, 0.04),
    Country("BR", "Brazil", "BRL", 0.20, 0.40, 0.03),
    Country("MX", "Mexico", "MXN", 0.058, 0.42, 0.03),
]

DEPARTMENTS: list[Department] = [
    Department("Engineering", 1.15, "Software Engineer", 0.30),
    Department("Product", 1.10, "Product Manager", 0.08),
    Department("Design", 1.05, "Product Designer", 0.05),
    Department("Sales", 1.00, "Sales Executive", 0.12),
    Department("Marketing", 0.95, "Marketing Specialist", 0.08),
    Department("Finance", 1.00, "Finance Analyst", 0.07),
    Department("HR", 0.90, "HR Specialist", 0.06),
    Department("Legal", 1.05, "Legal Counsel", 0.03),
    Department("Operations", 0.90, "Operations Analyst", 0.11),
    Department("Support", 0.75, "Support Specialist", 0.10),
]

# Org pyramid: more junior/mid employees than senior/director.
LEVELS: list[Level] = [
    Level("L1", 55000, 0.22),
    Level("L2", 72000, 0.28),
    Level("L3", 95000, 0.25),
    Level("L4", 120000, 0.13),
    Level("L5", 145000, 0.08),
    Level("L6", 190000, 0.04),
]


def level_title(level_code: str, department: Department) -> str:
    base = department.base_title
    if level_code == "L1":
        return f"{base} I"
    if level_code == "L2":
        return f"{base} II"
    if level_code == "L3":
        return f"Senior {base}"
    if level_code == "L4":
        return f"Lead {base}"
    if level_code == "L5":
        return f"{department.name} Manager"
    if level_code == "L6":
        return f"Director of {department.name}"
    raise ValueError(f"Unknown level code: {level_code}")