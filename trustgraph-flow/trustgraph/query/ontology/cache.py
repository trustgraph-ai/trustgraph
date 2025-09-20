"""
Caching system for OntoRAG query results and computations.
Provides multiple cache backends and intelligent cache management.
"""

import logging
import time
import json
import pickle
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    access_count: int
    ttl_seconds: Optional[int] = None
    tags: List[str] = None
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds

    def touch(self):
        """Update access time and count."""
        self.accessed_at = datetime.now()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_rate: float = 0.0

    def update_hit_rate(self):
        """Update hit rate calculation."""
        total_requests = self.hits + self.misses
        self.hit_rate = self.hits / total_requests if total_requests > 0 else 0.0


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None, tags: List[str] = None):
        """Set cache entry."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete cache entry."""
        pass

    @abstractmethod
    def clear(self, tags: Optional[List[str]] = None):
        """Clear cache entries."""
        pass

    @abstractmethod
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        pass

    @abstractmethod
    def cleanup_expired(self):
        """Clean up expired entries."""
        pass


class InMemoryCache(CacheBackend):
    """In-memory cache backend."""

    def __init__(self, max_size: int = 1000, max_size_bytes: int = 100 * 1024 * 1024):
        """Initialize in-memory cache.

        Args:
            max_size: Maximum number of entries
            max_size_bytes: Maximum total size in bytes
        """
        self.max_size = max_size
        self.max_size_bytes = max_size_bytes
        self.entries: Dict[str, CacheEntry] = {}
        self.stats = CacheStats()
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        with self._lock:
            entry = self.entries.get(key)
            if entry is None:
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None

            if entry.is_expired():
                del self.entries[key]
                self.stats.misses += 1
                self.stats.evictions += 1
                self.stats.total_entries -= 1
                self.stats.total_size_bytes -= entry.size_bytes
                self.stats.update_hit_rate()
                return None

            entry.touch()
            self.stats.hits += 1
            self.stats.update_hit_rate()
            return entry

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None, tags: List[str] = None):
        """Set cache entry."""
        with self._lock:
            # Calculate size
            try:
                size_bytes = len(pickle.dumps(value))
            except Exception:
                size_bytes = len(str(value).encode('utf-8'))

            # Create entry
            now = datetime.now()
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                accessed_at=now,
                access_count=1,
                ttl_seconds=ttl_seconds,
                tags=tags or [],
                size_bytes=size_bytes
            )

            # Check if we need to evict
            self._ensure_capacity(size_bytes)

            # Store entry
            old_entry = self.entries.get(key)
            if old_entry:
                self.stats.total_size_bytes -= old_entry.size_bytes
            else:
                self.stats.total_entries += 1

            self.entries[key] = entry
            self.stats.total_size_bytes += size_bytes

    def delete(self, key: str) -> bool:
        """Delete cache entry."""
        with self._lock:
            entry = self.entries.pop(key, None)
            if entry:
                self.stats.total_entries -= 1
                self.stats.total_size_bytes -= entry.size_bytes
                self.stats.evictions += 1
                return True
            return False

    def clear(self, tags: Optional[List[str]] = None):
        """Clear cache entries."""
        with self._lock:
            if tags is None:
                # Clear all
                self.stats.evictions += len(self.entries)
                self.entries.clear()
                self.stats.total_entries = 0
                self.stats.total_size_bytes = 0
            else:
                # Clear by tags
                to_delete = []
                for key, entry in self.entries.items():
                    if any(tag in entry.tags for tag in tags):
                        to_delete.append(key)

                for key in to_delete:
                    self.delete(key)

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self.stats.hits,
                misses=self.stats.misses,
                evictions=self.stats.evictions,
                total_entries=self.stats.total_entries,
                total_size_bytes=self.stats.total_size_bytes,
                hit_rate=self.stats.hit_rate
            )

    def cleanup_expired(self):
        """Clean up expired entries."""
        with self._lock:
            to_delete = []
            for key, entry in self.entries.items():
                if entry.is_expired():
                    to_delete.append(key)

            for key in to_delete:
                self.delete(key)

    def _ensure_capacity(self, new_size_bytes: int):
        """Ensure cache has capacity for new entry."""
        # Check size limit
        if self.stats.total_size_bytes + new_size_bytes > self.max_size_bytes:
            self._evict_by_size(new_size_bytes)

        # Check count limit
        if len(self.entries) >= self.max_size:
            self._evict_by_count()

    def _evict_by_size(self, needed_bytes: int):
        """Evict entries to free up space."""
        # Sort by access time (LRU)
        sorted_entries = sorted(
            self.entries.items(),
            key=lambda x: (x[1].accessed_at, x[1].access_count)
        )

        freed_bytes = 0
        for key, entry in sorted_entries:
            if freed_bytes >= needed_bytes:
                break
            freed_bytes += entry.size_bytes
            del self.entries[key]
            self.stats.total_entries -= 1
            self.stats.total_size_bytes -= entry.size_bytes
            self.stats.evictions += 1

    def _evict_by_count(self):
        """Evict least recently used entry."""
        if not self.entries:
            return

        # Find LRU entry
        lru_key = min(
            self.entries.keys(),
            key=lambda k: (self.entries[k].accessed_at, self.entries[k].access_count)
        )
        self.delete(lru_key)


