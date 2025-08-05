#!/usr/bin/env python3
"""
Direct test for improved space discovery using the same configuration as the test logs.
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"Loaded .env from {env_path}")

# Override with production values from test logs
os.environ['POLARION_BASE_URL'] = 'https://polarion-d.claas.local'
os.environ['POLARION_VERIFY_SSL'] = 'false'
os.environ['POLARION_PROJECT_ID'] = 'Python'

from polarion_api.client import PolarionClient
from polarion_api.config import PolarionConfig

def test_space_discovery():
    """Test the improved space discovery method."""
    
    config = PolarionConfig()
    
    # Check PAT
    if not config.personal_access_token or config.personal_access_token == 'your-personal-access-token-here':
        logger.error("Please set a valid POLARION_PERSONAL_ACCESS_TOKEN in .env file")
        logger.info("You can find this in your Polarion user profile under 'Personal Access Tokens'")
        return
    
    project_id = os.getenv('POLARION_PROJECT_ID', 'Python')
    
    logger.info("=" * 80)
    logger.info(f"Testing Space Discovery for Project: {project_id}")
    logger.info(f"Polarion URL: {config.base_url}")
    logger.info("=" * 80)
    
    try:
        # Create client
        client = PolarionClient(config=config)
        
        # Test the improved space discovery
        logger.info("Starting space discovery with improved method...")
        spaces = client.get_project_spaces(project_id)
        
        # Display results
        logger.info("\n" + "=" * 80)
        logger.info(f"DISCOVERED SPACES:")
        logger.info("=" * 80)
        
        if spaces:
            for i, space in enumerate(spaces, 1):
                logger.info(f"  {i:2d}. {space}")
            
            logger.info(f"\nTotal spaces found: {len(spaces)}")
            
            # Check for specific spaces
            expected_spaces = ["Product Layer", "ProductLayer", "product_layer"]
            found_expected = [s for s in expected_spaces if s in spaces]
            
            if found_expected:
                logger.info(f"\n✅ SUCCESS: Found expected space(s): {found_expected}")
            else:
                logger.warning(f"\n⚠️  WARNING: None of these spaces were found: {expected_spaces}")
                
                # Check if any space contains "product" or "layer"
                product_related = [s for s in spaces if "product" in s.lower() or "layer" in s.lower()]
                if product_related:
                    logger.info(f"    However, found related spaces: {product_related}")
        else:
            logger.warning("❌ No spaces found!")
            
    except Exception as e:
        logger.error(f"Space discovery failed: {e}", exc_info=True)
        
        # Check if it's an authentication issue
        if "401" in str(e) or "unauthorized" in str(e).lower():
            logger.info("\n💡 TIP: This looks like an authentication issue.")
            logger.info("   Please check your POLARION_PERSONAL_ACCESS_TOKEN in the .env file")
        elif "404" in str(e):
            logger.info("\n💡 TIP: Getting 404 errors. The API endpoints might not be available.")
            logger.info("   This could mean the REST API is not enabled in Polarion.")

if __name__ == "__main__":
    test_space_discovery()