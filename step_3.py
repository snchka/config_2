import json
import urllib.request
import urllib.error
import sys
import os
import re

# импортируем функции из step_1 и step_2
sys.path.insert(0, os.path.dirname(__file__))
from step_1 import parse_args, validate_args
from step_2 import fetch_package_metadata, parse_version


def read_test_repository(file_path):
    """
    Прочитать тестовый репозиторий из файла.
    Формат: строки вида "A: B C D" означают, что пакет A зависит от B, C, D.
    
    Параметры:
        file_path (str): путь к файлу тестового репозитория
    
    Возвращает:
        dict: словарь {пакет: [зависимости]}
    """
    graph = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    # пропускаем пустые строки и комментарии
                    continue
                
                # парсим строку формата "A: B C D"
                if ':' in line:
                    parts = line.split(':')
                    package = parts[0].strip()
                    deps_str = parts[1].strip()
                    dependencies = deps_str.split() if deps_str else []
                    graph[package] = dependencies
                else:
                    # формат "A B C D" (сам пакет и его зависимости)
                    parts = line.split()
                    if parts:
                        package = parts[0]
                        dependencies = parts[1:]
                        graph[package] = dependencies
        
        return graph
    except Exception as e:
        print(f"Ошибка при чтении тестового репозитория '{file_path}': {e}", file=sys.stderr)
        return {}


def get_all_dependencies(package_name, version='latest', test_graph=None):
    """
    Получить все зависимости пакета (прямые и транзитивные).
    
    Параметры:
        package_name (str): имя пакета
        version (str): версия пакета
        test_graph (dict): если не None, используется вместо реального репозитория
    
    Возвращает:
        dict: словарь {имя_пакета: информация}
    """
    if test_graph is not None:
        # режим тестового репозитория
        return _get_all_dependencies_test(package_name, test_graph)
    else:
        # режим реального репозитория (npm registry)
        return _get_all_dependencies_npm(package_name, version)


def _get_all_dependencies_test(root_package, test_graph):
    """
    Получить все зависимости в тестовом режиме (без рекурсии, используя DFS со стеком).
    """
    all_deps = {}
    visited = set()
    stack = [(root_package, 0)]  # (package, depth)
    cycles = set()  # для отслеживания циклов
    
    while stack:
        current_package, depth = stack.pop()
        
        # проверяем циклическую зависимость (простой случай)
        if current_package in visited:
            if current_package in stack:
                cycles.add((current_package, 'цикл'))
            continue
        
        visited.add(current_package)
        
        if current_package not in test_graph:
            continue
        
        # получаем прямые зависимости
        direct_deps = test_graph.get(current_package, [])
        
        for dep in direct_deps:
            if dep not in all_deps:
                all_deps[dep] = {'depth': depth + 1, 'direct_from': current_package}
                stack.append((dep, depth + 1))
    
    return all_deps


def _get_all_dependencies_npm(root_package, version='latest'):
    """
    Получить все зависимости в режиме реального npm репозитория (без рекурсии, используя DFS со стеком).
    """
    all_deps = {}
    visited = set()
    stack = [(root_package, 0)]  # (package, depth)
    direct_deps_cache = {}  # кэш для прямых зависимостей
    
    while stack:
        current_package, depth = stack.pop()
        
        if current_package in visited:
            continue
        
        visited.add(current_package)
        
        # получаем прямые зависимости (кэшируем)
        if current_package not in direct_deps_cache:
            metadata = fetch_package_metadata(current_package)
            if metadata is None:
                continue
            
            # находим версию
            versions_dict = metadata.get('versions', {})
            if not versions_dict:
                continue
            
            # для первого пакета используем запрошенную версию
            if current_package == root_package:
                pkg_version = version
            else:
                # для зависимостей берём latest
                dist_tags = metadata.get('dist-tags', {})
                pkg_version = dist_tags.get('latest', max(versions_dict.keys(), key=parse_version))
            
            if pkg_version not in versions_dict:
                continue
            
            version_info = versions_dict[pkg_version]
            direct_deps_cache[current_package] = version_info.get('dependencies', {})
        
        for dep_name in direct_deps_cache.get(current_package, {}).keys():
            if dep_name not in all_deps:
                all_deps[dep_name] = depth + 1
                stack.append((dep_name, depth + 1))
    
    return all_deps


