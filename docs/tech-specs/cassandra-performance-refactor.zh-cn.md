# 技术规范：Cassandra 知识库性能重构

**状态：** 草稿
**作者：** 助理
**日期：** 2025-09-18

## 概述

本规范解决了 TrustGraph Cassandra 知识库实现中的性能问题，并提出了针对 RDF 三元组存储和查询的优化方案。

## 当前实现

### 模式设计

当前实现使用单表设计，位于 `trustgraph-flow/trustgraph/direct/cassandra_kg.py`：

```sql
CREATE TABLE triples (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```

**次级索引：**
`triples_s` ON `s` (主语)
`triples_p` ON `p` (谓语)
`triples_o` ON `o` (宾语)

### 查询模式

当前实现支持 8 种不同的查询模式：

1. **get_all(collection, limit=50)** - 检索集合中的所有三元组
   ```sql
   SELECT s, p, o FROM triples WHERE collection = ? LIMIT 50
   ```

2. **get_s(collection, s, limit=10)** - 通过主题进行查询
   ```sql
   SELECT p, o FROM triples WHERE collection = ? AND s = ? LIMIT 10
   ```

3. **get_p(collection, p, limit=10)** - 通过谓词进行查询
   ```sql
   SELECT s, o FROM triples WHERE collection = ? AND p = ? LIMIT 10
   ```

4. **get_o(collection, o, limit=10)** - 通过对象查询
   ```sql
   SELECT s, p FROM triples WHERE collection = ? AND o = ? LIMIT 10
   ```

5. **get_sp(collection, s, p, limit=10)** - 通过主语 + 谓语进行查询。
   ```sql
   SELECT o FROM triples WHERE collection = ? AND s = ? AND p = ? LIMIT 10
   ```

6. **get_po(collection, p, o, limit=10)** - 通过谓词 + 对象进行查询 ⚠️
   ```sql
   SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
   ```

7. **get_os(collection, o, s, limit=10)** - 通过对象 + 主题进行查询 ⚠️
   ```sql
   SELECT p FROM triples WHERE collection = ? AND o = ? AND s = ? LIMIT 10 ALLOW FILTERING
   ```

8. **get_spo(collection, s, p, o, limit=10)** - 精确三元组匹配
   ```sql
   SELECT s as x FROM triples WHERE collection = ? AND s = ? AND p = ? AND o = ? LIMIT 10
   ```

### 当前架构

**文件: `trustgraph-flow/trustgraph/direct/cassandra_kg.py`**
单个 `KnowledgeGraph` 类处理所有操作
通过全局 `_active_clusters` 列表进行连接池管理
固定的表名: `"triples"`
每个用户模型的 keyspace
复制策略为 SimpleStrategy，因子为 1

