import tkinter as tk
import random
import math
from PIL import Image, ImageTk
import os
import threading
import winsound
import time
import wave


class Game:
    def __init__(self, root):
        self.root = root
        self.root.title("Ну, Погоди!")

        self.root.resizable(True, True)
        self.root.minsize(800, 600)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Базовые размеры для масштабирования
        self.BASE_WIDTH = 800
        self.BASE_HEIGHT = 600
        self.WIDTH = 800
        self.HEIGHT = 600
        self.FPS = 60
        self.EGG_SPEED_START = 3
        self.SPEED_INCREMENT = 0.2
        self.SPEED_INCREASE_INTERVAL = 10

        self.game_active = False
        self.game_paused = False
        self.game_over = False
        self.score = 0
        self.lives = 3
        self.egg_speed = self.EGG_SPEED_START
        self.spawn_timer = 0
        self.spawn_interval = 100
        self.basket_position = 1
        self.eggs = []

        self.wolf_obj = None
        self.basket_obj = None

        self.ui_elements = {}
        self.game_over_elements = []
        self.pause_elements = []
        self.current_menu = True
        self.images = {}
        self.sprite_cache = {}
        self.basket_direction = 'right'

        # Флаг для музыки
        self.music_playing = False
        self.music_enabled = True  # Флаг включения/выключения звука

        try:
            self.RESAMPLE_RESIZE = Image.Resampling.LANCZOS
        except AttributeError:
            try:
                self.RESAMPLE_RESIZE = Image.LANCZOS
            except AttributeError:
                self.RESAMPLE_RESIZE = Image.BICUBIC

        self.RESAMPLE_ROTATE = Image.BICUBIC

        self.sprites_dir = 'sprites'
        if not os.path.exists(self.sprites_dir):
            os.makedirs(self.sprites_dir)

        # Создаем папку для звуков если её нет
        self.sounds_dir = 'sounds'
        if not os.path.exists(self.sounds_dir):
            os.makedirs(self.sounds_dir)

        self.load_all_sprites()

        self.canvas = tk.Canvas(root, width=self.WIDTH, height=self.HEIGHT, bg='#87CEEB')
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind('<Configure>', self.on_canvas_resize)

        self.root.bind('<KeyPress>', self.handle_keypress)
        self.root.bind('<F11>', self.toggle_fullscreen)
        self.root.bind('<Escape>', self.handle_escape)

        # Инициализация точек
        self.update_spawn_and_target_points()
        self.show_main_menu()

        # Запуск музыки
        self.start_music()

    def load_all_sprites(self):
        sprites = {
            'background': 'background.png',
            'game_bg': 'game_bg.png',
            'wolf': 'wolf.png',
            'basket': 'basket.png',
            'egg': 'egg.png',
            'heart': 'heart.png',
            'chicken_coop': 'chicken_coop.png',
            'chute': 'chute.png',
            'sound_on': 'sound_on.png',
            'sound_off': 'sound_off.png'
        }

        for key, filename in sprites.items():
            filepath = os.path.join(self.sprites_dir, filename)
            if os.path.exists(filepath):
                try:
                    img = Image.open(filepath).convert('RGBA')
                    self.images[key] = img
                except Exception:
                    self.images[key] = None
            else:
                self.images[key] = None

    def start_music(self):
        """Запуск циклической фоновой музыки"""
        if not self.music_enabled:
            return

        music_file = os.path.join('sounds', 'background_music.wav')
        if os.path.exists(music_file) and not self.music_playing:
            self.music_playing = True
            threading.Thread(target=self._play_music_loop, args=(music_file,), daemon=True).start()

    def _play_music_loop(self, music_file):
        """Циклическое воспроизведение в отдельном потоке с пониженной громкостью"""
        # Получаем длительность трека один раз
        try:
            with wave.open(music_file, 'rb') as wav:
                duration = wav.getnframes() / wav.getframerate()
        except:
            duration = 1

        while self.music_playing:
            try:
                # Устанавливаем громкость (0-65535), 20000 - примерно 30% громкости
                volume = 20000
                # Используем waveOutSetVolume через ctypes для установки громкости
                import ctypes
                winmm = ctypes.windll.winmm
                # Установка громкости для левого и правого каналов
                winmm.waveOutSetVolume(0, volume + (volume << 16))

                winsound.PlaySound(music_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                # Ждем окончания трека с проверкой флага
                elapsed = 0
                while elapsed < duration and self.music_playing:
                    time.sleep(0.1)
                    elapsed += 0.1
            except:
                if self.music_playing:
                    time.sleep(1)

    def stop_music(self):
        """Полная остановка музыки"""
        self.music_playing = False
        try:
            winsound.PlaySound(None, winsound.SND_ASYNC)
        except:
            pass

    def pause_music(self):
        """Пауза музыки"""
        self.music_playing = False
        try:
            winsound.PlaySound(None, winsound.SND_ASYNC)
        except:
            pass

    def resume_music(self):
        """Возобновление музыки"""
        if not self.music_playing:
            self.start_music()

    def toggle_music(self, event=None):
        """Переключение музыки вкл/выкл"""
        self.music_enabled = not self.music_enabled

        if self.music_enabled:
            self.start_music()
        else:
            self.stop_music()

        # Обновляем отображение кнопки звука
        self.draw_sound_button()

    def draw_sound_button(self):
        """Отрисовка кнопки звука в левом верхнем углу"""
        # Удаляем старую кнопку если есть
        if 'sound_button' in self.ui_elements:
            self.canvas.delete(self.ui_elements['sound_button'])

        # Определяем размер кнопки
        scale = self.get_scale_factor()
        button_size = int(40 * scale)
        padding = int(20 * scale)

        # Позиция в левом верхнем углу
        button_x = padding + button_size // 2
        button_y = padding + button_size // 2

        # Выбираем спрайт в зависимости от состояния
        sprite_key = 'sound_on' if self.music_enabled else 'sound_off'
        sound_btn = self.get_scaled_sprite(sprite_key, button_size, button_size)

        if sound_btn:
            self.ui_elements['sound_button'] = self.canvas.create_image(
                button_x, button_y,
                image=sound_btn,
                anchor='center'
            )
            # Привязываем обработчик клика
            self.canvas.tag_bind(self.ui_elements['sound_button'], '<Button-1>', self.toggle_music)

    def get_scale_factor(self):
        """Получить коэффициент масштабирования относительно базового размера"""
        scale_x = self.WIDTH / self.BASE_WIDTH
        scale_y = self.HEIGHT / self.BASE_HEIGHT
        return min(scale_x, scale_y)

    def get_scaled_sprite(self, key, width, height):
        if width <= 0 or height <= 0:
            return None

        cache_key = f"{key}_{width}_{height}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        if key in self.images and self.images[key]:
            try:
                img = self.images[key].resize((width, height), self.RESAMPLE_RESIZE)
                photo = ImageTk.PhotoImage(img)
                self.sprite_cache[cache_key] = photo
                return photo
            except Exception:
                return None
        return None

    def get_flipped_sprite(self, key, width, height, flip_horizontal=False):
        if width <= 0 or height <= 0:
            return None

        cache_key = f"{key}_{width}_{height}_{flip_horizontal}"
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        if key in self.images and self.images[key]:
            try:
                img = self.images[key]
                if flip_horizontal:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                img = img.resize((width, height), self.RESAMPLE_RESIZE)
                photo = ImageTk.PhotoImage(img)
                self.sprite_cache[cache_key] = photo
                return photo
            except Exception:
                return None
        return None

    def update_spawn_and_target_points(self):
        """Обновление точек спавна и целей при изменении размера окна"""
        scale_x = self.WIDTH / self.BASE_WIDTH
        scale_y = self.HEIGHT / self.BASE_HEIGHT

        self.spawn_points = [
            ((20 + 40) * scale_x, (180 + 30) * scale_y),
            ((20 + 40) * scale_x, (380 + 30) * scale_y),
            ((700 + 40) * scale_x, (180 + 30) * scale_y),
            ((700 + 40) * scale_x, (380 + 30) * scale_y)
        ]

        self.target_points = [
            (self.WIDTH * 0.30, self.HEIGHT * 0.50),
            (self.WIDTH * 0.30, self.HEIGHT * 0.75),
            (self.WIDTH * 0.70, self.HEIGHT * 0.50),
            (self.WIDTH * 0.70, self.HEIGHT * 0.75)
        ]

        self.update_path_lengths()

    def update_path_lengths(self):
        """Вычисление длин путей для масштабирования скорости"""
        self.path_lengths = []
        for i in range(4):
            dx = self.target_points[i][0] - self.spawn_points[i][0]
            dy = self.target_points[i][1] - self.spawn_points[i][1]
            length = math.sqrt(dx ** 2 + dy ** 2)
            self.path_lengths.append(length)

    def get_scaled_speed(self):
        """Получить масштабированную скорость на основе размера окна"""
        scale = self.get_scale_factor()
        if hasattr(self, 'path_lengths') and self.path_lengths:
            avg_length = sum(self.path_lengths) / len(self.path_lengths)
            base_length = math.sqrt((self.BASE_WIDTH * 0.7 - 60) ** 2 + (self.BASE_HEIGHT * 0.75 - 210) ** 2)
            length_scale = avg_length / base_length if base_length > 0 else scale
        else:
            length_scale = scale

        return self.egg_speed * length_scale

    def on_canvas_resize(self, event):
        if event.width != self.WIDTH or event.height != self.HEIGHT:
            self.WIDTH = event.width
            self.HEIGHT = event.height

            self.update_spawn_and_target_points()

            if self.game_active and not self.game_over:
                new_eggs = []
                for egg in self.eggs:
                    if egg['active']:
                        old_start_x, old_start_y = egg['start_x'], egg['start_y']
                        old_end_x, old_end_y = egg['end_x'], egg['end_y']
                        old_lane = egg['lane']

                        new_start_x, new_start_y = self.spawn_points[old_lane]
                        new_end_x, new_end_y = self.target_points[old_lane]

                        old_dx = old_end_x - old_start_x
                        old_dy = old_end_y - old_start_y
                        old_distance = math.sqrt(old_dx ** 2 + old_dy ** 2)

                        current_dx = egg['x'] - old_start_x
                        current_dy = egg['y'] - old_start_y
                        current_distance = math.sqrt(current_dx ** 2 + current_dy ** 2)

                        if old_distance > 0:
                            progress = current_distance / old_distance
                        else:
                            progress = 0

                        new_dx = new_end_x - new_start_x
                        new_dy = new_end_y - new_start_y
                        new_x = new_start_x + new_dx * progress
                        new_y = new_start_y + new_dy * progress

                        egg['x'] = new_x
                        egg['y'] = new_y
                        egg['start_x'] = new_start_x
                        egg['start_y'] = new_start_y
                        egg['end_x'] = new_end_x
                        egg['end_y'] = new_end_y
                        self.canvas.coords(egg['id'], new_x, new_y)
                        new_eggs.append(egg)
                    else:
                        self.canvas.delete(egg['id'])
                self.eggs = new_eggs

            self.sprite_cache.clear()
            self.wolf_obj = None
            self.basket_obj = None

            if self.game_active and not self.game_paused and not self.game_over:
                self.canvas.delete('all')
                self.draw_game_environment()
            elif self.game_paused:
                self.canvas.delete('all')
                self.draw_game_environment()
                self.show_pause_screen()
            elif self.game_over:
                self.canvas.delete('all')
                self.draw_game_environment()
                self.update_ui()
            elif self.current_menu:
                self.show_main_menu()

    def toggle_fullscreen(self, event=None):
        is_fullscreen = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not is_fullscreen)

    def handle_escape(self, event=None):
        if self.root.attributes('-fullscreen'):
            self.root.attributes('-fullscreen', False)
        elif self.game_active:
            self.return_to_menu()

    def on_closing(self):
        self.stop_music()
        if self.root.attributes('-fullscreen'):
            self.root.attributes('-fullscreen', False)
        self.root.quit()
        self.root.destroy()

    def show_main_menu(self):
        self.canvas.delete('all')

        self.game_active = False
        self.game_paused = False
        self.game_over = False
        self.current_menu = True
        self.eggs.clear()
        self.wolf_obj = None
        self.basket_obj = None
        self.ui_elements.clear()
        self.game_over_elements.clear()
        self.pause_elements.clear()

        bg = self.get_scaled_sprite('background', self.WIDTH, self.HEIGHT)
        if bg:
            self.canvas.create_image(0, 0, anchor='nw', image=bg)

        # Кнопка звука в меню (левый верхний угол)
        self.draw_sound_button()

        self.canvas.create_text(self.WIDTH // 2, self.HEIGHT * 0.15,
                                text="НУ, ПОГОДИ!", font=('Arial', 52, 'bold'), fill='#FF4500')

        button_w, button_h = 250, 60
        start_y = self.HEIGHT * 0.35
        start_btn = self.canvas.create_rectangle(self.WIDTH // 2 - button_w // 2, start_y - button_h // 2,
                                                 self.WIDTH // 2 + button_w // 2, start_y + button_h // 2,
                                                 fill='#4CAF50', outline='white', width=2)
        start_text = self.canvas.create_text(self.WIDTH // 2, start_y,
                                             text="Начать игру", font=('Arial', 18, 'bold'), fill='white')
        self.canvas.tag_bind(start_btn, '<Button-1>', lambda e: self.start_game())
        self.canvas.tag_bind(start_text, '<Button-1>', lambda e: self.start_game())

        exit_y = self.HEIGHT * 0.48
        exit_btn = self.canvas.create_rectangle(self.WIDTH // 2 - button_w // 2, exit_y - button_h // 2,
                                                self.WIDTH // 2 + button_w // 2, exit_y + button_h // 2,
                                                fill='#f44336', outline='white', width=2)
        exit_text = self.canvas.create_text(self.WIDTH // 2, exit_y,
                                            text="ВЫХОД", font=('Arial', 18, 'bold'), fill='white')
        self.canvas.tag_bind(exit_btn, '<Button-1>', lambda e: self.root.quit())
        self.canvas.tag_bind(exit_text, '<Button-1>', lambda e: self.root.quit())

        rules_x = self.WIDTH * 0.70
        rules_y = self.HEIGHT * 0.28

        self.canvas.create_text(rules_x, rules_y, text="Правила игры",
                                font=('Arial', 22, 'bold'), fill='#FFD700', anchor='nw')

        rules_text = [
            "• WASD или стрелки —",
            "  перемещение корзины",
            "• Ловите яйца в корзину",
            "• 3 жизни — 3 промаха",
            "  до конца игры",
            "• Каждые 10 яиц",
            "  скорость увеличивается",
            "• ПРОБЕЛ — пауза",
            "• ESC — выход в меню"
        ]

        for i, line in enumerate(rules_text):
            self.canvas.create_text(rules_x, rules_y + 40 + i * 26,
                                    text=line, font=('Arial', 14), fill='white', anchor='nw')

    def show_pause_screen(self):
        for item in self.pause_elements:
            self.canvas.delete(item)
        self.pause_elements.clear()

        overlay = self.canvas.create_rectangle(0, 0, self.WIDTH, self.HEIGHT, fill='black', stipple='gray25')
        self.pause_elements.append(overlay)

        pause_text = self.canvas.create_text(self.WIDTH // 2, self.HEIGHT // 2 - 40, text="ПАУЗА",
                                             font=('Arial', 48, 'bold'), fill='#FFD700')
        self.pause_elements.append(pause_text)

        info_text = self.canvas.create_text(self.WIDTH // 2, self.HEIGHT // 2 + 10,
                                            text=f"Счёт: {self.score} | Жизни: {self.lives}",
                                            font=('Arial', 18), fill='white')
        self.pause_elements.append(info_text)

        hints = ["ПРОБЕЛ — продолжить", "ESC — выйти в меню"]
        for i, hint in enumerate(hints):
            hint_text = self.canvas.create_text(self.WIDTH // 2, self.HEIGHT // 2 + 50 + i * 30, text=hint,
                                                font=('Arial', 14), fill='#CCCCCC')
            self.pause_elements.append(hint_text)

        # Кнопка звука на паузе (левый верхний угол)
        self.draw_sound_button()

    def return_to_menu(self):
        self.game_active = False
        self.game_paused = False
        self.game_over = False
        self.current_menu = True
        self.resume_music()
        self.show_main_menu()

    def move_basket(self, new_position, direction):
        if self.game_active and not self.game_over and not self.game_paused:
            self.basket_position = new_position
            self.basket_direction = direction
            self.draw_wolf_and_basket()

    def handle_keypress(self, event):
        key = event.keysym
        char = event.char.lower() if event.char else ''

        if key == 'space' and self.game_over:
            self.return_to_menu()
            return

        if key == 'space' and self.game_active:
            if not self.game_paused and not self.game_over:
                self.game_paused = True
                self.pause_music()
                self.show_pause_screen()
            elif self.game_paused:
                self.game_paused = False
                self.resume_music()
                for item in self.pause_elements:
                    self.canvas.delete(item)
                self.pause_elements.clear()
                self.game_loop()
            return

        if not self.game_active or self.game_over or self.game_paused:
            return

        if key == 'Left' or char in ['a', 'ф']:
            if self.basket_position == 2:
                self.move_basket(0, 'left')
            elif self.basket_position == 3:
                self.move_basket(1, 'left')
        elif key == 'Right' or char in ['d', 'в']:
            if self.basket_position == 0:
                self.move_basket(2, 'right')
            elif self.basket_position == 1:
                self.move_basket(3, 'right')
        elif key == 'Up' or char in ['w', 'ц']:
            if self.basket_position == 1:
                self.move_basket(0, self.basket_direction)
            elif self.basket_position == 3:
                self.move_basket(2, self.basket_direction)
        elif key == 'Down' or char in ['s', 'ы']:
            if self.basket_position == 0:
                self.move_basket(1, self.basket_direction)
            elif self.basket_position == 2:
                self.move_basket(3, self.basket_direction)

    def draw_game_environment(self):
        bg = self.get_scaled_sprite('game_bg', self.WIDTH, self.HEIGHT)
        if bg:
            self.canvas.create_image(0, 0, anchor='nw', image=bg)

        # Кнопка звука в игре (левый верхний угол)
        self.draw_sound_button()

        scale_x = self.WIDTH / self.BASE_WIDTH
        scale_y = self.HEIGHT / self.BASE_HEIGHT

        chicken_coops = [(20, 180), (20, 380), (700, 180), (700, 380)]

        if self.images['chute']:
            for i in range(4):
                x1, y1 = self.spawn_points[i]
                x2, y2 = self.target_points[i]

                dx = x2 - x1
                dy = y2 - y1
                length = math.sqrt(dx * dx + dy * dy)
                angle = -math.degrees(math.atan2(dy, dx))

                chute_img = self.images['chute']
                chute_height = int(25 * scale_y)
                chute_width = int(length)

                if chute_width > 0 and chute_height > 0:
                    scaled = chute_img.resize((chute_width, chute_height), self.RESAMPLE_RESIZE)
                    rotated = scaled.rotate(angle, resample=self.RESAMPLE_ROTATE, expand=True)

                    cache_key = f"chute_{chute_width}_{chute_height}_{angle:.1f}"
                    if cache_key not in self.sprite_cache:
                        self.sprite_cache[cache_key] = ImageTk.PhotoImage(rotated)

                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2
                    self.canvas.create_image(cx, cy, image=self.sprite_cache[cache_key], anchor='center')

        if self.images['chicken_coop']:
            coop_w, coop_h = int(80 * scale_x), int(60 * scale_y)
            for x, y in chicken_coops:
                coop = self.get_scaled_sprite('chicken_coop', coop_w, coop_h)
                if coop:
                    self.canvas.create_image(x * scale_x, y * scale_y, anchor='nw', image=coop)

        self.ui_elements['score_text'] = self.canvas.create_text(
            self.WIDTH // 2, 50, text=f"{self.score}",
            font=('Arial', 48, 'bold'), fill='#FFD700', anchor='center'
        )

        self.canvas.create_text(
            self.WIDTH // 2, 20, text="Подсчет очков",
            font=('Arial', 16, 'bold'), fill='#FFFFFF', anchor='center'
        )

        if self.images['heart']:
            lives_y = 40
            heart_size = 35
            heart_spacing = 5
            start_x = self.WIDTH - (heart_size * 3 + heart_spacing * 2) - 20

            self.ui_elements['lives'] = []
            for i in range(3):
                x = start_x + i * (heart_size + heart_spacing)
                heart = self.get_scaled_sprite('heart', heart_size, heart_size)
                if heart:
                    heart_obj = self.canvas.create_image(x, lives_y, anchor='nw', image=heart)
                    self.ui_elements['lives'].append(heart_obj)

        self.wolf_obj = None
        self.basket_obj = None
        self.draw_wolf_and_basket()

    def draw_wolf_and_basket(self):
        scale = min(self.WIDTH / self.BASE_WIDTH, self.HEIGHT / self.BASE_HEIGHT)

        if self.images['wolf']:
            wolf_x, wolf_y = self.WIDTH // 2, self.HEIGHT // 2 - 50
            wolf_w, wolf_h = int(200 * scale), int(300 * scale)
            wolf_img = self.get_scaled_sprite('wolf', wolf_w, wolf_h)

            if wolf_img:
                if self.wolf_obj is None:
                    self.wolf_obj = self.canvas.create_image(wolf_x, wolf_y, image=wolf_img, anchor='center')
                else:
                    self.canvas.coords(self.wolf_obj, wolf_x, wolf_y)
                    self.canvas.itemconfig(self.wolf_obj, image=wolf_img)

        if self.images['basket']:
            basket_positions = [
                (int(self.WIDTH * 0.30), int(self.HEIGHT * 0.50)),
                (int(self.WIDTH * 0.30), int(self.HEIGHT * 0.75)),
                (int(self.WIDTH * 0.70), int(self.HEIGHT * 0.50)),
                (int(self.WIDTH * 0.70), int(self.HEIGHT * 0.75))
            ]
            basket_x, basket_y = basket_positions[self.basket_position]
            basket_w, basket_h = int(100 * scale), int(60 * scale)
            flip = (self.basket_direction == 'left')
            basket_img = self.get_flipped_sprite('basket', basket_w, basket_h, flip_horizontal=flip)

            if basket_img:
                if self.basket_obj is None:
                    self.basket_obj = self.canvas.create_image(basket_x, basket_y, image=basket_img, anchor='center')
                else:
                    self.canvas.coords(self.basket_obj, basket_x, basket_y)
                    self.canvas.itemconfig(self.basket_obj, image=basket_img)

    def spawn_egg(self):
        lane = random.randint(0, 3)

        start_x, start_y = self.spawn_points[lane]
        end_x, end_y = self.target_points[lane]

        if self.images['egg']:
            scale = min(self.WIDTH / self.BASE_WIDTH, self.HEIGHT / self.BASE_HEIGHT)
            egg_w = int(30 * scale)
            egg_h = int(egg_w * 1.2)

            egg_img = self.get_scaled_sprite('egg', egg_w, egg_h)

            if egg_img:
                egg_id = self.canvas.create_image(start_x, start_y, image=egg_img, anchor='center')

                egg = {
                    'id': egg_id,
                    'x': start_x,
                    'y': start_y,
                    'start_x': start_x,
                    'start_y': start_y,
                    'end_x': end_x,
                    'end_y': end_y,
                    'lane': lane,
                    'active': True
                }
                self.eggs.append(egg)

    def update_eggs(self):
        eggs_to_remove = []
        scaled_speed = self.get_scaled_speed()

        for egg in self.eggs:
            if not egg['active']:
                continue

            dx = egg['end_x'] - egg['x']
            dy = egg['end_y'] - egg['y']
            distance = math.sqrt(dx ** 2 + dy ** 2)

            if distance > scaled_speed:
                step_x = (dx / distance) * scaled_speed
                step_y = (dy / distance) * scaled_speed
                egg['x'] += step_x
                egg['y'] += step_y
                self.canvas.coords(egg['id'], egg['x'], egg['y'])
            else:
                basket_positions = [
                    (self.WIDTH * 0.30, self.HEIGHT * 0.50),
                    (self.WIDTH * 0.30, self.HEIGHT * 0.75),
                    (self.WIDTH * 0.70, self.HEIGHT * 0.50),
                    (self.WIDTH * 0.70, self.HEIGHT * 0.75)
                ]

                basket_x, basket_y = basket_positions[egg['lane']]
                egg_center_x = egg['x']
                egg_center_y = egg['y']

                distance_to_basket = math.sqrt((egg_center_x - basket_x) ** 2 + (egg_center_y - basket_y) ** 2)

                scale = self.get_scale_factor()
                basket_size = 40 * scale

                if distance_to_basket <= basket_size and egg['lane'] == self.basket_position:
                    self.score += 1

                    if self.score % self.SPEED_INCREASE_INTERVAL == 0:
                        self.egg_speed += self.SPEED_INCREMENT
                        self.spawn_interval = max(30, self.spawn_interval - 5)
                else:
                    self.lives -= 1
                    if self.lives <= 0:
                        self.game_over = True
                        self.game_active = False

                eggs_to_remove.append(egg)

        for egg in eggs_to_remove:
            self.canvas.delete(egg['id'])
            self.eggs.remove(egg)

    def update_ui(self):
        if 'score_text' in self.ui_elements:
            self.canvas.itemconfig(self.ui_elements['score_text'], text=f"{self.score}")

        if 'lives' in self.ui_elements:
            for i in range(len(self.ui_elements['lives'])):
                if i < self.lives:
                    self.canvas.itemconfig(self.ui_elements['lives'][i], state='normal')
                else:
                    self.canvas.itemconfig(self.ui_elements['lives'][i], state='hidden')

        if self.game_over:
            for item in self.game_over_elements:
                self.canvas.delete(item)
            self.game_over_elements.clear()

            overlay = self.canvas.create_rectangle(0, 0, self.WIDTH, self.HEIGHT, fill='black', stipple='gray25')
            self.game_over_elements.append(overlay)

            go_text = self.canvas.create_text(self.WIDTH // 2, self.HEIGHT // 2 - 40, text="ИГРА ОКОНЧЕНА",
                                              font=('Arial', 36, 'bold'), fill='#FF0000')
            fs_text = self.canvas.create_text(self.WIDTH // 2, self.HEIGHT // 2 + 20,
                                              text=f"Финальный счёт: {self.score}",
                                              font=('Arial', 24, 'bold'), fill='#FFD700')
            r_text = self.canvas.create_text(self.WIDTH // 2, self.HEIGHT // 2 + 70,
                                             text="Нажмите ПРОБЕЛ для возврата в меню",
                                             font=('Arial', 16), fill='white')

            self.game_over_elements.extend([go_text, fs_text, r_text])

            # Кнопка звука при game over (левый верхний угол)
            self.draw_sound_button()

    def start_game(self):
        self.game_active = True
        self.game_paused = False
        self.game_over = False
        self.current_menu = False
        self.score = 0
        self.lives = 3
        self.egg_speed = self.EGG_SPEED_START
        self.spawn_timer = 0
        self.spawn_interval = 90
        self.basket_position = 1
        self.basket_direction = 'right'

        self.eggs.clear()
        self.wolf_obj = None
        self.basket_obj = None
        self.ui_elements.clear()
        self.game_over_elements.clear()
        self.pause_elements.clear()
        self.sprite_cache.clear()

        self.canvas.delete('all')
        self.update_spawn_and_target_points()
        self.draw_game_environment()
        self.game_loop()

    def game_loop(self):
        if self.game_active and not self.game_over and not self.game_paused:
            self.spawn_timer += 1
            if self.spawn_timer >= self.spawn_interval:
                self.spawn_egg()
                self.spawn_timer = 0

            self.update_eggs()
            self.update_ui()

            self.root.after(1000 // self.FPS, self.game_loop)
        elif self.game_over:
            self.update_ui()


def main():
    root = tk.Tk()
    root.minsize(800, 600)
    root.geometry('800x600')

    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 800) // 2
    y = (screen_height - 600) // 2
    root.geometry(f'800x600+{x}+{y}')
    root.resizable(True, True)

    try:
        root.iconbitmap('icon.ico')
    except:
        pass

    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()