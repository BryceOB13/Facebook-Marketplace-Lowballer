"""
Property-based tests for session manager.

These tests verify universal properties that should hold across all valid
executions of session persistence operations.
"""

import pytest
import json
import tempfile
from pathlib import Path
from hypothesis import given, settings, strategies as st
from datetime import datetime
from src.session.session_manager import DealScoutSessionManager


# Strategy for generating session IDs (excluding path separators and special chars)
session_ids = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-',
    min_size=5,
    max_size=50
)

# Strategy for generating search queries
search_queries = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P')),
    min_size=1,
    max_size=100
)

# Strategy for generating price values
prices = st.integers(min_value=1, max_value=100000)

# Strategy for generating search filters
search_filters = st.builds(
    lambda min_p, max_p: {
        "min_price": min_p,
        "max_price": max_p
    },
    min_p=st.one_of(st.none(), prices),
    max_p=st.one_of(st.none(), prices)
)

# Strategy for generating session state
session_states = st.builds(
    lambda session_id, last_run, search_history, preferences: {
        "session_id": session_id,
        "last_run": last_run,
        "search_history": search_history,
        "preferences": preferences
    },
    session_id=session_ids,
    last_run=st.one_of(st.none(), st.datetimes().map(lambda dt: dt.isoformat())),
    search_history=st.lists(
        st.builds(
            lambda q, ts, f: {
                "query": q,
                "timestamp": ts,
                "filters": f
            },
            q=search_queries,
            ts=st.datetimes().map(lambda dt: dt.isoformat()),
            f=search_filters
        ),
        max_size=10
    ),
    preferences=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(st.integers(), st.text(), st.booleans()),
        max_size=5
    )
)


class TestSessionPersistenceRoundTrip:
    """Tests for Property 20: Session persistence round-trip."""
    
    @given(state=session_states)
    @settings(max_examples=100)
    def test_session_persistence_round_trip(self, state):
        """
        **Feature: marketplace-deal-scout, Property 20: Session persistence round-trip**
        
        For any session state saved to storage, loading the session should 
        restore the same state.
        
        **Validates: Requirements 5.1, 5.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create session manager with temporary directory
            manager = DealScoutSessionManager(
                session_id=state["session_id"],
                storage_type="file",
                base_dir=tmpdir
            )
            
            # Save the session state
            save_success = manager.save_session(state)
            assert save_success, "Session save should succeed"
            
            # Load the session state back
            loaded_state = manager.load_session()
            
            # Verify all fields match
            assert loaded_state["session_id"] == state["session_id"]
            assert loaded_state["last_run"] == state["last_run"]
            assert loaded_state["search_history"] == state["search_history"]
            assert loaded_state["preferences"] == state["preferences"]


class TestFileStorageLocation:
    """Tests for Property 21: File storage location."""
    
    @given(session_id=session_ids)
    @settings(max_examples=100)
    def test_file_storage_location(self, session_id):
        """
        **Feature: marketplace-deal-scout, Property 21: File storage location**
        
        For any file-based session with configured base_dir, the session file 
        should be created within that directory.
        
        **Validates: Requirements 5.3**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            
            # Create session manager
            manager = DealScoutSessionManager(
                session_id=session_id,
                storage_type="file",
                base_dir=str(base_dir)
            )
            
            # Create a simple session state
            state = {
                "session_id": session_id,
                "last_run": datetime.now().isoformat(),
                "search_history": [],
                "preferences": {}
            }
            
            # Save the session
            save_success = manager.save_session(state)
            assert save_success, "Session save should succeed"
            
            # Verify the file exists in the correct location
            expected_file = base_dir / f"{session_id}.json"
            assert expected_file.exists(), f"Session file should exist at {expected_file}"
            
            # Verify the file is within the base directory
            assert expected_file.parent == base_dir, \
                "Session file should be directly in base_dir"
            
            # Verify the file contains valid JSON
            with open(expected_file, 'r') as f:
                loaded_data = json.load(f)
            assert loaded_data["session_id"] == session_id


