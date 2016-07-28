"""
    A wrapper class to provide management to the localhost server.
"""

from repronim.orchestrator import Orchestrator

class LocalhostOrchestrator(Orchestrator):

    def start_server(self):
        return

    def get_target_host(self):
        return '127.0.0.1'