from app.seed.run import seed_core_data, seed_demo_users
from app.seed.users import DEMO_PASSWORD, DEMO_USERS

if __name__ == "__main__":
    employee_count, salary_record_count = seed_core_data()
    print(f"Seeded {employee_count} employees and {salary_record_count} salary records.")

    user_count = seed_demo_users()
    print(f"Seeded {user_count} demo users (password: {DEMO_PASSWORD}):")
    for demo_user in DEMO_USERS:
        print(f"  {demo_user['email']} ({demo_user['role'].value})")