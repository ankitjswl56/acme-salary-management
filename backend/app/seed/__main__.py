from app.seed.run import seed_core_data

if __name__ == "__main__":
    employee_count, salary_record_count = seed_core_data()
    print(f"Seeded {employee_count} employees and {salary_record_count} salary records.")