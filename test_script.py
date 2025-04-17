#!/usr/bin/env python3
"""
Example usage of the agent-based JSON transformation pipeline.
"""

import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from utils.logger import setup_logger
from agents.transformation_agent import TMSTransformationAgent

# Load environment variables from .env file if present
load_dotenv()

# Set up logging
logger = setup_logger(logging.INFO)

def process_example():
    """Process an example extraction JSON."""
    # Example data
    example_data = {
        "equipment_type": "Van",
        "reference_number": "0567696",
        "booking_confirmation_number": "10271",
        "total_rate": "1175.00",
        "freight_rate": "1175.00",
        "additional_rate": None,
        "shipper_section": [
            {
                "ship_from_company": "707 Fernley Railing Warehouse",
                "ship_from_address": "2275 E Newlands Dr, NV 89408 FERNLEY",
                "pickup_number": "1289969, 10271",
                "pickup_instructions": "MACROPOINT IS REQUIRED BY CUSTOMER FROM SHIPPER TO RECEIVER. FAILURE TO COMPLY WILL RESULT IN $100 DEDUCTION",
                "pickup_appointment_start_datetime": "01/28/25 11:00",
                "pickup_appointment_end_datetime": "01/28/25 11:00"
            }
        ],
        "receiver_section": [
            {
                "receiver_company": "Boise Cascade Building Materials Distrib",
                "receiver_address": "1020 W 3265 S, SOUTH SALT LAKEUT 84119",
                "receiver_delivery_number": "10271",
                "receiver_instructions": "Main - FCFS",
                "receiver_appointment_start_datetime": "01/29/25 08:00",
                "receiver_appointment_end_datetime": "01/29/25 15:00"
            }
        ],
        "customer_name": "Kirsch Transportation Services, Inc.",
        "email_domain": "kirschtrans.com",
        "customer_address": "1102 Douglas St, Omaha, NE 68102"
    }
    
    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    try:
        # Create agent and process the JSON
        logger.info("Creating TMS transformation agent...")
        agent = TMSTransformationAgent(api_key=api_key)
        
        # Transform data
        logger.info("Transforming example data...")
        tms_request = agent.process(example_data)
        
        # Print result
        logger.info("Transformation successful!")
        logger.info("\nTMS Request:")
        print(json.dumps(tms_request.model_dump(exclude_none=True), indent=2))
        
        # Save to file
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "example_agent_output.json"
        
        with open(output_file, "w") as f:
            json.dump(tms_request.model_dump(exclude_none=True), f, indent=2)
        
        logger.info(f"Output saved to {output_file}")
        
        # Show entity resolution results
        logger.info("\nEntity Resolution Results:")
        entity_mappings = agent.workflow.get_state()["entity_mappings"]
        logger.info(f"Customer: {example_data['customer_name']} -> {entity_mappings['customer_code']}")
        
        for i, shipper_code in enumerate(entity_mappings["shipper_codes"]):
            if i < len(example_data["shipper_section"]):
                shipper = example_data["shipper_section"][i]
                logger.info(f"Shipper: {shipper['ship_from_company']} -> {shipper_code}")
        
        for i, receiver_code in enumerate(entity_mappings["receiver_codes"]):
            if i < len(example_data["receiver_section"]):
                receiver = example_data["receiver_section"][i]
                logger.info(f"Receiver: {receiver['receiver_company']} -> {receiver_code}")
        
    except Exception as e:
        logger.error(f"Error processing example: {str(e)}")
        raise

if __name__ == "__main__":
    process_example()