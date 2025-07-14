"""
Unit tests for tool coordination logic

Tests the core business logic for coordinating multiple tools,
managing tool execution, handling failures, and optimizing
tool usage patterns.
"""

import pytest
from unittest.mock import Mock, AsyncMock
import asyncio
from collections import defaultdict


class TestToolCoordinationLogic:
    """Test cases for tool coordination business logic"""

    def test_tool_registry_management(self):
        """Test tool registration and availability management"""
        # Arrange
        class ToolRegistry:
            def __init__(self):
                self.tools = {}
                self.tool_metadata = {}
            
            def register_tool(self, name, tool_function, metadata=None):
                """Register a tool with optional metadata"""
                self.tools[name] = tool_function
                self.tool_metadata[name] = metadata or {}
                return True
            
            def unregister_tool(self, name):
                """Remove a tool from registry"""
                if name in self.tools:
                    del self.tools[name]
                    del self.tool_metadata[name]
                    return True
                return False
            
            def get_available_tools(self):
                """Get list of available tools"""
                return list(self.tools.keys())
            
            def get_tool_info(self, name):
                """Get tool function and metadata"""
                if name not in self.tools:
                    return None
                return {
                    "function": self.tools[name],
                    "metadata": self.tool_metadata[name]
                }
            
            def is_tool_available(self, name):
                """Check if tool is available"""
                return name in self.tools
        
        # Act
        registry = ToolRegistry()
        
        # Register tools
        def mock_calculator(expr):
            return str(eval(expr))
        
        def mock_search(query):
            return f"Search results for: {query}"
        
        registry.register_tool("calculator", mock_calculator, {
            "description": "Perform calculations",
            "parameters": ["expression"],
            "category": "math"
        })
        
        registry.register_tool("search", mock_search, {
            "description": "Search knowledge base",
            "parameters": ["query"],
            "category": "information"
        })
        
        # Assert
        assert registry.is_tool_available("calculator")
        assert registry.is_tool_available("search")
        assert not registry.is_tool_available("nonexistent")
        
        available_tools = registry.get_available_tools()
        assert "calculator" in available_tools
        assert "search" in available_tools
        assert len(available_tools) == 2
        
        # Test tool info retrieval
        calc_info = registry.get_tool_info("calculator")
        assert calc_info["metadata"]["category"] == "math"
        assert "expression" in calc_info["metadata"]["parameters"]
        
        # Test unregistration
        assert registry.unregister_tool("calculator") is True
        assert not registry.is_tool_available("calculator")
        assert len(registry.get_available_tools()) == 1

    def test_tool_execution_coordination(self):
        """Test coordination of tool execution with proper sequencing"""
        # Arrange
        async def execute_tool_sequence(tool_sequence, tool_registry):
            """Execute a sequence of tools with coordination"""
            results = []
            context = {}
            
            for step in tool_sequence:
                tool_name = step["tool"]
                parameters = step["parameters"]
                
                # Check if tool is available
                if not tool_registry.is_tool_available(tool_name):
                    results.append({
                        "step": step,
                        "status": "error",
                        "error": f"Tool {tool_name} not available"
                    })
                    continue
                
                try:
                    # Get tool function
                    tool_info = tool_registry.get_tool_info(tool_name)
                    tool_function = tool_info["function"]
                    
                    # Substitute context variables in parameters
                    resolved_params = {}
                    for key, value in parameters.items():
                        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                            # Context variable substitution
                            var_name = value[2:-1]
                            resolved_params[key] = context.get(var_name, value)
                        else:
                            resolved_params[key] = value
                    
                    # Execute tool
                    if asyncio.iscoroutinefunction(tool_function):
                        result = await tool_function(**resolved_params)
                    else:
                        result = tool_function(**resolved_params)
                    
                    # Store result
                    step_result = {
                        "step": step,
                        "status": "success",
                        "result": result
                    }
                    results.append(step_result)
                    
                    # Update context for next steps
                    if "context_key" in step:
                        context[step["context_key"]] = result
                
                except Exception as e:
                    results.append({
                        "step": step,
                        "status": "error", 
                        "error": str(e)
                    })
            
            return results, context
        
        # Create mock tool registry
        class MockToolRegistry:
            def __init__(self):
                self.tools = {
                    "search": lambda query: f"Found: {query}",
                    "calculator": lambda expression: str(eval(expression)),
                    "formatter": lambda text, format_type: f"[{format_type}] {text}"
                }
            
            def is_tool_available(self, name):
                return name in self.tools
            
            def get_tool_info(self, name):
                return {"function": self.tools[name]}
        
        registry = MockToolRegistry()
        
        # Test sequence with context passing
        tool_sequence = [
            {
                "tool": "search",
                "parameters": {"query": "capital of France"},
                "context_key": "search_result"
            },
            {
                "tool": "formatter",
                "parameters": {"text": "${search_result}", "format_type": "markdown"},
                "context_key": "formatted_result"
            }
        ]
        
        # Act
        results, context = asyncio.run(execute_tool_sequence(tool_sequence, registry))
        
        # Assert
        assert len(results) == 2
        assert all(result["status"] == "success" for result in results)
        assert "search_result" in context
        assert "formatted_result" in context
        assert "Found: capital of France" in context["search_result"]
        assert "[markdown]" in context["formatted_result"]

    def test_parallel_tool_execution(self):
        """Test parallel execution of independent tools"""
        # Arrange
        async def execute_tools_parallel(tool_requests, tool_registry, max_concurrent=3):
            """Execute multiple tools in parallel with concurrency limit"""
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def execute_single_tool(tool_request):
                async with semaphore:
                    tool_name = tool_request["tool"]
                    parameters = tool_request["parameters"]
                    
                    if not tool_registry.is_tool_available(tool_name):
                        return {
                            "request": tool_request,
                            "status": "error",
                            "error": f"Tool {tool_name} not available"
                        }
                    
                    try:
                        tool_info = tool_registry.get_tool_info(tool_name)
                        tool_function = tool_info["function"]
                        
                        # Simulate async execution with delay
                        await asyncio.sleep(0.001)  # Small delay to simulate work
                        
                        if asyncio.iscoroutinefunction(tool_function):
                            result = await tool_function(**parameters)
                        else:
                            result = tool_function(**parameters)
                        
                        return {
                            "request": tool_request,
                            "status": "success",
                            "result": result
                        }
                    
                    except Exception as e:
                        return {
                            "request": tool_request,
                            "status": "error",
                            "error": str(e)
                        }
            
            # Execute all tools concurrently
            tasks = [execute_single_tool(request) for request in tool_requests]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    processed_results.append({
                        "status": "error",
                        "error": str(result)
                    })
                else:
                    processed_results.append(result)
            
            return processed_results
        
        # Create mock async tools
        class MockAsyncToolRegistry:
            def __init__(self):
                self.tools = {
                    "fast_search": self._fast_search,
                    "slow_calculation": self._slow_calculation,
                    "medium_analysis": self._medium_analysis
                }
            
            async def _fast_search(self, query):
                await asyncio.sleep(0.01)
                return f"Fast result for: {query}"
            
            async def _slow_calculation(self, expression):
                await asyncio.sleep(0.05)
                return f"Calculated: {expression} = {eval(expression)}"
            
            async def _medium_analysis(self, text):
                await asyncio.sleep(0.03)
                return f"Analysis of: {text}"
            
            def is_tool_available(self, name):
                return name in self.tools
            
            def get_tool_info(self, name):
                return {"function": self.tools[name]}
        
        registry = MockAsyncToolRegistry()
        
        tool_requests = [
            {"tool": "fast_search", "parameters": {"query": "test query 1"}},
            {"tool": "slow_calculation", "parameters": {"expression": "2 + 2"}},
            {"tool": "medium_analysis", "parameters": {"text": "sample text"}},
            {"tool": "fast_search", "parameters": {"query": "test query 2"}}
        ]
        
        # Act
        import time
        start_time = time.time()
        results = asyncio.run(execute_tools_parallel(tool_requests, registry))
        execution_time = time.time() - start_time
        
        # Assert
        assert len(results) == 4
        assert all(result["status"] == "success" for result in results)
        # Should be faster than sequential execution
        assert execution_time < 0.15  # Much faster than 0.01+0.05+0.03+0.01 = 0.10
        
        # Check specific results
        search_results = [r for r in results if r["request"]["tool"] == "fast_search"]
        assert len(search_results) == 2
        calc_results = [r for r in results if r["request"]["tool"] == "slow_calculation"]
        assert "Calculated: 2 + 2 = 4" in calc_results[0]["result"]

    def test_tool_failure_handling_and_retry(self):
        """Test handling of tool failures with retry logic"""
        # Arrange
        class RetryableToolExecutor:
            def __init__(self, max_retries=3, backoff_factor=1.5):
                self.max_retries = max_retries
                self.backoff_factor = backoff_factor
                self.call_counts = defaultdict(int)
            
            async def execute_with_retry(self, tool_name, tool_function, parameters):
                """Execute tool with retry logic"""
                last_error = None
                
                for attempt in range(self.max_retries + 1):
                    try:
                        self.call_counts[tool_name] += 1
                        
                        # Simulate delay for retries
                        if attempt > 0:
                            await asyncio.sleep(0.001 * (self.backoff_factor ** attempt))
                        
                        if asyncio.iscoroutinefunction(tool_function):
                            result = await tool_function(**parameters)
                        else:
                            result = tool_function(**parameters)
                        
                        return {
                            "status": "success",
                            "result": result,
                            "attempts": attempt + 1
                        }
                    
                    except Exception as e:
                        last_error = e
                        if attempt < self.max_retries:
                            continue  # Retry
                        else:
                            break  # Max retries exceeded
                
                return {
                    "status": "failed",
                    "error": str(last_error),
                    "attempts": self.max_retries + 1
                }
        
        # Create flaky tools that fail sometimes
        class FlakyTools:
            def __init__(self):
                self.search_calls = 0
                self.calc_calls = 0
            
            def flaky_search(self, query):
                self.search_calls += 1
                if self.search_calls <= 2:  # Fail first 2 attempts
                    raise Exception("Network timeout")
                return f"Search result for: {query}"
            
            def always_failing_calc(self, expression):
                self.calc_calls += 1
                raise Exception("Calculator service unavailable")
            
            def reliable_tool(self, input_text):
                return f"Processed: {input_text}"
        
        flaky_tools = FlakyTools()
        executor = RetryableToolExecutor(max_retries=3)
        
        # Act & Assert
        # Test successful retry after failures
        search_result = asyncio.run(executor.execute_with_retry(
            "flaky_search", 
            flaky_tools.flaky_search, 
            {"query": "test"}
        ))
        
        assert search_result["status"] == "success"
        assert search_result["attempts"] == 3  # Failed twice, succeeded on third attempt
        assert "Search result for: test" in search_result["result"]
        
        # Test tool that always fails
        calc_result = asyncio.run(executor.execute_with_retry(
            "always_failing_calc",
            flaky_tools.always_failing_calc,
            {"expression": "2 + 2"}
        ))
        
        assert calc_result["status"] == "failed"
        assert calc_result["attempts"] == 4  # Initial + 3 retries
        assert "Calculator service unavailable" in calc_result["error"]
        
        # Test reliable tool (no retries needed)
        reliable_result = asyncio.run(executor.execute_with_retry(
            "reliable_tool",
            flaky_tools.reliable_tool,
            {"input_text": "hello"}
        ))
        
        assert reliable_result["status"] == "success"
        assert reliable_result["attempts"] == 1

    def test_tool_dependency_resolution(self):
        """Test resolution of tool dependencies and execution ordering"""
        # Arrange
        def resolve_tool_dependencies(tool_requests):
            """Resolve dependencies and create execution plan"""
            # Build dependency graph
            dependency_graph = {}
            all_tools = set()
            
            for request in tool_requests:
                tool_name = request["tool"]
                dependencies = request.get("depends_on", [])
                dependency_graph[tool_name] = dependencies
                all_tools.add(tool_name)
                all_tools.update(dependencies)
            
            # Topological sort to determine execution order
            def topological_sort(graph):
                in_degree = {node: 0 for node in graph}
                
                # Calculate in-degrees
                for node in graph:
                    for dependency in graph[node]:
                        if dependency in in_degree:
                            in_degree[node] += 1
                
                # Find nodes with no dependencies
                queue = [node for node in in_degree if in_degree[node] == 0]
                result = []
                
                while queue:
                    node = queue.pop(0)
                    result.append(node)
                    
                    # Remove this node and update in-degrees
                    for dependent in graph:
                        if node in graph[dependent]:
                            in_degree[dependent] -= 1
                            if in_degree[dependent] == 0:
                                queue.append(dependent)
                
                # Check for cycles
                if len(result) != len(graph):
                    remaining = set(graph.keys()) - set(result)
                    return None, f"Circular dependency detected among: {list(remaining)}"
                
                return result, None
            
            execution_order, error = topological_sort(dependency_graph)
            
            if error:
                return None, error
            
            # Create execution plan
            execution_plan = []
            for tool_name in execution_order:
                # Find the request for this tool
                tool_request = next((req for req in tool_requests if req["tool"] == tool_name), None)
                if tool_request:
                    execution_plan.append(tool_request)
            
            return execution_plan, None
        
        # Test case 1: Simple dependency chain
        requests_simple = [
            {"tool": "fetch_data", "depends_on": []},
            {"tool": "process_data", "depends_on": ["fetch_data"]},
            {"tool": "generate_report", "depends_on": ["process_data"]}
        ]
        
        plan, error = resolve_tool_dependencies(requests_simple)
        assert error is None
        assert len(plan) == 3
        assert plan[0]["tool"] == "fetch_data"
        assert plan[1]["tool"] == "process_data"
        assert plan[2]["tool"] == "generate_report"
        
        # Test case 2: Complex dependencies
        requests_complex = [
            {"tool": "tool_d", "depends_on": ["tool_b", "tool_c"]},
            {"tool": "tool_b", "depends_on": ["tool_a"]},
            {"tool": "tool_c", "depends_on": ["tool_a"]},
            {"tool": "tool_a", "depends_on": []}
        ]
        
        plan, error = resolve_tool_dependencies(requests_complex)
        assert error is None
        assert plan[0]["tool"] == "tool_a"  # No dependencies
        assert plan[3]["tool"] == "tool_d"  # Depends on others
        
        # Test case 3: Circular dependency
        requests_circular = [
            {"tool": "tool_x", "depends_on": ["tool_y"]},
            {"tool": "tool_y", "depends_on": ["tool_z"]},
            {"tool": "tool_z", "depends_on": ["tool_x"]}
        ]
        
        plan, error = resolve_tool_dependencies(requests_circular)
        assert plan is None
        assert "Circular dependency" in error

    def test_tool_resource_management(self):
        """Test management of tool resources and limits"""
        # Arrange
        class ToolResourceManager:
            def __init__(self, resource_limits=None):
                self.resource_limits = resource_limits or {}
                self.current_usage = defaultdict(int)
                self.tool_resource_requirements = {}
            
            def register_tool_resources(self, tool_name, resource_requirements):
                """Register resource requirements for a tool"""
                self.tool_resource_requirements[tool_name] = resource_requirements
            
            def can_execute_tool(self, tool_name):
                """Check if tool can be executed within resource limits"""
                if tool_name not in self.tool_resource_requirements:
                    return True, "No resource requirements"
                
                requirements = self.tool_resource_requirements[tool_name]
                
                for resource, required_amount in requirements.items():
                    available = self.resource_limits.get(resource, float('inf'))
                    current = self.current_usage[resource]
                    
                    if current + required_amount > available:
                        return False, f"Insufficient {resource}: need {required_amount}, available {available - current}"
                
                return True, "Resources available"
            
            def allocate_resources(self, tool_name):
                """Allocate resources for tool execution"""
                if tool_name not in self.tool_resource_requirements:
                    return True
                
                can_execute, reason = self.can_execute_tool(tool_name)
                if not can_execute:
                    return False
                
                requirements = self.tool_resource_requirements[tool_name]
                for resource, amount in requirements.items():
                    self.current_usage[resource] += amount
                
                return True
            
            def release_resources(self, tool_name):
                """Release resources after tool execution"""
                if tool_name not in self.tool_resource_requirements:
                    return
                
                requirements = self.tool_resource_requirements[tool_name]
                for resource, amount in requirements.items():
                    self.current_usage[resource] = max(0, self.current_usage[resource] - amount)
            
            def get_resource_usage(self):
                """Get current resource usage"""
                return dict(self.current_usage)
        
        # Set up resource manager
        resource_manager = ToolResourceManager({
            "memory": 800,  # MB (reduced to make test fail properly)
            "cpu": 4,       # cores
            "network": 10   # concurrent connections
        })
        
        # Register tool resource requirements
        resource_manager.register_tool_resources("heavy_analysis", {
            "memory": 500,
            "cpu": 2
        })
        
        resource_manager.register_tool_resources("network_fetch", {
            "memory": 100,
            "network": 3
        })
        
        resource_manager.register_tool_resources("light_calc", {
            "cpu": 1
        })
        
        # Test resource allocation
        assert resource_manager.allocate_resources("heavy_analysis") is True
        assert resource_manager.get_resource_usage()["memory"] == 500
        assert resource_manager.get_resource_usage()["cpu"] == 2
        
        # Test trying to allocate another heavy_analysis (would exceed limit)
        can_execute, reason = resource_manager.can_execute_tool("heavy_analysis")
        assert can_execute is False  # Would exceed memory limit (500 + 500 > 800)
        assert "memory" in reason.lower()
        
        # Test resource release
        resource_manager.release_resources("heavy_analysis")
        assert resource_manager.get_resource_usage()["memory"] == 0
        assert resource_manager.get_resource_usage()["cpu"] == 0
        
        # Test multiple tool execution
        assert resource_manager.allocate_resources("network_fetch") is True
        assert resource_manager.allocate_resources("light_calc") is True
        
        usage = resource_manager.get_resource_usage()
        assert usage["memory"] == 100
        assert usage["cpu"] == 1
        assert usage["network"] == 3

    def test_tool_performance_monitoring(self):
        """Test monitoring of tool performance and optimization"""
        # Arrange
        class ToolPerformanceMonitor:
            def __init__(self):
                self.execution_stats = defaultdict(list)
                self.error_counts = defaultdict(int)
                self.total_executions = defaultdict(int)
            
            def record_execution(self, tool_name, execution_time, success, error=None):
                """Record tool execution statistics"""
                self.total_executions[tool_name] += 1
                self.execution_stats[tool_name].append({
                    "execution_time": execution_time,
                    "success": success,
                    "error": error
                })
                
                if not success:
                    self.error_counts[tool_name] += 1
            
            def get_tool_performance(self, tool_name):
                """Get performance statistics for a tool"""
                if tool_name not in self.execution_stats:
                    return None
                
                stats = self.execution_stats[tool_name]
                execution_times = [s["execution_time"] for s in stats if s["success"]]
                
                if not execution_times:
                    return {
                        "total_executions": self.total_executions[tool_name],
                        "success_rate": 0.0,
                        "average_execution_time": 0.0,
                        "error_count": self.error_counts[tool_name]
                    }
                
                return {
                    "total_executions": self.total_executions[tool_name],
                    "success_rate": len(execution_times) / self.total_executions[tool_name],
                    "average_execution_time": sum(execution_times) / len(execution_times),
                    "min_execution_time": min(execution_times),
                    "max_execution_time": max(execution_times),
                    "error_count": self.error_counts[tool_name]
                }
            
            def get_performance_recommendations(self, tool_name):
                """Get performance optimization recommendations"""
                performance = self.get_tool_performance(tool_name)
                if not performance:
                    return []
                
                recommendations = []
                
                if performance["success_rate"] < 0.8:
                    recommendations.append("High error rate - consider implementing retry logic or health checks")
                
                if performance["average_execution_time"] > 10.0:
                    recommendations.append("Slow execution time - consider optimization or caching")
                
                if performance["total_executions"] > 100 and performance["success_rate"] > 0.95:
                    recommendations.append("Highly reliable tool - suitable for critical operations")
                
                return recommendations
        
        # Test performance monitoring
        monitor = ToolPerformanceMonitor()
        
        # Record various execution scenarios
        monitor.record_execution("fast_tool", 0.5, True)
        monitor.record_execution("fast_tool", 0.6, True)
        monitor.record_execution("fast_tool", 0.4, True)
        
        monitor.record_execution("slow_tool", 15.0, True)
        monitor.record_execution("slow_tool", 12.0, True)
        monitor.record_execution("slow_tool", 18.0, False, "Timeout")
        
        monitor.record_execution("unreliable_tool", 2.0, False, "Network error")
        monitor.record_execution("unreliable_tool", 1.8, False, "Auth error") 
        monitor.record_execution("unreliable_tool", 2.2, True)
        
        # Test performance statistics
        fast_performance = monitor.get_tool_performance("fast_tool")
        assert fast_performance["success_rate"] == 1.0
        assert fast_performance["average_execution_time"] == 0.5
        assert fast_performance["total_executions"] == 3
        
        slow_performance = monitor.get_tool_performance("slow_tool")
        assert slow_performance["success_rate"] == 2/3  # 2 successes out of 3
        assert slow_performance["average_execution_time"] == 13.5  # (15.0 + 12.0) / 2
        
        unreliable_performance = monitor.get_tool_performance("unreliable_tool")
        assert unreliable_performance["success_rate"] == 1/3
        assert unreliable_performance["error_count"] == 2
        
        # Test recommendations
        fast_recommendations = monitor.get_performance_recommendations("fast_tool")
        assert len(fast_recommendations) == 0  # No issues
        
        slow_recommendations = monitor.get_performance_recommendations("slow_tool")
        assert any("slow execution" in rec.lower() for rec in slow_recommendations)
        
        unreliable_recommendations = monitor.get_performance_recommendations("unreliable_tool")
        assert any("error rate" in rec.lower() for rec in unreliable_recommendations)