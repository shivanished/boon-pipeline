"""
LangGraph agent for TMS transformation workflow.
"""

import logging
import json
import re
from typing import Dict, Any, List, Tuple, Optional, TypedDict
from datetime import datetime
import operator

import anthropic
from langgraph.graph import StateGraph, START, END
from typing_extensions import Annotated

from models import TmsOrderEntryRequest, OrderEntryStopPayload, StopReferenceType
from constants import Constants
from utils.datetime_utils import parse_datetime, format_datetime_for_tms
from utils.text_utils import extract_phone_number, parse_address, extract_reference_numbers, extract_company_code

logger = logging.getLogger(__name__)

# State management for the agent workflow
class WorkflowState(TypedDict):
    extraction_json: Dict[str, Any]
    entity_mappings: Dict[str, Any]
    stop_data: List[Dict[str, Any]]
    revType_values: Dict[str, str]
    commodity_code: str
    tms_request: Optional[Dict[str, Any]]


class TMSTransformationAgent:
    """
    Agent-based workflow for transforming extraction data to TMS format.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the transformation agent.
        
        Args:
            api_key: API key for Anthropic
        """
        self.api_key = api_key
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # Initialize the state graph
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> Any:
        """
        Create the agent workflow.
        
        Returns:
            StateGraph for the transformation workflow
        """
        # Create StateGraph
        workflow = StateGraph(WorkflowState)
        
        # Define nodes
        workflow.add_node("extract_entities", self._extract_entities)
        workflow.add_node("process_stops", self._process_stops)
        workflow.add_node("determine_rev_types", self._determine_rev_types)
        workflow.add_node("determine_commodity", self._determine_commodity)
        workflow.add_node("create_tms_request", self._create_tms_request)
        
        # Define edges
        workflow.add_edge("extract_entities", "process_stops")
        workflow.add_edge("process_stops", "determine_rev_types")
        workflow.add_edge("determine_rev_types", "determine_commodity")
        workflow.add_edge("determine_commodity", "create_tms_request")
        workflow.add_edge("create_tms_request", END)
        
        # Set entry point
        workflow.set_entry_point("extract_entities")
        
        return workflow.compile()
    
    def process(self, extraction_json: Dict[str, Any]) -> TmsOrderEntryRequest:
        """
        Process extraction JSON through the agent workflow.
        
        Args:
            extraction_json: Extraction JSON data
            
        Returns:
            TMS Order Entry Request
        """
        # Initialize state
        initial_state = WorkflowState(
            extraction_json=extraction_json,
            entity_mappings={},
            stop_data=[],
            revType_values={},
            commodity_code="",
            tms_request=None
        )
        
        # Run the workflow
        logger.info("Starting agent-based transformation workflow")
        try:
            final_state = self.workflow.invoke(initial_state)
            
            # Convert the TMS request dict to a TmsOrderEntryRequest object
            if final_state["tms_request"]:
                return TmsOrderEntryRequest(**final_state["tms_request"])
            else:
                raise ValueError("Workflow did not produce a valid TMS request")
                
        except Exception as e:
            logger.error(f"Error in transformation workflow: {str(e)}")
            raise
    
    def _make_llm_decision(self, prompt: str) -> str:
        """
        Make a decision using the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            The LLM's response
        """
        try:
            logger.debug(f"Sending prompt to LLM: {prompt[:100]}...")
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            logger.debug("Received response from LLM")
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error making LLM decision: {str(e)}")
            return ""
    
    def _extract_entities(self, state: WorkflowState) -> WorkflowState:
        """
        Extract and map entities from extraction JSON.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        extraction_json = state["extraction_json"]
        
        # Prepare shipper and receiver details
        shipper_section = extraction_json.get("shipper_section", [])
        receiver_section = extraction_json.get("receiver_section", [])
        
        shipper_details = "\n".join([
            f"- Name: {shipper.get('ship_from_company', 'Unknown')}, Address: {shipper.get('ship_from_address', 'Unknown')}"
            for shipper in shipper_section
        ])
        
        receiver_details = "\n".join([
            f"- Name: {receiver.get('receiver_company', 'Unknown')}, Address: {receiver.get('receiver_address', 'Unknown')}"
            for receiver in receiver_section
        ])
        
        # Get customer info
        customer_name = extraction_json.get("customer_name", "Unknown")
        customer_address = extraction_json.get("customer_address", "Unknown")
        
        # Create prompt for entity extraction
        prompt = f"""
        You are an entity resolution specialist for logistics and transportation.
        Your task is to analyze company names and generate appropriate 4-letter codes
        that would be used in a Transportation Management System (TMS).
        
        For each entity, generate a 4-letter code following these rules:
        1. The code should be exactly 4 uppercase letters
        2. Use meaningful acronyms based on the company name
        3. For common companies, use industry standard abbreviations if possible
        4. If the company has multiple words, consider using first letters of each word
        5. For branch locations, focus on the parent company name, not the location
        
        Analyze these transportation entities and generate appropriate 4-letter TMS codes for each:
        
        Customer: {customer_name}
        Customer Address: {customer_address}
        
        Shippers:
        {shipper_details}
        
        Receivers:
        {receiver_details}
        
        Format your response as a JSON object with these keys:
        - customer_code: The 4-letter code for the customer
        - shipper_codes: A list of 4-letter codes for each shipper
        - receiver_codes: A list of 4-letter codes for each receiver
        """
        
        # Invoke LLM
        try:
            response = self._make_llm_decision(prompt)
            
            # Extract JSON from response
            entity_mappings = json.loads(response)
            
            # Update state
            state["entity_mappings"] = entity_mappings
            logger.info(f"Entity extraction completed successfully: {entity_mappings}")
            
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            # Fallback to basic extraction
            shipper_codes = [self._generate_basic_code(shipper.get("ship_from_company", "UNKN")) 
                            for shipper in shipper_section]
            receiver_codes = [self._generate_basic_code(receiver.get("receiver_company", "UNKN")) 
                             for receiver in receiver_section]
            
            state["entity_mappings"] = {
                "customer_code": self._generate_basic_code(customer_name),
                "shipper_codes": shipper_codes,
                "receiver_codes": receiver_codes
            }
        
        return state
    
    def _generate_basic_code(self, text: str) -> str:
        """
        Generate a basic 4-letter code from text.
        
        Args:
            text: Text to generate code from
            
        Returns:
            4-letter code
        """
        if not text or len(text.strip()) == 0:
            return "UNKN"
        
        # Clean the text
        clean = re.sub(r'[^A-Za-z0-9\s]', '', text.upper())
        words = clean.split()
        
        if len(words) == 0:
            return "UNKN"
        
        if len(words) == 1:
            # Single word - take first 4 letters
            word = words[0]
            if len(word) <= 4:
                return word.ljust(4, 'X')
            return word[:4]
        
        # Multiple words - take first letter of each word for up to 4 words
        code = ''.join(word[0] for word in words[:4])
        
        # If code is less than 4 letters, add letters from first word
        if len(code) < 4:
            if len(words[0]) > 1:
                code += words[0][1:5-len(code)]
            
            # Still need padding? Use X
            code = code.ljust(4, 'X')
        
        # If code is more than 4 letters, truncate
        return code[:4]
    
    def _process_stops(self, state: WorkflowState) -> WorkflowState:
        """
        Process stops data from extraction JSON.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        extraction_json = state["extraction_json"]
        entity_mappings = state["entity_mappings"]
        
        shipper_section = extraction_json.get("shipper_section", [])
        receiver_section = extraction_json.get("receiver_section", [])
        booking_confirmation_number = extraction_json.get("booking_confirmation_number")
        
        stop_data = []
        sequence = 1
        
        # Process shipper stops
        for i, shipper in enumerate(shipper_section):
            company_code = entity_mappings["shipper_codes"][i] if i < len(entity_mappings["shipper_codes"]) else "UNKN"
            
            pickup_number = shipper.get("pickup_number", "")
            pickup_instructions = shipper.get("pickup_instructions", "")
            
            start_datetime_str = shipper.get("pickup_appointment_start_datetime")
            end_datetime_str = shipper.get("pickup_appointment_end_datetime")
            
            # Parse dates
            start_datetime = parse_datetime(start_datetime_str)
            end_datetime = parse_datetime(end_datetime_str)
            
            # Format dates for TMS if available
            earliest_date = format_datetime_for_tms(start_datetime) if start_datetime else None
            latest_date = format_datetime_for_tms(end_datetime) if end_datetime else None
            
            # Extract phone number from instructions or other fields
            phone_number = extract_phone_number(pickup_instructions)
            
            # Extract reference numbers
            reference_numbers = []
            if pickup_number:
                for ref_type, ref_value in extract_reference_numbers(pickup_number):
                    reference_numbers.append({
                        "referenceType": Constants.REFERENCE_TYPE_MAPPING.get(ref_type, Constants.REF_REF),
                        "value": ref_value,
                        "referenceTable": "stops"
                    })
            
            # Add booking confirmation number as a LOAD reference if available
            if booking_confirmation_number:
                reference_numbers.append({
                    "referenceType": Constants.REF_LOAD,
                    "value": booking_confirmation_number,
                    "referenceTable": "stops"
                })
            
            # Create stop data
            stop = {
                "eventCode": Constants.PICKUP_EVENT_CODE,
                "stopType": Constants.PICKUP_STOP_TYPE,
                "companyID": company_code,
                "sequence": sequence,
                "billable": True,
                "earliestDate": earliest_date,
                "latestDate": latest_date,
                "arrivalDate": earliest_date,
                "departureDate": latest_date,
                "phoneNumber": phone_number,
                "referenceNumbers": reference_numbers
            }
            
            stop_data.append(stop)
            sequence += 1
        
        # Process receiver stops
        for i, receiver in enumerate(receiver_section):
            company_code = entity_mappings["receiver_codes"][i] if i < len(entity_mappings["receiver_codes"]) else "UNKN"
            
            delivery_number = receiver.get("receiver_delivery_number", "")
            receiver_instructions = receiver.get("receiver_instructions", "")
            
            start_datetime_str = receiver.get("receiver_appointment_start_datetime")
            end_datetime_str = receiver.get("receiver_appointment_end_datetime")
            
            # Parse dates
            start_datetime = parse_datetime(start_datetime_str)
            end_datetime = parse_datetime(end_datetime_str)
            
            # Format dates for TMS if available
            earliest_date = format_datetime_for_tms(start_datetime) if start_datetime else None
            latest_date = format_datetime_for_tms(end_datetime) if end_datetime else None
            
            # Extract phone number from instructions or other fields
            phone_number = extract_phone_number(receiver_instructions)
            
            # Extract reference numbers
            reference_numbers = []
            if delivery_number:
                for ref_type, ref_value in extract_reference_numbers(delivery_number):
                    reference_numbers.append({
                        "referenceType": Constants.REFERENCE_TYPE_MAPPING.get(ref_type, Constants.REF_REF),
                        "value": ref_value,
                        "referenceTable": "stops"
                    })
            
            # Add booking confirmation number as a LOAD reference if available
            if booking_confirmation_number and not any(ref["value"] == booking_confirmation_number for ref in reference_numbers):
                reference_numbers.append({
                    "referenceType": Constants.REF_LOAD,
                    "value": booking_confirmation_number,
                    "referenceTable": "stops"
                })
            
            # Create stop data
            stop = {
                "eventCode": Constants.DELIVERY_EVENT_CODE,
                "stopType": Constants.DELIVERY_STOP_TYPE,
                "companyID": company_code,
                "sequence": sequence,
                "billable": True,
                "earliestDate": earliest_date,
                "latestDate": latest_date,
                "arrivalDate": earliest_date,
                "departureDate": latest_date,
                "phoneNumber": phone_number,
                "referenceNumbers": reference_numbers
            }
            
            stop_data.append(stop)
            sequence += 1
        
        # Ensure we have at least one pickup and one delivery stop
        pickup_found = False
        delivery_found = False
        
        for stop in stop_data:
            if stop["stopType"] == Constants.PICKUP_STOP_TYPE:
                pickup_found = True
            elif stop["stopType"] == Constants.DELIVERY_STOP_TYPE:
                delivery_found = True
        
        if not pickup_found and stop_data:
            logger.warning("No pickup stop found, setting the first stop as pickup")
            stop_data[0]["stopType"] = Constants.PICKUP_STOP_TYPE
            stop_data[0]["eventCode"] = Constants.PICKUP_EVENT_CODE
        
        if not delivery_found and stop_data:
            logger.warning("No delivery stop found, setting the last stop as delivery")
            stop_data[-1]["stopType"] = Constants.DELIVERY_STOP_TYPE
            stop_data[-1]["eventCode"] = Constants.DELIVERY_EVENT_CODE
        
        # Update state
        state["stop_data"] = stop_data
        logger.info(f"Stop processing completed successfully: {len(stop_data)} stops")
        
        return state
    
    def _determine_rev_types(self, state: WorkflowState) -> WorkflowState:
        """
        Determine revenue types using LLM.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        extraction_json = state["extraction_json"]
        
        # Get locations for analysis
        shipper_section = extraction_json.get("shipper_section", [])
        receiver_section = extraction_json.get("receiver_section", [])
        
        origin_address = shipper_section[0].get("ship_from_address", "") if shipper_section else ""
        destination_address = receiver_section[0].get("receiver_address", "") if receiver_section else ""
        equipment_type = extraction_json.get("equipment_type", "Van")
        customer_name = extraction_json.get("customer_name", "")
        
        # Create prompt for determining rev types
        prompt = f"""
        You are a transportation revenue coding specialist.
        Your task is to determine the appropriate revenue type codes
        for a transportation order in a TMS system.
        
        Provide your answer as a valid JSON object with the rev type values.
        
        Based on the following transportation order information, determine the appropriate revType values for a TMS system:
        
        Customer: {customer_name}
        Origin: {origin_address}
        Destination: {destination_address}
        Equipment Type: {equipment_type}
        
        Please provide the following values:
        1. revType1 (options: LOGCOM, LOGOUT, STAND)
        2. revType2 (options: HOUSE, CZ, JBEMIS, STD, STI, STO)
        3. revType3 (options: IN, OUT, GSTET, JCLAY, JKOPP, LPATE, SCAMP)
        4. revType4 (options: LOCAL, MDWST, OTR, FLAT, MILES)
        
        Format your response as a valid JSON object with these four keys.
        """
        
        # Invoke LLM
        try:
            response = self._make_llm_decision(prompt)
            
            # Extract JSON from response
            rev_types = json.loads(response)
            
            # Update state
            state["revType_values"] = rev_types
            logger.info(f"Revenue type determination completed successfully: {rev_types}")
            
        except Exception as e:
            logger.error(f"Error determining rev types: {str(e)}")
            # Fallback to default values
            state["revType_values"] = {
                "revType1": Constants.REV_TYPE1_LOGCOM,
                "revType2": Constants.REV_TYPE2_HOUSE,
                "revType3": Constants.REV_TYPE3_IN,
                "revType4": Constants.REV_TYPE4_OTR
            }
        
        return state
    
    def _determine_commodity(self, state: WorkflowState) -> WorkflowState:
        """
        Determine commodity code using LLM.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        extraction_json = state["extraction_json"]
        
        # Get equipment type and temperature information
        equipment_type = extraction_json.get("equipment_type", "Van")
        trailer_type = Constants.EQUIPMENT_TYPE_MAPPING.get(equipment_type, Constants.TRAILER_TYPE_VAN)
        temperature_present = extraction_json.get("temperature_present", False)
        temperature_low = extraction_json.get("temperature_low")
        temperature_high = extraction_json.get("temperature_high")
        
        # Create prompt for determining commodity
        prompt = f"""
        You are a transportation commodity coding specialist.
        Your task is to determine the appropriate commodity code
        for a shipment in a TMS system.
        
        Provide your answer as a single commodity code string.
        
        Determine the appropriate commodity code for the following shipment:
        
        Equipment Type: {equipment_type}
        Trailer Type: {trailer_type}
        Temperature Controlled: {temperature_present}
        Temperature Low: {temperature_low}
        Temperature High: {temperature_high}
        
        Choose from these commodity codes:
        - BRICK (bricks, construction materials)
        - BUILDING (building materials)
        - DRYFOOD (dry food products)
        - FAK (freight of all kinds, general freight)
        - FRZFOOD (frozen food, requires temperature below 32F/0C)
        - FZN&RFR (frozen and refrigerated goods)
        - REFOOD (refrigerated food, requires temperature control but not frozen)
        - STEEL (steel products)
        - STONE (stone, rocks, gravel)
        
        Return only the commodity code as your answer, nothing else.
        """
        
        # Invoke LLM
        try:
            response = self._make_llm_decision(prompt)
            
            # Clean up response and ensure it's a valid commodity
            valid_commodities = [
                "BRICK", "BUILDING", "DRYFOOD", "FAK", "FRZFOOD", 
                "FZN&RFR", "REFOOD", "STEEL", "STONE"
            ]
            
            commodity_code = None
            for commodity in valid_commodities:
                if commodity in response:
                    commodity_code = commodity
                    break
            
            # Default to FAK if not found
            if not commodity_code:
                commodity_code = Constants.COMMODITY_FAK
            
            # Update state
            state["commodity_code"] = commodity_code
            logger.info(f"Commodity determination completed successfully: {commodity_code}")
            
        except Exception as e:
            logger.error(f"Error determining commodity: {str(e)}")
            # Fallback to default value
            state["commodity_code"] = Constants.COMMODITY_FAK
        
        return state
    
    def _create_tms_request(self, state: WorkflowState) -> WorkflowState:
        """
        Create the final TMS request.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        extraction_json = state["extraction_json"]
        entity_mappings = state["entity_mappings"]
        stop_data = state["stop_data"]
        rev_types = state["revType_values"]
        commodity_code = state["commodity_code"]
        
        # Extract basic information
        booking_confirmation_number = extraction_json.get("booking_confirmation_number")
        reference_number = extraction_json.get("reference_number")
        total_rate = extraction_json.get("total_rate")
        freight_rate = extraction_json.get("freight_rate")
        
        # Try to parse rates as floats
        try:
            charge_rate = float(freight_rate or total_rate or 0)
        except (TypeError, ValueError):
            charge_rate = Constants.DEFAULT_RATE
        
        # Extract primary reference numbers
        references = []
        if booking_confirmation_number:
            references.append((Constants.REF_LOAD, booking_confirmation_number))
        
        if reference_number:
            references.append((Constants.REF_REF, reference_number))
        
        # Extract remarks from shipper and receiver instructions
        remarks = []
        for shipper in extraction_json.get("shipper_section", []):
            if shipper.get("pickup_instructions"):
                remarks.append(f"Pickup: {shipper['pickup_instructions']}")
        
        for receiver in extraction_json.get("receiver_section", []):
            if receiver.get("receiver_instructions"):
                remarks.append(f"Delivery: {receiver['receiver_instructions']}")
        
        remark = " | ".join(remarks) if remarks else None
        
        # Create TMS request
        tms_request = {
            "startDate": datetime.now().strftime(Constants.TMS_TIME_FORMAT),
            "shipper": entity_mappings["shipper_codes"][0] if entity_mappings["shipper_codes"] else "UNKN",
            "consignee": entity_mappings["receiver_codes"][0] if entity_mappings["receiver_codes"] else "UNKN",
            "billTo": entity_mappings["customer_code"],
            "orderBy": entity_mappings["customer_code"],  # Same as billTo
            "weightUnit": Constants.WEIGHT_UNIT_LBS,
            "commodity": commodity_code,
            "temperatureUnits": Constants.TEMPERATURE_UNITS_FRNHGT,
            "chargeItemCode": Constants.CHARGE_ITEM_CODE_LHF,
            "chargeRateUnit": Constants.CHARGE_RATE_UNIT_FLT,
            "chargeRate": charge_rate,
            "currency": Constants.CURRENCY_US,
            "remark": remark,
            "stops": stop_data,
            "trailerType1": Constants.EQUIPMENT_TYPE_MAPPING.get(extraction_json.get("equipment_type", "Van"), Constants.TRAILER_TYPE_VAN),
            "revType1": rev_types.get("revType1", Constants.REV_TYPE1_LOGCOM),
            "revType2": rev_types.get("revType2", Constants.REV_TYPE2_HOUSE),
            "revType3": rev_types.get("revType3", Constants.REV_TYPE3_IN),
            "revType4": rev_types.get("revType4", Constants.REV_TYPE4_OTR),
            "referenceType1": references[0][0] if len(references) > 0 else None,
            "referenceType2": references[1][0] if len(references) > 1 else None,
            "referenceType3": references[2][0] if len(references) > 2 else None,
            "referenceNumber1": references[0][1] if len(references) > 0 else None,
            "referenceNumber2": references[1][1] if len(references) > 1 else None,
            "referenceNumber3": references[2][1] if len(references) > 2 else None,
            "status": Constants.ORDER_STATUS_AVAILABLE
        }
        
        # Update state
        state["tms_request"] = tms_request
        logger.info("TMS request creation completed successfully")
        
        return state