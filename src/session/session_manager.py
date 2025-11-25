"""
Session management for the Marketplace Deal Scout.

This module handles persistence of agent state across executions, including
session metadata, search history, and user preferences.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class DealScoutSessionManager:
    """Manages session persistence for the Deal Scout agent.
    
    Handles loading and saving session state to file-based storage with
    graceful error handling for storage failures.
    
    Attributes:
        session_id: Unique identifier for this session
        storage_type: Type of storage backend ("file" or "s3")
        base_dir: Base directory for file-based storage
    """
    
    def __init__(
        self,
        session_id: str,
        storage_type: str = "file",
        base_dir: str = "./agent_sessions"
    ):
        """Initialize session manager.
        
        Args:
            session_id: Unique identifier for this session
            storage_type: Storage backend type ("file" or "s3")
            base_dir: Base directory for file-based storage
        """
        self.session_id = session_id
        self.storage_type = storage_type
        self.base_dir = Path(base_dir)
        
        # Create base directory if it doesn't exist
        if self.storage_type == "file":
            try:
                self.base_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create session directory {self.base_dir}: {e}")
    
    def _get_session_file_path(self) -> Path:
        """Get the file path for this session.
        
        Returns:
            Path object for the session file
        """
        return self.base_dir / f"{self.session_id}.json"
    
    def load_session(self) -> Dict[str, Any]:
        """Load previous session state from persistent storage.
        
        Attempts to restore session state from file. If loading fails,
        logs the error and returns an empty session state for in-memory operation.
        
        Returns:
            Dictionary containing session state with keys:
                - session_id: Session identifier
                - last_run: ISO format timestamp of last execution
                - search_history: List of previous searches
                - preferences: User preferences dictionary
        """
        if self.storage_type != "file":
            logger.warning(f"Unsupported storage type: {self.storage_type}")
            return self._create_empty_session()
        
        session_file = self._get_session_file_path()
        
        if not session_file.exists():
            logger.info(f"No existing session found at {session_file}")
            return self._create_empty_session()
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            logger.info(f"Successfully loaded session from {session_file}")
            return session_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse session JSON from {session_file}: {e}")
            return self._create_empty_session()
        except IOError as e:
            logger.error(f"Failed to read session file {session_file}: {e}")
            return self._create_empty_session()
        except Exception as e:
            logger.error(f"Unexpected error loading session: {e}")
            return self._create_empty_session()
    
    def save_session(self, state: Dict[str, Any]) -> bool:
        """Save current session state to persistent storage.
        
        Persists the provided session state to file storage. If saving fails,
        logs the error and continues with in-memory state only.
        
        Args:
            state: Session state dictionary to persist
            
        Returns:
            True if save was successful, False otherwise
        """
        if self.storage_type != "file":
            logger.warning(f"Unsupported storage type: {self.storage_type}")
            return False
        
        session_file = self._get_session_file_path()
        
        try:
            # Ensure directory exists
            session_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write session to file
            with open(session_file, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Successfully saved session to {session_file}")
            return True
        except IOError as e:
            logger.error(f"Failed to write session file {session_file}: {e}")
            return False
        except TypeError as e:
            logger.error(f"Failed to serialize session state to JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving session: {e}")
            return False
    
    def _create_empty_session(self) -> Dict[str, Any]:
        """Create an empty session state.
        
        Returns:
            Dictionary with empty session structure
        """
        return {
            "session_id": self.session_id,
            "last_run": None,
            "search_history": [],
            "preferences": {}
        }
    
    def update_session_timestamp(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Update the last_run timestamp in session state.
        
        Args:
            state: Session state dictionary to update
            
        Returns:
            Updated session state with current timestamp
        """
        state["last_run"] = datetime.now().isoformat()
        return state
    
    def add_search_to_history(
        self,
        state: Dict[str, Any],
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add a search to the session history.
        
        Args:
            state: Session state dictionary
            query: Search query string
            filters: Optional search filters dictionary
            
        Returns:
            Updated session state with new search in history
        """
        search_entry = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "filters": filters or {}
        }
        
        if "search_history" not in state:
            state["search_history"] = []
        
        state["search_history"].append(search_entry)
        return state
