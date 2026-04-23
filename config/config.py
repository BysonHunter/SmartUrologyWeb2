class Config:
    locale: str
    gamma: float
    frequency_from: float
    frequency_to: float
    frequency_step: float
    energy_from: float
    energy_to: float
    energy_step: float
    mass: float
    round_numbers_count: int
    # color_theme: [str]
    # color_text_theme: [str]

    @staticmethod
    def create_default(stone_mass):
        config = Config()
        # config.locale = "RU"
        config.gamma = 0.4
        config.frequency_from = 8
        config.frequency_to = 15
        config.frequency_step = 1
        config.energy_from = 0.6
        config.energy_to = 2.4
        config.energy_step = 0.1
        config.mass = stone_mass
        config.round_numbers_count = 2
        config.color_theme = [
            (124, 179, 66),
            (67, 160, 71),
            (0, 137, 123),
            (0, 172, 193),
            (3, 155, 229),
            (30, 136, 229),
            (57, 73, 171),
            (94, 53, 177),
            (142, 36, 170),
            (216, 27, 96)
        ]

        config.color_text_theme = [
            (0, 0, 0),
            (0, 0, 0),
            (0, 0, 0),
            (0, 0, 0),
            (0, 0, 0),
            (0, 0, 0),
            (255, 255, 255),
            (255, 255, 255),
            (255, 255, 255),
            (255, 255, 255)
        ]

        return config


class ConfigProvider:
    _config: Config

    def init(self, config: Config):
        self._config = config

    def get_config(self):
        return self._config


config_provider_instance = ConfigProvider()
