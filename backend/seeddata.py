from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import DailyEntry
import random
from datetime import date, timedelta

def seed_data():
    db: Session = SessionLocal()

    try:
        start_date = date(2024, 12, 1)

        for i in range(30):
            flare = random.choice([0, 1])

            entry = DailyEntry(
                date=(start_date + timedelta(days=i)).isoformat(),
                itch=round(random.uniform(2, 8), 2),
                redness=round(random.uniform(2, 7), 2),
                scaling=round(random.uniform(1, 6), 2),
                joint_pain=round(random.uniform(0, 5), 2),
                fatigue=round(random.uniform(3, 8), 2),
                stress_level=round(random.uniform(3, 9), 2),
                sleep_quality=round(random.uniform(2, 8), 2),
                diet_quality=round(random.uniform(3, 8), 2),
                missed_medication=random.choice([0, 1]),
                topical_applied=random.choice([0, 1]),
                psoriasis_flare=flare,
                notes="Seed data"
            )

            db.add(entry)

        db.commit()
        print("✅ Seed data inserted successfully (30 rows)")

    except Exception as e:
        db.rollback()
        print("❌ Error while seeding:", e)

    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
