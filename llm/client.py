"""
LLM client for making decisions with Claude.
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from utils.text_utils import extract_company_code
import anthropic

logger = logging.getLogger(__name__)

class LlmClient:
    """Client for making LLM decisions."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LLM client.
        
        Args:
            api_key: Optional API key for Anthropic
        """
        # Use provided API key or get from environment
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def make_decision(self, prompt: str, model: str = "claude-3-5-sonnet-20240620") -> str:
        """
        Make a decision using the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            model: The model to use
            
        Returns:
            The LLM's response
        """
        try:
            logger.debug(f"Sending prompt to LLM: {prompt[:100]}...")
            
            response = self.client.messages.create(
                model=model,
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
    
    def get_rev_types(self, customer_name: str, origin_address: str, destination_address: str, equipment_type: str) -> Dict[str, str]:
        """
        Get the revenue types for a transportation order.
        
        Args:
            customer_name: Customer name
            origin_address: Origin address
            destination_address: Destination address
            equipment_type: Equipment type
            
        Returns:
            Dictionary with revType1, revType2, revType3, revType4
        """
        prompt = f"""
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
        
        Format your response as a JSON object with these four keys.
        """
        
        response = self.make_decision(prompt)
        
        try:
            # Try to extract JSON from the response
            json_pattern = r'\{.*\}'
            json_match = json.loads(response)
            return json_match
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            # Default values
            return {
                "revType1": "LOGCOM",
                "revType2": "HOUSE",
                "revType3": "IN",
                "revType4": "OTR"
            }
    
    def get_commodity(self, description: str, trailer_type: str, temperature: Optional[int] = None) -> str:
        """
        Determine the commodity code based on description and conditions.
        
        Args:
            description: Description of the goods
            trailer_type: Type of trailer
            temperature: Temperature requirements (if any)
            
        Returns:
            Commodity code
        """
        prompt = f"""
        Determine the appropriate commodity code for the following shipment:
        
        Description: {description}
        Trailer Type: {trailer_type}
        Temperature Requirements: {temperature if temperature is not None else 'None'}
        
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
        
        response = self.make_decision(prompt)
        
        # Clean up response and ensure it's in the list of valid commodities
        valid_commodities = [
            "BRICK", "BUILDING", "DRYFOOD", "FAK", "FRZFOOD", 
            "FZN&RFR", "REFOOD", "STEEL", "STONE"
        ]
        
        for commodity in valid_commodities:
            if commodity in response:
                return commodity
        
        # Default to FAK if no valid commodity is found
        return "FAK"
    
    def resolve_entity(self, name: str, address: str, entity_type: str) -> str:
        """
        Resolve an entity to a database entry, handling name changes and acquisitions.
        
        Args:
            name: Entity name
            address: Entity address
            entity_type: Type of entity (shipper, receiver, customer)
            
        Returns:
            Entity code for TMS
        """
        prompt = f"""
        I need to resolve this transportation entity to our database:
        
        Name: {name}
        Address: {address}
        Type: {entity_type}
        
        The entity might have been renamed, acquired, or relocated. Please provide:
        1. The most likely entity code (4 letters max)
        2. Confidence level (high, medium, low)
        
        Format as: "CODE|CONFIDENCE"
        """
        
        response = self.make_decision(prompt)
        
        # Parse the response
        try:
            parts = response.strip().split('|')
            code = parts[0].strip().upper()
            confidence = parts[1].strip().lower() if len(parts) > 1 else "low"
            
            # Validate code
            if len(code) > 4:
                code = code[:4]
            
            # If low confidence, create a generic code from the name
            if confidence == "low":
                code = extract_company_code(name)
                
            return code
        except Exception as e:
            logger.error(f"Error parsing entity resolution response: {str(e)}")
            return extract_company_code(name)