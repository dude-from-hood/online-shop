import psycopg

from app.api.schemas.customers import CustomerCreate, CustomerResponse
from app.core.config import settings
from app.repositories.customer_repository import CustomerRepository


class CustomerNotFoundError(Exception):
    pass


class CustomerHasOrdersError(Exception):
    pass


class CustomerService:
    def create_customer(self, data: CustomerCreate) -> CustomerResponse:
        try:
            with psycopg.connect(settings.database_url) as connection:
                row = CustomerRepository(connection).create(data.name, data.email)
        except psycopg.errors.UniqueViolation as error:
            raise ValueError("Customer with this email already exists") from error

        return self._to_response(row)

    def get_customer(self, customer_id: int) -> CustomerResponse:
        with psycopg.connect(settings.database_url) as connection:
            row = CustomerRepository(connection).get_by_id(customer_id)

        if row is None:
            raise CustomerNotFoundError

        return self._to_response(row)

    def delete_customer(self, customer_id: int) -> None:
        try:
            with psycopg.connect(settings.database_url) as connection:
                deleted = CustomerRepository(connection).delete(customer_id)
        except psycopg.errors.ForeignKeyViolation as error:
            raise CustomerHasOrdersError from error

        if not deleted:
            raise CustomerNotFoundError

    @staticmethod
    def _to_response(row: tuple) -> CustomerResponse:
        return CustomerResponse(
            id=row[0],
            name=row[1],
            email=row[2],
            created_at=row[3],
        )
