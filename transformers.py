# """
# Transformers for converting between data formats.
# """

# import logging
# from typing import Dict, Any, List, Optional, Tuple
# from datetime import datetime

# from models import TmsOrderEntryRequest, OrderEntryStopPayload, StopReferenceType
# from constants import Constants
# from utils.datetime_utils import parse_datetime, format_datetime_for_tms
# from utils.text_utils import extract_phone_number, parse_address, extract_reference_numbers, extract_company_code
# from llm.client import LlmClient

# logger = logging.getLogger(__name__)

# class ExtractionToTmsTransformer:
#     """Transformer for converting extraction JSON to TMS Order Entry Request."""
    
#     def __init__(self, llm_client: Optional[LlmClient] = None):
#         """
#         Initialize the transformer.
        
#         Args:
#             llm_client: Optional LLM client for making decisions
#         """
#         self.llm_client = llm_client or LlmClient()
    
#     def transform(self, extraction_json: Dict[str, Any]) -> TmsOrderEntryRequest:
#         """
#         Transform the extraction JSON into TMS Order Entry Request.
        
#         Args:
#             extraction_json: The extraction JSON
            
#         Returns:
#             TMS Order Entry Request
#         """
#         logger.info("Starting transformation of extraction JSON to TMS format")
        
#         # Extract basic information
#         equipment_type = extraction_json.get("equipment_type", "Van")
#         trailer_type = self._get_trailer_type(equipment_type)
#         booking_confirmation_number = extraction_json.get("booking_confirmation_number")
#         reference_number = extraction_json.get("reference_number")
#         total_rate = extraction_json.get("total_rate")
#         freight_rate = extraction_json.get("freight_rate")
        
#         # Try to parse rates as floats
#         try:
#             charge_rate = float(freight_rate or total_rate or 0)
#         except (TypeError, ValueError):
#             charge_rate = Constants.DEFAULT_RATE
        
#         # Get customer information
#         customer_name = extraction_json.get("customer_name", "")
#         customer_address = extraction_json.get("customer_address", "")
#         bill_to_code = self._resolve_entity(customer_name, customer_address, "customer")
        
#         # Process shipper information
#         shipper_section = extraction_json.get("shipper_section", [])
#         shipper_codes = []
#         stops = []
        
#         sequence = 1
#         for i, shipper in enumerate(shipper_section):
#             stop_payload = self._create_shipper_stop(shipper, sequence, booking_confirmation_number)
#             shipper_codes.append(stop_payload.companyID)
#             stops.append(stop_payload)
#             sequence += 1
        
#         # Process receiver information
#         receiver_section = extraction_json.get("receiver_section", [])
#         receiver_codes = []
        
#         for i, receiver in enumerate(receiver_section):
#             stop_payload = self._create_receiver_stop(receiver, sequence, booking_confirmation_number)
#             receiver_codes.append(stop_payload.companyID)
#             stops.append(stop_payload)
#             sequence += 1
        
#         # Ensure we have at least one pickup and one delivery stop
#         stops = self._validate_and_fix_stops(stops)
        
#         # Create primary reference numbers
#         references = self._extract_primary_references(booking_confirmation_number, reference_number)
        
#         # Ensure we have shipper and consignee codes
#         if not shipper_codes:
#             shipper_codes = ["UNKN"]
        
#         if not receiver_codes:
#             receiver_codes = ["UNKN"]
        
#         # Get rev types using LLM
#         origin_address = shipper_section[0].get("ship_from_address", "") if shipper_section else ""
#         destination_address = receiver_section[0].get("receiver_address", "") if receiver_section else ""
        
#         rev_types = self.llm_client.get_rev_types(
#             customer_name,
#             origin_address,
#             destination_address,
#             equipment_type
#         )
#         logger.info(f"Claude rev types output: {rev_types}")
        
#         # Determine commodity
#         commodity_desc = ""  # In a real implementation, this would come from the extraction JSON
#         commodity = self.llm_client.get_commodity(commodity_desc, trailer_type, None)
#         logger.info(f"Claude commodity output: {commodity}")
        
