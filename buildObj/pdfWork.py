import os.path
from fpdf import FPDF
from pathlib import Path
from readDicom.constants import img_format
from numpy import arange, around, tile, linspace
from config.config import Config


font_path = r"DejaVuSerifCondensed.ttf"

def _get_project_root() -> Path:
    """Корень проекта (SUD_v3) относительно текущего файла."""
    return Path(__file__).resolve().parents[1]


def _calc_laser_table(stone_mass: float):
    """
    Расчёт таблицы времени разрушения камня по формуле:
    t = m / (gamma * E * f)
    """
    cfg = Config.create_default(stone_mass=stone_mass)
    round_numbers = cfg.round_numbers_count

    energy_range = arange(cfg.energy_from, cfg.energy_to + cfg.energy_step, cfg.energy_step)
    frequency_range = arange(cfg.frequency_from, cfg.frequency_to + cfg.frequency_step, cfg.frequency_step)
    energy = tile(energy_range.reshape(-1, 1), (1, frequency_range.size))
    frequency = tile(frequency_range.reshape(1, -1), (energy_range.size, 1))
    result = around(stone_mass / (cfg.gamma * energy * frequency), round_numbers)

    bounds = linspace(result.min(), result.max(), len(cfg.color_theme) + 1)
    cell_colors = []
    for i in range(len(bounds) - 1):
        cell_colors.append(
            {
                "min": bounds[i],
                "max": bounds[i + 1],
                "background": cfg.color_theme[i],
                "text": cfg.color_text_theme[i],
            }
        )

    frequency_labels = [str(round(i, round_numbers)) for i in frequency[0]]
    energy_labels = [str(round(i[0], round_numbers)) for i in energy]
    return frequency_labels, energy_labels, result, cell_colors


def _append_laser_table(pdf: FPDF, stone_mass: float):
    """
    Добавляет в PDF таблицу времени разрушения для указанной массы камня.
    """
    frequency_labels, energy_labels, values, cell_colors = _calc_laser_table(stone_mass)
    height = 5
    left_col_w = 30
    value_col_w = 10  # одинаковая ширина для заголовка и значений

    pdf.cell(left_col_w, height, "Частота, Гц", 1, align="C")
    for lbl in frequency_labels:
        pdf.cell(value_col_w, height * 2, lbl, 1, align="C")
    pdf.ln(height)
    pdf.cell(left_col_w, height, "Энергия, Дж", 1, align="C")
    pdf.ln(height)

    for i in range(len(values)):
        pdf.cell(left_col_w, height, energy_labels[i], 1, fill=False, align="C")
        for j in range(len(values[i])):
            cur_value = values[i][j]
            for color in cell_colors:
                if color["min"] <= cur_value <= color["max"]:
                    pdf.set_fill_color(*color["background"])
                    pdf.set_text_color(*color["text"])
                    break
            pdf.cell(value_col_w, height, str(cur_value), 1, fill=True)
        pdf.ln(height)
        pdf.set_text_color(0, 0, 0)
        

