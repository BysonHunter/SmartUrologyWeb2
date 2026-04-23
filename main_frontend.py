import os
import zipfile
import subprocess
import json
import glob
import shutil
import uuid
import time
import threading
import tempfile
from flask import Flask, request, render_template, send_from_directory, url_for, session, jsonify
from werkzeug.utils import secure_filename
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Сначала импортируем pydicom и патчим его для JSON сериализации
import pydicom

# Патч для обработки PersonName
def safe_personname_str(self):
    try:
        return str(self.original_string) if hasattr(self, 'original_string') else "Unknown"
    except:
        return "Unknown"

pydicom.valuerep.PersonName.__str__ = safe_personname_str
pydicom.valuerep.PersonName.__repr__ = safe_personname_str

# Базовые конфигурации
BASE_UPLOAD_FOLDER = './in'
BASE_OUTPUT_FOLDER = './out'
BASE_WORKDIR_FOLDER = './workdir'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH_JSON = "outputPath.json"

# Создаем Flask приложение
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['BASE_UPLOAD_FOLDER'] = BASE_UPLOAD_FOLDER
app.config['BASE_OUTPUT_FOLDER'] = BASE_OUTPUT_FOLDER
app.config['BASE_WORKDIR_FOLDER'] = BASE_WORKDIR_FOLDER
app.config['APP_ROOT'] = APP_ROOT
app.config['OUTPUT_PATH_JSON'] = OUTPUT_PATH_JSON
app.config['JSON_AS_ASCII'] = False  # Для поддержки кириллицы
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 час

# Глобальный словарь для хранения статуса обработки
processing_status = {}
processing_tasks = {}  # Для хранения задач обработки