def build_dependency_graph(root_package, version='latest', max_depth=0, filter_substr='', test_file=None):
    """
    Построить полный граф зависимостей с применением фильтров и ограничений.
    
    Параметры:
        root_package (str): корневой пакет
        version (str): версия корневого пакета
        max_depth (int): максимальная глубина (0 = без ограничения)
        filter_substr (str): подстрока для исключения пакетов
        test_file (str): если не None, использовать тестовый репозиторий из файла
    
    Возвращает:
        dict: полный граф {пакет: {depth: ..., is_filtered: ...}}
    """
    # загружаем тестовый граф если нужно
    test_graph = None
    if test_file:
        test_graph = read_test_repository(test_file)
    
    # получаем все зависимости
    all_deps = get_all_dependencies(root_package, version, test_graph)
    
    # применяем фильтры
    filtered_graph = {}
    filtered_graph[root_package] = {
        'depth': 0,
        'is_filtered': False,
        'filter_reason': None
    }
    
    for pkg_name, info in all_deps.items():
        # определяем, используется ли фильтр
        is_filtered = False
        filter_reason = None
        
        if isinstance(info, dict):
            depth = info.get('depth', 0)
        else:
            depth = info
        
        # применяем max_depth
        if max_depth > 0 and depth > max_depth:
            is_filtered = True
            filter_reason = f'глубина {depth} > {max_depth}'
        
        # применяем фильтр подстроки
        if filter_substr and filter_substr in pkg_name:
            is_filtered = True
            filter_reason = f'содержит "{filter_substr}"'
        
        filtered_graph[pkg_name] = {
            'depth': depth,
            'is_filtered': is_filtered,
            'filter_reason': filter_reason
        }
    
    return filtered_graph


def print_dependency_graph(graph, package_name, version, max_depth, filter_substr, test_file=None):
    """
    Вывести информацию о построенном графе зависимостей.
    """
    print("\n" + "=" * 70)
    print("ЭТАП 3: ГРАФ ЗАВИСИМОСТЕЙ (DFS БЕЗ РЕКУРСИИ)")
    print("=" * 70)
    
    print(f"\nПараметры:")
    print(f"  Пакет: {package_name}")
    print(f"  Версия: {version}")
    print(f"  Максимальная глубина: {max_depth if max_depth > 0 else 'не ограничена'}")
    print(f"  Фильтр подстроки: '{filter_substr}'" if filter_substr else "  Фильтр подстроки: нет")
    print(f"  Тестовый репозиторий: {test_file if test_file else 'нет (real npm registry)'}")
    
    # разделяем зависимости на включённые и исключённые
    included = []
    excluded = []
    
    for pkg_name, info in sorted(graph.items()):
        depth = info['depth']
        is_filtered = info['is_filtered']
        reason = info['filter_reason']
        
        if pkg_name == package_name:
            continue
        
        if is_filtered:
            excluded.append((pkg_name, depth, reason))
        else:
            included.append((pkg_name, depth))
    
    # выводим включённые зависимости
    print(f"\nВключённые зависимости ({len(included)}):")
    print("-" * 70)
    if included:
        for pkg_name, depth in sorted(included, key=lambda x: (x[1], x[0])):
            print(f"  {'  ' * (depth - 1)}├─ {pkg_name} (уровень {depth})")
    else:
        print("  (нет)")
    
    # выводим исключённые зависимости (если есть)
    if excluded:
        print(f"\nИсключённые зависимости ({len(excluded)}):")
        print("-" * 70)
        for pkg_name, depth, reason in sorted(excluded, key=lambda x: (x[1], x[0])):
            print(f"  {pkg_name} (уровень {depth}) — причина: {reason}")
    
    print("\n" + "=" * 70)
    print(f"Всего пакетов в графе: {len(graph)}")
    print(f"Включено в анализ: {len(included) + 1}")  # +1 на корневой пакет
    print(f"Исключено: {len(excluded)}")
    print("=" * 70)


def main(argv=None):
    """
    Главная функция этапа 3.
    """
    # парсим аргументы
    args = parse_args(argv)
    
    # валидируем аргументы
    validate_args(args)
    
    # в режиме тестирования repo — это путь к файлу
    test_file = None
    if args.test_mode:
        test_file = args.repo
    
    # строим граф
    graph = build_dependency_graph(
        args.package,
        args.pkg_version,
        args.max_depth,
        args.filter_substr,
        test_file
    )
    
    # выводим результаты
    print_dependency_graph(
        graph,
        args.package,
        args.pkg_version,
        args.max_depth,
        args.filter_substr,
        test_file
    )


if __name__ == '__main__':
    main()
