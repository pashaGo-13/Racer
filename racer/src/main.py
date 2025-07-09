import sys
import random
from PyQt6.QtGui import QPainter, QColor, QFont, QImage, QPainterPath
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QElapsedTimer, QUrl
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtMultimedia import QSoundEffect

# --- Константы игры ---
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600
PLAYER_SPEED_INCREMENT = 0.5
MAX_PLAYER_SPEED = 10
TRAFFIC_CAR_SPEED_MIN = 3
TRAFFIC_CAR_SPEED_MAX = 7
NUM_LANES = 3

# --- Состояния игры ---
class GameState:
    MENU = 0
    PLAYING = 1
    SETTINGS = 2
    GAME_OVER = 3
    AUDIO_SETTINGS = 4
    DIFFICULTY_SETTINGS = 5
    GRAPHICS_SETTINGS = 6
    CONTROLS_SETTINGS = 7

# --- Класс игрового автомобиля ---
class PlayerCar:
    def __init__(self):
        self.width = 60
        self.height = 96
        self.x = (SCREEN_WIDTH / 2) - (self.width / 2)
        self.y = SCREEN_HEIGHT - self.height - 20
        self.speed = 0
        self.image = QImage("src/assets/images/player_car.png")
        if self.image.isNull():
            print("Ошибка: Не удалось загрузить изображение игрока")

    def get_rect(self):
        return QRectF(self.x, self.y, self.width, self.height)

    def draw(self, painter):
        scaled_image = self.image.scaled(self.width, self.height,
                                      Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)
        painter.drawImage(int(self.x), int(self.y), scaled_image)

# --- Класс встречного автомобиля ---
class TrafficCar:
    def __init__(self, x, y, base_speed, car_type):
        self.width = 60
        self.height = 98
        self.x = x
        self.y = y
        self.base_speed = base_speed
        
        # Выбираем случайное изображение машины
        car_images = [
            "src/assets/images/enemy_car_1.png",
            "src/assets/images/enemy_car_2.png",
            "src/assets/images/enemy_car_3.png"
        ]
        self.image = QImage(car_images[car_type])
        
        if self.image.isNull():
            print(f"Ошибка загрузки изображения машины типа {car_type}")

    def update(self, dt, player_speed):
        effective_speed = self.base_speed + player_speed * 1.5
        self.y += effective_speed * dt * 60

    def get_rect(self):
        return QRectF(self.x, self.y, self.width, self.height)

    def draw(self, painter):
        scaled_image = self.image.scaled(self.width, self.height,
                                      Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)
        painter.drawImage(int(self.x), int(self.y), scaled_image)

