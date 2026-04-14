import pygame
import sys
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 800, 600
FPS = 60

WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
DOOR_COLOR = (50, 200, 50)
GREEN = (0, 255, 0)
RED_LAVA = (220, 40, 20)
BOUNCE_COLOR = (0, 200, 255)

FONT = pygame.font.SysFont("Arial", 20, bold=True)
LARGE_FONT = pygame.font.SysFont("Arial", 60, bold=True)

PHYSICS = {
    "GRAVITY": 0.5,
    "FRICTION": -0.15,
    "JUMP_POWER": -11,
    "SPEED": 0.8
}

ASSETS, AUDIO = {}, {}

def load_image(name, size=None):
    full_path = os.path.join(BASE_DIR, name)
    img = pygame.image.load(full_path).convert_alpha()
    if size:
        img = pygame.transform.smoothscale(img, size)
    return img

def load_audio(name):
    path = os.path.join(BASE_DIR, name)
    try:
        return pygame.mixer.Sound(path)
    except:
        print(f"[ΠΡΟΕΙΔΟΠΟΙΗΣΗ] Δεν βρέθηκε: {name}")
        return None

def play_sfx(name):
    if name in AUDIO and AUDIO[name]:
        AUDIO[name].play()

def init_db():
    db_path = os.path.join(BASE_DIR, "highscore.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS scores (id INTEGER PRIMARY KEY, high_score INTEGER)''')
    c.execute('''SELECT high_score FROM scores WHERE id=1''')
    row = c.fetchone()
    if not row:
        c.execute('''INSERT INTO scores (id, high_score) VALUES (1, 0)''')
        conn.commit()
        val = 0
    else:
        val = row[0]
    conn.close()
    return val

def update_highscore_db(score):
    db_path = os.path.join(BASE_DIR, "highscore.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''UPDATE scores SET high_score=? WHERE id=1''', (score,))
    conn.commit()
    conn.close()

class Platform:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
    def draw(self, win, scroll):
        for tx in range(self.rect.x, self.rect.right, 40):
            for ty in range(self.rect.y, self.rect.bottom, 40):
                win.blit(ASSETS["tile"], (tx - scroll[0], ty - scroll[1]))

class Hazard:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
    def draw(self, win, scroll):
        pygame.draw.rect(win, RED_LAVA, (self.rect.x - scroll[0], self.rect.y - scroll[1], self.rect.w, self.rect.h))

class BouncePad:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
    def draw(self, win, scroll):
        pygame.draw.rect(win, BOUNCE_COLOR, (self.rect.x - scroll[0], self.rect.y - scroll[1], self.rect.w, self.rect.h))

class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 20)
    def draw(self, win, scroll):
        r = (self.rect.x - scroll[0], self.rect.y - scroll[1], self.rect.w, self.rect.h)
        pygame.draw.ellipse(win, GOLD, r)
        pygame.draw.ellipse(win, WHITE, (r[0]+4, r[1]+4, 6, 6))

class Enemy:
    def __init__(self, x, y, r):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.start_x = x
        self.range = r
        self.facing_right = True
        self.speed = 2
    def update(self):
        self.rect.x += self.speed if self.facing_right else -self.speed
        if self.rect.x > self.start_x + self.range: self.facing_right = False
        if self.rect.x < self.start_x: self.facing_right = True
    def draw(self, win, scroll):
        img = ASSETS["enemy"]
        if self.facing_right: img = pygame.transform.flip(img, True, False)
        win.blit(img, (self.rect.x - scroll[0], self.rect.y - scroll[1]))

class Player:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, 45, 60)
        self.pos = pygame.math.Vector2(0, 0)
        self.vel = pygame.math.Vector2(0, 0)
        self.acc = pygame.math.Vector2(0, 0)
        self.on_ground = False
        self.on_wall = 0
        self.coyote_timer = 0
        self.facing_right = True
        self.is_dead = False
        self.wall_slide_speed = 3
        self.wall_jump_lock = 0
        self.frame = 0

    def set_spawn(self, x, y):
        self.pos.update(x, y)
        self.rect.topleft = (x, y)
        self.vel.update(0, 0)
        self.on_wall = 0
        self.is_dead = False

    def jump(self):
        if self.on_wall and not self.on_ground:
            dir = -self.on_wall
            self.vel.y = PHYSICS["JUMP_POWER"]
            self.vel.x = dir * 10
            self.wall_jump_lock = 10
            play_sfx("jump")
        elif self.coyote_timer > 0:
            self.vel.y = PHYSICS["JUMP_POWER"]
            play_sfx("jump")

    def update(self, plats, haz, bouncers, enemies):
        self.acc.update(0, PHYSICS["GRAVITY"])
        keys = pygame.key.get_pressed()

        if self.wall_jump_lock > 0: self.wall_jump_lock -= 1

        if self.wall_jump_lock <= 0:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.acc.x = -PHYSICS["SPEED"]; self.facing_right = False
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.acc.x = PHYSICS["SPEED"]; self.facing_right = True

        self.acc.x += self.vel.x * PHYSICS["FRICTION"]
        self.vel.x += self.acc.x
        self.pos.x += self.vel.x + 0.5 * self.acc.x
        self.rect.x = int(self.pos.x)

        self.on_wall = 0
        for p in plats:
            if self.rect.colliderect(p.rect):
                if self.vel.x > 0: self.rect.right = p.rect.left
                elif self.vel.x < 0: self.rect.left = p.rect.right
                self.vel.x = 0
                self.pos.x = self.rect.x

        if not self.on_ground:
            right_check = self.rect.move(2, 0)
            left_check = self.rect.move(-2, 0)
            for p in plats:
                if right_check.colliderect(p.rect): self.on_wall = 1
                if left_check.colliderect(p.rect): self.on_wall = -1

        self.vel.y += self.acc.y
        if self.on_wall and not self.on_ground and self.vel.y > self.wall_slide_speed:
            self.vel.y = self.wall_slide_speed

        self.pos.y += self.vel.y + 0.5 * self.acc.y
        self.rect.y = int(self.pos.y)
        self.on_ground = False
        self.coyote_timer -= 1

        for p in plats:
            if self.rect.colliderect(p.rect):
                if self.vel.y > 0:
                    self.rect.bottom = p.rect.top
                    self.vel.y = 0; self.on_ground = True; self.coyote_timer = 10
                elif self.vel.y < 0:
                    self.rect.top = p.rect.bottom; self.vel.y = 0
                self.pos.y = self.rect.y

        for b in bouncers:
            if self.rect.colliderect(b.rect) and self.vel.y > 0:
                self.rect.bottom = b.rect.top; self.vel.y = -22; self.pos.y = self.rect.y; play_sfx("jump")

        for h in haz:
            if self.rect.colliderect(h.rect): self.is_dead = True

        for e in enemies[:]:
            if self.rect.colliderect(e.rect):
                if self.vel.y > 0 and self.rect.bottom < e.rect.centery + 10:
                    enemies.remove(e); self.vel.y = -8; play_sfx("jump")
                else:
                    self.is_dead = True

        if self.pos.y > 3000: self.is_dead = True
        self.frame += 1

    def draw(self, win, scroll):
        if not self.on_ground and self.on_wall == 0:
            img = ASSETS["jump"]
        elif abs(self.vel.x) > 0.5:
            img = ASSETS["run"] if (self.frame // 10) % 2 == 0 else ASSETS["idle"]
        else:
            img = ASSETS["idle"]
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
        win.blit(img, (self.rect.x - scroll[0], self.rect.y - scroll[1]))

class Game:
    def __init__(self):
        self.win = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Epic Platformer Deluxe")
        global ASSETS, AUDIO
        ASSETS["bg"] = load_image("bg.png", (WIDTH, HEIGHT))
        ASSETS["idle"] = load_image("idle.png", (45, 60))
        ASSETS["run"] = load_image("run1.png", (45, 60))
        ASSETS["jump"] = load_image("jump.png", (45, 60))
        ASSETS["tile"] = load_image("tile.png", (40, 40))
        ASSETS["enemy"] = load_image("enemy.png", (40, 40))
        AUDIO["jump"] = load_audio("jump.wav")
        AUDIO["coin"] = load_audio("coin.wav")

        bgm = os.path.join(BASE_DIR, "bgm.mp3")
        if os.path.exists(bgm):
            pygame.mixer.music.load(bgm)
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)

        self.clock = pygame.time.Clock()
        self.player = Player()
        self.high_score = init_db()
        self.state = "MENU"
        self.current_level = 1
        self.max_levels = 2
        self.score = 0
        self.level_start_score = 0
        self.lives = 3
        self.score_saved = False

    def load_level(self, level):
        self.scroll = [0, 0]
        self.score_saved = False
        
        if level == 1:
            self.player.set_spawn(100, 300)
            self.platforms =[
                Platform(-80, 0, 80, 1000), 
                Platform(0, 520, 400, 80),          
                Platform(560, 440, 80, 40),
                Platform(760, 400, 80, 40),
                Platform(960, 0, 40, 600), 
                Platform(1200, -200, 40, 720), 
                Platform(1240, -120, 400, 40),
                Platform(1800, 120, 120, 40),
                Platform(2000, 320, 120, 40),
                Platform(2200, 520, 120, 40),
                Platform(2520, 400, 520, 80)
            ]
            self.enemies =[
                Enemy(200, 480, 150),       
                Enemy(1400, -160, 100),     
                Enemy(2600, 360, 200)       
            ]
            self.hazards =[
                Hazard(400, 600, 550, 50), 
                Hazard(1300, -80, 80, 40), 
                Hazard(2320, 800, 800, 100) 
            ]
            self.bounce_pads =[
                BouncePad(840, 440, 40, 20), 
                BouncePad(1640, -80, 40, 20) 
            ]
            self.coins =[
                Coin(150, 480), Coin(300, 480), 
                Coin(590, 400), Coin(790, 360), 
                Coin(1050, 200), Coin(1100, 100), 
                Coin(1350, -160), Coin(1450, -160), 
                Coin(2550, 360), Coin(2650, 360) 
            ]
            self.door = pygame.Rect(2800, 320, 60, 80)

        elif level == 2:
            self.player.set_spawn(50, 500)
            self.platforms =[
                Platform(-80, 0, 80, 1000), 
                Platform(0, 600, 300, 80),
                Platform(400, 450, 100, 40),
                Platform(650, 300, 100, 40),
                Platform(900, 150, 100, 40),
                Platform(1200, 150, 400, 40),
                Platform(1700, 300, 150, 40),
                Platform(2000, 450, 400, 80)
            ]
            self.enemies =[
                Enemy(1300, 110, 200),
                Enemy(2100, 410, 150)
            ]
            self.hazards =[
                Hazard(300, 800, 2000, 100) 
            ]
            self.bounce_pads =[
                BouncePad(1650, 100, 40, 20)
            ]
            self.coins =[
                Coin(440, 400), Coin(690, 250), Coin(940, 100),
                Coin(1250, 100), Coin(1450, 100), Coin(1750, 250)
            ]
            self.door = pygame.Rect(2300, 370, 60, 80)

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if self.state == "MENU":
                    if event.key == pygame.K_RETURN: 
                        self.score = 0
                        self.level_start_score = 0
                        self.lives = 3 # Κάνουμε reset τις ζωές
                        self.current_level = 1
                        self.load_level(self.current_level)
                        self.state = "PLAYING"
                        
                elif self.state == "PLAYING":
                    if event.key == pygame.K_SPACE or event.key == pygame.K_w or event.key == pygame.K_UP:
                        self.player.jump()
                        
                elif self.state == "LEVEL_COMPLETE":
                    if event.key == pygame.K_RETURN:
                        self.level_start_score = self.score # Αποθήκευση σκορ για τη νέα πίστα
                        self.current_level += 1
                        self.load_level(self.current_level)
                        self.state = "PLAYING"
                        
                elif self.state == "WIN" or self.state == "GAME_OVER":
                    if event.key == pygame.K_r: 
                        self.state = "MENU" 
            
            if event.type == pygame.KEYUP:
                if self.state == "PLAYING":
                    if (event.key == pygame.K_SPACE or event.key == pygame.K_w or event.key == pygame.K_UP) and self.player.vel.y < 0:
                        self.player.vel.y *= 0.5 

    def update(self):
        if self.state == "PLAYING":
            for enemy in self.enemies:
                enemy.update()

            self.player.update(self.platforms, self.hazards, self.bounce_pads, self.enemies)
            
            # [NEW] Τι γίνεται αν πεθάνει;
            if self.player.is_dead:
                self.lives -= 1
                if self.lives > 0:
                    self.score = self.level_start_score # Αφαιρεί τα νομίσματα που μάζεψες σε αυτή την προσπάθεια
                    self.load_level(self.current_level) # Κάνει reset την πίστα (εχθρούς/νομίσματα)
                else:
                    self.state = "GAME_OVER"

            for coin in self.coins[:]: 
                if self.player.rect.colliderect(coin.rect):
                    self.coins.remove(coin) 
                    self.score += 10        
            
            if self.player.rect.colliderect(self.door):
                if self.current_level < self.max_levels:
                    self.state = "LEVEL_COMPLETE"
                else:
                    self.state = "WIN" 
            
            self.scroll[0] += (self.player.rect.x - self.scroll[0] - WIDTH // 2) / 15
            self.scroll[1] += (self.player.rect.y - self.scroll[1] - HEIGHT // 2) / 15

        elif self.state == "WIN":
            if not self.score_saved:
                if self.score > self.high_score:
                    self.high_score = self.score
                    update_highscore_db(self.high_score)
                self.score_saved = True

    def draw(self):
        bg_x = -(self.scroll[0] * 0.3) % WIDTH if self.state == "PLAYING" else 0
        self.win.blit(ASSETS["bg"], (bg_x, 0))
        self.win.blit(ASSETS["bg"], (bg_x - WIDTH, 0))
        
        if self.state == "MENU":
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(100)
            overlay.fill((0, 0, 0))
            self.win.blit(overlay, (0, 0))
            
            title_text = LARGE_FONT.render("EPIC PLATFORMER", True, WHITE)
            start_text = FONT.render("Press [ENTER] to Start", True, GOLD)
            hs_text = FONT.render(f"HIGH SCORE: {self.high_score}", True, GREEN)
            
            self.win.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//3))
            self.win.blit(start_text, (WIDTH//2 - start_text.get_width()//2, HEIGHT//2))
            self.win.blit(hs_text, (WIDTH//2 - hs_text.get_width()//2, HEIGHT//2 + 50))

        else:
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

            door_draw_rect = (self.door.x - render_scroll[0], self.door.y - render_scroll[1], self.door.w, self.door.h)
            pygame.draw.rect(self.win, DOOR_COLOR, door_draw_rect)

            for pad in self.bounce_pads: pad.draw(self.win, render_scroll)
            for hazard in self.hazards: hazard.draw(self.win, render_scroll)
            for enemy in self.enemies: enemy.draw(self.win, render_scroll)
            for plat in self.platforms: plat.draw(self.win, render_scroll)
            for coin in self.coins: coin.draw(self.win, render_scroll)
                
            if self.state != "GAME_OVER":
                self.player.draw(self.win, render_scroll)

            # [NEW] Εμφάνιση Ζωών!
            score_text = FONT.render(f"SCORE: {self.score}", True, GOLD)
            level_text = FONT.render(f"LEVEL: {self.current_level}/{self.max_levels}", True, WHITE)
            lives_text = FONT.render(f"LIVES: {self.lives}", True, RED_LAVA)
            
            self.win.blit(score_text, (20, 20))
            self.win.blit(level_text, (20, 50))
            self.win.blit(lives_text, (20, 80))

            if self.state == "LEVEL_COMPLETE":
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.set_alpha(150)
                overlay.fill((0, 0, 0))
                self.win.blit(overlay, (0, 0))
                
                win_text = LARGE_FONT.render("LEVEL CLEARED!", True, GREEN)
                sub_text = FONT.render("Press [ENTER] for Next Level", True, WHITE)
                self.win.blit(win_text, (WIDTH//2 - win_text.get_width()//2, HEIGHT//2 - 50))
                self.win.blit(sub_text, (WIDTH//2 - sub_text.get_width()//2, HEIGHT//2 + 30))

            elif self.state == "WIN":
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.set_alpha(150)
                overlay.fill((0, 0, 0))
                self.win.blit(overlay, (0, 0))
                
                win_text = LARGE_FONT.render("EPIC VICTORY!", True, GOLD)
                sub_text = FONT.render(f"Final Score: {self.score} | Press 'R' to Return to Menu", True, WHITE)
                self.win.blit(win_text, (WIDTH//2 - win_text.get_width()//2, HEIGHT//2 - 50))
                self.win.blit(sub_text, (WIDTH//2 - sub_text.get_width()//2, HEIGHT//2 + 30))

            elif self.state == "GAME_OVER":
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.set_alpha(180)
                overlay.fill((0, 0, 0))
                self.win.blit(overlay, (0, 0))
                
                over_text = LARGE_FONT.render("GAME OVER", True, RED_LAVA)
                sub_text = FONT.render("Press 'R' to Return to Menu", True, WHITE)
                self.win.blit(over_text, (WIDTH//2 - over_text.get_width()//2, HEIGHT//2 - 50))
                self.win.blit(sub_text, (WIDTH//2 - sub_text.get_width()//2, HEIGHT//2 + 30))

        pygame.display.update()

    def run(self):
        while True:
            self.events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

if __name__ == "__main__":
    game = Game()
    game.run()
