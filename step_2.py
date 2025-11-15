import json
import urllib.request
import urllib.error
import sys
import os

# импортируем функции из step_1 для парсинга аргументов
sys.path.insert(0, os.path.dirname(__file__))
from step_1 import parse_args, validate_args


def fetch_package_metadata(package_name, version='latest'):
    """
    Получить метаданные пакета из npm registry (https://registry.npmjs.org/).
    
    Параметры:
        package_name (str): имя пакета
        version (str): версия пакета (или 'latest')
    
    Возвращает:
        dict: объект с информацией о пакете, или None в случае ошибки
    """
    # URL npm registry по стандарту: https://registry.npmjs.org/{package_name}/{version}
    registry_url = f"https://registry.npmjs.org/{package_name}"
    
    try:
        # используем встроенный urllib для запроса (без внешних библиотек)
        with urllib.request.urlopen(registry_url, timeout=10) as response:
            data = response.read()
            return json.loads(data)
    except urllib.error.HTTPError as e:
        print(f"Ошибка HTTP при получении пакета '{package_name}': {e.code}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"Ошибка сети при получении пакета '{package_name}': {e.reason}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Ошибка разбора JSON для пакета '{package_name}': {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Неожиданная ошибка при получении пакета '{package_name}': {e}", file=sys.stderr)
        return None


def get_direct_dependencies(package_name, version='latest'):
    """
    Получить прямые зависимости пакета для конкретной версии.
    
    Параметры:
        package_name (str): имя пакета
        version (str): версия пакета (или 'latest')
    
    Возвращает:
        dict: словарь {имя_пакета: версия} или пустой dict в случае ошибки
    """
    # получаем полные метаданные пакета
    metadata = fetch_package_metadata(package_name)
    
    if metadata is None:
        return {}
    
    # в npm registry структура: metadata['versions'][version] содержит информацию версии
    versions_dict = metadata.get('versions', {})
    
    # если версия 'latest', ищем в поле 'dist-tags'
    if version == 'latest':
        dist_tags = metadata.get('dist-tags', {})
        latest_version = dist_tags.get('latest')
        if latest_version:
            version = latest_version
        else:
            # если нет latest tag, берём последнюю версию из версий
            if versions_dict:
                version = max(versions_dict.keys(), key=lambda v: parse_version(v))
    
    # получаем объект версии
    if version not in versions_dict:
        print(f"Версия '{version}' не найдена для пакета '{package_name}'", file=sys.stderr)
        return {}
    
    version_info = versions_dict[version]
    
    # прямые зависимости хранятся в поле 'dependencies'
    dependencies = version_info.get('dependencies', {})
    
    return dependencies


def parse_version(version_str):
    """
    Простой парсер версии для сравнения.
    Преобразует версию в кортеж чисел для сравнения.
    
    Параметры:
        version_str (str): строка версии (например, "1.2.3")
    
    Возвращает:
        tuple: кортеж целых чисел
    """
    try:
        # удаляем префиксы типа 'v' и берём только цифры и точки
        clean = version_str.lstrip('v')
        parts = clean.split('.')
        return tuple(int(p) if p.isdigit() else 0 for p in parts)
    except (ValueError, AttributeError):
        return (0,)


def print_dependencies(dependencies_dict, package_name, version):
    """
    Вывести прямые зависимости в формате "имя@версия".
    
    Параметры:
        dependencies_dict (dict): словарь {имя: версия}
        package_name (str): имя анализируемого пакета
        version (str): версия анализируемого пакета
    """
    print(f"\nПрямые зависимости пакета '{package_name}' версии '{version}':")
    print("=" * 60)
    
    if not dependencies_dict:
        print("(нет зависимостей)")
        return
    
    # сортируем по имени для удобства
    for dep_name in sorted(dependencies_dict.keys()):
        dep_version = dependencies_dict[dep_name]
        print(f"  {dep_name}@{dep_version}")
    
    print("=" * 60)
    print(f"Всего: {len(dependencies_dict)} прямых зависимостей")


def main(argv=None):
    """
    Главная функция этапа 2.
    Парсит аргументы, получает зависимости и выводит их на экран.
    """
    # парсим аргументы из командной строки
    args = parse_args(argv)
    
    # валидируем аргументы
    validate_args(args)
    
    print("=" * 60)
    print("ЭТАП 2: СБОР ДАННЫХ О ЗАВИСИМОСТЯХ")
    print("=" * 60)
    
    # выводим параметры (как в этапе 1)
    print("\nПараметры:")
    print(f"  package: {args.package}")
    print(f"  version: {args.pkg_version}")
    print(f"  repo: {args.repo}")
    print()
    
    # получаем прямые зависимости
    print("Получение информации о зависимостях...")
    dependencies = get_direct_dependencies(args.package, args.pkg_version)
    
    # выводим результаты
    print_dependencies(dependencies, args.package, args.pkg_version)


if __name__ == '__main__':
    main()
