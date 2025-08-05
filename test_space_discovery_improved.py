#!/usr/bin/env python3
"""
Test script for improved space discovery method.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from polarion_api.client import PolarionClient
from polarion_api.config import PolarionConfig

def test_space_discovery():
    """Test the improved space discovery method."""
    
    # Get configuration from environment
    project_id = os.getenv('POLARION_PROJECT_ID', 'Python')
    
    # Check if environment is configured
    config = PolarionConfig()
    if not config.personal_access_token:
        logger.error("Missing POLARION_PERSONAL_ACCESS_TOKEN in environment")
        return
    
    logger.info(f"Testing space discovery for project: {project_id}")
    logger.info(f"Using Polarion instance: {config.base_url}")
    
    try:
        # Create client with config
        client = PolarionClient(config=config)
        
        # Discover spaces
        logger.info("Starting space discovery...")
        spaces = client.get_project_spaces(project_id)
        
        # Display results
        logger.info("=" * 80)
        logger.info(f"DISCOVERED SPACES FOR PROJECT '{project_id}':")
        logger.info("=" * 80)
        
        if spaces:
            for i, space in enumerate(spaces, 1):
                logger.info(f"  {i}. {space}")
            logger.info(f"\nTotal spaces found: {len(spaces)}")
            
            # Check if "Product Layer" was found
            product_layer_variations = [
                "Product Layer", "ProductLayer", "product_layer",
                "Product-Layer", "product-layer"
            ]
            
            found_product_layer = any(
                space in spaces for space in product_layer_variations
            )
            
            if found_product_layer:
                logger.info("✅ SUCCESS: 'Product Layer' space was found!")
            else:
                logger.warning("⚠️ WARNING: 'Product Layer' space was NOT found")
                logger.info("\nTrying direct access to 'Product Layer' space...")
                
                # Try to directly access the space
                for variation in product_layer_variations:
                    try:
                        # Try to get work items from this space
                        endpoint = f"/projects/{project_id}/spaces/{variation}"
                        logger.debug(f"Trying space variation: {variation}")
                        # This would need to be implemented in the client
                        # For now, we just log the attempt
                    except Exception as e:
                        logger.debug(f"Failed to access space '{variation}': {e}")
                        
        else:
            logger.warning("No spaces found!")
        
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Space discovery failed: {e}", exc_info=True)

if __name__ == "__main__":
    test_space_discovery()