# Создание базовых каталогов
os.makedirs(BASE_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(BASE_OUTPUT_FOLDER, exist_ok=True)
os.makedirs(BASE_WORKDIR_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Проверка разрешенных расширений файлов"""
    return filename.lower().endswith('.zip')


def secure_unzip_file(file_path, extract_path):
    """Безопасная распаковка ZIP архива"""
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                filename = secure_filename(member.filename)
                if filename == "":
                    continue
                zip_ref.extract(member, extract_path)
    except zipfile.BadZipFile:
        logger.error(f"Файл '{file_path}' поврежден или не является zip-архивом.", exc_info=True)
        raise ValueError("Файл поврежден или не является zip-архивом.")
    except Exception as e:
        logger.error(f"Ошибка при распаковке файла '{file_path}': {e}", exc_info=True)
        raise


def get_user_session_folders(session_id):
    """Создает уникальные пути для каждого пользователя"""
    return {
        'upload': os.path.join(BASE_UPLOAD_FOLDER, session_id),
        'workdir': os.path.join(BASE_WORKDIR_FOLDER, session_id),
        'output': os.path.join(BASE_OUTPUT_FOLDER, session_id)
    }


def cleanup_user_folders(session_id, keep_workdir=True):
    """Очистка временных файлов пользователя (только in и out, workdir сохраняем)"""
    folders = get_user_session_folders(session_id)
    
    cleaned_folders = []
    for folder_type, folder_path in folders.items():
        # Всегда сохраняем workdir
        if keep_workdir and folder_type == 'workdir':
            continue
            
        try:
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path, ignore_errors=True)
                logger.info(f"Очищена папка: {folder_path}")
                cleaned_folders.append(folder_path)
        except Exception as e:
            logger.error(f"Ошибка при очистке {folder_path}: {e}")
    
    return cleaned_folders


def ensure_user_folders(session_id):
    """Создание папок для пользовательской сессии"""
    folders = get_user_session_folders(session_id)
    for folder in folders.values():
        os.makedirs(folder, exist_ok=True)
    return folders


def update_processing_status(session_id, stage, progress, message=None, status="processing", pdf_filename=None):
    """Обновляет статус обработки для сессии"""
    processing_status[session_id] = {
        'stage': stage,
        'progress': progress,
        'message': message,
        'status': status,  # processing, completed, error
        'timestamp': time.time()
    }
    
    if pdf_filename:
        processing_status[session_id]['pdf_filename'] = pdf_filename
    
    logger.info(f"Сессия {session_id}: {stage} - {progress}% - {message}")


def get_available_series(dicom_dir):
    """
    Получение информации о доступных сериях
    
    Args:
        dicom_dir: Путь к директории с DICOM файлами
        
    Returns:
        dict: Информация о сериях и пациенте
    """
    try:
        # Импортируем необходимые функции
        from readDicom.readDicomUtils import readDicomFolder
        
        # Получаем информацию о сериях
        series_info = readDicomFolder(dicom_dir, tempfile.gettempdir(), None)
        
        # Обрабатываем результат
        if isinstance(series_info, dict) and 'available_series' in series_info:
            # Преобразуем все значения в строки
            for series in series_info['available_series']:
                for key in list(series.keys()):
                    if not isinstance(series[key], (str, int, float, bool, type(None))):
                        series[key] = str(series[key])
            
            # Обрабатываем информацию о пациенте
            if 'patient_info' in series_info:
                patient_info = series_info['patient_info']
                if isinstance(patient_info, dict):
                    for key in list(patient_info.keys()):
                        if not isinstance(patient_info[key], (str, int, float, bool, type(None))):
                            patient_info[key] = str(patient_info[key])
                else:
                    # Если это объект, конвертируем в словарь
                    series_info['patient_info'] = {
                        'patient_name': str(getattr(patient_info, 'patient_name', 'Unknown')),
                        'patient_id': str(getattr(patient_info, 'patient_id', 'Unknown')),
                        'study_date': str(getattr(patient_info, 'study_date', ''))
                    }
            
            return series_info
        
        return {"available_series": [], "patient_info": {}}
        
    except Exception as e:
        logger.error(f"Ошибка при получении информации о сериях: {e}")
        return {"available_series": [], "patient_info": {}}


def find_pdf_report(output_dir):
    """Поиск PDF отчета в указанной директории"""
    try:
        # Ищем PDF файлы рекурсивно
        pdf_files = glob.glob(os.path.join(output_dir, "**/*.pdf"), recursive=True)
        
        if pdf_files:
            # Сортируем по времени изменения (самый новый первый)
            pdf_files.sort(key=os.path.getmtime, reverse=True)
            return pdf_files[0]
        
        # Пробуем другие возможные пути
        possible_paths = [
            os.path.join(output_dir, "report.pdf"),
            os.path.join(output_dir, "*.pdf"),
        ]
        
        for path_pattern in possible_paths:
            found_files = glob.glob(path_pattern)
            if found_files:
                found_files.sort(key=os.path.getmtime, reverse=True)
                return found_files[0]
        
        return None
        
    except Exception as e:
        logger.error(f"Ошибка при поиске PDF отчета: {e}")
        return None


def process_dicom_series_thread(dicomDirPath, saveImagePath, outputDir, selected_series, session_id):
    """
    Функция для обработки DICOM серии в отдельном потоке
    """
    pdf_filename = None
    
    try:
        # Импортируем необходимые функции
        from readDicom.readDicomUtils import readDicomFolder
        from readDicom.getPaths import copyInputDirToOutputDir
        from readDicom.response import responseOutPaths
        from detectObj.detObjects import detect_objects
        from buildObj.calcObjParam import main as calc_stones
        
        # 1. Чтение выбранной серии
        update_processing_status(session_id, "Чтение DICOM серии", 10, 
                               f"Чтение серии {selected_series}...")
        logger.info(f"Чтение серии {selected_series} из {dicomDirPath}")
        
        currentPatientSaveFolder = readDicomFolder(dicomDirPath, saveImagePath, selected_series)
        
        if not os.path.exists(currentPatientSaveFolder):
            raise ValueError(f"Не удалось создать папку с результатами: {currentPatientSaveFolder}")
        
        # 2. Детектирование объектов
        update_processing_status(session_id, "Детектирование объектов", 30, 
                               "Поиск почек и камней...")
        logger.info("Детектирование объектов...")
        detect_objects(detect_folder=currentPatientSaveFolder)
        
        # 3. Расчет параметров объектов
        update_processing_status(session_id, "Расчет параметров", 60, 
                               "Анализ найденных камней...")
        logger.info("Расчет параметров камней...")
        stones_dir = calc_stones(currentPatientSaveFolder)
        
        # 4. Сохранение результатов
        update_processing_status(session_id, "Сохранение результатов", 80, 
                               "Генерация отчета...")
        logger.info("Сохранение результатов...")
        responseOutPaths(outputDir)
        
        if os.path.exists(stones_dir):
            copyInputDirToOutputDir(stones_dir, outputDir)
        
        # 5. Поиск PDF отчета
        update_processing_status(session_id, "Завершение", 90, 
                               "Поиск сгенерированного отчета...")
        
        # Даем время для сохранения файла
        time.sleep(3)
        
        # Ищем PDF отчет
        pdf_path = find_pdf_report(outputDir)
        
        if pdf_path and os.path.exists(pdf_path):
            # Получаем имя файла PDF
            pdf_filename = os.path.basename(pdf_path)
            
            # Копируем PDF в корень выходной директории для удобного доступа
            pdf_dest = os.path.join(outputDir, pdf_filename)
            
            if pdf_path != pdf_dest:
                shutil.copy2(pdf_path, pdf_dest)
            
            update_processing_status(session_id, "Завершено", 100, 
                                   "Обработка успешно завершена!", "completed", pdf_filename)
            
            logger.info(f"Обработка завершена успешно! PDF отчет: {pdf_filename}")
        else:
            update_processing_status(session_id, "Завершено с предупреждением", 100, 
                                   "PDF отчет не найден", "completed")
            logger.warning("Обработка завершена, но PDF отчет не найден")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке DICOM данных: {e}", exc_info=True)
        update_processing_status(session_id, "Ошибка", 0, 
                               f"Ошибка: {str(e)[:200]}", "error")


def start_processing_task(dicomDirPath, saveImagePath, outputDir, selected_series, session_id):
    """
    Запуск обработки в отдельном потоке
    """
    # Удаляем старую задачу если есть
    if session_id in processing_tasks:
        old_task = processing_tasks[session_id]
        if old_task.is_alive():
            try:
                old_task.join(timeout=1)
            except:
                pass
    
    # Создаем новую задачу
    task = threading.Thread(
        target=process_dicom_series_thread,
        args=(dicomDirPath, saveImagePath, outputDir, selected_series, session_id)
    )
    task.daemon = True
    task.start()
    
    # Сохраняем задачу
    processing_tasks[session_id] = task
    return task


def close_user_session(session_id):
    """
    Закрытие сессии пользователя - удаление папок in и out
    
    Args:
        session_id: ID сессии пользователя
        
    Returns:
        list: Список удаленных папок
    """
    try:
        # Останавливаем обработку если она идет
        if session_id in processing_tasks:
            task = processing_tasks[session_id]
            if task.is_alive():
                try:
                    task.join(timeout=2)
                except:
                    pass
        
        # Удаляем статус обработки
        if session_id in processing_status:
            del processing_status[session_id]
        
        # Удаляем задачу
        if session_id in processing_tasks:
            del processing_tasks[session_id]
        
        # Очищаем папки in и out (workdir сохраняем)
        cleaned_folders = cleanup_user_folders(session_id, keep_workdir=True)
        
        logger.info(f"Сессия {session_id} закрыта. Удалены папки: {cleaned_folders}")
        return cleaned_folders
        
    except Exception as e:
        logger.error(f"Ошибка при закрытии сессии {session_id}: {e}")
        return []


def cleanup_old_sessions():
    """Очистка старых сессий (вызывается периодически)"""
    try:
        current_time = time.time()
        max_age = 3600  # 1 час в секундах
        
        # Очищаем старые папки в upload
        for session_folder in os.listdir(BASE_UPLOAD_FOLDER):
            session_path = os.path.join(BASE_UPLOAD_FOLDER, session_folder)
            if os.path.isdir(session_path):
                try:
                    folder_time = os.path.getctime(session_path)
                    if current_time - folder_time > max_age:
                        shutil.rmtree(session_path, ignore_errors=True)
                        logger.info(f"Удалена старая сессия upload: {session_folder}")
                except:
                    pass
        
        # Очищаем старые папки в output
        for session_folder in os.listdir(BASE_OUTPUT_FOLDER):
            session_path = os.path.join(BASE_OUTPUT_FOLDER, session_folder)
            if os.path.isdir(session_path):
                try:
                    folder_time = os.path.getctime(session_path)
                    if current_time - folder_time > max_age:
                        shutil.rmtree(session_path, ignore_errors=True)
                        logger.info(f"Удалена старая сессия output: {session_folder}")
                except:
                    pass
                    
    except Exception as e:
        logger.error(f"Ошибка при очистке старых сессий: {e}")


@app.before_request
def before_request():
    """Инициализация сессии для каждого пользователя"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        logger.info(f"Создана новая сессия: {session['session_id']}")
    
    # Периодическая очистка старых сессий (раз в 10 запросов)
    if int(time.time()) % 10 == 0:
        cleanup_old_sessions()


@app.route('/', methods=['GET', 'POST'])
def index():
    """Главная страница с загрузкой файлов и выбором серии"""
    message = None
    error = None
    pdf_path = None
    series_list = None
    patient_info = None
    processing_active = False
    processing_completed = False
    show_results = False

    session_id = session.get('session_id')
    
    # Проверяем, есть ли завершенная обработка
    if session_id and session_id in processing_status:
        status = processing_status[session_id]
        status_type = status.get('status', '')
        
        if status_type == 'processing':
            processing_active = True
        elif status_type == 'completed':
            processing_completed = True
            show_results = True
            
            # Проверяем, есть ли PDF для скачивания
            if 'pdf_filename' in status:
                pdf_filename = status['pdf_filename']
                user_folders = get_user_session_folders(session_id)
                pdf_file_path = os.path.join(user_folders['output'], pdf_filename)
                
                if os.path.exists(pdf_file_path):
                    pdf_path = url_for('send_pdf', session_id=session_id, filename=pdf_filename)
                    message = "Обработка завершена успешно! PDF отчет готов к скачиванию."
                else:
                    # Пробуем найти PDF вручную
                    if os.path.exists(user_folders['output']):
                        pdf_files = glob.glob(os.path.join(user_folders['output'], "*.pdf"))
                        if pdf_files:
                            pdf_file = pdf_files[0]
                            pdf_filename = os.path.basename(pdf_file)
                            pdf_path = url_for('send_pdf', session_id=session_id, filename=pdf_filename)
                            message = "Обработка завершена успешно! PDF отчет готов к скачиванию."

    # Этап 1: Загрузка файлов
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']

        if not file or file.filename == '':
            error = 'Не выбран файл'
            return render_template('index.html', message=message, pdf_path=pdf_path, 
                                 error=error, series_list=series_list, patient_info=patient_info,
                                 processing_active=processing_active, show_results=show_results,
                                 processing_completed=processing_completed,
                                 session_id=session_id)

        if not allowed_file(file.filename):
            error = 'Недопустимый тип файла. Разрешены только ZIP архивы.'
            return render_template('index.html', message=message, pdf_path=pdf_path,
                                 error=error, series_list=series_list, patient_info=patient_info,
                                 processing_active=processing_active, show_results=show_results,
                                 processing_completed=processing_completed,
                                 session_id=session_id)

        filename = secure_filename(file.filename)
        user_folders = ensure_user_folders(session_id)
        file_path = os.path.join(user_folders['upload'], filename)

        try:
            # Обновляем статус - начало загрузки
            update_processing_status(session_id, "Загрузка файла", 10, "Сохранение ZIP-архива")
            
            file.save(file_path)
            
            # Обновляем статус - распаковка
            update_processing_status(session_id, "Распаковка архива", 20, "Извлечение DICOM файлов")
            
            secure_unzip_file(file_path, user_folders['upload'])
            
            # Проверяем, что файлы распаковались
            if not os.listdir(user_folders['upload']):
                error = "ZIP-архив пуст или файлы не распаковались"
                logger.error(error)
                raise ValueError(error)
                
            logger.info(f"Файлы распакованы в: {user_folders['upload']}")
            
            # Получаем список доступных серий
            update_processing_status(session_id, "Поиск DICOM серий", 30, "Анализ структуры данных")
            
            series_info = get_available_series(user_folders['upload'])
            
            if 'available_series' in series_info and series_info['available_series']:
                # Сохраняем в сессии
                session['series_list'] = series_info['available_series']
                session['patient_info'] = series_info.get('patient_info', {})
                session['uploaded_dir'] = user_folders['upload']
                
                series_list = session['series_list']
                patient_info = session['patient_info']
                
                message = f"Найдено {len(series_list)} DICOM серий. Выберите серию для анализа."
                
                # Сбрасываем статус обработки только если она не активна
                if not processing_active:
                    if session_id in processing_status:
                        del processing_status[session_id]
            else:
                error = "Не найдено доступных DICOM серий в загруженных файлах"
                cleanup_user_folders(session_id, keep_workdir=True)
            
        except Exception as e:
            error = f"Ошибка при сохранении или распаковке файла: {e}"
            logger.error(error, exc_info=True)
            cleanup_user_folders(session_id, keep_workdir=True)
            
        finally:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
    
    # Этап 2: Выбор и обработка серии
    elif request.method == 'POST' and 'selected_series' in request.form:
        try:
            selected_series = int(request.form['selected_series'])
            
            # Проверяем наличие необходимых данных
            if ('uploaded_dir' not in session or 
                'series_list' not in session):
                error = "Данные сессии утеряны. Пожалуйста, загрузите файлы заново."
                return render_template('index.html', message=message, pdf_path=pdf_path,
                                     error=error, series_list=series_list, patient_info=patient_info,
                                     processing_active=processing_active, show_results=show_results,
                                     processing_completed=processing_completed,
                                     session_id=session_id)
            
            # Проверяем, не идет ли уже обработка
            if processing_active:
                error = "Обработка уже запущена. Пожалуйста, дождитесь завершения."
                return render_template('index.html', message=message, pdf_path=pdf_path,
                                     error=error, series_list=series_list, patient_info=patient_info,
                                     processing_active=True, show_results=show_results,
                                     processing_completed=processing_completed,
                                     session_id=session_id)
            
            # Сохраняем выбранную серию
            session['selected_series'] = selected_series
            
            # Получаем папки пользователя
            user_folders = ensure_user_folders(session_id)
            
            # Очищаем предыдущие результаты
            if os.path.exists(user_folders['output']):
                shutil.rmtree(user_folders['output'], ignore_errors=True)
            os.makedirs(user_folders['output'], exist_ok=True)
            
            # Запускаем обработку в отдельном потоке
            task = start_processing_task(
                dicomDirPath=session['uploaded_dir'],
                saveImagePath=user_folders['workdir'],
                outputDir=user_folders['output'],
                selected_series=selected_series,
                session_id=session_id
            )
            
            processing_active = True
            message = f"Запущена обработка серии {selected_series}. Это может занять несколько минут..."
            
            # Сохраняем информацию о выбранной серии
            for series in session['series_list']:
                if series['number'] == selected_series:
                    session['selected_series_info'] = series
                    break
            
        except ValueError:
            error = "Неверный номер серии. Пожалуйста, выберите серию из списка."
        except Exception as e:
            error = f"Ошибка при запуске обработки: {e}"
            logger.error(error, exc_info=True)
            update_processing_status(session_id, "Ошибка", 0, str(e), "error")
    
    # Отображаем существующие данные
    if 'series_list' in session:
        series_list = session['series_list']
        patient_info = session.get('patient_info', {})
    
    # Проверяем, есть ли уже готовые результаты (PDF) без активной обработки
    if not processing_active and not show_results and session_id:
        user_folders = get_user_session_folders(session_id)
        if os.path.exists(user_folders['output']):
            pdf_files = glob.glob(os.path.join(user_folders['output'], "*.pdf"))
            if pdf_files:
                pdf_file = pdf_files[0]
                pdf_filename = os.path.basename(pdf_file)
                pdf_path = url_for('send_pdf', session_id=session_id, filename=pdf_filename)
                show_results = True
                processing_completed = True
                message = "Обнаружен предыдущий результат анализа. PDF отчет готов к скачиванию."
                
                # Обновляем статус
                update_processing_status(session_id, "Завершено", 100, 
                                       "Обнаружен предыдущий результат", "completed", pdf_filename)
    
    return render_template('index.html', message=message, pdf_path=pdf_path,
                         error=error, series_list=series_list, patient_info=patient_info,
                         processing_active=processing_active, show_results=show_results,
                         processing_completed=processing_completed,
                         session_id=session_id)


@app.route('/progress')
def get_progress():
    """Возвращает текущий статус обработки для сессии"""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': 'Сессия не найдена'})
    
    status = processing_status.get(session_id, {})
    
    # Если обработка завершена более 30 секунд назад, сохраняем только PDF информацию
    if status.get('status') == 'completed':
        timestamp = status.get('timestamp', 0)
        if time.time() - timestamp > 30:  # 30 секунд после завершения
            # Сохраняем только PDF информацию
            if 'pdf_filename' in status:
                pdf_info = {
                    'status': 'completed',
                    'pdf_filename': status['pdf_filename'],
                    'progress': 100,
                    'stage': 'Завершено',
                    'message': 'Обработка завершена успешно!'
                }
                processing_status[session_id] = pdf_info
                return jsonify(pdf_info)
    
    return jsonify(status)


@app.route('/out/<session_id>/<filename>')
def send_pdf(session_id, filename):
    """Отдача файлов с проверкой session_id для безопасности"""
    user_output_folder = os.path.join(BASE_OUTPUT_FOLDER, session_id)
    
    # Дополнительная проверка безопасности
    if not os.path.exists(user_output_folder):
        return "Файл не найден", 404
    
    file_path = os.path.join(user_output_folder, filename)
    if not os.path.exists(file_path):
        return "Файл не найден", 404
    
    # Проверяем расширение файла
    if not filename.lower().endswith('.pdf'):
        return "Недопустимый тип файла", 400
        
    return send_from_directory(user_output_folder, filename, as_attachment=True)


@app.route('/close_session', methods=['POST'])
def close_session():
    """Закрытие текущей сессии пользователя (AJAX)"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'status': 'error', 'message': 'Сессия не найдена'})
        
        cleaned_folders = close_user_session(session_id)
        
        # Очищаем сессию
        session.clear()
        
        # Создаем новую сессию
        new_session_id = str(uuid.uuid4())
        session['session_id'] = new_session_id
        
        return jsonify({
            'status': 'success', 
            'message': f'Сессия закрыта. Удалено {len(cleaned_folders)} папок.',
            'new_session_id': new_session_id
        })
        
    except Exception as e:
        logger.error(f"Ошибка при закрытии сессии: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/reset_processing', methods=['POST'])
def reset_processing():
    """Сброс статуса обработки (используется после показа результатов)"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'status': 'error', 'message': 'Сессия не найдена'})
        
        # Получаем папки пользователя
        user_folders = get_user_session_folders(session_id)
        
        # Удаляем статус обработки
        if session_id in processing_status:
            del processing_status[session_id]
        
        # Удаляем задачу обработки
        if session_id in processing_tasks:
            del processing_tasks[session_id]
        
        # Очищаем выходную папку (но сохраняем workdir для возможного повторного использования)
        if os.path.exists(user_folders['output']):
            shutil.rmtree(user_folders['output'], ignore_errors=True)
        
        # Очищаем некоторые данные сессии, но оставляем загруженные файлы
        if 'selected_series' in session:
            del session['selected_series']
        if 'selected_series_info' in session:
            del session['selected_series_info']
        
        return jsonify({'status': 'success', 'message': 'Статус обработки сброшен. Можно начать новый анализ.'})
        
    except Exception as e:
        logger.error(f"Ошибка при сбросе обработки: {e}")
        return jsonify({'status': 'error', 'message': str(e)})


@app.errorhandler(413)
def too_large(e):
    return "Файл слишком большой", 413


@app.errorhandler(404)
def not_found(e):
    return "Страница не найдена", 404


@app.errorhandler(500)
def internal_error(e):
    return "Внутренняя ошибка сервера", 500


if __name__ == '__main__':
    # Запускаем автоматическую очистку старых сессий в отдельном потоке
    def auto_cleanup():
        while True:
            time.sleep(600)  # 10 минут
            cleanup_old_sessions()
    
    cleanup_thread = threading.Thread(target=auto_cleanup, daemon=True)
    cleanup_thread.start()
    
    logger.info("Сервер запускается...")
    logger.info(f"Папка загрузок: {BASE_UPLOAD_FOLDER}")
    logger.info(f"Папка результатов: {BASE_OUTPUT_FOLDER}")
    logger.info(f"Папка временных файлов: {BASE_WORKDIR_FOLDER}")
    
    app.run(debug=True, threaded=True, port=5000, host='0.0.0.0')