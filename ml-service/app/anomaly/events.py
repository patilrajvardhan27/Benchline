"""The slice of pricing.price-point-recorded.v1 this service reads."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PricePointData(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    price_point_id: uuid.UUID = Field(alias="pricePointId")
    item_id: str = Field(alias="itemId")
    item_group_id: str = Field(alias="itemGroupId")
    source: str
    unit_price: Decimal = Field(alias="unitPrice", gt=0)
    previous_unit_price: Decimal | None = Field(default=None, alias="previousUnitPrice")
    effective_date: date = Field(alias="effectiveDate")


class PricePointRecorded(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: uuid.UUID
    type: str
    data: PricePointData