**集成点:**
**写入路径:** `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
**查询路径:** `trustgraph-flow/trustgraph/query/triples/cassandra/service.py`
**知识存储:** `trustgraph-flow/trustgraph/tables/knowledge.py`

## 识别出的性能问题

### 模式层级问题

1. **低效的主键设计**
   当前: `PRIMARY KEY (collection, s, p, o)`
   导致常见访问模式下的聚类效果不佳
   强制使用昂贵的二级索引

2. **过度使用二级索引** ⚠️
   在高基数列（s, p, o）上使用了三个二级索引
   Cassandra 中的二级索引很昂贵，并且扩展性较差
   查询 6 和 7 需要 `ALLOW FILTERING`，表明数据建模存在问题

3. **分区热点风险**
   单个分区键 `collection` 可能会创建分区热点
   大型集合会集中在单个节点上
   没有用于负载均衡的分布策略

### 查询层级问题

1. **ALLOW FILTERING 的使用** ⚠️
   两种查询类型（get_po, get_os）需要 `ALLOW FILTERING`
   这些查询会扫描多个分区，并且非常昂贵
   性能会随着数据量的增加而线性下降

2. **低效的访问模式**
   没有针对常见的 RDF 查询模式进行优化
   缺少用于频繁查询组合的复合索引
   没有考虑图遍历模式

3. **缺乏查询优化**
   没有预处理语句缓存
   没有查询提示或优化策略
   没有考虑简单的 LIMIT 之外的分页

## 问题陈述

当前的 Cassandra 知识库实现存在两个关键的性能瓶颈：

### 1. get_po 查询性能低效

`get_po(collection, p, o)` 查询非常低效，因为它需要 `ALLOW FILTERING`:

```sql
SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
```

**问题所在：**
`ALLOW FILTERING` 迫使 Cassandra 扫描集合中的所有分区。
性能会随着数据量的线性增长而下降。
这是一个常见的 RDF 查询模式（查找具有特定谓词-对象关系的实体）。
随着数据增长，这会在集群上产生显著的负载。

### 2. 聚类策略不佳

当前主键 `PRIMARY KEY (collection, s, p, o)` 提供的聚类优势有限：

**当前聚类的存在问题：**
将 `collection` 作为分区键，无法有效分布数据。
大多数集合包含各种数据，这使得聚类无效。
未考虑 RDF 查询中的常见访问模式。
大型集合会在单个节点上创建热点分区。
聚类列 (s, p, o) 未针对典型的图遍历模式进行优化。

**影响：**
查询无法受益于数据局部性。
缓存利用率低下。
集群节点上的负载分布不均匀。
随着集合的增长，会出现可扩展性瓶颈。

## 建议的解决方案：4 表反规范化策略

### 概述

用四个专门设计的表替换单个 `triples` 表，每个表针对特定的查询模式进行了优化。 这消除了对辅助索引和 ALLOW FILTERING 的需求，同时为所有类型的查询提供最佳性能。 第四个表实现了在复合分区键下高效地删除集合的功能。

### 新的模式设计

**表 1：以实体为中心的查询 (triples_s)**
```sql
CREATE TABLE triples_s (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY ((collection, s), p, o)
);
```
**优化：** get_s, get_sp, get_os
**分区键：** (collection, s) - 比仅使用 collection 的分区方式分布更好
**聚类：** (p, o) - 允许对主语进行高效的谓词/对象查找

**表 2：谓词-对象查询 (triples_p)**
```sql
CREATE TABLE triples_p (
    collection text,
    p text,
    o text,
    s text,
    PRIMARY KEY ((collection, p), o, s)
);
```
**优化：** get_p, get_po (消除 ALLOW FILTERING!)
**分区键：** (collection, p) - 通过谓词直接访问
**聚类：** (o, s) - 高效的对象-主体遍历

**表 3：面向对象的查询 (triples_o)**
```sql
CREATE TABLE triples_o (
    collection text,
    o text,
    s text,
    p text,
    PRIMARY KEY ((collection, o), s, p)
);
```
**优化：** get_o
**分区键：** (collection, o) - 通过对象直接访问
**聚类：** (s, p) - 高效的主体-谓语遍历

**表 4：集合管理与 SPO 查询 (triples_collection)**
```sql
CREATE TABLE triples_collection (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```
**优化：** get_spo, delete_collection
**分区键：** 仅限集合 - 启用高效的集合级别操作
**聚类：** (s, p, o) - 标准三元组排序
**目的：** 既用于精确的SPO查找，也用作删除索引

### 查询映射

| 原始查询 | 目标表 | 性能提升 |
|----------------|-------------|------------------------|
| get_all(collection) | triples_s | 允许过滤 (对于扫描是可以接受的) |
| get_s(collection, s) | triples_s | 直接分区访问 |
| get_p(collection, p) | triples_p | 直接分区访问 |
| get_o(collection, o) | triples_o | 直接分区访问 |
| get_sp(collection, s, p) | triples_s | 分区 + 聚类 |
| get_po(collection, p, o) | triples_p | **不再需要 ALLOW FILTERING!** |
| get_os(collection, o, s) | triples_o | 分区 + 聚类 |
| get_spo(collection, s, p, o) | triples_collection | 精确键查找 |
| delete_collection(collection) | triples_collection | 读取索引，批量删除所有 |

### 集合删除策略

对于复合分区键，我们不能简单地执行 `DELETE FROM table WHERE collection = ?`。 而是：

1. **读取阶段：** 查询 `triples_collection` 以枚举所有三元组：
   ```sql
   SELECT s, p, o FROM triples_collection WHERE collection = ?
   ```
   这很高效，因为 `collection` 是此表的分割键。

2. **删除阶段：** 对于每个三元组 (s, p, o)，使用完整的分割键从所有 4 个表中删除数据。
   ```sql
   DELETE FROM triples_s WHERE collection = ? AND s = ? AND p = ? AND o = ?
   DELETE FROM triples_p WHERE collection = ? AND p = ? AND o = ? AND s = ?
   DELETE FROM triples_o WHERE collection = ? AND o = ? AND s = ? AND p = ?
   DELETE FROM triples_collection WHERE collection = ? AND s = ? AND p = ? AND o = ?
   ```
   批量处理，每次100个，以提高效率。

**权衡分析：**
✅ 保持最佳查询性能，采用分布式分区。
✅ 大型集合不会出现热点分区。
❌ 删除逻辑更复杂（先读取，再删除）。
❌ 删除时间与集合大小成正比。

### 优点

1. **消除 ALLOW FILTERING** - 每个查询都有最佳访问路径（除了全表扫描）。
2. **无需二级索引** - 每个表本身就是其查询模式的索引。
3. **更好的数据分布** - 组合分区键能有效分散负载。
4. **可预测的性能** - 查询时间与结果大小成正比，而不是总数据量。
5. **利用 Cassandra 的优势** - 专为 Cassandra 的架构设计。
6. **支持集合删除** - `triples_collection` 作为删除索引。

## 实施计划

### 需要修改的文件

#### 主要实施文件

**`trustgraph-flow/trustgraph/direct/cassandra_kg.py`** - 需要完全重写。

**需要重构的现有方法：**
```python
# Schema initialization
def init(self) -> None  # Replace single table with three tables

# Insert operations
def insert(self, collection, s, p, o) -> None  # Write to all three tables

# Query operations (API unchanged, implementation optimized)
def get_all(self, collection, limit=50)      # Use triples_by_subject
def get_s(self, collection, s, limit=10)     # Use triples_by_subject
def get_p(self, collection, p, limit=10)     # Use triples_by_po
def get_o(self, collection, o, limit=10)     # Use triples_by_object
def get_sp(self, collection, s, p, limit=10) # Use triples_by_subject
def get_po(self, collection, p, o, limit=10) # Use triples_by_po (NO ALLOW FILTERING!)
def get_os(self, collection, o, s, limit=10) # Use triples_by_subject
def get_spo(self, collection, s, p, o, limit=10) # Use triples_by_subject

# Collection management
def delete_collection(self, collection) -> None  # Delete from all three tables
```

#### 集成文件 (无需修改任何逻辑)

**`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`**
无需修改 - 使用现有的知识图谱 API
自动受益于性能改进

**`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`**
无需修改 - 使用现有的知识图谱 API
自动受益于性能改进

### 需要更新的测试文件

#### 单元测试
**`tests/unit/test_storage/test_triples_cassandra_storage.py`**
更新测试预期，以适应模式更改
添加多表一致性测试
验证查询计划中是否包含 ALLOW FILTERING

**`tests/unit/test_query/test_triples_cassandra_query.py`**
更新性能断言
对所有 8 种查询模式进行针对新表的测试
验证查询是否路由到正确的表

#### 集成测试
**`tests/integration/test_cassandra_integration.py`**
使用新模式进行端到端测试
性能基准测试比较
跨表的数据一致性验证

**`tests/unit/test_storage/test_cassandra_config_integration.py`**
更新模式验证测试
测试迁移场景

### 实施策略

#### 第一阶段：模式和核心方法
1. **重写 `init()` 方法** - 创建四个表而不是一个
2. **重写 `insert()` 方法** - 批量写入所有四个表
3. **实现预处理语句** - 以获得最佳性能
4. **添加表路由逻辑** - 将查询定向到最佳表
5. **实现集合删除** - 从 triples_collection 中读取，批量删除所有表中的数据

#### 第二阶段：查询方法优化
1. **重写每个 get_* 方法** 以使用最佳表
2. **删除所有 ALLOW FILTERING 的用法**
3. **实现高效的聚类键使用**
4. **添加查询性能日志记录**

#### 第三阶段：集合管理
1. **更新 `delete_collection()`** - 从所有三个表中删除
2. **添加一致性验证** - 确保所有表保持同步
3. **实现批量操作** - 用于原子级多表操作

### 关键实施细节

#### 批量写入策略
```python
def insert(self, collection, s, p, o):
    batch = BatchStatement()

    # Insert into all four tables
    batch.add(self.insert_subject_stmt, (collection, s, p, o))
    batch.add(self.insert_po_stmt, (collection, p, o, s))
    batch.add(self.insert_object_stmt, (collection, o, s, p))
    batch.add(self.insert_collection_stmt, (collection, s, p, o))

    self.session.execute(batch)
```

#### 查询路由逻辑
```python
def get_po(self, collection, p, o, limit=10):
    # Route to triples_p table - NO ALLOW FILTERING!
    return self.session.execute(
        self.get_po_stmt,
        (collection, p, o, limit)
    )

def get_spo(self, collection, s, p, o, limit=10):
    # Route to triples_collection table for exact SPO lookup
    return self.session.execute(
        self.get_spo_stmt,
        (collection, s, p, o, limit)
    )
```

#### 集合删除逻辑
```python
def delete_collection(self, collection):
    # Step 1: Read all triples from collection table
    rows = self.session.execute(
        f"SELECT s, p, o FROM {self.collection_table} WHERE collection = %s",
        (collection,)
    )

    # Step 2: Batch delete from all 4 tables
    batch = BatchStatement()
    count = 0

    for row in rows:
        s, p, o = row.s, row.p, row.o

        # Delete using full partition keys for each table
        batch.add(SimpleStatement(
            f"DELETE FROM {self.subject_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.po_table} WHERE collection = ? AND p = ? AND o = ? AND s = ?"
        ), (collection, p, o, s))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.object_table} WHERE collection = ? AND o = ? AND s = ? AND p = ?"
        ), (collection, o, s, p))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.collection_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        count += 1

        # Execute every 100 triples to avoid oversized batches
        if count % 100 == 0:
            self.session.execute(batch)
            batch = BatchStatement()

    # Execute remaining deletions
    if count % 100 != 0:
        self.session.execute(batch)

    logger.info(f"Deleted {count} triples from collection {collection}")
