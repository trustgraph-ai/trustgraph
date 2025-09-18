
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from ssl import SSLContext, PROTOCOL_TLSv1_2

# Global list to track clusters for cleanup
_active_clusters = []

class KnowledgeGraph:

    def __init__(
            self, hosts=None,
            keyspace="trustgraph", username=None, password=None
    ):

        if hosts is None:
            hosts = ["localhost"]

        self.keyspace = keyspace
        self.table = "triples"  # Fixed table name for unified schema
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
                collection text,
                s text,
                p text,
                o text,
                PRIMARY KEY (collection, s, p, o)
            );
        """);

        self.session.execute(f"""
            create index if not exists {self.table}_s
                ON {self.table} (s);
        """);

        self.session.execute(f"""
            create index if not exists {self.table}_p
                ON {self.table} (p);
        """);

        self.session.execute(f"""
            create index if not exists {self.table}_o
                ON {self.table} (o);
        """);

    def insert(self, collection, s, p, o):

        self.session.execute(
            f"insert into {self.table} (collection, s, p, o) values (%s, %s, %s, %s)",
            (collection, s, p, o)
        )

    def get_all(self, collection, limit=50):
        return self.session.execute(
            f"select s, p, o from {self.table} where collection = %s limit {limit}",
            (collection,)
        )

    def get_s(self, collection, s, limit=10):
        return self.session.execute(
            f"select p, o from {self.table} where collection = %s and s = %s limit {limit}",
            (collection, s)
        )

    def get_p(self, collection, p, limit=10):
        return self.session.execute(
            f"select s, o from {self.table} where collection = %s and p = %s limit {limit}",
            (collection, p)
        )

    def get_o(self, collection, o, limit=10):
        return self.session.execute(
            f"select s, p from {self.table} where collection = %s and o = %s limit {limit}",
            (collection, o)
        )

    def get_sp(self, collection, s, p, limit=10):
        return self.session.execute(
            f"select o from {self.table} where collection = %s and s = %s and p = %s limit {limit}",
            (collection, s, p)
        )

    def get_po(self, collection, p, o, limit=10):
        return self.session.execute(
            f"select s from {self.table} where collection = %s and p = %s and o = %s limit {limit} allow filtering",
            (collection, p, o)
        )

    def get_os(self, collection, o, s, limit=10):
        return self.session.execute(
            f"select p from {self.table} where collection = %s and o = %s and s = %s limit {limit} allow filtering",
            (collection, o, s)
        )

    def get_spo(self, collection, s, p, o, limit=10):
        return self.session.execute(
            f"""select s as x from {self.table} where collection = %s and s = %s and p = %s and o = %s limit {limit}""",
            (collection, s, p, o)
        )

    def delete_collection(self, collection):
        """Delete all triples for a specific collection"""
        self.session.execute(
            f"delete from {self.table} where collection = %s",
            (collection,)
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
