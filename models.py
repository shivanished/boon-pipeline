"""
Data models for the TMS system using Pydantic.
Defines the structure for TMS Order Entry Requests and related entities.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class StopReferenceType(BaseModel):
    """Reference number associated with a stop."""
    referenceType: str
    value: str
    referenceTable: str = "stops"


class OrderEntryStopPayload(BaseModel):
    """Represents a stop in the transportation order."""
    eventCode: str
    stopType: str
    companyID: Optional[str] = None
    sequence: int
    billable: bool = True
    earliestDate: Optional[str] = None
    latestDate: Optional[str] = None
    arrivalDate: Optional[str] = None
    departureDate: Optional[str] = None
    phoneNumber: Optional[str] = None
    referenceNumbers: List[StopReferenceType] = []


class TmsOrderEntryRequest(BaseModel):
    """
    Main model for TMS Order Entry Request.
    This is what will be submitted to the TMS API.
    """
    startDate: str
    shipper: str
    consignee: str
    billTo: str
    orderBy: str
    weight: Optional[float] = None
    weightUnit: str
    commodity: str
    commodityValue: Optional[float] = None
    maxTemperature: Optional[int] = None
    minTemperature: Optional[int] = None
    temperatureUnits: str
    count: Optional[int] = None
    countUnit: Optional[str] = None
    chargeItemCode: str
    chargeRateUnit: str
    chargeRate: float
    currency: str
    remark: Optional[str] = None
    stops: List[OrderEntryStopPayload]
    trailerType1: str
    revType1: str
    revType2: Optional[str] = None
    revType3: str
    revType4: str
    extraInfo1: Optional[str] = None
    referenceType1: Optional[str] = None
    referenceType2: Optional[str] = None
    referenceType3: Optional[str] = None
    referenceNumber1: Optional[str] = None
    referenceNumber2: Optional[str] = None
    referenceNumber3: Optional[str] = None
    status: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary."""
        return self.model_dump(exclude_none=True)


class ExtractionShipperSection(BaseModel):
    """Represents the shipper section from extraction JSON."""
    ship_from_company: Optional[str] = None
    ship_from_address: Optional[str] = None
    pickup_number: Optional[str] = None
    pickup_instructions: Optional[str] = None
    pickup_appointment_start_datetime: Optional[str] = None
    pickup_appointment_end_datetime: Optional[str] = None
    pickup_phone_number: Optional[str] = None


class ExtractionReceiverSection(BaseModel):
    """Represents the receiver section from extraction JSON."""
    receiver_company: Optional[str] = None
    receiver_address: Optional[str] = None
    receiver_delivery_number: Optional[str] = None
    receiver_instructions: Optional[str] = None
    receiver_appointment_start_datetime: Optional[str] = None
    receiver_appointment_end_datetime: Optional[str] = None
    receiver_phone_number: Optional[str] = None


class ExtractionJson(BaseModel):
    """Model for the extraction JSON data."""
    equipment_type: Optional[str] = None
    reference_number: Optional[str] = None
    booking_confirmation_number: Optional[str] = None
    total_rate: Optional[str] = None
    freight_rate: Optional[str] = None
    additional_rate: Optional[str] = None
    shipper_section: List[ExtractionShipperSection] = []
    receiver_section: List[ExtractionReceiverSection] = []
    customer_name: Optional[str] = None
    email_domain: Optional[str] = None
    customer_address: Optional[str] = None