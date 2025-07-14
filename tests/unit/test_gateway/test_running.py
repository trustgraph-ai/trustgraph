"""
Tests for Gateway Running utility class
"""

import pytest

from trustgraph.gateway.running import Running


class TestRunning:
    """Test cases for Running class"""

    def test_running_initialization(self):
        """Test Running class initialization"""
        running = Running()
        
        # Should start with running = True
        assert running.running is True

    def test_running_get_method(self):
        """Test Running.get() method returns current state"""
        running = Running()
        
        # Should return True initially
        assert running.get() is True
        
        # Should return False after stopping
        running.stop()
        assert running.get() is False

    def test_running_stop_method(self):
        """Test Running.stop() method sets running to False"""
        running = Running()
        
        # Initially should be True
        assert running.running is True
        
        # After calling stop(), should be False
        running.stop()
        assert running.running is False

    def test_running_stop_is_idempotent(self):
        """Test that calling stop() multiple times is safe"""
        running = Running()
        
        # Stop multiple times
        running.stop()
        assert running.running is False
        
        running.stop()
        assert running.running is False
        
        # get() should still return False
        assert running.get() is False

    def test_running_state_transitions(self):
        """Test the complete state transition from running to stopped"""
        running = Running()
        
        # Initial state: running
        assert running.get() is True
        assert running.running is True
        
        # Transition to stopped
        running.stop()
        assert running.get() is False
        assert running.running is False

    def test_running_multiple_instances_independent(self):
        """Test that multiple Running instances are independent"""
        running1 = Running()
        running2 = Running()
        
        # Both should start as running
        assert running1.get() is True
        assert running2.get() is True
        
        # Stop only one
        running1.stop()
        
        # States should be independent
        assert running1.get() is False
        assert running2.get() is True
        
        # Stop the other
        running2.stop()
        
        # Both should now be stopped
        assert running1.get() is False
        assert running2.get() is False