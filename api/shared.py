"""
Shared state for API
"""

# In-memory storage for simulations (use Redis/database in production)
simulations = {}

# WebSocket connections for each simulation
websockets = {}