class TestGracefulStorageFailure:
    """Tests for Property 22: Graceful storage failure."""
    
    @given(state=session_states)
    @settings(max_examples=100)
    def test_graceful_storage_failure(self, state):
        """
        **Feature: marketplace-deal-scout, Property 22: Graceful storage failure**
        
        For any session storage failure, the system should continue execution 
        with in-memory state and log the error.
        
        **Validates: Requirements 5.4**
        """
        # Create session manager with invalid directory path (read-only or non-existent parent)
        # We'll use a path that cannot be created
        invalid_base_dir = "/root/invalid_path_that_cannot_be_created_12345"
        
        manager = DealScoutSessionManager(
            session_id=state["session_id"],
            storage_type="file",
            base_dir=invalid_base_dir
        )
        
        # Attempt to save should fail gracefully
        save_success = manager.save_session(state)
        assert save_success is False, "Save should return False on failure"
        
        # Loading should return empty session (graceful degradation)
        loaded_state = manager.load_session()
        assert loaded_state is not None, "Load should return a state even on failure"
        assert isinstance(loaded_state, dict), "Loaded state should be a dictionary"
        assert "session_id" in loaded_state, "Loaded state should have session_id"
    
    @given(session_id=session_ids)
    @settings(max_examples=100)
    def test_load_nonexistent_session_graceful(self, session_id):
        """
        Test that loading a non-existent session returns empty state gracefully.
        
        For any session that doesn't exist, loading should return an empty session
        state without raising exceptions.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DealScoutSessionManager(
                session_id=session_id,
                storage_type="file",
                base_dir=tmpdir
            )
            
            # Load without saving first
            loaded_state = manager.load_session()
            
            # Should return empty session structure
            assert loaded_state is not None
            assert loaded_state["session_id"] == session_id
            assert loaded_state["last_run"] is None
            assert loaded_state["search_history"] == []
            assert loaded_state["preferences"] == {}
    
    @given(session_id=session_ids)
    @settings(max_examples=100)
    def test_load_corrupted_json_graceful(self, session_id):
        """
        Test that loading corrupted JSON returns empty state gracefully.
        
        For any corrupted session file, loading should return an empty session
        state without raising exceptions.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            
            # Create a corrupted JSON file
            session_file = base_dir / f"{session_id}.json"
            # Ensure parent directory exists
            session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(session_file, 'w') as f:
                f.write("{ invalid json content }")
            
            manager = DealScoutSessionManager(
                session_id=session_id,
                storage_type="file",
                base_dir=str(base_dir)
            )
            
            # Load should handle corruption gracefully
            loaded_state = manager.load_session()
            
            # Should return empty session structure
            assert loaded_state is not None
            assert loaded_state["session_id"] == session_id
            assert loaded_state["last_run"] is None
            assert loaded_state["search_history"] == []
            assert loaded_state["preferences"] == {}


class TestSessionOperations:
    """Additional tests for session operations."""
    
    @given(state=session_states, query=search_queries)
    @settings(max_examples=50)
    def test_add_search_to_history(self, state, query):
        """
        Test that searches can be added to session history.
        
        For any session state and search query, adding to history should
        preserve existing history and add new entry.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DealScoutSessionManager(
                session_id=state["session_id"],
                storage_type="file",
                base_dir=tmpdir
            )
            
            initial_history_length = len(state.get("search_history", []))
            
            # Add search to history
            updated_state = manager.add_search_to_history(state, query)
            
            # Verify history grew by one
            assert len(updated_state["search_history"]) == initial_history_length + 1
            
            # Verify new entry has correct query
            new_entry = updated_state["search_history"][-1]
            assert new_entry["query"] == query
            assert "timestamp" in new_entry
            assert "filters" in new_entry
    
    @given(state=session_states)
    @settings(max_examples=50)
    def test_update_session_timestamp(self, state):
        """
        Test that session timestamp is updated correctly.
        
        For any session state, updating timestamp should set last_run to current time.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = DealScoutSessionManager(
                session_id=state["session_id"],
                storage_type="file",
                base_dir=tmpdir
            )
            
            # Update timestamp
            updated_state = manager.update_session_timestamp(state)
            
            # Verify timestamp was set
            assert updated_state["last_run"] is not None
            
            # Verify it's a valid ISO format datetime string
            try:
                datetime.fromisoformat(updated_state["last_run"])
            except ValueError:
                pytest.fail(f"Invalid ISO format timestamp: {updated_state['last_run']}")
