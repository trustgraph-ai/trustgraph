
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

class TrustGraph:

    def __init__(self, hosts=None):

        if hosts is None:
            hosts = ["localhost"]
            
        self.cluster = Cluster(hosts)
        self.session = self.cluster.connect()

        self.init()

    def clear(self):

        self.session.execute("""
            drop keyspace if exists trustgraph;
        """);

        self.init()

    def init(self):

        self.session.execute("""
            create keyspace if not exists trustgraph
                with replication = { 
                   'class' : 'SimpleStrategy', 
                   'replication_factor' : 1 
                };
        """);

        self.session.set_keyspace('trustgraph')

        self.session.execute("""
            create table if not exists triples (
                s text,
                p text,
                o text,
                PRIMARY KEY (s, p)
            );
        """);

        self.session.execute("""
            create index if not exists triples_p
                ON triples (p);
        """);

        self.session.execute("""
            create index if not exists triples_o
                ON triples (o);
        """);

    def insert(self, s, p, o):
    
        self.session.execute(
            "insert into triples (s, p, o) values (%s, %s, %s)",
            (s, p, o)
        )

    def get_all(self, limit=50):
        return self.session.execute(
            f"select s, p, o from triples limit {limit}"
        )

    def get_s(self, s, limit=10):
        return self.session.execute(
            f"select p, o from triples where s = %s",
            (s,)
        )

    def get_p(self, p, limit=10):
        return self.session.execute(
            f"select s, o from triples where p = %s limit {limit}",
            (p,)
        )

    def get_o(self, o, limit=10):
        return self.session.execute(
            f"select s, p from triples where o = %s limit {limit}",
            (o,)
        )

    def get_sp(self, s, p, limit=10):
        return self.session.execute(
            f"select o from triples where s = %s and p = %s limit {limit}",
            (s, p)
        )

    def get_po(self, p, o, limit=10):
        return self.session.execute(
            f"select s from triples where p = %s and o = %s allow filtering limit {limit}",
            (p, o)
        )

    def get_os(self, o, s, limit=10):
        return self.session.execute(
            f"select s from triples where o = %s and s = %s limit {limit}",
            (o, s)
        )

    def get_spo(self, s, p, o, limit=10):
        return self.session.execute(
            f"""select s as x from triples where s = %s and p = %s and o = %s limit {limit}""",
            (s, p, o)
        )