def create_PDF(stones_dir_path, RS_params, LS_params, param_numpy):
    
    root = _get_project_root()
    logo_path = root / "icons" / "logo.png"
    
    # font_path = r"./fonts/DejaVuSerifCondensed.ttf"
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    pdf.add_font('DejaVu', '', font_path, uni=True)
    pdf.set_font('DejaVu', '', 8)
    width = 150
    height = 5
    col_width = pdf.w / 3.5
    row_height = pdf.font_size
    spacing = 1

    if logo_path.exists():
        pdf.image(x=20, name=str(logo_path), w=150, h=20)
    pdf.cell(width, height, txt=f'', ln=1, align="C")
    research = Path(stones_dir_path).parts[-2]

    pdf.cell(width, height, txt=f'Пациент: {param_numpy[2]}, ID пациента {param_numpy[3]}', ln=1, align="L")
    pdf.cell(width, height, txt=f'Дата исследования КТ: {param_numpy[0]}', ln=1, align="L")
    pdf.cell(width, height, txt=f'Дата исследования поиска камней: {research}', ln=1, align="L")

    #  pdf.add_page()  # Вставка новой страницы
    
    pdf.cell(width, height, txt=f'В правой почке найдено {len(RS_params)} камней', ln=1, align="L")
    if len(RS_params) > 0:
        pdf.cell(width, height, txt="Параметры камней", ln=1, align="L")
        for stone in range(len(RS_params)):
            r_data = [['размеры камня                    ', f'{RS_params[stone][2]:.2f} см Х {RS_params[stone][3]:.2f} '
                                                            f'см Х {RS_params[stone][4]:.2f} см'],
                      ['масса камня, грамм               ', f'{RS_params[stone][10]:.2f}'],
                      ['средняя плотность, гр/см3        ', f'{RS_params[stone][11]:.2f}'],
                      ['масса по средней плотности, грамм', f'{RS_params[stone][12]:.2f}'],
                      ['максимальная плотность по HU     ', f'{RS_params[stone][13]}'],
                      ['минимальная плотность по HU      ', f'{RS_params[stone][14]}'],
                      ['средняя плотность по HU          ', f'{RS_params[stone][15]:.0f}']
                      ]

                        
            pdf.cell(width, height, txt=f'Правая почка. Камень № {stone + 1}', ln=1, align="L")
            detImgWStoneDest = (
                stones_dir_path + 
                param_numpy[3] + 
                '_' + 
                str(RS_params[stone][1]) + 
                '.' + img_format
                )
            if os.path.exists(detImgWStoneDest):
                pdf.image(detImgWStoneDest, w=70, h=70)
            pdf.image(stones_dir_path + '/stone_rk_' + str(stone) + '.png', w=50, h=50)
            x_pos = pdf.get_x()
            y_pos = pdf.get_y()
            if os.path.exists(stones_dir_path + '/stonerk_' + str(stone) + '_1.png'):
                pdf.image(x=x_pos + 50, y=y_pos - 50, name=stones_dir_path + '/stonerk_' + str(stone) + '_1.png', w=100,
                          h=50)
            for row in r_data:
                for item in row:
                    pdf.cell(col_width, row_height * spacing, txt=item, border=1)
                pdf.ln(row_height * spacing)
            pdf.ln(row_height * spacing)
            pdf.cell(width, height, txt='Таблица времени разрушения камня', ln=1, align="L")
            _append_laser_table(pdf, float(RS_params[stone][10]))
            pdf.ln(row_height * spacing)
        pdf.ln(pdf.h)
        

    #  pdf.add_page() # Вставка новой страницы
    
    pdf.cell(width, height, txt=f'В левой почке найдено {len(LS_params)} камней', ln=1, align="L")
    if len(LS_params) > 0:
        pdf.cell(width, height, txt="Параметры камней", ln=1, align="L")
        for stone in range(len(LS_params)):
            l_data = [['размеры камня                    ', f'{LS_params[stone][2]:.2f} см Х {LS_params[stone][3]:.2f} '
                                                            f'см Х {LS_params[stone][4]:.2f} см'],
                      ['масса камня, грамм               ', f'{LS_params[stone][10]:.2f}'],
                      ['средняя плотность, гр/см3        ', f'{LS_params[stone][11]:.2f}'],
                      ['масса по средней плотности, грамм', f'{LS_params[stone][12]:.2f}'],
                      ['максимальная плотность по HU     ', f'{LS_params[stone][13]}'],
                      ['минимальная плотность по HU      ', f'{LS_params[stone][14]}'],
                      ['средняя плотность по HU          ', f'{LS_params[stone][15]:.0f}']
                      ]

                        
            pdf.cell(width, height, txt=f'Левая почка. Камень № {stone + 1}', ln=1, align="L")
            detImgWStoneDest = (stones_dir_path 
                                + param_numpy[3] 
                                + '_' 
                                + str(LS_params[stone][1]) 
                                + '.' 
                                + img_format
            )
            if os.path.exists(detImgWStoneDest):
                pdf.image(detImgWStoneDest, w=70, h=70)
            pdf.image(stones_dir_path + '/stone_lk_' + str(stone) + '.png', w=50, h=50)
            x_pos = pdf.get_x()
            y_pos = pdf.get_y()
            if os.path.exists(stones_dir_path + '/stonelk_' + str(stone) + '_1.png'):
                pdf.image(x=x_pos + 50, y=y_pos - 50, name=stones_dir_path + '/stonelk_' + str(stone) + '_1.png', w=100,
                          h=50)
            for row in l_data:
                for item in row:
                    pdf.cell(col_width, row_height * spacing, txt=item, border=1)
                pdf.ln(row_height * spacing)
            pdf.ln(row_height * spacing)
            pdf.cell(width, height, txt='Таблица времени разрушения камня', ln=1, align="L")
            _append_laser_table(pdf, float(LS_params[stone][10]))
            pdf.ln(row_height * spacing)
    pdfFileName = stones_dir_path + f'{param_numpy[3]}_{research}SI.pdf'
    if os.path.exists(pdfFileName):
        os.remove(pdfFileName)
    pdf.output(pdfFileName)
    return pdfFileName


def read_n_print_pdf(pdfFileName):
    import webbrowser
    file_to_open = r"file://" + str(pdfFileName)
    webbrowser.open_new(file_to_open)
