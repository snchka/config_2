import argparse
import os
import sys


def parse_args(argv=None):
	parser = argparse.ArgumentParser(description='CLI-прототип визуализатора зависимостей (этап 1)')

	parser.add_argument('--package', '-p', dest='package', required=True,
						help='Имя анализируемого пакета')

	parser.add_argument('--repo', '-r', dest='repo', required=True,
						help='URL-адрес репозитория или путь к файлу тестового репозитория')

	parser.add_argument('--test', action='store_true', dest='test_mode',
						help='Режим работы с тестовым репозиторием (указанный --repo трактуется как путь к файлу)')

	parser.add_argument('--pkg-version', dest='pkg_version', default='latest',
						help="Версия пакета (по умолчанию 'latest')")

	parser.add_argument('--out', '-o', dest='out_file', default='graph.png',
						help='Имя генерируемого файла с изображением графа (по умолчанию graph.png)')

	parser.add_argument('--ascii', action='store_true', dest='ascii_tree',
						help='Вывести зависимости в формате ASCII-дерева')

	parser.add_argument('--max-depth', dest='max_depth', type=int, default=0,
						help='Максимальная глубина анализа зависимостей (0 = без ограничения)')

	parser.add_argument('--filter', dest='filter_substr', default='',
						help='Подстрока для фильтрации пакетов (игнорировать пакеты, содержащие подстроку)')

	return parser.parse_args(argv)


def validate_args(args):
	# проверка имени пакета
	if not args.package or not args.package.strip():
		print('Ошибка: параметр --package не может быть пустым', file=sys.stderr)
		sys.exit(2)

	# проверка режима тестового репозитория и пути/URL
	if args.test_mode:
		# в тестовом режиме --repo обязан быть существующим файлом
		if not os.path.exists(args.repo):
			print(f"Ошибка: в тестовом режиме файл репозитория не найден: {args.repo}", file=sys.stderr)
			sys.exit(2)
		if not os.path.isfile(args.repo):
			print(f"Ошибка: указанный путь не является файлом: {args.repo}", file=sys.stderr)
			sys.exit(2)
	else:
		# простейшая проверка URL (для этапа 1 достаточно базовой валидации)
		repo = args.repo
		ok_prefixes = ('http://', 'https://', 'git://', 'git@')
		if not any(repo.startswith(p) for p in ok_prefixes):
			print('Ошибка: параметр --repo должен быть URL (начинаться с http://, https://, git:// или git@) '
				  'или используйте флаг --test и путь к файлу', file=sys.stderr)
			sys.exit(2)

	# версия пакета
	if not args.pkg_version or not args.pkg_version.strip():
		print('Ошибка: параметр --pkg-version не может быть пустой', file=sys.stderr)
		sys.exit(2)

	# имя выходного файла
	if not args.out_file or not args.out_file.strip():
		print('Ошибка: параметр --out не может быть пустым', file=sys.stderr)
		sys.exit(2)

	# проверка расширения
	# просто предупреждаем, если расширение не то
	_, ext = os.path.splitext(args.out_file)
	if ext and ext.lower() not in ('.png', '.svg', '.mmd', '.mermaid'):
		print(f"Внимание: расширение выходного файла '{ext}' необычное. Ожидаемые: .png, .svg, .mmd, .mermaid", file=sys.stderr)

	# max_depth
	if args.max_depth is None:
		print('Ошибка: параметр --max-depth не задан', file=sys.stderr)
		sys.exit(2)
	if args.max_depth < 0:
		print('Ошибка: параметр --max-depth должен быть >= 0 (0 = без ограничения)', file=sys.stderr)
		sys.exit(2)

	# filter_substr можно оставить пустым


def print_params(args):
	# вывести все параметры в формате ключ=значение
	# порядок отсортирован по имени ключа для стабильности
	params = {
		'package': args.package,
		'repo': args.repo,
		'test_mode': args.test_mode,
		'pkg_version': args.pkg_version,
		'out_file': args.out_file,
		'ascii_tree': args.ascii_tree,
		'max_depth': args.max_depth,
		'filter_substr': args.filter_substr,
	}

	for k in sorted(params.keys()):
		print(f"{k}={params[k]}")


def main(argv=None):
	args = parse_args(argv)
	validate_args(args)
	print_params(args)


if __name__ == '__main__':
	main()