class FileCache(CacheBackend):
    """File-based cache backend."""

    def __init__(self, cache_dir: str, max_files: int = 10000):
        """Initialize file cache.

        Args:
            cache_dir: Directory to store cache files
            max_files: Maximum number of cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_files = max_files
        self.stats = CacheStats()
        self._lock = threading.RLock()

        # Load existing stats
        self._load_stats()

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        with self._lock:
            cache_file = self.cache_dir / f"{self._safe_key(key)}.cache"
            if not cache_file.exists():
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None

            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)

                if entry.is_expired():
                    cache_file.unlink()
                    self.stats.misses += 1
                    self.stats.evictions += 1
                    self.stats.total_entries -= 1
                    self.stats.update_hit_rate()
                    return None

                entry.touch()
                # Update file modification time
                cache_file.touch()

                self.stats.hits += 1
                self.stats.update_hit_rate()
                return entry

            except Exception as e:
                logger.error(f"Error reading cache file {cache_file}: {e}")
                cache_file.unlink(missing_ok=True)
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None, tags: List[str] = None):
        """Set cache entry."""
        with self._lock:
            cache_file = self.cache_dir / f"{self._safe_key(key)}.cache"

            # Create entry
            now = datetime.now()
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                accessed_at=now,
                access_count=1,
                ttl_seconds=ttl_seconds,
                tags=tags or []
            )

            try:
                # Ensure capacity
                self._ensure_capacity()

                # Write to file
                with open(cache_file, 'wb') as f:
                    pickle.dump(entry, f)

                entry.size_bytes = cache_file.stat().st_size

                if not cache_file.exists():
                    self.stats.total_entries += 1

                self.stats.total_size_bytes += entry.size_bytes
                self._save_stats()

            except Exception as e:
                logger.error(f"Error writing cache file {cache_file}: {e}")

    def delete(self, key: str) -> bool:
        """Delete cache entry."""
        with self._lock:
            cache_file = self.cache_dir / f"{self._safe_key(key)}.cache"
            if cache_file.exists():
                size = cache_file.stat().st_size
                cache_file.unlink()
                self.stats.total_entries -= 1
                self.stats.total_size_bytes -= size
                self.stats.evictions += 1
                self._save_stats()
                return True
            return False

    def clear(self, tags: Optional[List[str]] = None):
        """Clear cache entries."""
        with self._lock:
            if tags is None:
                # Clear all
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
                self.stats.evictions += self.stats.total_entries
                self.stats.total_entries = 0
                self.stats.total_size_bytes = 0
            else:
                # Clear by tags
                for cache_file in self.cache_dir.glob("*.cache"):
                    try:
                        with open(cache_file, 'rb') as f:
                            entry = pickle.load(f)
                        if any(tag in entry.tags for tag in tags):
                            size = cache_file.stat().st_size
                            cache_file.unlink()
                            self.stats.total_entries -= 1
                            self.stats.total_size_bytes -= size
                            self.stats.evictions += 1
                    except Exception:
                        continue

            self._save_stats()

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self.stats.hits,
                misses=self.stats.misses,
                evictions=self.stats.evictions,
                total_entries=self.stats.total_entries,
                total_size_bytes=self.stats.total_size_bytes,
                hit_rate=self.stats.hit_rate
            )

    def cleanup_expired(self):
        """Clean up expired entries."""
        with self._lock:
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        entry = pickle.load(f)
                    if entry.is_expired():
                        size = cache_file.stat().st_size
                        cache_file.unlink()
                        self.stats.total_entries -= 1
                        self.stats.total_size_bytes -= size
                        self.stats.evictions += 1
                except Exception:
                    # Remove corrupted files
                    cache_file.unlink()

            self._save_stats()

    def _safe_key(self, key: str) -> str:
        """Convert key to safe filename."""
        import hashlib
        return hashlib.md5(key.encode()).hexdigest()

    def _ensure_capacity(self):
        """Ensure cache has capacity for new entry."""
        cache_files = list(self.cache_dir.glob("*.cache"))
        if len(cache_files) >= self.max_files:
            # Remove oldest file
            oldest_file = min(cache_files, key=lambda f: f.stat().st_mtime)
            size = oldest_file.stat().st_size
            oldest_file.unlink()
            self.stats.total_entries -= 1
            self.stats.total_size_bytes -= size
            self.stats.evictions += 1

    def _load_stats(self):
        """Load statistics from file."""
        stats_file = self.cache_dir / "stats.json"
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    data = json.load(f)
                self.stats = CacheStats(**data)
            except Exception:
                pass

    def _save_stats(self):
        """Save statistics to file."""
        stats_file = self.cache_dir / "stats.json"
        try:
            with open(stats_file, 'w') as f:
                json.dump(asdict(self.stats), f, default=str)
        except Exception:
            pass


class CacheManager:
    """Cache manager with multiple backends and intelligent caching strategies."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize cache manager.

        Args:
            config: Cache configuration
        """
        self.config = config
        self.backends: Dict[str, CacheBackend] = {}
        self.default_backend = config.get('default_backend', 'memory')
        self.default_ttl = config.get('default_ttl_seconds', 3600)  # 1 hour

        # Initialize backends
        self._init_backends()

        # Start cleanup task
        self.cleanup_interval = config.get('cleanup_interval_seconds', 300)  # 5 minutes
        self._start_cleanup_task()

    def _init_backends(self):
        """Initialize cache backends."""
        backends_config = self.config.get('backends', {})

        # Memory backend
        if 'memory' in backends_config or self.default_backend == 'memory':
            memory_config = backends_config.get('memory', {})
            self.backends['memory'] = InMemoryCache(
                max_size=memory_config.get('max_size', 1000),
                max_size_bytes=memory_config.get('max_size_bytes', 100 * 1024 * 1024)
            )

        # File backend
        if 'file' in backends_config or self.default_backend == 'file':
            file_config = backends_config.get('file', {})
            self.backends['file'] = FileCache(
                cache_dir=file_config.get('cache_dir', './cache'),
                max_files=file_config.get('max_files', 10000)
            )

    def get(self, key: str, backend: Optional[str] = None) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key
            backend: Backend name (optional)

        Returns:
            Cached value or None
        """
        backend_name = backend or self.default_backend
        cache_backend = self.backends.get(backend_name)

        if cache_backend is None:
            logger.warning(f"Cache backend '{backend_name}' not found")
            return None

        entry = cache_backend.get(key)
        return entry.value if entry else None

    def set(self,
           key: str,
           value: Any,
           ttl_seconds: Optional[int] = None,
           tags: Optional[List[str]] = None,
           backend: Optional[str] = None):
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
            tags: Cache tags
            backend: Backend name (optional)
        """
        backend_name = backend or self.default_backend
        cache_backend = self.backends.get(backend_name)

        if cache_backend is None:
            logger.warning(f"Cache backend '{backend_name}' not found")
            return

        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        cache_backend.set(key, value, ttl, tags)

    def delete(self, key: str, backend: Optional[str] = None) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key
            backend: Backend name (optional)

        Returns:
            True if deleted
        """
        backend_name = backend or self.default_backend
        cache_backend = self.backends.get(backend_name)

        if cache_backend is None:
            return False

        return cache_backend.delete(key)

    def clear(self, tags: Optional[List[str]] = None, backend: Optional[str] = None):
        """Clear cache entries.

        Args:
            tags: Tags to clear (optional)
            backend: Backend name (optional)
        """
        if backend:
            cache_backend = self.backends.get(backend)
            if cache_backend:
                cache_backend.clear(tags)
        else:
            # Clear all backends
            for cache_backend in self.backends.values():
                cache_backend.clear(tags)

    def get_stats(self) -> Dict[str, CacheStats]:
        """Get statistics for all backends.

        Returns:
            Dictionary of backend name to statistics
        """
        return {name: backend.get_stats() for name, backend in self.backends.items()}

    def cleanup_expired(self):
        """Clean up expired entries in all backends."""
        for backend in self.backends.values():
            try:
                backend.cleanup_expired()
            except Exception as e:
                logger.error(f"Error cleaning up cache backend: {e}")

    def _start_cleanup_task(self):
        """Start periodic cleanup task."""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(self.cleanup_interval)
                    self.cleanup_expired()
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")

        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()


# Cache decorators and utilities

def cache_result(cache_manager: CacheManager,
                key_func: Optional[callable] = None,
                ttl_seconds: Optional[int] = None,
                tags: Optional[List[str]] = None,
                backend: Optional[str] = None):
    """Decorator to cache function results.

    Args:
        cache_manager: Cache manager instance
        key_func: Function to generate cache key
        ttl_seconds: Time to live
        tags: Cache tags
        backend: Backend name
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            # Try to get from cache
            cached_result = cache_manager.get(cache_key, backend)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache_manager.set(cache_key, result, ttl_seconds, tags, backend)

            return result

        return wrapper
    return decorator