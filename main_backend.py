"""
лучше не изменять данный файл, кроме случаев если очень хочется исправить названия переменных или удалить ненужные функции
здесь порядок выполнения функций и порядок вызова функций
"""


from readDicom.readDicomUtils import *
from readDicom.getPaths import *
from detectObj.detObjects import *
from buildObj import calcObjParam
from readDicom.response import *


def get_available_series(dicomDirPath = "./in"):
    """
    Получение списка доступных серий в DICOM каталоге
    
    Args:
        dicomDirPath: Путь к каталогу с DICOM файлами
        
    Returns:
        Словарь с информацией о доступных сериях
    """
    # Используем обновленную функцию readDicomFolder
    series_info = readDicomFolder(dicomDirPath, "./temp", None)
    return series_info


def start_read_dicoms(dicomDirPath = "./in", saveImagePath = "./workdir", selected_series=None):
    """
    Чтение dicom файлов выбранной серии
    
    Args:
        dicomDirPath: Путь к каталогу с DICOM файлами
        saveImagePath: Путь для сохранения изображений
        selected_series: Номер выбранной серии
        
    Returns:
        currentPatientSaveFolder: Путь к папке с результатами
    """
    currentPatientSaveFolder = readDicomFolder(dicomDirPath, saveImagePath, selected_series)
    return currentPatientSaveFolder

    
def processing(dicomDirPath = "./in", saveImagePath = "./workdir", outputDir = "./out", selected_series=None):
    """
    Полный цикл обработки DICOM серии
    
    Args:
        dicomDirPath: Путь к каталогу с DICOM файлами
        saveImagePath: Путь для сохранения промежуточных изображений
        outputDir: Путь для сохранения результатов
        selected_series: Номер выбранной серии
    """
    # Чтение выбранной серии
    currentPatientSaveFolder = start_read_dicoms(dicomDirPath, saveImagePath, selected_series)
    
    # Детектирование объектов
    detect_objects(detect_folder=currentPatientSaveFolder)
    
    # Расчет параметров объектов
    inputDirOfImages = currentPatientSaveFolder
    StonesDir = calcObjParam.main(inputDirOfImages)
    
    # Сохранение результатов
    responseOutPaths(outputDir)
    copyInputDirToOutputDir(StonesDir, outputDir)


if __name__ == "__main__":
    # Точка входа для автономного запуска
    dicomDirPath = "./in"
    saveImagePath = "./workdir"
    outputDir = "./out"
    
    # Сначала получаем список доступных серий
    print("Поиск доступных DICOM серий...")
    series_info = get_available_series(dicomDirPath)
    
    if "available_series" in series_info and series_info["available_series"]:
        print("\nДоступные серии:")
        for i, series in enumerate(series_info["available_series"]):
            print(f"{i+1}. Серия {series['number']}: {series['description']} ({series['image_count']} изображений)")
        
        # Выбор серии (в автономном режиме выбираем первую)
        selected_idx = 0
        if len(series_info["available_series"]) > 1:
            try:
                selected_idx = int(input(f"\nВыберите серию (1-{len(series_info['available_series'])}): ")) - 1
                if selected_idx < 0 or selected_idx >= len(series_info["available_series"]):
                    selected_idx = 0
            except:
                selected_idx = 0
        
        selected_series = series_info["available_series"][selected_idx]["number"]
        print(f"\nВыбрана серия: {selected_series}")
        
        # Запуск обработки
        processing(dicomDirPath, saveImagePath, outputDir, selected_series)
    else:
        print("Не найдено доступных DICOM серий")