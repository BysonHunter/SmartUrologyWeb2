def getSeriesNumber(series_numbers, SeriesDescription, CountOfImages):
    """
    Возвращает список всех доступных серий для выбора пользователем.
    
    Args:
        series_numbers: Список номеров серий
        SeriesDescription: Список описаний серий
        CountOfImages: Список количества изображений в каждой серии
        
    Returns:
        Список словарей с информацией о всех сериях для выбора пользователем
    """
    
    series_list = []
    
    try:
        for i in range(len(series_numbers)):
            series_info = {
                "number": series_numbers[i],
                "description": SeriesDescription[i] if i < len(SeriesDescription) else "Unknown",
                "image_count": CountOfImages[i] if i < len(CountOfImages) else 0,
                "chance_str": f'Series: {series_numbers[i]}, Descr: {SeriesDescription[i] if i < len(SeriesDescription) else "Unknown"}, SOP: {CountOfImages[i] if i < len(CountOfImages) else 0}'
            }
            series_list.append(series_info)
            
    except IndexError:
        print("Ошибка: списки series_numbers, SeriesDescription и CountOfImages имеют разную длину.")
        return []
    except Exception as e:
        print(f"Ошибка при обработке серий: {e}")
        return []
    
    return series_list