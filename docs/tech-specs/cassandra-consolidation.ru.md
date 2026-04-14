---
layout: default
title: "Техническое описание: Консолидация конфигурации Cassandra"
parent: "Russian (Beta)"
---

# Техническое описание: Консолидация конфигурации Cassandra

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**Статус:** Черновик
**Автор:** Assistant
**Дата:** 2024-09-03

## Обзор

Данное техническое описание посвящено неконсистентности именования и шаблонов конфигурации параметров подключения к Cassandra в кодовой базе TrustGraph. В настоящее время существуют две различные схемы именования параметров (`cassandra_*` против `graph_*`), что приводит к путанице и усложняет обслуживание.

## Описание проблемы

В кодовой базе в настоящее время используются два различных набора параметров конфигурации Cassandra:

1. **Модули Knowledge/Config/Library** используют:
   `cassandra_host` (список хостов)
   `cassandra_user`
   `cassandra_password`

2. **Модули Graph/Storage** используют:
   `graph_host` (один хост, иногда преобразуется в список)
   `graph_username`
   `graph_password`

3. **Неконсистентное использование в командной строке**:
   Некоторые процессоры (например, `kg-store`) не предоставляют параметры Cassandra в качестве аргументов командной строки
   Другие процессоры предоставляют их с разными именами и форматами
   Тексты справки не отражают значения переменных окружения по умолчанию

Оба набора параметров подключаются к одному кластеру Cassandra, но с разными соглашениями об именовании, что приводит к:
Путанице в конфигурации для пользователей
Увеличенной нагрузке на обслуживание
Неконсистентной документации
Возможности неправильной конфигурации
Невозможности перезаписать настройки через командную строку в некоторых процессорах

## Предлагаемое решение

### 1. Стандартизация имен параметров

Все модули будут использовать согласованные имена параметров `cassandra_*`:
`cassandra_host` - Список хостов (хранится внутри как список)
`cassandra_username` - Имя пользователя для аутентификации
`cassandra_password` - Пароль для аутентификации

### 2. Аргументы командной строки

Все процессоры ДОЛЖНЫ предоставлять конфигурацию Cassandra через аргументы командной строки:
`--cassandra-host` - Список хостов, разделенный запятыми
`--cassandra-username` - Имя пользователя для аутентификации
`--cassandra-password` - Пароль для аутентификации

### 3. Передача через переменные окружения

Если параметры командной строки не указаны явно, система будет проверять переменные окружения:
`CASSANDRA_HOST` - Список хостов, разделенный запятыми
`CASSANDRA_USERNAME` - Имя пользователя для аутентификации
`CASSANDRA_PASSWORD` - Пароль для аутентификации

### 4. Значения по умолчанию

Если ни параметры командной строки, ни переменные окружения не указаны:
`cassandra_host` по умолчанию `["cassandra"]`
`cassandra_username` по умолчанию `None` (без аутентификации)
`cassandra_password` по умолчанию `None` (без аутентификации)

### 5. Требования к тексту справки

Вывод команды `--help` должен:
Показывать значения переменных окружения в качестве значений по умолчанию, если они установлены
Никогда не отображать значения паролей (показывать `****` или `<set>` вместо этого)
Четко указывать порядок разрешения в тексте справки

Пример вывода справки:
```
--cassandra-host HOST
    Cassandra host list, comma-separated (default: prod-cluster-1,prod-cluster-2)
    [from CASSANDRA_HOST environment variable]

--cassandra-username USERNAME
    Cassandra username (default: cassandra_user)
    [from CASSANDRA_USERNAME environment variable]
    
--cassandra-password PASSWORD  
    Cassandra password (default: <set from environment>)
```

## Детали реализации

### Порядок разрешения параметров

Для каждого параметра Cassandra порядок разрешения будет следующим:
1. Значение аргумента командной строки
2. Значение переменной окружения (`CASSANDRA_*`)
3. Значение по умолчанию

### Обработка параметров хостов

Параметр `cassandra_host`:
Командная строка принимает строку, разделенную запятыми: `--cassandra-host "host1,host2,host3"`
Переменная окружения принимает строку, разделенную запятыми: `CASSANDRA_HOST="host1,host2,host3"`
Внутри всегда хранится в виде списка: `["host1", "host2", "host3"]`
Один хост: `"localhost"` → преобразуется в `["localhost"]`
Уже является списком: `["host1", "host2"]` → используется как есть

