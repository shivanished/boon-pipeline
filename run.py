# language: python
#!/usr/bin/env python3
import json
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

from utils.logger import setup_logger
from agents.transformation_agent import TMSTransformationAgent

def run():
    load_dotenv()
    logger = setup_logger(logging.INFO)
    
    extraction_dir = Path("extraction")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    agent = TMSTransformationAgent(api_key=api_key)
    
    for input_file in extraction_dir.glob("*.json"):
        logger.info(f"Processing file: {input_file}")
        try:
            with open(input_file, "r") as f:
                extraction_data = json.load(f)
            
            tms_request = agent.process(extraction_data)
            
            output_file = output_dir / f"{input_file.stem}_tms.json"
            with open(output_file, "w") as f_out:
                json.dump(tms_request.model_dump(exclude_none=True), f_out, indent=2)
            
            logger.info(f"Output saved to: {output_file}")
        except Exception as e:
            logger.error(f"Error processing file {input_file}: {str(e)}")

if __name__ == "__main__":
    run()