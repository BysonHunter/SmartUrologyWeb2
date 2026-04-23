class SliceDTO:
    def __init__(self, label, x, z, w, h, conf):
        self.label = label
        self.x = x
        self.z = z
        self.w = w
        self.h = h
        self.conf = conf

        self.min_x = self.x - w / 2
        self.max_x = self.x + w / 2
        self.min_z = self.z - h / 2
        self.max_z = self.z + h / 2


class LayerDTO:
    def __init__(self, y, slice_list):
        self.y = y
        self.slice_list = slice_list


class ObjectParamsDto:
    def __init__(self, x_center, z_center, w, h, number, first_index, last_index):
        self.x_center = x_center
        self.z_center = z_center
        self.w = w
        self.h = h
        self.number = number
        self.first_index = first_index
        self.last_index = last_index


class Parser:
    """ нужно ли парсить строку файла """

    def parse_condition(self, line):
        first_token = line.split(' ')[0]
        return first_token.isdigit()

    ''' преобразование строки в объект '''

    def line_transform(self, line):
        tokens = list(map(lambda x: float(x), line.split(' ')))
        return SliceDTO(
            label=tokens[0],
            x=tokens[1],
            z=tokens[2],
            w=tokens[3],
            h=tokens[4],
            conf=tokens[5]
        )

    ''' парсинг имени файла '''

    def filename_parser(self, filename):
        return int(filename[5:8])

    ''' парсинг файла '''

    def parse(self, path, filename):
        file = open(path + filename, 'r', encoding="ISO-8859-1")
        try:
            lines = [line for line in file.readlines() if self.parse_condition(line)]
            y = self.filename_parser(filename)
            layer = LayerDTO(y, list(map(self.line_transform, lines)))
            return layer
        except Exception:
            file.close()
            raise


class kidney_type:
    normal = 0
    pieloectasy = 1
