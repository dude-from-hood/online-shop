import psycopg
from fastapi import APIRouter, HTTPException, status

from app.api.schemas.customers import CustomerCreate, CustomerResponse
from app.services.customer_service import (
    CustomerHasOrdersError,
    CustomerNotFoundError,
    CustomerService,
)


router = APIRouter(prefix="/customers", tags=["Customers"])
service = CustomerService()


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate) -> CustomerResponse:
    try:
        return service.create_customer(payload)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Could not create customer") from error


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int) -> CustomerResponse:
    try:
        return service.get_customer(customer_id)
    except CustomerNotFoundError as error:
        raise HTTPException(status_code=404, detail="Customer not found") from error
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Could not fetch customer") from error


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int) -> None:
    try:
        service.delete_customer(customer_id)
    except CustomerNotFoundError as error:
        raise HTTPException(status_code=404, detail="Customer not found") from error
    except CustomerHasOrdersError as error:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete customer with existing orders",
        ) from error
    except psycopg.Error as error:
        raise HTTPException(status_code=503, detail="Could not delete customer") from error
