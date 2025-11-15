import sys
import os
import subprocess
import base64
import urllib.request
import json

# импортируем функции из других модулей
sys.path.insert(0, os.path.dirname(__file__))
from step_4 import add_reverse_mode_to_args
from step_3 import build_dependency_graph, read_test_repository


def generate_mermaid_graph(graph, root_package, is_reverse=False):
    """
    Сгенерировать текстовое представление графа в формате Mermaid.
    
    Параметры:
        graph (dict): граф зависимостей {пакет: {depth, is_filtered, ...}}
        root_package (str): корневой пакет
        is_reverse (bool): если True, используются обратные зависимости
    
    Возвращает:
        str: Mermaid диаграмма
    """
    # инициализируем диаграмму
    lines = ['graph TD']
    
    # добавляем корневой узел
    lines.append(f'    Root["{root_package}"]')
    
    # разделяем пакеты на включённые и исключённые
    included_deps = {}
    for pkg_name, info in graph.items():
        if pkg_name != root_package and not info['is_filtered']:
            included_deps[pkg_name] = info['depth']
    
    # если нет зависимостей, вернём простую диаграмму
    if not included_deps:
        return '\n'.join(lines)
    
    # добавляем связи между пакетами
    # для этого нужно восстановить связи из графа
    # (так как у нас только глубина, строим дерево на основе глубины)
    
    # группируем по уровням
    levels = {}
    for pkg, depth in included_deps.items():
        if depth not in levels:
            levels[depth] = []
        levels[depth].append(pkg)
    
    # добавляем узлы
    for depth in sorted(levels.keys()):
        for i, pkg in enumerate(sorted(levels[depth])):
            # используем идентификатор без спецсимволов для Mermaid
            safe_pkg = pkg.replace('-', '_').replace('.', '_').replace('@', '')
            lines.append(f'    {safe_pkg}["{pkg}"]')
    
    # добавляем связи (от родительского уровня к потомкам)
    prev_level_nodes = ['Root']
    for depth in sorted(levels.keys()):
        current_level_nodes = [n.replace('-', '_').replace('.', '_').replace('@', '') for n in sorted(levels[depth])]
        
        if depth == 1:
            # первый уровень связан с корневым пакетом
            for node in current_level_nodes:
                lines.append(f'    Root --> {node}')
        else:
            # для остальных уровней связываем с узлами предыдущего уровня
            # (упрощённая версия)
            if prev_level_nodes:
                parent = prev_level_nodes[0] if prev_level_nodes else 'Root'
                for node in current_level_nodes[:len(prev_level_nodes)]:
                    lines.append(f'    {parent} --> {node}')
        
        prev_level_nodes = current_level_nodes
    
    return '\n'.join(lines)


