"""
Cassandra integration tests using Podman containers

These tests verify end-to-end functionality of Cassandra storage and query processors
with real database instances. Compatible with Fedora Linux and Podman.

Uses a single container for all tests to minimize startup time.
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock

from .cassandra_test_helper import cassandra_container
from trustgraph.direct.cassandra_kg import KnowledgeGraph
from trustgraph.storage.triples.cassandra.write import Processor as StorageProcessor
from trustgraph.query.triples.cassandra.service import Processor as QueryProcessor
from trustgraph.schema import Triple, Term, Metadata, Triples, TriplesQueryRequest, IRI, LITERAL


@pytest.mark.integration
@pytest.mark.slow
class TestCassandraIntegration:
    """Integration tests for Cassandra using a single shared container"""

    @pytest.fixture(scope="class")
    def cassandra_shared_container(self):
        """Class-level fixture: single Cassandra container for all tests"""
        with cassandra_container() as container:
            yield container
    
    def setup_method(self):
        """Track all created clients for cleanup"""
        self.clients_to_close = []
    
    def teardown_method(self):
        """Clean up all Cassandra connections"""
        import gc
        
        for client in self.clients_to_close:
            try:
                client.close()
            except Exception:
                pass  # Ignore errors during cleanup
        
        # Clear the list and force garbage collection
        self.clients_to_close.clear()
        gc.collect()
        
        # Small delay to let threads finish
        time.sleep(0.5)

    @pytest.mark.asyncio
    async def test_complete_cassandra_integration(self, cassandra_shared_container):
        """Complete integration test covering all Cassandra functionality"""
        container = cassandra_shared_container
        host, port = container.get_connection_host_port()
        
        print("=" * 60)
        print("RUNNING COMPLETE CASSANDRA INTEGRATION TEST")
        print("=" * 60)
        
        # =====================================================
        # Test 1: Basic KnowledgeGraph Operations
        # =====================================================
        print("\n1. Testing basic KnowledgeGraph operations...")

        client = KnowledgeGraph(
            hosts=[host],
            keyspace="test_basic"
        )
        self.clients_to_close.append(client)
        
        # Insert test data
        collection = "test_collection"
        client.insert(collection, "http://example.org/alice", "knows", "http://example.org/bob")
        client.insert(collection, "http://example.org/alice", "age", "25")
        client.insert(collection, "http://example.org/bob", "age", "30")

        # Test get_all
        all_results = list(client.get_all(collection, limit=10))
        assert len(all_results) == 3
        print(f"✓ Stored and retrieved {len(all_results)} triples")
        
        # Test get_s (subject query)
        alice_results = list(client.get_s(collection, "http://example.org/alice", limit=10))
        assert len(alice_results) == 2
        alice_predicates = [r.p for r in alice_results]
        assert "knows" in alice_predicates
        assert "age" in alice_predicates
        print("✓ Subject queries working")
        
        # Test get_p (predicate query)
        age_results = list(client.get_p("age", limit=10))
        assert len(age_results) == 2
        age_subjects = [r.s for r in age_results]
        assert "http://example.org/alice" in age_subjects
        assert "http://example.org/bob" in age_subjects
        print("✓ Predicate queries working")
        
        # =====================================================
        # Test 2: Storage Processor Integration
        # =====================================================
        print("\n2. Testing storage processor integration...")
        
        storage_processor = StorageProcessor(
            taskgroup=MagicMock(),
            hosts=[host],
            keyspace="test_storage",
            table="test_triples"
        )
        # Track the KnowledgeGraph instance that will be created
        self.storage_processor = storage_processor
        
        # Create test message
        storage_message = Triples(
            metadata=Metadata(user="testuser", collection="testcol"),
            triples=[
                Triple(
                    s=Term(type=IRI, iri="http://example.org/person1"),
                    p=Term(type=IRI, iri="http://example.org/name"),
                    o=Term(type=LITERAL, value="Alice Smith")
                ),
                Triple(
                    s=Term(type=IRI, iri="http://example.org/person1"),
                    p=Term(type=IRI, iri="http://example.org/age"),
                    o=Term(type=LITERAL, value="25")
                ),
                Triple(
                    s=Term(type=IRI, iri="http://example.org/person1"),
                    p=Term(type=IRI, iri="http://example.org/department"),
                    o=Term(type=LITERAL, value="Engineering")
                )
            ]
        )
        
        # Store triples via processor
        await storage_processor.store_triples(storage_message)
        # Track the created TrustGraph instance
        if hasattr(storage_processor, 'tg'):
            self.clients_to_close.append(storage_processor.tg)
        
        # Verify data was stored
        storage_results = list(storage_processor.tg.get_s("http://example.org/person1", limit=10))
        assert len(storage_results) == 3
        
        predicates = [row.p for row in storage_results]
        objects = [row.o for row in storage_results]
        
        assert "http://example.org/name" in predicates
        assert "http://example.org/age" in predicates
        assert "http://example.org/department" in predicates
        assert "Alice Smith" in objects
        assert "25" in objects
        assert "Engineering" in objects
        print("✓ Storage processor working")
        
        # =====================================================
        # Test 3: Query Processor Integration
        # =====================================================
        print("\n3. Testing query processor integration...")
        
        query_processor = QueryProcessor(
            taskgroup=MagicMock(),
            hosts=[host],
            keyspace="test_query",
            table="test_triples"
        )
        
        # Use same storage processor for the query keyspace
        query_storage_processor = StorageProcessor(
            taskgroup=MagicMock(),
            hosts=[host],
            keyspace="test_query",
            table="test_triples"
        )
        
        # Store test data for querying
        query_test_message = Triples(
            metadata=Metadata(user="testuser", collection="testcol"),
            triples=[
                Triple(
                    s=Term(type=IRI, iri="http://example.org/alice"),
                    p=Term(type=IRI, iri="http://example.org/knows"),
                    o=Term(type=IRI, iri="http://example.org/bob")
                ),
                Triple(
                    s=Term(type=IRI, iri="http://example.org/alice"),
                    p=Term(type=IRI, iri="http://example.org/age"),
                    o=Term(type=LITERAL, value="30")
                ),
                Triple(
                    s=Term(type=IRI, iri="http://example.org/bob"),
                    p=Term(type=IRI, iri="http://example.org/knows"),
                    o=Term(type=IRI, iri="http://example.org/charlie")
                )
            ]
        )
        await query_storage_processor.store_triples(query_test_message)
        
        # Debug: Check what was actually stored
        print("Debug: Checking what was stored for Alice...")
        direct_results = list(query_storage_processor.tg.get_s("http://example.org/alice", limit=10))
        print(f"Direct KnowledgeGraph results: {len(direct_results)}")
        for result in direct_results:
            print(f"  S=http://example.org/alice, P={result.p}, O={result.o}")
        
        # Test S query (find all relationships for Alice)
        s_query = TriplesQueryRequest(
            s=Term(type=IRI, iri="http://example.org/alice"),
            p=None,  # None for wildcard
            o=None,  # None for wildcard
            limit=10,
            user="testuser",
            collection="testcol"
        )
        s_results = await query_processor.query_triples(s_query)
        print(f"Query processor results: {len(s_results)}")
        for result in s_results:
            print(f"  S={result.s.iri}, P={result.p.iri}, O={result.o.iri if result.o.type == IRI else result.o.value}")
        assert len(s_results) == 2

        s_predicates = [t.p.iri for t in s_results]
        assert "http://example.org/knows" in s_predicates
        assert "http://example.org/age" in s_predicates
        print("✓ Subject queries via processor working")

        # Test P query (find all "knows" relationships)
        p_query = TriplesQueryRequest(
            s=None,  # None for wildcard
            p=Term(type=IRI, iri="http://example.org/knows"),
            o=None,  # None for wildcard
            limit=10,
            user="testuser",
            collection="testcol"
        )
        p_results = await query_processor.query_triples(p_query)
        print(p_results)
        assert len(p_results) == 2  # Alice knows Bob, Bob knows Charlie

        p_subjects = [t.s.iri for t in p_results]
        assert "http://example.org/alice" in p_subjects
        assert "http://example.org/bob" in p_subjects
        print("✓ Predicate queries via processor working")
        
        # =====================================================
        # Test 4: Concurrent Operations
        # =====================================================
        print("\n4. Testing concurrent operations...")
        
        concurrent_processor = StorageProcessor(
            taskgroup=MagicMock(),
            hosts=[host],
            keyspace="test_concurrent",
            table="test_triples"
        )
        
        # Create multiple coroutines for concurrent storage
        async def store_person_data(person_id, name, age, department):
            message = Triples(
                metadata=Metadata(user="concurrent_test", collection="people"),
                triples=[
                    Triple(
                        s=Term(type=IRI, iri=f"http://example.org/{person_id}"),
                        p=Term(type=IRI, iri="http://example.org/name"),
                        o=Term(type=LITERAL, value=name)
                    ),
                    Triple(
                        s=Term(type=IRI, iri=f"http://example.org/{person_id}"),
                        p=Term(type=IRI, iri="http://example.org/age"),
                        o=Term(type=LITERAL, value=str(age))
                    ),
                    Triple(
                        s=Term(type=IRI, iri=f"http://example.org/{person_id}"),
                        p=Term(type=IRI, iri="http://example.org/department"),
                        o=Term(type=LITERAL, value=department)
                    )
                ]
            )
            await concurrent_processor.store_triples(message)
        
        # Store data for multiple people concurrently
        people_data = [
            ("person1", "John Doe", 25, "Engineering"),
            ("person2", "Jane Smith", 30, "Marketing"),
            ("person3", "Bob Wilson", 35, "Engineering"),
            ("person4", "Alice Brown", 28, "Sales"),
        ]
        
        # Run storage operations concurrently
        store_tasks = [store_person_data(pid, name, age, dept) for pid, name, age, dept in people_data]
        await asyncio.gather(*store_tasks)
        # Track the created TrustGraph instance
        if hasattr(concurrent_processor, 'tg'):
            self.clients_to_close.append(concurrent_processor.tg)
        
        # Verify all names were stored
        name_results = list(concurrent_processor.tg.get_p("http://example.org/name", limit=10))
        assert len(name_results) == 4
        
        stored_names = [r.o for r in name_results]
        expected_names = ["John Doe", "Jane Smith", "Bob Wilson", "Alice Brown"]
        
        for name in expected_names:
            assert name in stored_names
        
        # Verify department data
        dept_results = list(concurrent_processor.tg.get_p("http://example.org/department", limit=10))
        assert len(dept_results) == 4
        
        stored_depts = [r.o for r in dept_results]
        assert "Engineering" in stored_depts
        assert "Marketing" in stored_depts
        assert "Sales" in stored_depts
        print("✓ Concurrent operations working")
        
        # =====================================================
        # Test 5: Complex Queries and Data Integrity
        # =====================================================
        print("\n5. Testing complex queries and data integrity...")
        
        complex_processor = StorageProcessor(
            taskgroup=MagicMock(),
            hosts=[host],
            keyspace="test_complex",
            table="test_triples"
        )
        
        # Create a knowledge graph about a company
        company_graph = Triples(
            metadata=Metadata(user="integration_test", collection="company"),
            triples=[
                # People and their types
                Triple(
                    s=Term(type=IRI, iri="http://company.org/alice"),
                    p=Term(type=IRI, iri="http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                    o=Term(type=IRI, iri="http://company.org/Employee")
                ),
                Triple(
                    s=Term(type=IRI, iri="http://company.org/bob"),
                    p=Term(type=IRI, iri="http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                    o=Term(type=IRI, iri="http://company.org/Employee")
                ),
                # Relationships
                Triple(
                    s=Term(type=IRI, iri="http://company.org/alice"),
                    p=Term(type=IRI, iri="http://company.org/reportsTo"),
                    o=Term(type=IRI, iri="http://company.org/bob")
                ),
                Triple(
                    s=Term(type=IRI, iri="http://company.org/alice"),
                    p=Term(type=IRI, iri="http://company.org/worksIn"),
                    o=Term(type=IRI, iri="http://company.org/engineering")
                ),
                # Personal info
                Triple(
                    s=Term(type=IRI, iri="http://company.org/alice"),
                    p=Term(type=IRI, iri="http://company.org/fullName"),
                    o=Term(type=LITERAL, value="Alice Johnson")
                ),
                Triple(
                    s=Term(type=IRI, iri="http://company.org/alice"),
                    p=Term(type=IRI, iri="http://company.org/email"),
                    o=Term(type=LITERAL, value="alice@company.org")
                ),
            ]
        )
        
        # Store the company knowledge graph
        await complex_processor.store_triples(company_graph)
        # Track the created TrustGraph instance
        if hasattr(complex_processor, 'tg'):
            self.clients_to_close.append(complex_processor.tg)
        
        # Verify all Alice's data
        alice_data = list(complex_processor.tg.get_s("http://company.org/alice", limit=20))
        assert len(alice_data) == 5
        
        alice_predicates = [r.p for r in alice_data]
        expected_predicates = [
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://company.org/reportsTo",
            "http://company.org/worksIn",
            "http://company.org/fullName",
            "http://company.org/email"
        ]
        for pred in expected_predicates:
            assert pred in alice_predicates
        
        # Test type-based queries
        employee_results = list(complex_processor.tg.get_p("http://www.w3.org/1999/02/22-rdf-syntax-ns#type", limit=10))
        print(employee_results)
        assert len(employee_results) == 2
        
        employees = [r.s for r in employee_results]
        assert "http://company.org/alice" in employees
        assert "http://company.org/bob" in employees
        print("✓ Complex queries and data integrity working")
        
        # =====================================================
        # Summary
        # =====================================================
        print("\n" + "=" * 60)
        print("✅ ALL CASSANDRA INTEGRATION TESTS PASSED!")
        print("✅ Basic operations: PASSED")
        print("✅ Storage processor: PASSED") 
        print("✅ Query processor: PASSED")
        print("✅ Concurrent operations: PASSED")
        print("✅ Complex queries: PASSED")
        print("=" * 60)
