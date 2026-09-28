import asyncio
import os
import sys
from decimal import Decimal

# Ensure root workspace directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.logging import logger
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models.centre_test_offering import CentreTestOffering
from app.models.diagnostic_centre import DiagnosticCentre
from app.models.diagnostic_test import DiagnosticTest
from app.models.user import User
from app.repositories.centre_repository import CentreRepository
from app.repositories.offering_repository import OfferingRepository
from app.repositories.test_repository import TestRepository
from app.repositories.user_repository import UserRepository
from app.utils.enums import UserRole


async def seed_data():
    logger.info("Initializing database tables if not exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        centre_repo = CentreRepository(session)
        test_repo = TestRepository(session)
        offering_repo = OfferingRepository(session)

        logger.info("Seeding Admin & User accounts...")
        # 1. Admin Account
        admin_email = settings.SEED_ADMIN_EMAIL
        admin = await user_repo.get_by_email(admin_email)
        if not admin:
            admin = User(
                email=admin_email,
                password_hash=hash_password(settings.SEED_ADMIN_PASSWORD),
                full_name="EVE Admin",
                phone="+919876543210",
                role=UserRole.ADMIN,
                is_active=True,
            )
            await user_repo.create(admin)
            logger.info(f"Created Admin user: {admin_email}")

        # 2. Demo Patient Account
        demo_email = settings.SEED_USER_EMAIL
        demo_user = await user_repo.get_by_email(demo_email)
        if not demo_user:
            demo_user = User(
                email=demo_email,
                password_hash=hash_password(settings.SEED_USER_PASSWORD),
                full_name="John Doe",
                phone="+919123456789",
                role=UserRole.USER,
                is_active=True,
            )
            await user_repo.create(demo_user)
            logger.info(f"Created Demo user: {demo_email}")

        # 3. Diagnostic Centres
        centres_data = [
            {
                "name": "EVE Healthcare Koramangala",
                "address": "123, 80 Feet Road, 4th Block, Koramangala",
                "city": "Bangalore",
                "state": "Karnataka",
                "pincode": "560034",
                "latitude": Decimal("12.935240"),
                "longitude": Decimal("77.624480"),
            },
            {
                "name": "EVE Healthcare Indiranagar",
                "address": "456, 100 Feet Road, HAL 2nd Stage, Indiranagar",
                "city": "Bangalore",
                "state": "Karnataka",
                "pincode": "560038",
                "latitude": Decimal("12.978360"),
                "longitude": Decimal("77.640830"),
            },
            {
                "name": "EVE Healthcare Bandra",
                "address": "789, Turner Road, Bandra West",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400050",
                "latitude": Decimal("19.059600"),
                "longitude": Decimal("72.829500"),
            },
        ]

        created_centres = []
        for cdata in centres_data:
            c_items, _ = await centre_repo.list_centres(city=cdata["city"], limit=100)
            existing_c = next((c for c in c_items if c.name == cdata["name"]), None)
            if not existing_c:
                centre = DiagnosticCentre(**cdata, is_active=True)
                created_c = await centre_repo.create(centre)
                created_centres.append(created_c)
                logger.info(f"Created Diagnostic Centre: {cdata['name']}")
            else:
                created_centres.append(existing_c)

        # 4. Diagnostic Tests
        tests_data = [
            {
                "name": "Complete Blood Count (CBC)",
                "code": "CBC",
                "description": "Measures overall health and detects red/white blood cells and platelet counts.",
                "category": "HAEMATOLOGY",
                "preparation_instructions": "Fasting not required.",
            },
            {
                "name": "Thyroid Profile (T3, T4, TSH)",
                "code": "THYROID",
                "description": "Evaluates thyroid gland functionality and hormonal balance.",
                "category": "ENDOCRINOLOGY",
                "preparation_instructions": "Overnight 8-10 hours fasting recommended.",
            },
            {
                "name": "Lipid Profile",
                "code": "LIPID_PROFILE",
                "description": "Measures cholesterol, HDL, LDL, and triglycerides.",
                "category": "BIOCHEMISTRY",
                "preparation_instructions": "10-12 hours strict fasting required.",
            },
            {
                "name": "Liver Function Test (LFT)",
                "code": "LFT",
                "description": "Assesses liver enzymes, bilirubin, and protein levels.",
                "category": "BIOCHEMISTRY",
                "preparation_instructions": "Fasting for 8 hours required.",
            },
            {
                "name": "Kidney Function Test (KFT)",
                "code": "KFT",
                "description": "Evaluates kidney function including urea, creatinine, and electrolytes.",
                "category": "BIOCHEMISTRY",
                "preparation_instructions": "Drink plenty of water before test.",
            },
            {
                "name": "HbA1c Glycated Hemoglobin",
                "code": "HBA1C",
                "description": "Measures average blood sugar levels over the past 3 months.",
                "category": "DIABETES",
                "preparation_instructions": "Fasting not required.",
            },
        ]

        created_tests = []
        for tdata in tests_data:
            existing_t = await test_repo.get_by_code(tdata["code"])
            if not existing_t:
                test = DiagnosticTest(**tdata, is_active=True)
                created_t = await test_repo.create(test)
                created_tests.append(created_t)
                logger.info(f"Created Diagnostic Test: {tdata['code']} - {tdata['name']}")
            else:
                created_tests.append(existing_t)

        # 5. Centre Test Offerings
        pricing_map = {
            "CBC": Decimal("450.00"),
            "THYROID": Decimal("850.00"),
            "LIPID_PROFILE": Decimal("950.00"),
            "LFT": Decimal("1100.00"),
            "KFT": Decimal("1050.00"),
            "HBA1C": Decimal("650.00"),
        }

        for centre in created_centres:
            for test in created_tests:
                existing_offering = await offering_repo.get_by_centre_and_test(centre.id, test.id)
                if not existing_offering:
                    base_price = pricing_map.get(test.code, Decimal("500.00"))
                    offering = CentreTestOffering(
                        centre_id=centre.id,
                        test_id=test.id,
                        price=base_price,
                        duration_minutes=30,
                        is_available=True,
                    )
                    await offering_repo.create(offering)
                    logger.info(f"Offered {test.code} at {centre.name} for INR {base_price}")

        await session.commit()
        logger.info("Seed data processing completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
