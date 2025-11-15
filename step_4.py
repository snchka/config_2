import sys
import os

# импортируем функции из других модулей
sys.path.insert(0, os.path.dirname(__file__))
from step_3 import read_test_repository, build_dependency_graph


def build_reverse_dependency_graph(root_package, max_depth=0, filter_substr='', test_file=None):
    """
    Построить граф обратных зависимостей (пакеты, которые зависят от root_package).
    
    Параметры:
        root_package (str): пакет, для которого ищем обратные зависимости
        max_depth (int): максимальная глубина
        filter_substr (str): подстрока для исключения
        test_file (str): путь к тестовому репозиторию
    
    Возвращает:
        dict: граф {пакет: {depth, is_filtered, filter_reason}}
    """
    # загружаем тестовый граф
    test_graph = None
    if test_file:
        test_graph = read_test_repository(test_file)
    
    # получаем все обратные зависимости
    all_reverse_deps = _get_all_reverse_dependencies(root_package, test_graph)
    
    # применяем фильтры
    filtered_graph = {}
    filtered_graph[root_package] = {
        'depth': 0,
        'is_filtered': False,
        'filter_reason': None
    }
    
    for pkg_name, depth in all_reverse_deps.items():
        is_filtered = False
        filter_reason = None
        
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


def _get_all_reverse_dependencies(root_package, test_graph=None):
    """
    Получить все обратные зависимости (DFS без рекурсии).
    Ищем пакеты, которые (прямо или транзитивно) зависят от root_package.
    
    Параметры:
        root_package (str): пакет для поиска обратных зависимостей
        test_graph (dict): граф тестового репозитория
    
    Возвращает:
        dict: {пакет: глубина}
    """
    if test_graph is None:
        return {}
    
    # строим инвертированный граф: reverse_graph[A] = [список пакетов, зависящих от A]
    reverse_graph = {}
    for pkg, deps in test_graph.items():
        for dep in deps:
            if dep not in reverse_graph:
                reverse_graph[dep] = []
            reverse_graph[dep].append(pkg)
    
    # DFS со стеком для поиска обратных зависимостей
    all_reverse_deps = {}
    visited = set()
    stack = [(root_package, 0)]  # (package, depth)
    
    while stack:
        current_package, depth = stack.pop()
        
        if current_package in visited:
            continue
        
        visited.add(current_package)
        
        # получаем пакеты, которые зависят от current_package
        dependents = reverse_graph.get(current_package, [])
        
        for dependent in dependents:
            if dependent != root_package and dependent not in all_reverse_deps:
                all_reverse_deps[dependent] = depth + 1
                stack.append((dependent, depth + 1))
    
    return all_reverse_deps


def print_reverse_dependencies(graph, root_package, max_depth, filter_substr, test_file=None):
    """
    Вывести обратные зависимости на экран.
    """
    print("\n" + "=" * 70)
    print("ЭТАП 4: ОБРАТНЫЕ ЗАВИСИМОСТИ")
    print("=" * 70)
    
    print(f"\nПараметры:")
    print(f"  Пакет (ищем кто от него зависит): {root_package}")
    print(f"  Максимальная глубина: {max_depth if max_depth > 0 else 'не ограничена'}")
    print(f"  Фильтр подстроки: '{filter_substr}'" if filter_substr else "  Фильтр подстроки: нет")
    print(f"  Тестовый репозиторий: {test_file if test_file else 'нет'}")
    
    # разделяем зависимости на включённые и исключённые
    included = []
    excluded = []
    
    for pkg_name, info in sorted(graph.items()):
        depth = info['depth']
        is_filtered = info['is_filtered']
        reason = info['filter_reason']
        
        if pkg_name == root_package:
            continue
        
        if is_filtered:
            excluded.append((pkg_name, depth, reason))
        else:
            included.append((pkg_name, depth))
    
    # выводим включённые обратные зависимости
    print(f"\nПакеты, которые зависят от '{root_package}' ({len(included)}):")
    print("-" * 70)
    if included:
        for pkg_name, depth in sorted(included, key=lambda x: (x[1], x[0])):
            print(f"  {'  ' * (depth - 1)}├─ {pkg_name} (уровень {depth})")
    else:
        print("  (нет)")
    
    # выводим исключённые зависимости
    if excluded:
        print(f"\nИсключённые из анализа ({len(excluded)}):")
        print("-" * 70)
        for pkg_name, depth, reason in sorted(excluded, key=lambda x: (x[1], x[0])):
            print(f"  {pkg_name} (уровень {depth}) - причина: {reason}")
    
    print("\n" + "=" * 70)
    print(f"Всего пакетов в графе: {len(graph)}")
    print(f"Обратные зависимости (включено): {len(included)}")
    print(f"Исключено: {len(excluded)}")
    print("=" * 70)