### Логика аутентификации

Аутентификация будет использоваться, когда указаны и `cassandra_username`, и `cassandra_password`:
```python
if cassandra_username and cassandra_password:
    # Use SSL context and PlainTextAuthProvider
else:
    # Connect without authentication
```

## Файлы для изменения

### Модули, использующие параметры `graph_*` (которые необходимо изменить):
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/rows/cassandra/write.py`
`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`

### Модули, использующие параметры `cassandra_*` (которые необходимо обновить с использованием резервного варианта из среды):
`trustgraph-flow/trustgraph/tables/config.py`
`trustgraph-flow/trustgraph/tables/knowledge.py`
`trustgraph-flow/trustgraph/tables/library.py`
`trustgraph-flow/trustgraph/storage/knowledge/store.py`
`trustgraph-flow/trustgraph/cores/knowledge.py`
`trustgraph-flow/trustgraph/librarian/librarian.py`
`trustgraph-flow/trustgraph/librarian/service.py`
`trustgraph-flow/trustgraph/config/service/service.py`
`trustgraph-flow/trustgraph/cores/service.py`

### Тестовые файлы для обновления:
`tests/unit/test_cores/test_knowledge_manager.py`
`tests/unit/test_storage/test_triples_cassandra_storage.py`
`tests/unit/test_query/test_triples_cassandra_query.py`
`tests/integration/test_objects_cassandra_integration.py`

## Стратегия реализации

### Этап 1: Создание общего вспомогательного класса конфигурации
Создайте вспомогательные функции для стандартизации конфигурации Cassandra во всех процессорах:

```python
import os
import argparse

def get_cassandra_defaults():
    """Get default values from environment variables or fallback."""
    return {
        'host': os.getenv('CASSANDRA_HOST', 'cassandra'),
        'username': os.getenv('CASSANDRA_USERNAME'),
        'password': os.getenv('CASSANDRA_PASSWORD')
    }

def add_cassandra_args(parser: argparse.ArgumentParser):
    """
    Add standardized Cassandra arguments to an argument parser.
    Shows environment variable values in help text.
    """
    defaults = get_cassandra_defaults()
    
    # Format help text with env var indication
    host_help = f"Cassandra host list, comma-separated (default: {defaults['host']})"
    if 'CASSANDRA_HOST' in os.environ:
        host_help += " [from CASSANDRA_HOST]"
    
    username_help = f"Cassandra username"
    if defaults['username']:
        username_help += f" (default: {defaults['username']})"
        if 'CASSANDRA_USERNAME' in os.environ:
            username_help += " [from CASSANDRA_USERNAME]"
    
    password_help = "Cassandra password"
    if defaults['password']:
        password_help += " (default: <set>)"
        if 'CASSANDRA_PASSWORD' in os.environ:
            password_help += " [from CASSANDRA_PASSWORD]"
    
    parser.add_argument(
        '--cassandra-host',
        default=defaults['host'],
        help=host_help
    )
    
    parser.add_argument(
        '--cassandra-username',
        default=defaults['username'],
        help=username_help
    )
    
    parser.add_argument(
        '--cassandra-password',
        default=defaults['password'],
        help=password_help
    )

def resolve_cassandra_config(args) -> tuple[list[str], str|None, str|None]:
    """
    Convert argparse args to Cassandra configuration.
    
    Returns:
        tuple: (hosts_list, username, password)
    """
    # Convert host string to list
    if isinstance(args.cassandra_host, str):
        hosts = [h.strip() for h in args.cassandra_host.split(',')]
    else:
        hosts = args.cassandra_host
    
    return hosts, args.cassandra_username, args.cassandra_password
```

### Фаза 2: Обновление модулей с использованием параметров `graph_*`
1. Изменить имена параметров с `graph_*` на `cassandra_*`
2. Заменить собственные методы `add_args()` на стандартизированные методы `add_cassandra_args()`
3. Использовать общие вспомогательные функции конфигурации
4. Обновить строки документации

Пример преобразования:
```python
# OLD CODE
@staticmethod
def add_args(parser):
    parser.add_argument(
        '-g', '--graph-host',
        default="localhost",
        help=f'Graph host (default: localhost)'
    )
    parser.add_argument(
        '--graph-username',
        default=None,
        help=f'Cassandra username'
    )

