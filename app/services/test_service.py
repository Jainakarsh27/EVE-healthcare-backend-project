import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.diagnostic_test import DiagnosticTest
from app.repositories.test_repository import TestRepository
from app.schemas.test import TestCreate, TestResponse, TestUpdate
from app.utils.pagination import PaginatedResponse, PaginationParams


class TestService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.test_repo = TestRepository(session)

    async def create_test(self, test_in: TestCreate) -> TestResponse:
        existing = await self.test_repo.get_by_code(test_in.code)
        if existing:
            raise ConflictError(
                message=f"Test with code '{test_in.code}' already exists",
                code="TEST_CODE_ALREADY_EXISTS",
            )

        test = DiagnosticTest(
            name=test_in.name,
            code=test_in.code.upper(),
            description=test_in.description,
            category=test_in.category,
            preparation_instructions=test_in.preparation_instructions,
            is_active=test_in.is_active,
        )
        created = await self.test_repo.create(test)
        await self.session.commit()
        return TestResponse.model_validate(created)

    async def get_test(self, test_id: uuid.UUID) -> TestResponse:
        test = await self.test_repo.get_by_id(test_id)
        if not test:
            raise NotFoundError(message="Diagnostic test not found", code="TEST_NOT_FOUND")
        return TestResponse.model_validate(test)

    async def update_test(self, test_id: uuid.UUID, test_in: TestUpdate) -> TestResponse:
        test = await self.test_repo.get_by_id(test_id)
        if not test:
            raise NotFoundError(message="Diagnostic test not found", code="TEST_NOT_FOUND")

        if test_in.code and test_in.code.upper() != test.code:
            existing = await self.test_repo.get_by_code(test_in.code)
            if existing:
                raise ConflictError(
                    message=f"Test code '{test_in.code}' is already taken",
                    code="TEST_CODE_ALREADY_EXISTS",
                )

        update_data = test_in.model_dump(exclude_unset=True)
        if "code" in update_data:
            update_data["code"] = update_data["code"].upper()

        for field, value in update_data.items():
            setattr(test, field, value)

        updated = await self.test_repo.update(test)
        await self.session.commit()
        return TestResponse.model_validate(updated)

    async def delete_test(self, test_id: uuid.UUID) -> None:
        test = await self.test_repo.get_by_id(test_id)
        if not test:
            raise NotFoundError(message="Diagnostic test not found", code="TEST_NOT_FOUND")
        test.is_active = False
        await self.test_repo.update(test)
        await self.session.commit()

    async def list_tests(
        self,
        category: str | None = None,
        is_active: bool | None = None,
        params: PaginationParams | None = None,
    ) -> PaginatedResponse[TestResponse]:
        params = params or PaginationParams()
        items, total = await self.test_repo.list_tests(
            category=category,
            is_active=is_active,
            offset=params.offset,
            limit=params.page_size,
        )
        responses = [TestResponse.model_validate(item) for item in items]
        return PaginatedResponse.create(responses, total, params)
