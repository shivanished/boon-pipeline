"""
Entity resolution utilities using LLM for dynamic entity mapping.
"""

import logging
import re
import json
from typing import Dict, Optional, Any, List

from llm.client import LlmClient
from utils.text_utils import clean_text, extract_company_code

logger = logging.getLogger(__name__)

class EntityResolver:
    """
    Dynamic entity resolver using LLM-based reasoning.
    """
    
    def __init__(self, llm_client: Optional[LlmClient] = None):
        """
        Initialize the entity resolver.
        
        Args:
            llm_client: Optional LLM client for making decisions
        """
        self.llm_client = llm_client or LlmClient()
        self.entity_cache = {}  # Cache resolved entities
    
    def resolve(self, name: str, address: str, entity_type: str) -> str:
        """
        Resolve an entity name to a TMS code.
        
        Args:
            name: Entity name
            address: Entity address
            entity_type: Type of entity (shipper, receiver, customer)
            
        Returns:
            Entity code for TMS
        """
        if not name:
            return self._generate_fallback_code(entity_type)
        
        # Check cache first
        cache_key = f"{name.upper()}|{entity_type}"
        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key]
        
        # Parse address for additional context
        city, state = self._extract_location_from_address(address)
        
        # Use LLM to generate code
        code = self._generate_code_with_llm(name, city, state, entity_type)
        
        # Cache result
        self.entity_cache[cache_key] = code
        return code
    
    def _extract_location_from_address(self, address: str) -> tuple:
        """
        Extract city and state from address.
        
        Args:
            address: Address string
            
        Returns:
            Tuple of (city, state)
        """
        if not address:
            return ("", "")
        
        # Simple regex to extract city and state
        # This is a simplistic approach - in production, use a proper address parser
        state_pattern = r'([A-Z]{2})'
        city_pattern = r'([A-Za-z\s.]+?),'
        
        state = ""
        city = ""
        
        state_match = re.search(state_pattern, address)
        if state_match:
            state = state_match.group(1)
        
        city_match = re.search(city_pattern, address)
        if city_match:
            city = city_match.group(1).strip()
        
        return (city, state)
    
    def _generate_code_with_llm(self, name: str, city: str, state: str, entity_type: str) -> str:
        """
        Generate a TMS code using LLM-based analysis.
        
        Args:
            name: Company name
            city: City location
            state: State location
            entity_type: Type of entity
            
        Returns:
            4-letter TMS code
        """
        # Prepare prompt for LLM
        prompt = f"""
        I need to generate a 4-letter TMS code for this transportation entity:
        
        Company Name: {name}
        Location: {city}, {state}
        Entity Type: {entity_type}
        
        Rules for generating the code:
        1. The code should be exactly 4 uppercase letters
        2. Try to use meaningful acronyms based on the company name
        3. For common companies, use industry standard abbreviations if possible
        4. If the company has multiple words, consider using first letters of each word
        5. For branch locations, focus on the parent company name, not the location
        
        Please provide ONLY the 4-letter code and nothing else in your response.
        """
        
        response = self.llm_client.make_decision(prompt)
        
        # Extract code from response - looking for 4 uppercase letters
        code_match = re.search(r'[A-Z]{4}', response.upper())
        if code_match:
            return code_match.group(0)
        
        # If no valid code found, create a fallback based on company name
        return self._generate_fallback_code(name)
    
    def _generate_fallback_code(self, text: str) -> str:
        """
        Generate a fallback 4-letter code from text.
        
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
    
    def batch_resolve(self, extraction_json: Dict[str, Any]) -> Dict[str, str]:
        """
        Batch resolve entities from an extraction JSON.
        
        Args:
            extraction_json: Extraction JSON data
            
        Returns:
            Dictionary mapping entity types to codes
        """
        results = {}
        
        # Resolve customer
        customer_name = extraction_json.get("customer_name", "")
        customer_address = extraction_json.get("customer_address", "")
        results["customer"] = self.resolve(customer_name, customer_address, "customer")
        
        # Resolve shippers
        shipper_section = extraction_json.get("shipper_section", [])
        results["shippers"] = []
        
        for shipper in shipper_section:
            company = shipper.get("ship_from_company", "")
            address = shipper.get("ship_from_address", "")
            code = self.resolve(company, address, "shipper")
            results["shippers"].append(code)
        
        # Resolve receivers
        receiver_section = extraction_json.get("receiver_section", [])
        results["receivers"] = []
        
        for receiver in receiver_section:
            company = receiver.get("receiver_company", "")
            address = receiver.get("receiver_address", "")
            code = self.resolve(company, address, "receiver")
            results["receivers"].append(code)
        
        return results