def save_mermaid_as_png(mermaid_text, output_file):
    """
    Сохранить Mermaid диаграмму как PNG используя kroki.io сервис.
    
    Параметры:
        mermaid_text (str): текст Mermaid диаграммы
        output_file (str): путь к выходному PNG файлу
    
    Возвращает:
        bool: успешно ли сохранён файл
    """
    try:
        # используем kroki.io API (бесплатный сервис для преобразования диаграмм)
        kroki_url = "https://kroki.io/mermaid/png"
        
        # отправляем запрос
        data = mermaid_text.encode('utf-8')
        req = urllib.request.Request(
            kroki_url,
            data=data,
            headers={'Content-Type': 'text/plain'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            png_data = response.read()
        
        # сохраняем PNG файл
        with open(output_file, 'wb') as f:
            f.write(png_data)
        
        print(f"✓ PNG сохранён: {output_file}")
        return True
        
    except urllib.error.HTTPError as e:
        print(f"✗ Ошибка HTTP при сохранении PNG: {e.code}", file=sys.stderr)
        print(f"  Подсказка: сервис kroki.io может быть недоступен. Mermaid текст сохранён.", file=sys.stderr)
        return False
    except urllib.error.URLError as e:
        print(f"✗ Ошибка сети: {e.reason}", file=sys.stderr)
        print(f"  Подсказка: проверьте интернет соединение.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"✗ Ошибка при сохранении PNG: {e}", file=sys.stderr)
        return False


def generate_ascii_tree(graph, root_package):
    """
    Сгенерировать ASCII-представление дерева зависимостей.
    
    Параметры:
        graph (dict): граф зависимостей
        root_package (str): корневой пакет
    
    Возвращает:
        str: ASCII-дерево
    """
    lines = [f"{root_package}"]
    
    # группируем по уровням
    levels = {}
    for pkg_name, info in graph.items():
        if pkg_name != root_package and not info['is_filtered']:
            depth = info['depth']
            if depth not in levels:
                levels[depth] = []
            levels[depth].append(pkg_name)
    
    # печатаем каждый уровень
    for depth in sorted(levels.keys()):
        prefix = "│   " * (depth - 1)
        for i, pkg in enumerate(sorted(levels[depth])):
            is_last = (i == len(levels[depth]) - 1)
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{pkg}")
    
    return "\n".join(lines)


def save_mermaid_text(mermaid_text, output_file):
    """
    Сохранить текст Mermaid диаграммы в файл.
    
    Параметры:
        mermaid_text (str): текст Mermaid диаграммы
        output_file (str): путь к выходному файлу
    """
    try:
        mmd_file = output_file.rsplit('.', 1)[0] + '.mmd'
        with open(mmd_file, 'w', encoding='utf-8') as f:
            f.write(mermaid_text)
        print(f"✓ Mermaid текст сохранён: {mmd_file}")
        return True
    except Exception as e:
        print(f"✗ Ошибка при сохранении Mermaid текста: {e}", file=sys.stderr)
        return False


def main(argv=None):
    """
    Главная функция этапа 5.
    """
    # создаём расширенный парсер
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
    
    # получаем граф
    test_file = args.repo if args.test_mode else None
    
    graph = build_dependency_graph(
        args.package,
        args.pkg_version,
        args.max_depth,
        args.filter_substr,
        test_file
    )
    
    # выводим заголовок
    print("\n" + "=" * 70)
    print("ЭТАП 5: ВИЗУАЛИЗАЦИЯ ГРАФА ЗАВИСИМОСТЕЙ")
    print("=" * 70)
    
    print(f"\nПараметры:")
    print(f"  Пакет: {args.package}")
    print(f"  Версия: {args.pkg_version}")
    print(f"  Выходной файл: {args.out_file}")
    print(f"  Режим ASCII: {'да' if args.ascii_tree else 'нет'}")
    
    # генерируем Mermaid диаграмму
    print("\n1. Генерация Mermaid диаграммы...")
    mermaid_text = generate_mermaid_graph(graph, args.package, args.reverse_mode)
    print(f"✓ Mermaid диаграмма сгенерирована ({len(mermaid_text)} символов)")
    
    # сохраняем Mermaid текст
    print("\n2. Сохранение Mermaid текста...")
    save_mermaid_text(mermaid_text, args.out_file)
    
    # сохраняем PNG
    print("\n3. Сохранение изображения PNG...")
    png_result = save_mermaid_as_png(mermaid_text, args.out_file)
    if not png_result:
        print(f"  (Используйте Mermaid Live Editor: https://mermaid.live)")
    
    # выводим ASCII-дерево если нужно
    if args.ascii_tree:
        print("\n4. ASCII-представление зависимостей:")
        print("-" * 70)
        ascii_tree = generate_ascii_tree(graph, args.package)
        print(ascii_tree)
    
    # статистика
    print("\n" + "=" * 70)
    total_packages = len(graph)
    included = sum(1 for info in graph.values() if not info['is_filtered'])
    excluded = total_packages - included
    
    print(f"Статистика:")
    print(f"  Всего пакетов в графе: {total_packages}")
    print(f"  Включено в визуализацию: {included}")
    print(f"  Исключено фильтрами: {excluded}")
    print("=" * 70)


if __name__ == '__main__':
    main()