```

#### 预处理语句优化
```python
def prepare_statements(self):
    # Cache prepared statements for better performance
    self.insert_subject_stmt = self.session.prepare(
        f"INSERT INTO {self.subject_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    self.insert_po_stmt = self.session.prepare(
        f"INSERT INTO {self.po_table} (collection, p, o, s) VALUES (?, ?, ?, ?)"
    )
    self.insert_object_stmt = self.session.prepare(
        f"INSERT INTO {self.object_table} (collection, o, s, p) VALUES (?, ?, ?, ?)"
    )
    self.insert_collection_stmt = self.session.prepare(
        f"INSERT INTO {self.collection_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    # ... query statements
```

## 迁移策略

### 数据迁移方法

#### 选项 1：蓝绿部署（推荐）
1. **并行部署新模式和现有模式** - 暂时使用不同的表名
2. **双写期** - 在过渡期间同时写入旧模式和新模式
3. **后台迁移** - 将现有数据复制到新表中
4. **切换读取** - 在数据迁移完成后，将查询路由到新表中
5. **删除旧表** - 在验证期结束后

#### 选项 2：原地迁移
1. **模式添加** - 在现有键空间中创建新表
2. **数据迁移脚本** - 批量从旧表复制到新表
3. **应用程序更新** - 在迁移完成后部署新代码
4. **清理旧表** - 删除旧表和索引

### 向后兼容性

#### 部署策略
```python
# Environment variable to control table usage during migration
USE_LEGACY_TABLES = os.getenv('CASSANDRA_USE_LEGACY', 'false').lower() == 'true'

class KnowledgeGraph:
    def __init__(self, ...):
        if USE_LEGACY_TABLES:
            self.init_legacy_schema()
        else:
            self.init_optimized_schema()
```

#### 迁移脚本
```python
def migrate_data():
    # Read from old table
    old_triples = session.execute("SELECT collection, s, p, o FROM triples")

    # Batch write to new tables
    for batch in batched(old_triples, 100):
        batch_stmt = BatchStatement()
        for row in batch:
            # Add to all three new tables
            batch_stmt.add(insert_subject_stmt, row)
            batch_stmt.add(insert_po_stmt, (row.collection, row.p, row.o, row.s))
            batch_stmt.add(insert_object_stmt, (row.collection, row.o, row.s, row.p))
        session.execute(batch_stmt)
```

### 验证策略

#### 数据一致性检查
```python
def validate_migration():
    # Count total records in old vs new tables
    old_count = session.execute("SELECT COUNT(*) FROM triples WHERE collection = ?", (collection,))
    new_count = session.execute("SELECT COUNT(*) FROM triples_by_subject WHERE collection = ?", (collection,))

    assert old_count == new_count, f"Record count mismatch: {old_count} vs {new_count}"

    # Spot check random samples
    sample_queries = generate_test_queries()
    for query in sample_queries:
        old_result = execute_legacy_query(query)
        new_result = execute_optimized_query(query)
        assert old_result == new_result, f"Query results differ for {query}"
```

## 测试策略

### 性能测试

#### 基准测试场景
1. **查询性能比较**
   所有 8 种查询类型的性能指标（测试前后）
   重点关注 get_po 性能改进（消除 ALLOW FILTERING）
   测量不同数据规模下的查询延迟

2. **负载测试**
   并发查询执行
   批量操作的写入吞吐量
   内存和 CPU 利用率

3. **可伸缩性测试**
   随着集合大小增加的性能
   多集合查询的分布
   集群节点利用率

#### 测试数据集
**小型:** 每个集合 10K 个三元组
**中型:** 每个集合 100K 个三元组
**大型:** 1M+ 个三元组
**多个集合:** 测试分区分布

### 功能测试

#### 单元测试更新
```python
# Example test structure for new implementation
class TestCassandraKGPerformance:
    def test_get_po_no_allow_filtering(self):
        # Verify get_po queries don't use ALLOW FILTERING
        with patch('cassandra.cluster.Session.execute') as mock_execute:
            kg.get_po('test_collection', 'predicate', 'object')
            executed_query = mock_execute.call_args[0][0]
            assert 'ALLOW FILTERING' not in executed_query

    def test_multi_table_consistency(self):
        # Verify all tables stay in sync
        kg.insert('test', 's1', 'p1', 'o1')

        # Check all tables contain the triple
        assert_triple_exists('triples_by_subject', 'test', 's1', 'p1', 'o1')
        assert_triple_exists('triples_by_po', 'test', 'p1', 'o1', 's1')
        assert_triple_exists('triples_by_object', 'test', 'o1', 's1', 'p1')
```

#### 集成测试更新
```python
class TestCassandraIntegration:
    def test_query_performance_regression(self):
        # Ensure new implementation is faster than old
        old_time = benchmark_legacy_get_po()
        new_time = benchmark_optimized_get_po()
        assert new_time < old_time * 0.5  # At least 50% improvement

    def test_end_to_end_workflow(self):
        # Test complete write -> query -> delete cycle
        # Verify no performance degradation in integration
```

### 回滚计划

#### 快速回滚策略
1. **环境变量切换** - 立即切换回旧版表
2. **保留旧版表** - 在性能得到验证之前，不要删除
3. **监控警报** - 基于错误率/延迟的自动化回滚触发

#### 回滚验证
```python
def rollback_to_legacy():
    # Set environment variable
    os.environ['CASSANDRA_USE_LEGACY'] = 'true'

    # Restart services to pick up change
    restart_cassandra_services()

    # Validate functionality
    run_smoke_tests()
```

## 风险与考量

### 性能风险
**写入延迟增加** - 每个插入操作需要 4 次写入（比 3 表方案多 33%）
**存储开销** - 需要 4 倍的存储空间（比 3 表方案多 33%）
**批量写入失败** - 需要适当的错误处理
**删除复杂性** - 集合删除需要先读取再删除的循环

### 运维风险
**迁移复杂性** - 大数据集的数据迁移
**一致性挑战** - 确保所有表保持同步
**监控缺失** - 需要新的指标来监控多表操作

### 缓解策略
1. **逐步推广** - 从小型集合开始
2. **全面监控** - 跟踪所有性能指标
3. **自动化验证** - 持续进行一致性检查
4. **快速回滚能力** - 基于环境选择表

## 成功标准

### 性能改进
[ ] **消除 ALLOW FILTERING** - `get_po` 和 `get_os` 查询在没有过滤的情况下运行
[ ] **查询延迟降低** - 查询响应时间提高 50% 以上
[ ] **更好的负载分布** - 没有热分区，集群节点上的负载分布均匀
[ ] **可扩展的性能** - 查询时间与结果大小成正比，而不是与总数据量成正比

### 功能需求
[ ] **API 兼容性** - 所有现有代码继续保持不变
[ ] **数据一致性** - 所有三个表保持同步
[ ] **零数据丢失** - 迁移保留所有现有三元组
[ ] **向后兼容性** - 能够回滚到旧模式

### 运维需求
[ ] **安全迁移** - 蓝绿部署，具有回滚能力
[ ] **监控覆盖** - 针对多表操作的全面指标
[ ] **测试覆盖** - 所有查询模式都经过性能基准测试
[ ] **文档** - 更新部署和运维流程

## 时间线

### 第一阶段：实施
[ ] 使用多表模式重写 `cassandra_kg.py`
[ ] 实施批量写入操作
[ ] 添加准备语句优化
[ ] 更新单元测试

### 第二阶段：集成测试
[ ] 更新集成测试
[ ] 性能基准测试
[ ] 使用真实数据量的负载测试
[ ] 数据一致性验证脚本

### 第三阶段：迁移规划
[ ] 蓝绿部署脚本
[ ] 数据迁移工具
[ ] 监控仪表板更新
[ ] 回滚流程

### 第四阶段：生产部署
[ ] 逐步推广到生产环境
[ ] 性能监控和验证
[ ] 清理旧表
[ ] 文档更新

## 结论

这种多表反规范化策略直接解决了两个关键的性能瓶颈：

1. **消除昂贵的 ALLOW FILTERING**，通过为每种查询模式提供最佳的表结构
2. **提高聚类效率**，通过复合分区键来合理地分配负载

该方法利用了 Cassandra 的优势，同时保持完整的 API 兼容性，确保现有代码能够自动受益于性能改进。
