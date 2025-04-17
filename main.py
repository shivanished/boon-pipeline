#!/usr/bin/env python3
"""
Main entry point for the agent-based JSON transformation pipeline.
This script takes extraction JSON files and converts them to TMS JSON format.
"""

import json
import argparse
import logging
import os
import glob
from pathlib import Path
from typing import Dict, Any, List

from utils.logger import setup_logger
from agents.transformation_agent import TMSTransformationAgent
logger = logging.getLogger(__name__)

def process_json_file(input_file: str, output_file: str = None, api_key: str = None) -> Dict[str, Any]:
    """
    Process an extraction JSON file and return the TMS order entry request.
    
    Args:
        input_file: Path to the input JSON file
        output_file: Optional path to output JSON file
        api_key: Optional API key for LLM service
        
    Returns:
        The TMS order entry request as a dictionary
    """
    try:
        # Read input file
        with open(input_file, 'r') as f:
            extraction_json = json.load(f)
        
        # Create agent and process the JSON
        agent = TMSTransformationAgent(api_key=api_key)
        tms_request = agent.process(extraction_json)
        
        # Convert to dictionary
        result = tms_request.model_dump(exclude_none=True)
        
        # Write to output file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
        
        return result
    
    except Exception as e:
        logger.error(f"Error processing file {input_file}: {str(e)}")
        raise

def process_batch(input_files: List[str], output_dir: str, api_key: str = None) -> Dict[str, Any]:
    """
    Process a batch of extraction JSON files.
    
    Args:
        input_files: List of input file paths
        output_dir: Directory for output files
        api_key: Optional API key for LLM service
        
    Returns:
        Dictionary with results for each file
    """
    results = {}
    for input_file in input_files:
        try:
            output_file = f"{output_dir}/{Path(input_file).stem}_tms.json"
            result = process_json_file(input_file, output_file, api_key)
            results[input_file] = {"status": "success", "output_file": output_file}
        except Exception as e:
            results[input_file] = {"status": "error", "message": str(e)}
    
    return results

def main():
    """Main function to run the transformation pipeline."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Transform extraction JSON to TMS JSON using agents')
    parser.add_argument('--input', '-i', required=True, help='Input JSON file or directory')
    parser.add_argument('--output', '-o', help='Output JSON file or directory')
    parser.add_argument('--batch', '-b', action='store_true', help='Process a batch of files')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--api-key', help='API key for LLM service')
    parser.add_argument('--submit', '-s', action='store_true', help='Submit to TMS API after processing')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logger(log_level)
    
    # Get API key from args or environment
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    
    try:
        if args.batch:
            # Process a batch of files
            input_path = args.input
            if os.path.isdir(input_path):
                # Get all JSON files in directory
                input_files = glob.glob(f"{input_path}/*.json")
            else:
                # Treat as glob pattern
                input_files = glob.glob(input_path)
            
            if not input_files:
                logger.error(f"No input files found matching: {args.input}")
                return 1
            
            # Create output directory if needed
            output_dir = args.output or os.path.join(os.path.dirname(input_path), 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            # Process all files
            logger.info(f"Processing {len(input_files)} files in batch mode")
            results = process_batch(input_files, output_dir, api_key)
            
            # Print summary
            success_count = sum(1 for result in results.values() if result["status"] == "success")
            error_count = sum(1 for result in results.values() if result["status"] == "error")
            
            logger.info(f"Batch processing complete. Success: {success_count}, Errors: {error_count}")
            
            # Log errors if any
            for input_file, result in results.items():
                if result["status"] == "error":
                    logger.error(f"Failed to process {input_file}: {result['message']}")
            
            # Submit to TMS API if requested
            # if args.submit and success_count > 0:
            #     logger.info("Submitting successful transformations to TMS API")
            #     api_client = TmsApiClient()
            #     for input_file, result in results.items():
            #         if result["status"] == "success":
            #             try:
            #                 with open(result["output_file"], 'r') as f:
            #                     tms_request = json.load(f)
                            
            #                 response = api_client.submit_order(tms_request)
            #                 logger.info(f"API submission for {input_file}: Success")
            #             except Exception as e:
            #                 logger.error(f"API submission for {input_file} failed: {str(e)}")
        
        else:
            # Process a single file
            input_file = args.input
            if not os.path.isfile(input_file):
                logger.error(f"Input file not found: {input_file}")
                return 1
            
            # Determine output file
            output_file = args.output
            if not output_file and input_file.endswith('.json'):
                output_dir = os.path.dirname(input_file) or '.'
                output_file = f"{output_dir}/{Path(input_file).stem}_tms.json"
            
            # Process the file
            logger.info(f"Processing file: {input_file}")
            result = process_json_file(input_file, output_file, api_key)
            
            logger.info(f"Processing complete. Output written to: {output_file}")
            
            # Submit to TMS API if requested
            # if args.submit:
            #     logger.info("Submitting to TMS API")
            #     try:
            #         api_client = TmsApiClient()
            #         response = api_client.submit_order(result)
            #         logger.info("API submission successful")
            #     except Exception as e:
            #         logger.error(f"API submission failed: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())