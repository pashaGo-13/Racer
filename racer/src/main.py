import sys
import random
import json
from pathlib import Path
from PyQt6.QtGui import (QPainter, QColor, QFont, QImage, QPainterPath, 
                         QPen, QLinearGradient, QConicalGradient, QCursor)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QElapsedTimer, QUrl, QPoint
from PyQt6.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit
from PyQt6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput

# Константы игры
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600
PLAYER_SPEED_INCREMENT = 0.1
MAX_PLAYER_SPEED = 25.6
TRAFFIC_CAR_SPEED_MIN = 5
TRAFFIC_CAR_SPEED_MAX = 20
NUM_LANES = 4
HIGHSCORES_FILE = "highscores.json"

# Цветовая палитра
DARK_GRAY = QColor(40, 40, 45)
MEDIUM_GRAY = QColor(60, 60, 65)
LIGHT_GRAY = QColor(80, 80, 85)
ACCENT_COLOR = QColor(100, 150, 200)
TEXT_COLOR = QColor(220, 220, 220)
HIGHLIGHT_COLOR = QColor(120, 180, 240)

# Стиль кнопок
BUTTON_COLOR = QColor(30, 30, 30, 220)
BUTTON_HOVER = QColor(50, 50, 50, 220)
BUTTON_PRESSED = QColor(20, 20, 20, 220)
BUTTON_TEXT = QColor(230, 230, 230)
BUTTON_BORDER = QColor(80, 80, 80, 150)
BUTTON_RADIUS = 12

# Стиль ползунков
SLIDER_HEIGHT = 14
SLIDER_HANDLE_SIZE = 24
SLIDER_COLOR = QColor(70, 70, 70)
SLIDER_FILL = QColor(150, 150, 150)
SLIDER_HANDLE_COLOR = QColor(200, 200, 200)
SLIDER_RADIUS = 7

# Состояния игры
class GameState:
    MENU = 0
    PLAYING = 1
    SETTINGS = 2
    GAME_OVER = 3
    AUDIO_SETTINGS = 4
    DIFFICULTY_SETTINGS = 5
    GRAPHICS_SETTINGS = 6
    CONTROLS_SETTINGS = 7
    HIGHSCORES = 8

class PlayerCar:
    def __init__(self):
        self.width = 60
        self.height = 98
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

class TrafficCar:
    def __init__(self, x, y, base_speed, car_type):
        self.width = 60
        self.height = 98
        self.x = x
        self.y = y
        self.base_speed = base_speed
        
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

class GameWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setWindowTitle("Dark Racer")
        self.init_game()
        self.setup_timers()
        self.load_resources()
        self.highscores = self.load_highscores()
        self.custom_font = QFont("Segoe UI", 12)
        self.custom_font.setWeight(QFont.Weight.Medium)

    def init_game(self):
        self.game_state = GameState.MENU
        self.score = 0
        self.player_car = PlayerCar()
        self.traffic_cars = []
        self.music_volume = 50
        self.sound_volume = 70
        self.difficulty = 1
        self.graphics_quality = 2
        self.auto_acceleration = True
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.space_pressed = False

    def setup_timers(self):
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.game_loop)
        self.game_timer.start(16)
        self.elapsed_timer = QElapsedTimer()
        self.elapsed_timer.start()
        self.spawn_traffic_timer = QTimer(self)
        self.spawn_traffic_timer.timeout.connect(self.spawn_traffic_car)
        self.spawn_traffic_timer_interval = 2000

    def load_resources(self):
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
        
        # Фоновая музыка
        self.background_music = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.background_music.setAudioOutput(self.audio_output)
        music_path = "src/assets/sounds/music.mp3"
        self.background_music.setSource(QUrl.fromLocalFile(music_path))
        self.audio_output.setVolume(self.music_volume / 100.0)
        
        # Дорожное полотно и фон меню
        self.road_offset = 0
        self.road_speed_multiplier = 5
        self.road_image = QImage("src/assets/images/road.png")
        if self.road_image.isNull():
            print("Ошибка загрузки дорожного полотна")
            self.scaled_road_image = None
            self.scaled_menu_bg = None
        else:
            self.scaled_road_image = self.road_image.scaled(
                SCREEN_WIDTH, SCREEN_HEIGHT,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Создаем затемненную версию для фона меню
            self.scaled_menu_bg = QImage(self.scaled_road_image)
            darken = QImage(self.scaled_menu_bg.size(), QImage.Format.Format_ARGB32)
            darken.fill(QColor(0, 0, 0, 160))
            painter = QPainter(self.scaled_menu_bg)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Darken)
            painter.drawImage(0, 0, darken)
            painter.end()

    def load_highscores(self):
        try:
            if Path(HIGHSCORES_FILE).exists():
                with open(HIGHSCORES_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки таблицы рекордов: {e}")
        
        return [
            {"name": "Player1", "score": 1000},
            {"name": "Player2", "score": 800},
            {"name": "Player3", "score": 600},
            {"name": "Player4", "score": 400},
            {"name": "Player5", "score": 200},
            {"name": "Player6", "score": 100},
            {"name": "Player7", "score": 90},
            {"name": "Player8", "score": 80},
            {"name": "Player9", "score": 70},
            {"name": "Player10", "score": 60}
        ]

    def save_highscores(self):
        try:
            with open(HIGHSCORES_FILE, 'w') as f:
                json.dump(self.highscores, f, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения таблицы рекордов: {e}")

    def check_highscore(self, score):
        if len(self.highscores) < 10:
            return True
        return score > self.highscores[-1]["score"]

    def add_highscore(self, name, score):
        self.highscores.append({"name": name, "score": score})
        self.highscores.sort(key=lambda x: x["score"], reverse=True)
        self.highscores = self.highscores[:10]
        self.save_highscores()

    def game_loop(self):
        delta_time = self.elapsed_timer.restart() / 1000.0
        self.road_offset += 1  # Для анимации фона в меню
        if self.game_state == GameState.PLAYING:
            self.update_game_state(delta_time)
        self.update()

    def update_game_state(self, dt):
        self.update_player_position(dt)
        self.update_traffic(dt)
        self.update_road_animation()

    def update_player_position(self, dt):
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
        
        self.handle_sound_effects()

    def handle_sound_effects(self):
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
        cars_to_remove = []
        
        for car in self.traffic_cars:
            car.update(dt, self.player_car.speed)
            
            if car.y > SCREEN_HEIGHT:
                cars_to_remove.append(car)
                self.score += 10
                
            if self.player_car.get_rect().intersects(car.get_rect()):
                self.play_sound('crash')
                self.handle_game_over()
                
        for car in cars_to_remove:
            self.traffic_cars.remove(car)

    def update_road_animation(self):
        if self.scaled_road_image and not self.scaled_road_image.isNull():
            self.road_offset += (self.road_speed_multiplier + self.player_car.speed) * 0.06
            self.road_offset %= SCREEN_HEIGHT

    def spawn_traffic_car(self):
        if self.game_state != GameState.PLAYING:
            return
        
        lane_index = random.randint(0, NUM_LANES - 1)
        lane_center = (SCREEN_WIDTH / NUM_LANES) * (lane_index + 0.5)
        x_pos = lane_center - 25
    
        car_type = random.randint(0, 2)
        base_speed = self.get_traffic_speed()
        speed_modifiers = [0.9, 1.0, 1.1]
        speed = base_speed * speed_modifiers[car_type]
    
        if not any(abs(car.x - x_pos) < 50 and car.y < 150 for car in self.traffic_cars):
            self.traffic_cars.append(TrafficCar(x_pos, -80, speed, car_type))

    def get_traffic_speed(self):
        base_min = TRAFFIC_CAR_SPEED_MIN
        base_max = TRAFFIC_CAR_SPEED_MAX
    
        if self.difficulty == 0:
            return random.uniform(base_min, base_min + (base_max - base_min) * 0.5)
        elif self.difficulty == 1:
            return random.uniform(base_min, base_max)
        else:
            return random.uniform(base_min + (base_max - base_min) * 0.5, base_max + 2)

    def handle_game_over(self):
        self.game_state = GameState.GAME_OVER
        self.spawn_traffic_timer.stop()
        self.background_music.stop()
    
        if self.check_highscore(self.score):
            QTimer.singleShot(100, self.show_highscore_dialog)

    def show_highscore_dialog(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle('Новый рекорд!')
        dialog.setLabelText(f'Ваш результат: {self.score}\nВведите ваше имя:')
        dialog.setTextValue('')
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        
        line_edit = dialog.findChild(QLineEdit)
        if line_edit:
            line_edit.setMaxLength(15)
        
        ok = dialog.exec()
        name = dialog.textValue()
        
        if ok and name:
            self.add_highscore(name, self.score)

    def start_new_game(self):
        self.game_state = GameState.PLAYING
        self.reset_game()
        self.spawn_traffic_timer.start(self.spawn_traffic_timer_interval)
        self.background_music.setLoops(QMediaPlayer.Loops.Infinite)
        self.background_music.play()

    def reset_game(self):
        self.score = 0
        self.player_car = PlayerCar()
        self.traffic_cars = []
        self.road_offset = 0
        self.elapsed_timer.restart()

    def update_sound_volumes(self):
        for sound in self.sound_effects.values():
            sound.setVolume(self.sound_volume / 100.0)
        
        if hasattr(self, 'audio_output'):
            self.audio_output.setVolume(self.music_volume / 100.0)

    def play_sound(self, sound_name):
        if sound_name in self.sound_effects:
            self.sound_effects[sound_name].play()

    def draw_common_background(self, painter, title=""):
        if self.scaled_menu_bg and not self.scaled_menu_bg.isNull():
            painter.drawImage(0, int(self.road_offset % SCREEN_HEIGHT), self.scaled_menu_bg)
            painter.drawImage(0, int(self.road_offset % SCREEN_HEIGHT) - SCREEN_HEIGHT, self.scaled_menu_bg)
        
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))
        
        if title:
            painter.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
            painter.setPen(TEXT_COLOR)
            painter.drawText(QRectF(0, 80, SCREEN_WIDTH, 60),
                           Qt.AlignmentFlag.AlignCenter, title)
            
            painter.setPen(QPen(QColor(100, 100, 100, 150), 1))
            painter.drawLine(SCREEN_WIDTH//4, 140, 3*SCREEN_WIDTH//4, 140)

    def draw_button(self, painter, rect, text, color=None, hover=False, pressed=False):
        if pressed:
            btn_color = BUTTON_PRESSED
        elif hover:
            btn_color = BUTTON_HOVER
        else:
            btn_color = color if color else BUTTON_COLOR
        
        path = QPainterPath()
        path.addRoundedRect(rect, BUTTON_RADIUS, BUTTON_RADIUS)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(path, btn_color)
        
        painter.setPen(QPen(BUTTON_BORDER, 1.2))
        painter.drawPath(path)
        
        painter.setPen(BUTTON_TEXT)
        painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Medium))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        
        return rect

    def draw_button_block(self, painter, buttons, start_y=None):
        button_width = 250
        button_height = 50
        spacing = 20
        
        if start_y is None:
            start_y = SCREEN_HEIGHT // 2 - (len(buttons) * (button_height + spacing) - spacing) // 2
        
        button_rects = []
        for i, (text, _) in enumerate(buttons):
            rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2,
                         start_y + i * (button_height + spacing),
                         button_width, button_height)
            
            mouse_pos = self.mapFromGlobal(QCursor.pos())
            mouse_pos_f = QPointF(mouse_pos)  # Преобразуем QPoint в QPointF
            hover = rect.contains(mouse_pos_f)
            pressed = hover and QApplication.mouseButtons() == Qt.MouseButton.LeftButton
            
            button_rects.append(self.draw_button(painter, rect, text, None, hover, pressed))
        
        return button_rects

    def draw_back_button(self, painter):
        back_rect = QRectF(20, SCREEN_HEIGHT - 70, 100, 40)
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        mouse_pos_f = QPointF(mouse_pos)  # Преобразуем QPoint в QPointF
        hover = back_rect.contains(mouse_pos_f)
        pressed = hover and QApplication.mouseButtons() == Qt.MouseButton.LeftButton
        self.draw_button(painter, back_rect, "Назад", MEDIUM_GRAY, hover, pressed)
        return back_rect

    def draw_slider(self, painter, x, y, width, value):
        bg_rect = QRectF(x, y, width, SLIDER_HEIGHT)
        path = QPainterPath()
        path.addRoundedRect(bg_rect, SLIDER_RADIUS, SLIDER_RADIUS)
        painter.fillPath(path, SLIDER_COLOR)
        
        fill_width = max(SLIDER_HANDLE_SIZE/2, (width * (value / 100)))
        fill_rect = QRectF(x, y, fill_width, SLIDER_HEIGHT)
        fill_path = QPainterPath()
        fill_path.addRoundedRect(fill_rect, SLIDER_RADIUS, SLIDER_RADIUS)
        painter.fillPath(fill_path, SLIDER_FILL)
        
        handle_x = x + (width * (value / 100)) - (SLIDER_HANDLE_SIZE/2)
        handle_rect = QRectF(handle_x, y - (SLIDER_HANDLE_SIZE-SLIDER_HEIGHT)/2, 
                            SLIDER_HANDLE_SIZE, SLIDER_HANDLE_SIZE)
        
        gradient = QLinearGradient(handle_rect.topLeft(), handle_rect.bottomLeft())
        gradient.setColorAt(0, SLIDER_HANDLE_COLOR)
        gradient.setColorAt(1, QColor(170, 170, 170))
        
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.setBrush(gradient)
        painter.drawEllipse(handle_rect)

    def draw_menu(self, painter):
        self.draw_common_background(painter, "DARK RACER")
        
        buttons = [
            ("СТАРТ", GameState.PLAYING),
            ("РЕКОРДЫ", GameState.HIGHSCORES),
            ("НАСТРОЙКИ", GameState.SETTINGS),
            ("ВЫХОД", None)
        ]
        self.draw_button_block(painter, buttons, SCREEN_HEIGHT//2 - 100)

    def draw_settings_menu(self, painter):
        self.draw_common_background(painter, "НАСТРОЙКИ")
        
        buttons = [
            ("АУДИО", GameState.AUDIO_SETTINGS),
            ("СЛОЖНОСТЬ", GameState.DIFFICULTY_SETTINGS),
            ("ГРАФИКА", GameState.GRAPHICS_SETTINGS),
            ("УПРАВЛЕНИЕ", GameState.CONTROLS_SETTINGS)
        ]
        self.draw_button_block(painter, buttons)
        self.draw_back_button(painter)

    def draw_audio_settings(self, painter):
        self.draw_common_background(painter, "НАСТРОЙКИ АУДИО")
        
        painter.setFont(QFont("Segoe UI", 16))
        painter.setPen(TEXT_COLOR)
        
        painter.drawText(50, 170, "Громкость музыки:")
        self.draw_slider(painter, 50, 190, SCREEN_WIDTH-100, self.music_volume)
        
        painter.drawText(50, 270, "Громкость звуков:")
        self.draw_slider(painter, 50, 290, SCREEN_WIDTH-100, self.sound_volume)
        
        self.draw_back_button(painter)

    def draw_difficulty_settings(self, painter):
        self.draw_common_background(painter, "УРОВЕНЬ СЛОЖНОСТИ")
        
        difficulties = ["ЛЕГКИЙ", "СРЕДНИЙ", "СЛОЖНЫЙ"]
        for i, diff in enumerate(difficulties):
            color = HIGHLIGHT_COLOR if self.difficulty == i else MEDIUM_GRAY
            rect = QRectF(SCREEN_WIDTH//2 - 120, 180 + i*90, 240, 60)
            self.draw_button(painter, rect, diff, color)
        
        self.draw_back_button(painter)

    def draw_graphics_settings(self, painter):
        self.draw_common_background(painter, "КАЧЕСТВО ГРАФИКИ")
        
        qualities = ["НИЗКОЕ", "СРЕДНЕЕ", "ВЫСОКОЕ"]
        for i, qual in enumerate(qualities):
            color = HIGHLIGHT_COLOR if self.graphics_quality == i else MEDIUM_GRAY
            rect = QRectF(SCREEN_WIDTH//2 - 120, 180 + i*90, 240, 60)
            self.draw_button(painter, rect, qual, color)
        
        self.draw_back_button(painter)

    def draw_controls_settings(self, painter):
        self.draw_common_background(painter, "НАСТРОЙКИ УПРАВЛЕНИЯ")
        
        options = ["АВТОУСКОРЕНИЕ", "РУЧНОЕ УПРАВЛЕНИЕ"]
        for i, opt in enumerate(options):
            active = (i == 0 and self.auto_acceleration) or (i == 1 and not self.auto_acceleration)
            color = HIGHLIGHT_COLOR if active else MEDIUM_GRAY
            rect = QRectF(SCREEN_WIDTH//2 - 150, 180 + i*90, 300, 60)
            self.draw_button(painter, rect, opt, color)
        
        self.draw_back_button(painter)

    def draw_highscores(self, painter):
        self.draw_common_background(painter, "ТАБЛИЦА РЕКОРДОВ")
        
        painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        painter.setPen(TEXT_COLOR)
        painter.drawText(150, 180, "ИГРОК")
        painter.drawText(400, 180, "ОЧКИ")
        
        painter.setFont(QFont("Segoe UI", 16))
        
        for i, record in enumerate(self.highscores[:10]):
            y_pos = 220 + i * 35
            painter.drawText(150, y_pos, f"{i+1}. {record['name']}")
            painter.drawText(400, y_pos, str(record['score']))
        
        self.draw_back_button(painter)

    def draw_game_over(self, painter):
        painter.fillRect(self.rect(), QColor(0, 0, 0, 180))
        
        painter.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        painter.setPen(Qt.GlobalColor.red)
        painter.drawText(QRectF(0, 150, SCREEN_WIDTH, 60),
                        Qt.AlignmentFlag.AlignCenter,
                        "АВАРИЯ!")
        
        painter.setFont(QFont("Segoe UI", 24))
        painter.setPen(TEXT_COLOR)
        painter.drawText(QRectF(0, 220, SCREEN_WIDTH, 40),
                        Qt.AlignmentFlag.AlignCenter,
                        f"ВАШ СЧЕТ: {self.score}")

        button_width = 200
        button_height = 50
        button_y = SCREEN_HEIGHT // 2 + 50
        
        restart_rect = QRectF(
            SCREEN_WIDTH // 2 - button_width - 10, 
            button_y, 
            button_width, 
            button_height
        )
        self.draw_button(painter, restart_rect, "ИГРАТЬ СНОВА")
        
        menu_rect = QRectF(
            SCREEN_WIDTH // 2 + 10, 
            button_y, 
            button_width, 
            button_height
        )
        self.draw_button(painter, menu_rect, "ГЛАВНОЕ МЕНЮ")

    def draw_game(self, painter):
        if self.scaled_road_image:
            painter.drawImage(0, int(self.road_offset), self.scaled_road_image)
            painter.drawImage(0, int(self.road_offset - SCREEN_HEIGHT), self.scaled_road_image)
        else:
            painter.fillRect(self.rect(), DARK_GRAY)
        
        self.player_car.draw(painter)
        for car in self.traffic_cars:
            car.draw(painter)
        
        painter.setFont(QFont("Segoe UI", 16))
        painter.setPen(TEXT_COLOR)
        painter.drawText(10, 30, f"СЧЕТ: {self.score}")
        painter.drawText(10, 60, f"СКОРОСТЬ: {int(self.player_car.speed * 10)} КМ/Ч")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.custom_font)
        
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
        elif self.game_state == GameState.HIGHSCORES:
            self.draw_highscores(painter)
        elif self.game_state in (GameState.PLAYING, GameState.GAME_OVER):
            self.draw_game(painter)
            
            if self.game_state == GameState.GAME_OVER:
                self.draw_game_over(painter)

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
                self.background_music.stop()
                self.game_state = GameState.MENU
                
        elif self.game_state in (GameState.SETTINGS, GameState.AUDIO_SETTINGS, 
                               GameState.DIFFICULTY_SETTINGS, GameState.GRAPHICS_SETTINGS,
                               GameState.CONTROLS_SETTINGS, GameState.HIGHSCORES):
            if event.key() in (Qt.Key.Key_M, Qt.Key.Key_Escape):
                self.background_music.stop()
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
            pos = event.pos()
            pos_f = QPointF(pos)  # Преобразуем QPoint в QPointF
            
            if self.game_state == GameState.GAME_OVER:
                self.handle_game_over_click(pos_f)
            elif self.game_state == GameState.MENU:
                self.handle_menu_click(pos_f)
            elif self.game_state == GameState.SETTINGS:
                self.handle_settings_click(pos_f)
            elif self.game_state == GameState.AUDIO_SETTINGS:
                self.handle_audio_settings_click(pos_f)
            elif self.game_state == GameState.DIFFICULTY_SETTINGS:
                self.handle_difficulty_settings_click(pos_f)
            elif self.game_state == GameState.GRAPHICS_SETTINGS:
                self.handle_graphics_settings_click(pos_f)
            elif self.game_state == GameState.CONTROLS_SETTINGS:
                self.handle_controls_settings_click(pos_f)
            elif self.game_state == GameState.HIGHSCORES:
                self.handle_highscores_click(pos_f)

    def handle_game_over_click(self, pos):
        button_width = 200
        button_height = 50
        button_y = SCREEN_HEIGHT // 2 + 50
        
        restart_rect = QRectF(
            SCREEN_WIDTH // 2 - button_width - 10, 
            button_y, 
            button_width, 
            button_height
        )
        if restart_rect.contains(pos):
            self.start_new_game()
        
        menu_rect = QRectF(
            SCREEN_WIDTH // 2 + 10, 
            button_y, 
            button_width, 
            button_height
        )
        if menu_rect.contains(pos):
            self.game_state = GameState.MENU

    def handle_menu_click(self, pos):
        button_width = 250
        button_height = 50
        spacing = 20
        start_y = SCREEN_HEIGHT // 2 - 100
        
        new_game_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                              start_y, 
                              button_width, 
                              button_height)
        highscores_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                                start_y + button_height + spacing, 
                                button_width, 
                                button_height)
        settings_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                              start_y + 2*(button_height + spacing), 
                              button_width, 
                              button_height)
        exit_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                          start_y + 3*(button_height + spacing), 
                          button_width, 
                          button_height)
        
        if new_game_rect.contains(pos):
            self.start_new_game()
        elif highscores_rect.contains(pos):
            self.game_state = GameState.HIGHSCORES
        elif settings_rect.contains(pos):
            self.game_state = GameState.SETTINGS
        elif exit_rect.contains(pos):
            QApplication.instance().quit()

    def handle_settings_click(self, pos):
        button_width = 250
        button_height = 50
        spacing = 20
        start_y = SCREEN_HEIGHT // 2 - 150
        
        audio_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                           start_y, 
                           button_width, 
                           button_height)
        difficulty_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                               start_y + button_height + spacing, 
                               button_width, 
                               button_height)
        graphics_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                             start_y + 2*(button_height + spacing), 
                             button_width, 
                             button_height)
        controls_rect = QRectF(SCREEN_WIDTH // 2 - button_width // 2, 
                             start_y + 3*(button_height + spacing), 
                             button_width, 
                             button_height)
        back_rect = QRectF(20, SCREEN_HEIGHT - 70, 100, 40)
        
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
        # Ползунок музыки
        if 50 <= pos.x() <= SCREEN_WIDTH-50 and 190 <= pos.y() <= 190+SLIDER_HEIGHT:
            self.music_volume = int(((pos.x()-50) / (SCREEN_WIDTH-100)) * 100)
            self.music_volume = max(0, min(100, self.music_volume))
            self.audio_output.setVolume(self.music_volume / 100.0)
        
        # Ползунок звуков
        elif 50 <= pos.x() <= SCREEN_WIDTH-50 and 290 <= pos.y() <= 290+SLIDER_HEIGHT:
            self.sound_volume = int(((pos.x()-50) / (SCREEN_WIDTH-100)) * 100)
            self.sound_volume = max(0, min(100, self.sound_volume))
            self.update_sound_volumes()
            
        # Кнопка "Назад"
        elif QRectF(20, SCREEN_HEIGHT-70, 100, 40).contains(pos):
            self.game_state = GameState.SETTINGS

    def handle_difficulty_settings_click(self, pos):
        for i in range(3):
            rect = QRectF(SCREEN_WIDTH//2 - 120, 180 + i*90, 240, 60)
            if rect.contains(pos):
                self.difficulty = i
                break
                
        if QRectF(20, SCREEN_HEIGHT-70, 100, 40).contains(pos):
            self.game_state = GameState.SETTINGS

    def handle_graphics_settings_click(self, pos):
        for i in range(3):
            rect = QRectF(SCREEN_WIDTH//2 - 120, 180 + i*90, 240, 60)
            if rect.contains(pos):
                self.graphics_quality = i
                break
                
        if QRectF(20, SCREEN_HEIGHT-70, 100, 40).contains(pos):
            self.game_state = GameState.SETTINGS

    def handle_controls_settings_click(self, pos):
        for i in range(2):
            rect = QRectF(SCREEN_WIDTH//2 - 150, 180 + i*90, 300, 60)
            if rect.contains(pos):
                self.auto_acceleration = (i == 0)
                break
                
        if QRectF(20, SCREEN_HEIGHT-70, 100, 40).contains(pos):
            self.game_state = GameState.SETTINGS

    def handle_highscores_click(self, pos):
        if QRectF(20, SCREEN_HEIGHT-70, 100, 40).contains(pos):
            self.game_state = GameState.MENU

    def mouseMoveEvent(self, event):
        if self.game_state in [GameState.MENU, GameState.SETTINGS, 
                             GameState.AUDIO_SETTINGS, GameState.DIFFICULTY_SETTINGS,
                             GameState.GRAPHICS_SETTINGS, GameState.CONTROLS_SETTINGS,
                             GameState.HIGHSCORES]:
            self.update()  # Для обновления hover-эффектов

if __name__ == "__main__":
    app = QApplication(sys.argv)
    game = GameWidget()
    game.show()
    sys.exit(app.exec())