#         # Create TMS Order Entry Request
#         tms_request = TmsOrderEntryRequest(
#             startDate=datetime.now().strftime(Constants.TMS_TIME_FORMAT),
#             shipper=shipper_codes[0],
#             consignee=receiver_codes[0],
#             billTo=bill_to_code,
#             orderBy=bill_to_code,  # Same as billTo
#             weight=None,  # Not available in extraction JSON
#             weightUnit=Constants.WEIGHT_UNIT_LBS,
#             commodity=commodity,
#             commodityValue=None,
#             maxTemperature=None,
#             minTemperature=None,
#             temperatureUnits=Constants.TEMPERATURE_UNITS_FRNHGT,
#             count=None,
#             countUnit=None,
#             chargeItemCode=Constants.CHARGE_ITEM_CODE_LHF,
#             chargeRateUnit=Constants.CHARGE_RATE_UNIT_FLT,
#             chargeRate=charge_rate,
#             currency=Constants.CURRENCY_US,
#             remark=self._extract_remarks(shipper_section, receiver_section),
#             stops=stops,
#             trailerType1=trailer_type,
#             revType1=rev_types.get("revType1", Constants.REV_TYPE1_LOGCOM),
#             revType2=rev_types.get("revType2", Constants.REV_TYPE2_HOUSE),
#             revType3=rev_types.get("revType3", Constants.REV_TYPE3_IN),
#             revType4=rev_types.get("revType4", Constants.REV_TYPE4_OTR),
#             extraInfo1=None,
#             referenceType1=references[0][0] if len(references) > 0 else None,
#             referenceType2=references[1][0] if len(references) > 1 else None,
#             referenceType3=references[2][0] if len(references) > 2 else None,
#             referenceNumber1=references[0][1] if len(references) > 0 else None,
#             referenceNumber2=references[1][1] if len(references) > 1 else None,
#             referenceNumber3=references[2][1] if len(references) > 2 else None,
#             status=Constants.ORDER_STATUS_AVAILABLE
#         )
        
#         logger.info("Completed transformation of extraction JSON to TMS format")
#         return tms_request
    
#     def _get_trailer_type(self, equipment_type: str) -> str:
#         """
#         Map the equipment type to a trailer type.
        
#         Args:
#             equipment_type: Equipment type from extraction JSON
            
#         Returns:
#             Trailer type for TMS
#         """
#         return Constants.EQUIPMENT_TYPE_MAPPING.get(equipment_type, Constants.TRAILER_TYPE_VAN)
    
#     def _resolve_entity(self, name: str, address: str, entity_type: str) -> str:
#         """
#         Resolve an entity to a TMS code.
        
#         Args:
#             name: Entity name
#             address: Entity address
#             entity_type: Type of entity (shipper, receiver, customer)
            
#         Returns:
#             Entity code for TMS
#         """
#         # In a real implementation, this would query a database
#         # For now, use the LLM to simulate entity resolution
#         return self.llm_client.resolve_entity(name, address, entity_type)
    
#     def _create_shipper_stop(self, shipper: Dict[str, Any], sequence: int, booking_confirmation_number: Optional[str]) -> OrderEntryStopPayload:
#         """
#         Create a stop payload for a shipper.
        
#         Args:
#             shipper: Shipper information
#             sequence: Stop sequence number
#             booking_confirmation_number: Booking confirmation number
            
#         Returns:
#             Stop payload
#         """
#         company_name = shipper.get("ship_from_company", "")
#         company_code = self._resolve_entity(company_name, shipper.get("ship_from_address", ""), "shipper")
        
#         pickup_number = shipper.get("pickup_number", "")
#         pickup_instructions = shipper.get("pickup_instructions", "")
        
#         start_datetime_str = shipper.get("pickup_appointment_start_datetime")
#         end_datetime_str = shipper.get("pickup_appointment_end_datetime")
        
#         # Parse dates
#         start_datetime = parse_datetime(start_datetime_str)
#         end_datetime = parse_datetime(end_datetime_str)
        
#         # Format dates for TMS if available
#         earliest_date = format_datetime_for_tms(start_datetime) if start_datetime else None
#         latest_date = format_datetime_for_tms(end_datetime) if end_datetime else None
        
#         # Extract phone number from instructions or other fields
#         phone_number = extract_phone_number(pickup_instructions)
        
#         # Extract reference numbers
#         reference_numbers = []
#         if pickup_number:
#             for ref_type, ref_value in extract_reference_numbers(pickup_number):
#                 reference_numbers.append(
#                     StopReferenceType(
#                         referenceType=Constants.REFERENCE_TYPE_MAPPING.get(ref_type, Constants.REF_REF),
#                         value=ref_value
#                     )
#                 )
        
#         # Add booking confirmation number as a LOAD reference if available
#         if booking_confirmation_number:
#             reference_numbers.append(
#                 StopReferenceType(
#                     referenceType=Constants.REF_LOAD,
#                     value=booking_confirmation_number
#                 )
#             )
        
#         # Create stop payload
#         return OrderEntryStopPayload(
#             eventCode=Constants.PICKUP_EVENT_CODE,
#             stopType=Constants.PICKUP_STOP_TYPE,
#             companyID=company_code,
#             sequence=sequence,
#             billable=True,
#             earliestDate=earliest_date,
#             latestDate=latest_date,
#             arrivalDate=earliest_date,
#             departureDate=latest_date,
#             phoneNumber=phone_number,
#             referenceNumbers=reference_numbers
#         )
    
#     def _create_receiver_stop(self, receiver: Dict[str, Any], sequence: int, booking_confirmation_number: Optional[str]) -> OrderEntryStopPayload:
#         """
#         Create a stop payload for a receiver.
        
#         Args:
#             receiver: Receiver information
#             sequence: Stop sequence number
#             booking_confirmation_number: Booking confirmation number
            
