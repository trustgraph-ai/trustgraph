"""
Helper for managing Cassandra containers in integration tests
Alternative to testcontainers for Fedora/Podman compatibility
"""

import subprocess
import time
import socket
from contextlib import contextmanager
from cassandra.cluster import Cluster
from cassandra.policies import RetryPolicy


class CassandraTestContainer:
    """Simple Cassandra container manager using Podman"""
    
    def __init__(self, image="docker.io/library/cassandra:4.1", port=9042):
        self.image = image
        self.port = port
        self.container_name = f"test-cassandra-{int(time.time())}"
        self.container_id = None
    
    def start(self):
        """Start Cassandra container"""
        # Remove any existing container with same name
        subprocess.run([
            "podman", "rm", "-f", self.container_name
        ], capture_output=True)
        
        # Start new container with faster startup options
        result = subprocess.run([
            "podman", "run", "-d", 
            "--name", self.container_name,
            "-p", f"{self.port}:9042",
            "-e", "JVM_OPTS=-Dcassandra.skip_wait_for_gossip_to_settle=0",
            self.image
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start container: {result.stderr}")
        
        self.container_id = result.stdout.strip()
        
        # Wait for Cassandra to be ready
        self._wait_for_ready()
        return self
    
    def stop(self):
        """Stop and remove container"""
        import time
        if self.container_name:
            # Small delay before stopping to ensure connections are closed
            time.sleep(0.5)
            subprocess.run([
                "podman", "rm", "-f", self.container_name
            ], capture_output=True)
    
    def get_connection_host_port(self):
        """Get host and port for connection"""
        return "localhost", self.port
    
    def _wait_for_ready(self, timeout=120):
        """Wait for Cassandra to be ready for CQL queries"""
        start_time = time.time()
        
        print(f"Waiting for Cassandra to be ready on port {self.port}...")
        
        while time.time() - start_time < timeout:
            try:
                # First check if port is open
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(("localhost", self.port))
                sock.close()
                
                if result == 0:
                    # Port is open, now try to connect with Cassandra driver
                    try:
                        cluster = Cluster(['localhost'], port=self.port)
                        cluster.connect_timeout = 5
                        session = cluster.connect()
                        
                        # Try a simple query to verify Cassandra is ready
                        session.execute("SELECT release_version FROM system.local")
                        session.shutdown()
                        cluster.shutdown()
                        
                        print("Cassandra is ready!")
                        return
                        
                    except Exception as e:
                        print(f"Cassandra not ready yet: {e}")
                        pass
                        
            except Exception as e:
                print(f"Connection check failed: {e}")
                pass
            
            time.sleep(3)
        
        raise RuntimeError(f"Cassandra not ready after {timeout} seconds")


@contextmanager
def cassandra_container(image="docker.io/library/cassandra:4.1", port=9042):
    """Context manager for Cassandra container"""
    container = CassandraTestContainer(image, port)
    try:
        container.start()
        yield container
    finally:
        container.stop()
