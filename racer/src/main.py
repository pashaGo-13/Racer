import sys
import random
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPainter, QColor, QFont, QImage
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QElapsedTimer

# Константы
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600

PLAYER_SPEED_INCREMENT = 0.5
MAX_PLAYER_SPEED = 10
TRAFFIC_CAR_SPEED_MIN = 3
TRAFFIC_CAR_SPEED_MAX = 7
LANE_WIDTH = 80
NUM_LANES = 4

class PlayerCar:
    def __init__(self):
        self.width = 50
        self.height = 80
        self.x = (SCREEN_WIDTH / 2) - (self.width / 2)
        self.y = SCREEN_HEIGHT - self.height - 20
        self.speed = 0
        self.image = QImage(r"C:\reposit\Racer\racer\src\assets\images\player_car.png")

    def get_rect(self):
        return QRectF(self.x, self.y, self.width, self.height)

    def draw(self, painter):
        scaled_image = self.image.scaled(self.width, self.height,
                                         Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
        painter.drawImage(int(self.x), int(self.y), scaled_image)


class TrafficCar:
    def __init__(self, x, y, base_speed):
        self.width = 50
        self.height = 80
        self.x = x
        self.y = y
        self.base_speed = base_speed

        self.image = QImage(r"C:\reposit\Racer\racer\src\assets\images\enemy_car_1.png")

        if self.image.isNull():
            print(f"Ошибка: Не удалось загрузить изображение для встречной машины. Проверьте путь: C:\\reposit\\Racer\\racer\\src\\assets\\images\\enemy_car_1.png")

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
        self.setWindowTitle("Traffic Racer Qt6")
        self.game_over = False
        self.score = 0

        self.player_car = PlayerCar()
        self.traffic_cars = []

        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False

        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.game_loop)
        self.timer_interval_ms = 16
        self.game_timer.start(self.timer_interval_ms)

        self.elapsed_timer = QElapsedTimer()
        self.elapsed_timer.start()

        self.spawn_traffic_timer = QTimer(self)
        self.spawn_traffic_timer.timeout.connect(self.spawn_traffic_car)
        self.spawn_traffic_timer_interval = 2000
        self.spawn_traffic_timer.start(self.spawn_traffic_timer_interval)

        self.road_offset = 0
        self.road_speed_multiplier = 5

        self.road_image = QImage(r"C:\reposit\Racer\racer\src\assets\images\road.png")
        if self.road_image.isNull():
            print("Ошибка: Не удалось загрузить изображение дороги. Проверьте путь: C:\\reposit\\Racer\\racer\\src\\assets\\images\\road.png")

        self.scaled_road_image = None
        if not self.road_image.isNull():
            self.scaled_road_image = self.road_image.scaled(
                SCREEN_WIDTH, SCREEN_WIDTH,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

    def game_loop(self):
        if self.game_over:
            return

        delta_time = self.elapsed_timer.restart() / 1000.0

        self.update_game_state(delta_time)
        self.update()

    def update_game_state(self, dt):
        if self.left_pressed:
            self.player_car.x -= 300 * dt
            if self.player_car.x < 0: self.player_car.x = 0
        if self.right_pressed:
            self.player_car.x += 300 * dt
            if self.player_car.x + self.player_car.width > SCREEN_WIDTH:
                self.player_car.x = SCREEN_WIDTH - self.player_car.width
        if self.up_pressed:
            self.player_car.speed += PLAYER_SPEED_INCREMENT * dt * 60
            if self.player_car.speed > MAX_PLAYER_SPEED: self.player_car.speed = MAX_PLAYER_SPEED
        if self.down_pressed:
            self.player_car.speed -= PLAYER_SPEED_INCREMENT * dt * 60
            if self.player_car.speed < 0: self.player_car.speed = 0

        cars_to_remove = []
        for car in self.traffic_cars:
            car.update(dt, self.player_car.speed)
            if car.y > SCREEN_HEIGHT:
                cars_to_remove.append(car)
                self.score += 10

            if self.player_car.get_rect().intersects(car.get_rect()):
                self.game_over = True
                self.game_timer.stop()
                self.spawn_traffic_timer.stop()
                print("Игра окончена!")

        for car in cars_to_remove:
            self.traffic_cars.remove(car)

        self.road_offset += (self.road_speed_multiplier + self.player_car.speed) * dt * 60
        # --- ИЗМЕНЕННЫЙ КОД: Зацикливаем смещение по высоте СКРИНА, а не изображения ---
        if self.scaled_road_image and not self.scaled_road_image.isNull():
            self.road_offset %= SCREEN_HEIGHT # <--- Ключевое изменение здесь
        else:
            self.road_offset = 0
        # --- КОНЕЦ ИЗМЕНЕННОГО КОДА ---


    def spawn_traffic_car(self):
        if self.game_over:
            return

        lane_index = random.randint(0, NUM_LANES - 1)
        lane_center_x = (SCREEN_WIDTH / NUM_LANES) * lane_index + (SCREEN_WIDTH / NUM_LANES) / 2

        temp_car_width = 50
        temp_car_height = 80

        x_pos = lane_center_x - temp_car_width / 2
        y_pos = -temp_car_height

        speed = random.uniform(TRAFFIC_CAR_SPEED_MIN, TRAFFIC_CAR_SPEED_MAX)

        can_spawn = True
        for car in self.traffic_cars:
            if abs(car.x - x_pos) < temp_car_width and car.y < 150:
                can_spawn = False
                break
        if can_spawn:
            self.traffic_cars.append(TrafficCar(x_pos, y_pos, speed))


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.scaled_road_image and not self.scaled_road_image.isNull():
            img_height = self.scaled_road_image.height() # Это 600 пикселей

            # Рисуем изображение, смещая его
            painter.drawImage(0, int(self.road_offset), self.scaled_road_image)
            # Рисуем вторую копию над первой
            painter.drawImage(0, int(self.road_offset - img_height), self.scaled_road_image)
            # Рисуем третью копию, чтобы гарантировать полное покрытие экрана (600+600+600=1800, при 800 экрана)
            # Это перекрытие гарантирует, что всегда есть что рисовать.
            painter.drawImage(0, int(self.road_offset - img_height * 2), self.scaled_road_image)
        else:
            painter.fillRect(self.rect(), QColor(50, 50, 50))


        self.player_car.draw(painter)

        for car in self.traffic_cars:
            car.draw(painter)

        painter.setFont(QFont("Arial", 16))
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(10, 30, f"Счет: {self.score}")
        painter.drawText(10, 60, f"Скорость: {int(self.player_car.speed * 10)} км/ч")

        painter.setPen(Qt.GlobalColor.red)
        if self.game_over:
            painter.setFont(QFont("Arial", 48, QFont.Weight.Bold))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "ИГРА ОКОНЧЕНА")


    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Left:
            self.left_pressed = True
        elif event.key() == Qt.Key.Key_Right:
            self.right_pressed = True
        elif event.key() == Qt.Key.Key_Up:
            self.up_pressed = True
        elif event.key() == Qt.Key.Key_Down:
            self.down_pressed = True
        elif event.key() == Qt.Key.Key_R and self.game_over:
            self.reset_game()

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Left:
            self.left_pressed = False
        elif event.key() == Qt.Key.Key_Right:
            self.right_pressed = False
        elif event.key() == Qt.Key.Key_Up:
            self.up_pressed = False
        elif event.key() == Qt.Key.Key_Down:
            self.down_pressed = False

    def reset_game(self):
        self.game_over = False
        self.score = 0
        self.player_car = PlayerCar()
        self.traffic_cars = []
        self.road_offset = 0
        self.elapsed_timer.restart()
        self.game_timer.start(self.timer_interval_ms)
        self.spawn_traffic_timer.start(self.spawn_traffic_timer_interval)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    game = GameWidget()
    game.show()
    sys.exit(app.exec())