#         Returns:
#             Stop payload
#         """
#         company_name = receiver.get("receiver_company", "")
#         company_code = self._resolve_entity(company_name, receiver.get("receiver_address", ""), "receiver")
        
#         delivery_number = receiver.get("receiver_delivery_number", "")
#         receiver_instructions = receiver.get("receiver_instructions", "")
        
#         start_datetime_str = receiver.get("receiver_appointment_start_datetime")
#         end_datetime_str = receiver.get("receiver_appointment_end_datetime")
        
#         # Parse dates
#         start_datetime = parse_datetime(start_datetime_str)
#         end_datetime = parse_datetime(end_datetime_str)
        
#         # Format dates for TMS if available
#         earliest_date = format_datetime_for_tms(start_datetime) if start_datetime else None
#         latest_date = format_datetime_for_tms(end_datetime) if end_datetime else None
        
#         # Extract phone number from instructions or other fields
#         phone_number = extract_phone_number(receiver_instructions)
        
#         # Extract reference numbers
#         reference_numbers = []
#         if delivery_number:
#             for ref_type, ref_value in extract_reference_numbers(delivery_number):
#                 reference_numbers.append(
#                     StopReferenceType(
#                         referenceType=Constants.REFERENCE_TYPE_MAPPING.get(ref_type, Constants.REF_REF),
#                         value=ref_value
#                     )
#                 )
        
#         # Add booking confirmation number as a LOAD reference if available
#         if booking_confirmation_number and not any(ref.value == booking_confirmation_number for ref in reference_numbers):
#             reference_numbers.append(
#                 StopReferenceType(
#                     referenceType=Constants.REF_LOAD,
#                     value=booking_confirmation_number
#                 )
#             )
        
#         # Create stop payload
#         return OrderEntryStopPayload(
#             eventCode=Constants.DELIVERY_EVENT_CODE,
#             stopType=Constants.DELIVERY_STOP_TYPE,
#             companyID=company_code,
#             sequence=sequence,
#             billable=True,
#             earliestDate=earliest_date,
#             latestDate=latest_date,
#             arrivalDate=earliest_date,
#             departureDate=latest_date,
#             phoneNumber=phone_number,
#             referenceNumbers=reference_numbers
#         )
    
#     def _validate_and_fix_stops(self, stops: List[OrderEntryStopPayload]) -> List[OrderEntryStopPayload]:
#         """
#         Ensure we have at least one pickup and one delivery stop.
        
#         Args:
#             stops: List of stops
            
#         Returns:
#             Validated and fixed stops
#         """
#         if not stops:
#             raise ValueError("No stops found in extraction JSON")
        
#         if not any(stop.stopType == Constants.PICKUP_STOP_TYPE for stop in stops):
#             # Set first stop as pickup if none exists
#             logger.warning("No pickup stop found, setting the first stop as pickup")
#             stops[0].stopType = Constants.PICKUP_STOP_TYPE
#             stops[0].eventCode = Constants.PICKUP_EVENT_CODE
        
#         if not any(stop.stopType == Constants.DELIVERY_STOP_TYPE for stop in stops):
#             # Set last stop as delivery if none exists
#             logger.warning("No delivery stop found, setting the last stop as delivery")
#             stops[-1].stopType = Constants.DELIVERY_STOP_TYPE
#             stops[-1].eventCode = Constants.DELIVERY_EVENT_CODE
        
#         return stops
    
#     def _extract_primary_references(self, booking_confirmation_number: Optional[str], reference_number: Optional[str]) -> List[Tuple[str, str]]:
#         """
#         Extract primary reference numbers for the order.
        
#         Args:
#             booking_confirmation_number: Booking confirmation number
#             reference_number: Reference number
            
#         Returns:
#             List of tuples (reference_type, reference_number)
#         """
#         references = []
        
#         if booking_confirmation_number:
#             references.append((Constants.REF_LOAD, booking_confirmation_number))
        
#         if reference_number:
#             references.append((Constants.REF_REF, reference_number))
        
#         return references
    
#     def _extract_remarks(self, shipper_section: List[Dict[str, Any]], receiver_section: List[Dict[str, Any]]) -> Optional[str]:
#         """
#         Extract remarks from shipper and receiver instructions.
        
#         Args:
#             shipper_section: Shipper section
#             receiver_section: Receiver section
            
#         Returns:
#             Remarks for TMS
#         """
#         remarks = []
        
#         # Get shipper instructions
#         for shipper in shipper_section:
#             if shipper.get("pickup_instructions"):
#                 remarks.append(f"Pickup: {shipper['pickup_instructions']}")
        
#         # Get receiver instructions
#         for receiver in receiver_section:
#             if receiver.get("receiver_instructions"):
#                 remarks.append(f"Delivery: {receiver['receiver_instructions']}")
        
#         if remarks:
#             return " | ".join(remarks)
        
#         return None