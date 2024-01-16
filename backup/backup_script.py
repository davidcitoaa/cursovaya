import yadisk
import os
from datetime import datetime

# Вставьте ваш токен здесь
token = "y0_AgAAAAAHrDArAADLWwAAAAD4KtKx-qc5w0nCSsqyf3m-fKTnJoN_tpo"

# Подключаемся к Яндекс.Диску
y = yadisk.YaDisk(token=token)


# Путь к папке, которую хотите забэкапить
backup_folder = "D:\\Учеба\\Универ\\3 курс\\5 семестр\\БД/Курсач\\cursovaya"

# Создаем уникальное и красивое имя папки с текущей датой и временем
backup_time = datetime.now().strftime("Backup_%Y-%m-%d_%H-%M-%S")
remote_backup_folder = "disk:/" + backup_time  # Добавляем префикс "disk:/"

# Проверяем, подключен ли Яндекс.Диск
if not y.check_token():
    print("Неверный токен!")
else:
    # Счетчик общего количества файлов
    total_files = 0

    # Проходим по всем файлам и папкам в директории
    for root, dirs, files in os.walk(backup_folder):
        total_files += len(files)

    # Проходим по всем файлам и папкам в директории
    for index, (root, dirs, files) in enumerate(os.walk(backup_folder), start=1):
        for file in files:
            local_path = os.path.join(root, file)
            remote_path = remote_backup_folder + "/" + os.path.relpath(local_path, backup_folder).replace("\\", "/")

            # Создаем все родительские папки для файла, если они еще не созданы
            parts = remote_path.split("/")
            path_to_create = "disk:/"
            for part in parts[1:-1]:  # пропускаем имя файла и первый слеш
                path_to_create += part + "/"
                if not y.exists(path_to_create):
                    y.mkdir(path_to_create)

            # Загружаем файлы
            with open(local_path, 'rb') as f:
                print(f"Загружаем файл {index}/{total_files}: {local_path}")
                y.upload(f, remote_path)

    print("Бэкап завершен.")