# NEW CODE  
@staticmethod
def add_args(parser):
    FlowProcessor.add_args(parser)
    add_cassandra_args(parser)  # Use standard helper
```

### Фаза 3: Обновление модулей с использованием параметров `cassandra_*`
1. Добавить поддержку аргументов командной строки там, где это отсутствует (например, `kg-store`).
2. Заменить существующие определения аргументов на `add_cassandra_args()`.
3. Использовать `resolve_cassandra_config()` для обеспечения согласованности разрешения.
4. Обеспечить согласованную обработку списка хостов.

### Фаза 4: Обновление тестов и документации
1. Обновить все файлы тестов для использования новых имен параметров.
2. Обновить документацию CLI.
3. Обновить документацию API.
4. Добавить документацию по переменным окружения.

## Обратная совместимость

Для поддержания обратной совместимости во время перехода:

1. **Предупреждения об устаревании** для параметров `graph_*`.
2. **Псевдонимы параметров** - изначально принимать как старые, так и новые имена.
3. **Поэтапное внедрение** в течение нескольких релизов.
4. **Обновления документации** с руководством по миграции.

Пример кода обратной совместимости:
```python
def __init__(self, **params):
    # Handle deprecated graph_* parameters
    if 'graph_host' in params:
        warnings.warn("graph_host is deprecated, use cassandra_host", DeprecationWarning)
        params.setdefault('cassandra_host', params.pop('graph_host'))
    
    if 'graph_username' in params:
        warnings.warn("graph_username is deprecated, use cassandra_username", DeprecationWarning)
        params.setdefault('cassandra_username', params.pop('graph_username'))
    
    # ... continue with standard resolution
```

## Стратегия тестирования

1. **Юнит-тесты** для логики разрешения конфигурации
2. **Интеграционные тесты** с различными комбинациями конфигурации
3. **Тесты переменных окружения**
4. **Тесты обратной совместимости** с устаревшими параметрами
5. **Тесты Docker Compose** с переменными окружения

## Обновления документации

1. Обновить всю документацию по командам CLI
2. Обновить документацию API
3. Создать руководство по миграции
4. Обновить примеры Docker Compose
5. Обновить справочную документацию по конфигурации

## Риски и меры по их снижению

| Риск | Влияние | Меры по снижению |
|------|--------|------------|
| Изменения, нарушающие работу пользователей | Высокое | Реализовать период обратной совместимости |
| Спутанность конфигурации во время перехода | Среднее | Четкая документация и предупреждения об устаревании |
| Сбои в тестах | Среднее | Комплексное обновление тестов |
| Проблемы при развертывании Docker | Высокое | Обновить все примеры Docker Compose |

## Критерии успеха

[ ] Все модули используют согласованные имена параметров `cassandra_*`
[ ] Все процессоры предоставляют настройки Cassandra через аргументы командной строки
[ ] Текстовая справка по командной строке показывает значения переменных окружения по умолчанию
[ ] Значения паролей никогда не отображаются в справке
[ ] Механизм отката к переменным окружения работает правильно
[ ] `cassandra_host` последовательно обрабатывается как список внутри
[ ] Обратная совместимость поддерживается не менее 2 версий
[ ] Все тесты проходят с новой системой конфигурации
[ ] Документация полностью обновлена
[ ] Примеры Docker Compose работают с переменными окружения

## План

**Неделя 1:** Реализовать общий помощник конфигурации и обновить модули `graph_*`
**Неделя 2:** Добавить поддержку переменных окружения в существующие модули `cassandra_*`
**Неделя 3:** Обновить тесты и документацию
**Неделя 4:** Интеграционное тестирование и исправление ошибок

## Будущие соображения

Рассмотреть возможность расширения этой модели на другие конфигурации баз данных (например, Elasticsearch)
Реализовать проверку конфигурации и улучшенные сообщения об ошибках
Добавить поддержку конфигурации пула соединений Cassandra
Рассмотреть возможность добавления поддержки файлов конфигурации (.env)
