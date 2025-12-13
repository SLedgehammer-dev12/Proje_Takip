"""
Update checker utility.

Handles checking for updates from remote GitHub repository.
"""

import json
import logging
import urllib.request
import webbrowser
from typing import Tuple, Optional, Dict, Any
from packaging import version

from natural_gas_g5.config.settings import config


class UpdateChecker:
    """Checks for application updates."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_version = config.APP_VERSION
        self.update_url = config.UPDATE_CHECK_URL
    
    def check_for_updates(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if a new version is available.
        
        Returns:
            Tuple of (is_update_available, update_info_dict)
        """
        try:
            self.logger.info(f"Checking for updates from: {self.update_url}")
            
            # Fetch version file with short timeout
            with urllib.request.urlopen(self.update_url, timeout=5) as response:
                if response.status != 200:
                    self.logger.warning(f"Update check failed with status: {response.status}")
                    return False, None
                
                data = json.loads(response.read().decode('utf-8'))
                
                remote_version = data.get('version')
                if not remote_version:
                    return False, None
                
                # Compare versions using packaging.version
                if version.parse(remote_version) > version.parse(self.current_version):
                    self.logger.info(f"New version found: {remote_version} (Current: {self.current_version})")
                    return True, data
                
                self.logger.info("Application is up to date")
                return False, None
                
        except urllib.error.URLError as e:
            self.logger.warning(f"Network error checking updates: {e}")
            return False, None
        except Exception as e:
            self.logger.error(f"Update check failed: {e}", exc_info=True)
            return False, None

    def open_download_page(self, url: str = None):
        """Open the download/repo page in browser."""
        target_url = url or config.REPO_URL
        webbrowser.open(target_url)
