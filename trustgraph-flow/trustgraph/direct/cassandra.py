
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from ssl import SSLContext, PROTOCOL_TLSv1_2

# Global list to track clusters for cleanup
_active_clusters = []

class TrustGraph:

    def __init__(
            self, hosts=None,
            keyspace="trustgraph", table="default", username=None, password=None
    ):

        if hosts is None:
            hosts = ["localhost"]

        self.keyspace = keyspace
        self.table = table
        self.username = username
            
        if username and password:
            ssl_context = SSLContext(PROTOCOL_TLSv1_2)
            auth_provider = PlainTextAuthProvider(username=username, password=password)
            self.cluster = Cluster(hosts, auth_provider=auth_provider, ssl_context=ssl_context)
        else:
            self.cluster = Cluster(hosts)
        self.session = self.cluster.connect()
        
        # Track this cluster globally
        _active_clusters.append(self.cluster)

        self.init()

    def clear(self):

        self.session.execute(f"""
            drop keyspace if exists {self.keyspace};
        """);

        self.init()

    def init(self):

        self.session.execute(f"""
            create keyspace if not exists {self.keyspace}
                with replication = {{ 
                   'class' : 'SimpleStrategy', 
                   'replication_factor' : 1 
                }};
        """);

        self.session.set_keyspace(self.keyspace)

        self.session.execute(f"""
            create table if not exists {self.table} (
                s text,
                p text,
                o text,
                PRIMARY KEY (s, p, o)
            );
        """);

        self.session.execute(f"""
            create index if not exists {self.table}_p
                ON {self.table} (p);
        """);

        self.session.execute(f"""
            create index if not exists {self.table}_o
                ON {self.table} (o);
        """);

    def insert(self, s, p, o):
    
        self.session.execute(
            f"insert into {self.table} (s, p, o) values (%s, %s, %s)",
            (s, p, o)
        )

    def get_all(self, limit=50):
        return self.session.execute(
            f"select s, p, o from {self.table} limit {limit}"
        )

    def get_s(self, s, limit=10):
        return self.session.execute(
            f"select p, o from {self.table} where s = %s limit {limit}",
            (s,)
        )

    def get_p(self, p, limit=10):
        return self.session.execute(
            f"select s, o from {self.table} where p = %s limit {limit}",
            (p,)
        )

    def get_o(self, o, limit=10):
        return self.session.execute(
            f"select s, p from {self.table} where o = %s limit {limit}",
            (o,)
        )

    def get_sp(self, s, p, limit=10):
        return self.session.execute(
            f"select o from {self.table} where s = %s and p = %s limit {limit}",
            (s, p)
        )

    def get_po(self, p, o, limit=10):
        return self.session.execute(
            f"select s from {self.table} where p = %s and o = %s limit {limit} allow filtering",
            (p, o)
        )

    def get_os(self, o, s, limit=10):
        return self.session.execute(
            f"select p from {self.table} where o = %s and s = %s limit {limit}",
            (o, s)
        )

    def get_spo(self, s, p, o, limit=10):
        return self.session.execute(
            f"""select s as x from {self.table} where s = %s and p = %s and o = %s limit {limit}""",
            (s, p, o)
        )

    def close(self):
        """Close the Cassandra session and cluster connections properly"""
        if hasattr(self, 'session') and self.session:
            self.session.shutdown()
        if hasattr(self, 'cluster') and self.cluster:
            self.cluster.shutdown()
            # Remove from global tracking
            if self.cluster in _active_clusters:
                _active_clusters.remove(self.cluster)
