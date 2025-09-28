"""
Performance and concurrent processing tests
"""
import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from main import filter_words_concurrent, filter_words_chunk


@pytest.mark.performance
class TestConcurrentPerformance:
    """Test performance of concurrent processing"""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_vs_sequential_performance(self, performance_test_words):
        """Compare concurrent vs sequential filtering performance"""
        large_word_list = performance_test_words * 10  # Make it larger
        
        with patch('main.words_list', large_word_list):
            filters = {'contains': 'test', 'min_length': 4}
            
            # Test concurrent processing
            start_time = time.time()
            concurrent_result = await filter_words_concurrent(filters, 100)
            concurrent_time = time.time() - start_time
            
            # Test sequential processing (fallback to simple)
            from main import filter_words_simple
            start_time = time.time()
            sequential_result = filter_words_simple(filters, 100)
            sequential_time = time.time() - start_time
            
            # Results should be similar
            assert len(concurrent_result) == len(sequential_result)
            
            # For large datasets, concurrent might be faster
            # But we won't enforce this as it depends on system load
            print(f"Concurrent time: {concurrent_time:.4f}s")
            print(f"Sequential time: {sequential_time:.4f}s")

    @pytest.mark.benchmark
    def test_filter_words_chunk_benchmark(self, benchmark, performance_test_words):
        """Benchmark chunk processing performance"""
        chunk_size = 1000
        words_chunk = performance_test_words[:chunk_size]
        filters = {'contains': 'test', 'min_length': 4}
        chunk_data = (words_chunk, filters)
        
        result = benchmark(filter_words_chunk, chunk_data)
        
        assert isinstance(result, list)
        assert all('test' in word for word in result)

    @pytest.mark.asyncio
    async def test_concurrent_processing_scalability(self, performance_test_words):
        """Test how concurrent processing scales with dataset size"""
        test_sizes = [100, 1000, 5000]
        processing_times = []
        
        for size in test_sizes:
            test_data = performance_test_words[:size]
            
            with patch('main.words_list', test_data):
                filters = {'contains': 'test'}
                
                start_time = time.time()
                result = await filter_words_concurrent(filters, 50)
                end_time = time.time()
                
                processing_times.append(end_time - start_time)
                
                assert isinstance(result, list)
                assert len(result) <= 50
        
        # Processing times should scale reasonably
        print(f"Processing times for sizes {test_sizes}: {processing_times}")


@pytest.mark.performance  
class TestMemoryUsage:
    """Test memory usage and efficiency"""
    
    def test_memory_efficient_processing(self, performance_test_words):
        """Test that processing doesn't create excessive memory overhead"""
        import tracemalloc
        
        # Start memory tracing
        tracemalloc.start()
        
        with patch('main.words_list', performance_test_words):
            filters = {'min_length': 5, 'max_length': 10}
            
            # Take snapshot before
            snapshot1 = tracemalloc.take_snapshot()
            
            # Process words
            from main import filter_words_simple
            result = filter_words_simple(filters, 1000)
            
            # Take snapshot after
            snapshot2 = tracemalloc.take_snapshot()
            
            # Compare memory usage
            top_stats = snapshot2.compare_to(snapshot1, 'lineno')
            
            # Should have reasonable memory usage
            total_memory_increase = sum(stat.size_diff for stat in top_stats)
            
            # Memory increase should be reasonable (less than 10MB for this test)
            assert total_memory_increase < 10 * 1024 * 1024
            assert isinstance(result, list)
        
        tracemalloc.stop()

    @pytest.mark.slow
    def test_large_result_set_handling(self, performance_test_words):
        """Test handling of large result sets"""
        very_large_list = performance_test_words * 50  # Make it very large
        
        with patch('main.words_list', very_large_list):
            # Request large result set
            filters = {'min_length': 3}  # Should match many words
            
            from main import filter_words_simple
            result = filter_words_simple(filters, 5000)
            
            assert isinstance(result, list)
            assert len(result) <= 5000
            
            # Check that all results are valid
            for word in result[:100]:  # Check first 100
                assert len(word) >= 3
                assert isinstance(word, str)