def add_reverse_mode_to_args():
    """
    Расширяем парсер аргументов для поддержки режима обратных зависимостей.
    """
    import argparse
    parser = argparse.ArgumentParser(description='Визуализатор зависимостей пакетов (этап 4)')
    
    parser.add_argument('--package', '-p', dest='package', required=True,
                        help='Имя анализируемого пакета')
    
    parser.add_argument('--repo', '-r', dest='repo', required=True,
                        help='URL-адрес репозитория или путь к файлу тестового репозитория')
    
    parser.add_argument('--test', action='store_true', dest='test_mode',
                        help='Режим работы с тестовым репозиторием')
    
    parser.add_argument('--pkg-version', dest='pkg_version', default='latest',
                        help="Версия пакета (по умолчанию latest)")
    
    parser.add_argument('--out', '-o', dest='out_file', default='graph.png',
                        help='Имя генерируемого файла с изображением графа')
    
    parser.add_argument('--ascii', action='store_true', dest='ascii_tree',
                        help='Вывести зависимости в формате ASCII-дерева')
    
    parser.add_argument('--max-depth', dest='max_depth', type=int, default=0,
                        help='Максимальная глубина анализа')
    
    parser.add_argument('--filter', dest='filter_substr', default='',
                        help='Подстрока для фильтрации пакетов')
    
    parser.add_argument('--reverse', action='store_true', dest='reverse_mode',
                        help='Режим обратных зависимостей')
    
    return parser


def main(argv=None):
    """
    Главная функция этапа 4.
    """
    # создаём расширенный парсер с поддержкой --reverse
    parser = add_reverse_mode_to_args()
    args = parser.parse_args(argv)
    
    # базовая валидация
    if not args.package or not args.package.strip():
        print('Ошибка: параметр --package обязателен', file=sys.stderr)
        sys.exit(2)
    
    if args.test_mode:
        if not os.path.exists(args.repo):
            print(f"Ошибка: файл не найден: {args.repo}", file=sys.stderr)
            sys.exit(2)
    
    if args.max_depth < 0:
        print('Ошибка: параметр --max-depth должен быть >= 0', file=sys.stderr)
        sys.exit(2)
    
    # в режиме тестирования repo — это путь к файлу
    test_file = None
    if args.test_mode:
        test_file = args.repo
    
    # определяем режим работы
    if args.reverse_mode:
        # режим обратных зависимостей
        graph = build_reverse_dependency_graph(
            args.package,
            args.max_depth,
            args.filter_substr,
            test_file
        )
        print_reverse_dependencies(graph, args.package, args.max_depth, args.filter_substr, test_file)
    else:
        # режим прямых зависимостей (как в этапе 3)
        graph = build_dependency_graph(
            args.package,
            args.pkg_version,
            args.max_depth,
            args.filter_substr,
            test_file
        )
        from step_3 import print_dependency_graph
        print_dependency_graph(graph, args.package, args.pkg_version, args.max_depth, args.filter_substr, test_file)


if __name__ == '__main__':
    main()
