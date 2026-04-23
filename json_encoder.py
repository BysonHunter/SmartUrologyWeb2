"""
Кастомный JSON энкодер для обработки объектов pydicom
"""

import json
from datetime import datetime
from decimal import Decimal
import pydicom
from pydicom.multival import MultiValue


class PydicomJSONEncoder(json.JSONEncoder):
    """Кастомный JSON энкодер для обработки объектов pydicom"""
    
    def default(self, obj):
        # Обработка PersonName из pydicom
        if isinstance(obj, pydicom.valuerep.PersonName):
            return str(obj)
        
        # Обработка MultiValue из pydicom
        if isinstance(obj, MultiValue):
            return list(obj)
        
        # Обработка datetime
        if isinstance(obj, (datetime, pydicom.valuerep.DA, pydicom.valuerep.DT, pydicom.valuerep.TM)):
            return str(obj)
        
        # Обработка Decimal
        if isinstance(obj, Decimal):
            return float(obj)
        
        # Обработка других специальных типов pydicom
        if hasattr(obj, '__dict__'):
            # Преобразуем объект в словарь
            result = {}
            for key, value in obj.__dict__.items():
                if not key.startswith('_'):
                    result[key] = self.default(value)
            return result
        
        # Для всех остальных типов используем стандартную обработку
        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError:
            return str(obj)


def pydicom_to_dict(ds):
    """
    Конвертирует Dataset pydicom в словарь
    
    Args:
        ds: Dataset pydicom
        
    Returns:
        dict: Словарь с данными
    """
    if ds is None:
        return {}
    
    result = {}
    for elem in ds:
        # Пропускаем пиксельные данные
        if elem.tag == pydicom.tag.Tag(0x7FE0, 0x0010):  # PixelData
            continue
        
        key = str(elem.name).replace(' ', '_')
        
        try:
            # Преобразуем значение
            if isinstance(elem.value, (pydicom.valuerep.PersonName, 
                                      pydicom.valuerep.DA, 
                                      pydicom.valuerep.DT, 
                                      pydicom.valuerep.TM)):
                result[key] = str(elem.value)
            elif isinstance(elem.value, MultiValue):
                result[key] = list(elem.value)
            elif isinstance(elem.value, Decimal):
                result[key] = float(elem.value)
            else:
                result[key] = elem.value
        except:
            result[key] = str(elem.value)
    
    return result


def safe_json_dumps(data):
    """
    Безопасная сериализация JSON с поддержкой pydicom объектов
    
    Args:
        data: Данные для сериализации
        
    Returns:
        str: JSON строка
    """
    return json.dumps(data, cls=PydicomJSONEncoder, ensure_ascii=False)