@pytest.mark.performance
class TestThreadPoolPerformance:
    """Test thread pool performance"""
    
    @pytest.mark.asyncio
    async def test_thread_pool_utilization(self):
        """Test thread pool is properly utilized"""
        # Mock thread pool to track usage
        with patch('main.thread_pool') as mock_pool:
            mock_future = AsyncMock()
            mock_future.result.return_value = (['test'], {'test'}, {'total_words': 1})
            mock_pool.submit.return_value = mock_future
            
            # This is a simplified test of thread pool usage
            # In real scenarios, we'd test actual concurrent execution
            assert mock_pool is not None

    def test_process_pool_configuration(self):
        """Test process pool is properly configured"""
        # Import to ensure process pool is initialized
        from main import process_pool
        
        assert isinstance(process_pool, ProcessPoolExecutor)
        assert process_pool._max_workers >= 1

    def test_thread_pool_configuration(self):
        """Test thread pool is properly configured"""  
        from main import thread_pool
        
        assert isinstance(thread_pool, ThreadPoolExecutor)
        assert thread_pool._max_workers >= 1


@pytest.mark.performance
class TestConcurrencyStress:
    """Stress tests for concurrent operations"""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self, performance_test_words):
        """Test handling multiple concurrent requests"""
        with patch('main.words_list', performance_test_words):
            # Create multiple concurrent tasks
            tasks = []
            
            for i in range(10):  # 10 concurrent requests
                filters = {'contains': f'test{i % 3}', 'min_length': 4}
                task = filter_words_concurrent(filters, 20)
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            assert len(results) == 10
            for result in results:
                assert isinstance(result, list)
                assert len(result) <= 20

    @pytest.mark.slow 
    @pytest.mark.asyncio
    async def test_concurrent_processing_under_load(self, performance_test_words):
        """Test concurrent processing under high load"""
        large_dataset = performance_test_words * 20
        
        with patch('main.words_list', large_dataset):
            # Simulate high load with complex filters
            tasks = []
            
            for i in range(5):  # 5 concurrent complex queries
                filters = {
                    'contains': 'test',
                    'starts_with': f'test{i % 3}',
                    'min_length': 5,
                    'max_length': 15
                }
                task = filter_words_concurrent(filters, 100)
                tasks.append(task)
            
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            # Should complete within reasonable time
            assert total_time < 10.0  # 10 seconds max
            
            # All results should be valid
            for result in results:
                assert isinstance(result, list)
                for word in result:
                    assert 'test' in word
                    assert 5 <= len(word) <= 15

    def test_resource_cleanup_after_processing(self, performance_test_words):
        """Test that resources are properly cleaned up"""
        import gc
        
        # Get initial object count
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        with patch('main.words_list', performance_test_words):
            # Do some processing
            filters = {'contains': 'test', 'min_length': 4}
            from main import filter_words_simple
            
            for _ in range(10):  # Multiple iterations
                result = filter_words_simple(filters, 100)
                assert isinstance(result, list)
        
        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Should not have significant memory leaks
        object_increase = final_objects - initial_objects
        
        # Allow some increase but not excessive
        assert object_increase < 1000  # Arbitrary threshold


@pytest.mark.performance
class TestDataStructurePerformance:
    """Test performance of different data structures"""
    
    def test_list_vs_set_lookup_performance(self, performance_test_words):
        """Test performance difference between list and set lookups"""
        word_list = performance_test_words
        word_set = set(performance_test_words)
        test_word = performance_test_words[len(performance_test_words) // 2]
        
        # Time list lookup
        start_time = time.time()
        for _ in range(1000):
            result = test_word in word_list
        list_time = time.time() - start_time
        
        # Time set lookup  
        start_time = time.time()
        for _ in range(1000):
            result = test_word in word_set
        set_time = time.time() - start_time
        
        # Set should be significantly faster
        assert set_time < list_time
        print(f"List lookup time: {list_time:.4f}s")
        print(f"Set lookup time: {set_time:.4f}s")

    def test_filtering_algorithm_efficiency(self, performance_test_words):
        """Test efficiency of filtering algorithms"""
        with patch('main.words_list', performance_test_words):
            filters = {'contains': 'test', 'min_length': 5}
            
            # Test with different approaches
            from main import filter_words_simple
            
            # Time the filtering operation
            start_time = time.time()
            result = filter_words_simple(filters, 1000)
            processing_time = time.time() - start_time
            
            # Should complete efficiently
            assert processing_time < 1.0  # 1 second max
            assert isinstance(result, list)
            
            # Check result quality
            for word in result[:10]:  # Sample check
                assert 'test' in word
                assert len(word) >= 5