# --- Основной класс игры ---
class GameWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setWindowTitle("Traffic Racer Qt6")
        
        # Инициализация игровых параметров
        self.init_game()
        
        # Настройка таймеров
        self.setup_timers()
        
        # Загрузка ресурсов
        self.load_resources()

    def init_game(self):
        """Инициализация игровых переменных"""
        self.game_state = GameState.MENU
        self.score = 0
        self.player_car = PlayerCar()
        self.traffic_cars = []
        
        # Настройки по умолчанию
        self.music_volume = 50
        self.sound_volume = 70
        self.difficulty = 1
        self.graphics_quality = 2
        self.auto_acceleration = True
        
        # Состояния клавиш
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.space_pressed = False

    def setup_timers(self):
        """Настройка игровых таймеров"""
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.game_loop)
        self.game_timer.start(16)  # ~60 FPS
        
        self.elapsed_timer = QElapsedTimer()
        self.elapsed_timer.start()
        
        self.spawn_traffic_timer = QTimer(self)
        self.spawn_traffic_timer.timeout.connect(self.spawn_traffic_car)
        self.spawn_traffic_timer_interval = 2000  # 2 секунды

    def load_resources(self):
        """Загрузка звуков и изображений"""
        # Звуковые эффекты
        self.sound_effects = {
            'gas': QSoundEffect(),
            'brake': QSoundEffect(),
            'crash': QSoundEffect(),
            'honk': QSoundEffect()
        }
        
        sound_files = {
            'gas': "src/assets/sounds/gas.wav",
            'brake': "src/assets/sounds/brake.wav",
            'crash': "src/assets/sounds/crash.wav",
            'honk': "src/assets/sounds/honk.wav"
        }
        
        for name, path in sound_files.items():
            self.sound_effects[name].setSource(QUrl.fromLocalFile(path))
        
        self.update_sound_volumes()
        
        # Дорожное полотно
        self.road_offset = 0
        self.road_speed_multiplier = 5
        self.road_image = QImage("src/assets/images/road.png")
        if self.road_image.isNull():
            print("Ошибка загрузки дорожного полотна")
            self.scaled_road_image = None
        else:
            self.scaled_road_image = self.road_image.scaled(
                SCREEN_WIDTH, SCREEN_WIDTH,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

    # --- Основной игровой цикл ---
    def game_loop(self):
        delta_time = self.elapsed_timer.restart() / 1000.0
        
        if self.game_state == GameState.PLAYING:
            self.update_game_state(delta_time)
        
        self.update()

    def update_game_state(self, dt):
        """Обновление игрового состояния"""
        self.update_player_position(dt)
        self.update_traffic(dt)
        self.update_road_animation()

    def update_player_position(self, dt):
        """Обновление позиции игрока"""
        if self.left_pressed:
            self.player_car.x = max(0, self.player_car.x - 300 * dt)
        if self.right_pressed:
            self.player_car.x = min(SCREEN_WIDTH - self.player_car.width, 
                                  self.player_car.x + 300 * dt)
        
        if not self.auto_acceleration:
            if self.up_pressed:
                self.player_car.speed = min(MAX_PLAYER_SPEED, 
                                          self.player_car.speed + PLAYER_SPEED_INCREMENT * dt * 60)
            if self.down_pressed:
                self.player_car.speed = max(0, 
                                          self.player_car.speed - PLAYER_SPEED_INCREMENT * dt * 60)
        else:
            self.player_car.speed = min(MAX_PLAYER_SPEED, 
                                      self.player_car.speed + PLAYER_SPEED_INCREMENT * dt * 30)
        
        # Обработка звуков
        self.handle_sound_effects()

    def handle_sound_effects(self):
        """Управление звуковыми эффектами"""
        if self.up_pressed and not self.auto_acceleration and not self.sound_effects['gas'].isPlaying():
            self.play_sound('gas')
        elif not self.up_pressed and self.sound_effects['gas'].isPlaying():
            self.sound_effects['gas'].stop()
            
        if self.down_pressed and not self.auto_acceleration and not self.sound_effects['brake'].isPlaying():
            self.play_sound('brake')
        elif not self.down_pressed and self.sound_effects['brake'].isPlaying():
            self.sound_effects['brake'].stop()
            
        if self.space_pressed and not self.sound_effects['honk'].isPlaying():
            self.play_sound('honk')
        elif not self.space_pressed and self.sound_effects['honk'].isPlaying():
            self.sound_effects['honk'].stop()

    def update_traffic(self, dt):
        """Обновление трафика и проверка столкновений"""
        cars_to_remove = []
        
        for car in self.traffic_cars:
            car.update(dt, self.player_car.speed)
            
            if car.y > SCREEN_HEIGHT:
                cars_to_remove.append(car)
                self.score += 10
                
            if self.player_car.get_rect().intersects(car.get_rect()):
                self.play_sound('crash')
                self.game_over()
                
        for car in cars_to_remove:
            self.traffic_cars.remove(car)

    def update_road_animation(self):
        """Анимация дорожного полотна"""
        if self.scaled_road_image and not self.scaled_road_image.isNull():
            self.road_offset += (self.road_speed_multiplier + self.player_car.speed) * 0.06
            self.road_offset %= SCREEN_HEIGHT

    def spawn_traffic_car(self):
        if self.game_state != GameState.PLAYING:
            return
        
        lane_index = random.randint(0, NUM_LANES - 1)
        lane_center = (SCREEN_WIDTH / NUM_LANES) * (lane_index + 0.5)
        x_pos = lane_center - 25
    
        # Выбираем случайный тип машины (0, 1 или 2)
        car_type = random.randint(0, 2)
    
        # Базовая скорость в зависимости от сложности
        base_speed = self.get_traffic_speed()
    
        # Модификатор скорости в зависимости от типа машины
        speed_modifiers = [0.9, 1.0, 1.1]  # Медленные, нормальные, быстрые
        speed = base_speed * speed_modifiers[car_type]
    
        # Проверка на перекрытие с другими машинами
        if not any(abs(car.x - x_pos) < 50 and car.y < 150 for car in self.traffic_cars):
            self.traffic_cars.append(TrafficCar(x_pos, -80, speed, car_type))

    def get_traffic_speed(self):
        """Возвращает базовую скорость в зависимости от сложности"""
        base_min = TRAFFIC_CAR_SPEED_MIN
        base_max = TRAFFIC_CAR_SPEED_MAX
    
        if self.difficulty == 0:  # Легкий
            return random.uniform(base_min, base_min + (base_max - base_min) * 0.5)
        elif self.difficulty == 1:  # Средний
            return random.uniform(base_min, base_max)
        else:  # Сложный
            return random.uniform(base_min + (base_max - base_min) * 0.5, base_max + 2)

    def game_over(self):
        """Обработка окончания игры"""
        self.game_state = GameState.GAME_OVER
        self.spawn_traffic_timer.stop()

    def start_new_game(self):
        """Начало новой игры"""
        self.game_state = GameState.PLAYING
        self.reset_game()
        self.spawn_traffic_timer.start(self.spawn_traffic_timer_interval)

    def reset_game(self):
        """Сброс игровых параметров"""
        self.score = 0
        self.player_car = PlayerCar()
        self.traffic_cars = []
        self.road_offset = 0
        self.elapsed_timer.restart()

    # --- Методы работы со звуком ---
    def update_sound_volumes(self):
        """Обновление громкости звуков"""
        for sound in self.sound_effects.values():
            sound.setVolume(self.sound_volume / 100.0)

    def play_sound(self, sound_name):
        """Воспроизведение звука"""
        if sound_name in self.sound_effects:
            self.sound_effects[sound_name].play()

    # --- Методы отрисовки ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.game_state == GameState.MENU:
            self.draw_menu(painter)
        elif self.game_state == GameState.SETTINGS:
            self.draw_settings_menu(painter)
        elif self.game_state == GameState.AUDIO_SETTINGS:
            self.draw_audio_settings(painter)
        elif self.game_state == GameState.DIFFICULTY_SETTINGS:
            self.draw_difficulty_settings(painter)
        elif self.game_state == GameState.GRAPHICS_SETTINGS:
            self.draw_graphics_settings(painter)
        elif self.game_state == GameState.CONTROLS_SETTINGS:
            self.draw_controls_settings(painter)
        elif self.game_state in (GameState.PLAYING, GameState.GAME_OVER):
            self.draw_game(painter)
            
            if self.game_state == GameState.GAME_OVER:
                self.draw_game_over(painter)

    def draw_game(self, painter):
        """Отрисовка игрового экрана"""
        # Дорожное полотно
        if self.scaled_road_image:
            painter.drawImage(0, int(self.road_offset), self.scaled_road_image)
            painter.drawImage(0, int(self.road_offset - SCREEN_HEIGHT), self.scaled_road_image)
        else:
            painter.fillRect(self.rect(), QColor(50, 50, 50))
        
        # Машины
        self.player_car.draw(painter)
        for car in self.traffic_cars:
            car.draw(painter)
        
        # Интерфейс
        painter.setFont(QFont("Arial", 16))
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(10, 30, f"Счет: {self.score}")
        painter.drawText(10, 60, f"Скорость: {int(self.player_car.speed * 10)} км/ч")

    def draw_game_over(self, painter):
        """Отрисовка экрана окончания игры"""
        painter.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        painter.setPen(Qt.GlobalColor.red)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "ИГРА ОКОНЧЕНА")
        
        painter.setFont(QFont("Arial", 24))
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(self.rect(), 
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom, 
                        "Нажмите 'R' для перезапуска или 'M' для меню")

    # --- Унифицированные методы отрисовки меню ---
    def draw_common_background(self, painter, title):
        """Общий фон для всех меню"""
        painter.fillRect(self.rect(), QColor(35, 35, 40))
        
        # Заголовок
        painter.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        painter.setPen(QColor(220, 220, 220))
        painter.drawText(QRectF(0, 80, SCREEN_WIDTH, 60),
                        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                        title)
        
        # Декоративная линия
        painter.setPen(QColor(70, 130, 180, 150))
        painter.drawLine(SCREEN_WIDTH // 4, 140, 3 * SCREEN_WIDTH // 4, 140)

    def draw_button(self, painter, rect, text, color=None):
        """Отрисовка кнопки"""
        button_color = color if color else QColor(70, 130, 180)
        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        painter.fillPath(path, button_color)
        
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 12, QFont.Weight.Medium))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        return rect

    def draw_button_block(self, painter, buttons, start_y=None):
        """Отрисовка блока кнопок"""
        button_width = 220
        button_height = 45
        spacing = 15
        
        if start_y is None:
            start_y = SCREEN_HEIGHT // 2 - (len(buttons) * (button_height + spacing) - spacing) // 2
        
        button_rects = []
        for i, (text, _) in enumerate(buttons):
            rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2,
                         start_y + i * (button_height + spacing),
                         button_width, button_height)
            button_rects.append(self.draw_button(painter, rect, text))
        
        return button_rects

    def draw_back_button(self, painter):
        """Кнопка 'Назад'"""
        back_rect = QRectF(20, SCREEN_HEIGHT - 70, 150, 45)
        return self.draw_button(painter, back_rect, "Назад", QColor(100, 100, 100))

    def draw_footer(self, painter):
        """Нижний колонтитул"""
        painter.setFont(QFont("Arial", 9))
        painter.setPen(QColor(150, 150, 150))
        painter.drawText(10, SCREEN_HEIGHT - 15, "v1.0")

    # --- Конкретные меню ---
    def draw_menu(self, painter):
        """Главное меню"""
        self.draw_common_background(painter, "Traffic Racer Qt6")
        buttons = [
            ("Новая игра", GameState.PLAYING),
            ("Настройки", GameState.SETTINGS),
            ("Выход", None)
        ]
        self.draw_button_block(painter, buttons)
        self.draw_footer(painter)

    def draw_settings_menu(self, painter):
        """Меню настроек"""
        self.draw_common_background(painter, "НАСТРОЙКИ")
        buttons = [
            ("Аудио", GameState.AUDIO_SETTINGS),
            ("Сложность", GameState.DIFFICULTY_SETTINGS),
            ("Графика", GameState.GRAPHICS_SETTINGS),
            ("Управление", GameState.CONTROLS_SETTINGS)
        ]
        self.draw_button_block(painter, buttons)
        self.draw_back_button(painter)
        self.draw_footer(painter)

    def draw_audio_settings(self, painter):
        """Настройки аудио"""
        self.draw_common_background(painter, "НАСТРОЙКИ АУДИО")
        
        # Громкость музыки
        painter.setFont(QFont("Arial", 16))
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(50, 150, "Громкость музыки:")
        self.draw_slider(painter, 50, 180, self.music_volume, QColor(0, 150, 0))
        
        # Громкость звуков
        painter.drawText(50, 250, "Громкость звуков:")
        self.draw_slider(painter, 50, 280, self.sound_volume, QColor(0, 0, 150))
        
        self.draw_back_button(painter)
        self.draw_footer(painter)

    def draw_difficulty_settings(self, painter):
        """Настройки сложности"""
        self.draw_common_background(painter, "УРОВЕНЬ СЛОЖНОСТИ")
        
        difficulties = ["Легкий", "Средний", "Сложный"]
        for i, diff in enumerate(difficulties):
            color = QColor(100, 200, 100) if self.difficulty == i else QColor(100, 100, 100)
            rect = QRectF(SCREEN_WIDTH // 2 - 100, 150 + i * 80, 200, 60)
            self.draw_button(painter, rect, diff, color)
        
        self.draw_back_button(painter)
        self.draw_footer(painter)

    def draw_graphics_settings(self, painter):
        """Настройки графики"""
        self.draw_common_background(painter, "КАЧЕСТВО ГРАФИКИ")
        
        qualities = ["Низкое", "Среднее", "Высокое"]
        for i, qual in enumerate(qualities):
            color = QColor(100, 200, 100) if self.graphics_quality == i else QColor(100, 100, 100)
            rect = QRectF(SCREEN_WIDTH // 2 - 100, 150 + i * 80, 200, 60)
            self.draw_button(painter, rect, qual, color)
        
        self.draw_back_button(painter)
        self.draw_footer(painter)

    def draw_controls_settings(self, painter):
        """Настройки управления"""
        self.draw_common_background(painter, "НАСТРОЙКИ УПРАВЛЕНИЯ")
        
        options = ["Автоускорение", "Ручное управление"]
        for i, opt in enumerate(options):
            active = (i == 0 and self.auto_acceleration) or (i == 1 and not self.auto_acceleration)
            color = QColor(100, 200, 100) if active else QColor(100, 100, 100)
            rect = QRectF(SCREEN_WIDTH // 2 - 125, 150 + i * 80, 250, 60)
            self.draw_button(painter, rect, opt, color)
        
        self.draw_back_button(painter)
        self.draw_footer(painter)

    def draw_slider(self, painter, x, y, value, color):
        """Отрисовка ползунка с исправлением типов"""
        width = SCREEN_WIDTH - 100
        height = 20
    
        # Фон ползунка
        painter.fillRect(QRectF(x, y, width, height), QColor(100, 100, 100))
    
        # Заполненная часть (преобразуем value в int)
        filled_width = int(width * (value / 100))
        painter.fillRect(QRectF(x, y, filled_width, height), color)

    # --- Обработка ввода ---
    def keyPressEvent(self, event):
        if self.game_state == GameState.PLAYING:
            if event.key() == Qt.Key.Key_Left:
                self.left_pressed = True
            elif event.key() == Qt.Key.Key_Right:
                self.right_pressed = True
            elif event.key() == Qt.Key.Key_Up and not self.auto_acceleration:
                self.up_pressed = True
            elif event.key() == Qt.Key.Key_Down and not self.auto_acceleration:
                self.down_pressed = True
            elif event.key() == Qt.Key.Key_Space:
                self.space_pressed = True
                
        elif self.game_state == GameState.GAME_OVER:
            if event.key() == Qt.Key.Key_R:
                self.start_new_game()
            elif event.key() == Qt.Key.Key_M:
                self.game_state = GameState.MENU
                
        elif self.game_state in (GameState.SETTINGS, GameState.AUDIO_SETTINGS, 
                               GameState.DIFFICULTY_SETTINGS, GameState.GRAPHICS_SETTINGS,
                               GameState.CONTROLS_SETTINGS):
            if event.key() in (Qt.Key.Key_M, Qt.Key.Key_Escape):
                self.game_state = GameState.MENU

    def keyReleaseEvent(self, event):
        if self.game_state == GameState.PLAYING:
            if event.key() == Qt.Key.Key_Left:
                self.left_pressed = False
            elif event.key() == Qt.Key.Key_Right:
                self.right_pressed = False
            elif event.key() == Qt.Key.Key_Up:
                self.up_pressed = False
            elif event.key() == Qt.Key.Key_Down:
                self.down_pressed = False
            elif event.key() == Qt.Key.Key_Space:
                self.space_pressed = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = QPointF(event.pos())
            
            if self.game_state == GameState.MENU:
                self.handle_menu_click(pos)
            elif self.game_state == GameState.SETTINGS:
                self.handle_settings_click(pos)
            elif self.game_state == GameState.AUDIO_SETTINGS:
                self.handle_audio_settings_click(pos)
            elif self.game_state == GameState.DIFFICULTY_SETTINGS:
                self.handle_difficulty_settings_click(pos)
            elif self.game_state == GameState.GRAPHICS_SETTINGS:
                self.handle_graphics_settings_click(pos)
            elif self.game_state == GameState.CONTROLS_SETTINGS:
                self.handle_controls_settings_click(pos)

    def handle_menu_click(self, pos):
        """Обработка кликов в главном меню"""
        button_width = 220
        button_height = 45
        spacing = 15
        start_y = SCREEN_HEIGHT // 2 - (3 * (button_height + spacing) - spacing) // 2
        
        new_game_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, start_y, 
                              button_width, button_height)
        settings_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                              start_y + button_height + spacing, 
                              button_width, button_height)
        exit_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                          start_y + 2 * (button_height + spacing), 
                          button_width, button_height)
        
        if new_game_rect.contains(pos):
            self.start_new_game()
        elif settings_rect.contains(pos):
            self.game_state = GameState.SETTINGS
        elif exit_rect.contains(pos):
            QApplication.instance().quit()

    def handle_settings_click(self, pos):
        """Обработка кликов в меню настроек"""
        button_width = 220
        button_height = 45
        spacing = 15
        start_y = SCREEN_HEIGHT // 2 - (4 * (button_height + spacing) - spacing) // 2
        
        audio_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, start_y, 
                           button_width, button_height)
        difficulty_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                                start_y + button_height + spacing, 
                                button_width, button_height)
        graphics_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                              start_y + 2 * (button_height + spacing), 
                              button_width, button_height)
        controls_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                              start_y + 3 * (button_height + spacing), 
                              button_width, button_height)
        back_rect = QRectF(20, SCREEN_HEIGHT - 70, 150, 45)
        
        if audio_rect.contains(pos):
            self.game_state = GameState.AUDIO_SETTINGS
        elif difficulty_rect.contains(pos):
            self.game_state = GameState.DIFFICULTY_SETTINGS
        elif graphics_rect.contains(pos):
            self.game_state = GameState.GRAPHICS_SETTINGS
        elif controls_rect.contains(pos):
            self.game_state = GameState.CONTROLS_SETTINGS
        elif back_rect.contains(pos):
            self.game_state = GameState.MENU

    def handle_audio_settings_click(self, pos):
        """Обработка кликов в настройках аудио"""
        # Ползунок музыки
        if 50 <= pos.x() <= SCREEN_WIDTH - 50 and 180 <= pos.y() <= 200:
            self.music_volume = int((pos.x() - 50) / (SCREEN_WIDTH - 100) * 100)
            self.music_volume = max(0, min(100, self.music_volume))
            
        # Ползунок звуков
        elif 50 <= pos.x() <= SCREEN_WIDTH - 50 and 280 <= pos.y() <= 300:
            self.sound_volume = int((pos.x() - 50) / (SCREEN_WIDTH - 100) * 100)
            self.sound_volume = max(0, min(100, self.sound_volume))
            self.update_sound_volumes()
            
        # Кнопка Назад
        elif QRectF(20, SCREEN_HEIGHT - 70, 150, 45).contains(pos):
            self.game_state = GameState.SETTINGS

    def handle_difficulty_settings_click(self, pos):
        """Обработка кликов в настройках сложности"""
        for i in range(3):
            rect = QRectF(SCREEN_WIDTH // 2 - 100, 150 + i * 80, 200, 60)
            if rect.contains(pos):
                self.difficulty = i
                break
                
        if QRectF(20, SCREEN_HEIGHT - 70, 150, 45).contains(pos):
            self.game_state = GameState.SETTINGS

    def handle_graphics_settings_click(self, pos):
        """Обработка кликов в настройках графики"""
        for i in range(3):
            rect = QRectF(SCREEN_WIDTH // 2 - 100, 150 + i * 80, 200, 60)
            if rect.contains(pos):
                self.graphics_quality = i
                break
                
        if QRectF(20, SCREEN_HEIGHT - 70, 150, 45).contains(pos):
            self.game_state = GameState.SETTINGS

    def handle_controls_settings_click(self, pos):
        """Обработка кликов в настройках управления"""
        for i in range(2):
            rect = QRectF(SCREEN_WIDTH // 2 - 125, 150 + i * 80, 250, 60)
            if rect.contains(pos):
                self.auto_acceleration = (i == 0)
                break
                
        if QRectF(20, SCREEN_HEIGHT - 70, 150, 45).contains(pos):
            self.game_state = GameState.SETTINGS

if __name__ == "__main__":
    app = QApplication(sys.argv)
    game = GameWidget()
    game.show()
    sys.exit(app.exec())