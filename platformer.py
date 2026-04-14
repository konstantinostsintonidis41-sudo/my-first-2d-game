import pygame
import sys
import os
import sqlite3 # [NEW] Εισαγωγή της βιβλιοθήκης για τη Βάση Δεδομένων

# Βρίσκει τον σωστό φάκελο
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

pygame.init()
pygame.font.init()

# --- ΒΑΣΙΚΕΣ ΡΥΘΜΙΣΕΙΣ ---
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

ASSETS = {}

def load_image(name, size=None):
    full_path = os.path.join(BASE_DIR, name)
    try:
        img = pygame.image.load(full_path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    except Exception as e:
        print(f"\n[ΣΦΑΛΜΑ Pygame] Κάτι πήγε στραβά με το αρχείο: {name}")
        print(f"Λεπτομέρειες: {e}\n")
        sys.exit()

# --- [NEW] ΣΥΝΑΡΤΗΣΕΙΣ ΒΑΣΗΣ ΔΕΔΟΜΕΝΩΝ (BACK-END) ---
def init_db():
    """Δημιουργεί τη βάση και τον πίνακα αν δεν υπάρχουν και επιστρέφει το High Score."""
    db_path = os.path.join(BASE_DIR, "highscore.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS scores (id INTEGER PRIMARY KEY, high_score INTEGER)''')
    
    # Ψάχνουμε να δούμε αν υπάρχει ήδη αποθηκευμένο σκορ
    cursor.execute('''SELECT high_score FROM scores WHERE id=1''')
    row = cursor.fetchone()
    
    if row is None:
        # Αν παίζεις για πρώτη φορά, βάζουμε το High Score στο 0
        cursor.execute('''INSERT INTO scores (id, high_score) VALUES (1, 0)''')
        conn.commit()
        highscore = 0
    else:
        highscore = row[0]
        
    conn.close()
    return highscore

def update_highscore_db(new_score):
    """Ανανεώνει το High Score στη βάση δεδομένων."""
    db_path = os.path.join(BASE_DIR, "highscore.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''UPDATE scores SET high_score = ? WHERE id=1''', (new_score,))
    conn.commit()
    conn.close()
# ---------------------------------------------------

class Platform:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
    def draw(self, win, scroll):
        for tile_x in range(self.rect.x, self.rect.right, 40):
            for tile_y in range(self.rect.y, self.rect.bottom, 40):
                win.blit(ASSETS["tile"], (tile_x - scroll[0], tile_y - scroll[1]))

class Hazard:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
    def draw(self, win, scroll):
        draw_rect = (self.rect.x - scroll[0], self.rect.y - scroll[1], self.rect.w, self.rect.h)
        pygame.draw.rect(win, RED_LAVA, draw_rect)

class BouncePad:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)
    def draw(self, win, scroll):
        draw_rect = (self.rect.x - scroll[0], self.rect.y - scroll[1], self.rect.w, self.rect.h)
        pygame.draw.rect(win, BOUNCE_COLOR, draw_rect)

class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 20)
    def draw(self, win, scroll):
        draw_rect = (self.rect.x - scroll[0], self.rect.y - scroll[1], self.rect.w, self.rect.h)
        pygame.draw.ellipse(win, GOLD, draw_rect)
        pygame.draw.ellipse(win, WHITE, (draw_rect[0]+4, draw_rect[1]+4, 6, 6))

class Enemy:
    def __init__(self, x, y, walk_range):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.start_x = x
        self.walk_range = walk_range
        self.speed = 2
        self.facing_right = True

    def update(self):
        if self.facing_right:
            self.rect.x += self.speed
            if self.rect.x > self.start_x + self.walk_range:
                self.facing_right = False
        else:
            self.rect.x -= self.speed
            if self.rect.x < self.start_x:
                self.facing_right = True

    def draw(self, win, scroll):
        img = ASSETS["enemy"]
        if self.facing_right:
            img = pygame.transform.flip(img, True, False) 
        win.blit(img, (self.rect.x - scroll[0], self.rect.y - scroll[1]))

class Player:
    def __init__(self):
        self.rect = pygame.Rect(100, 300, 45, 60)
        self.pos = pygame.math.Vector2(100, 300)
        self.vel = pygame.math.Vector2(0, 0)
        self.acc = pygame.math.Vector2(0, 0)
        
        self.on_ground = False
        self.coyote_timer = 0
        self.on_wall = 0
        
        self.facing_right = True
        self.frame_count = 0 

    def jump(self):
        if self.coyote_timer > 0:
            self.vel.y = PHYSICS["JUMP_POWER"]
            self.coyote_timer = 0 
        elif self.on_wall != 0 and not self.on_ground:
            # [NEW] ΔΥΝΑΤΟ WALL JUMP! Σε πετάει πάνω και μακριά από τον τοίχο
            self.vel.y = PHYSICS["JUMP_POWER"] 
            self.vel.x = -self.on_wall * 15 # Σπρώξιμο προς την αντίθετη κατεύθυνση
            # Γυρίζει αμέσως τον παίκτη να κοιτάει προς τα εκεί που πήδηξε
            self.facing_right = True if self.on_wall == -1 else False

    def die(self):
        self.pos = pygame.math.Vector2(100, 300)
        self.vel = pygame.math.Vector2(0, 0)

    def update(self, platforms, hazards, bounce_pads, enemies):
        self.acc = pygame.math.Vector2(0, PHYSICS["GRAVITY"])
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.acc.x = -PHYSICS["SPEED"]
            self.facing_right = False 
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.acc.x = PHYSICS["SPEED"]
            self.facing_right = True 

        self.acc.x += self.vel.x * PHYSICS["FRICTION"]
        
        self.vel.x += self.acc.x
        self.pos.x += self.vel.x + 0.5 * self.acc.x
        self.rect.x = int(self.pos.x)
        
        self.on_wall = 0 # Μηδενίζουμε την τιμή κάθε καρέ

        # 1. Έλεγχος σύγκρουσης δεξιά/αριστερά
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel.x > 0:
                    self.rect.right = plat.rect.left
                elif self.vel.x < 0:
                    self.rect.left = plat.rect.right
                self.vel.x = 0
                self.pos.x = self.rect.x

        # 2. [NEW] Πιο έξυπνος εντοπισμός τοίχου (ακόμα κι αν έχουμε ταχύτητα 0)
        # Κοιτάμε 1 pixel πιο πέρα για να δούμε αν ακουμπάμε τοίχο!
        if not self.on_ground:
            right_check = self.rect.move(1, 0)
            left_check = self.rect.move(-1, 0)
            for plat in platforms:
                if right_check.colliderect(plat.rect):
                    self.on_wall = 1
                elif left_check.colliderect(plat.rect):
                    self.on_wall = -1

        self.vel.y += self.acc.y
        self.pos.y += self.vel.y + 0.5 * self.acc.y
        
        # 3. [NEW] Wall Slide (Γλίστρημα στον τοίχο) ΜΟΝΟ όταν πατάς προς τα εκεί!
        if self.on_wall != 0 and self.vel.y > 0 and not self.on_ground:
            # Αν ακουμπάω δεξιό τοίχο και πατάω ΔΕΞΙΑ, ή αριστερό και πατάω ΑΡΙΣΤΕΡΑ
            if (self.on_wall == 1 and (keys[pygame.K_RIGHT] or keys[pygame.K_d])) or \
               (self.on_wall == -1 and (keys[pygame.K_LEFT] or keys[pygame.K_a])):
                self.vel.y = 2 # Ταχύτητα γλιστρήματος (αργά προς τα κάτω)

        self.rect.y = int(self.pos.y)

        self.on_ground = False
        self.coyote_timer -= 1 
        
        for plat in platforms:
            if self.rect.colliderect(plat.rect):
                if self.vel.y > 0:
                    self.rect.bottom = plat.rect.top
                    self.vel.y = 0
                    self.on_ground = True
                    self.coyote_timer = 10 
                elif self.vel.y < 0:
                    self.rect.top = plat.rect.bottom
                    self.vel.y = 0
                self.pos.y = self.rect.y

        for pad in bounce_pads:
            if self.rect.colliderect(pad.rect) and self.vel.y > 0:
                self.rect.bottom = pad.rect.top
                self.vel.y = -22 
                self.pos.y = self.rect.y

        for hazard in hazards:
            if self.rect.colliderect(hazard.rect):
                self.die() 

        for enemy in enemies[:]:
            if self.rect.colliderect(enemy.rect):
                if self.vel.y > 0 and self.rect.bottom < enemy.rect.centery + 10:
                    enemies.remove(enemy) 
                    self.vel.y = -8       
                else:
                    self.die() 

        if self.pos.y > 2000: 
            self.die()
            
        self.frame_count += 1 

    def draw(self, win, scroll):
        if not self.on_ground and self.on_wall == 0:
            current_image = ASSETS["jump"]
        elif abs(self.vel.x) > 0.5:
            if (self.frame_count // 10) % 2 == 0:
                current_image = ASSETS["run"]
            else:
                current_image = ASSETS["idle"]
        else:
            current_image = ASSETS["idle"]

        if not self.facing_right:
            current_image = pygame.transform.flip(current_image, True, False)

        draw_x = self.rect.x - scroll[0]
        draw_y = self.rect.y - scroll[1]
        win.blit(current_image, (draw_x, draw_y))

    def draw(self, win, scroll):
        if not self.on_ground and self.on_wall == 0:
            current_image = ASSETS["jump"]
        elif abs(self.vel.x) > 0.5:
            if (self.frame_count // 10) % 2 == 0:
                current_image = ASSETS["run"]
            else:
                current_image = ASSETS["idle"]
        else:
            current_image = ASSETS["idle"]

        if not self.facing_right:
            current_image = pygame.transform.flip(current_image, True, False)

        draw_x = self.rect.x - scroll[0]
        draw_y = self.rect.y - scroll[1]
        win.blit(current_image, (draw_x, draw_y))

class Game:
    def __init__(self):
        self.win = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Epic Indie Platformer - Final Build")
        
        global ASSETS
        ASSETS["bg"] = load_image("bg.png", (WIDTH, HEIGHT))
        ASSETS["idle"] = load_image("idle.png", (45, 60))
        ASSETS["run"] = load_image("run1.png", (45, 60))
        ASSETS["jump"] = load_image("jump.png", (45, 60))
        ASSETS["tile"] = load_image("tile.png", (40, 40))
        ASSETS["enemy"] = load_image("enemy.png", (40, 40))

        self.clock = pygame.time.Clock()
        self.player = Player()
        self.scroll = [0, 0]
        self.score = 0
        
        # [NEW] Φόρτωση High Score από τη βάση δεδομένων!
        self.high_score = init_db()
        self.score_saved = False # Για να μην αποθηκεύει το σκορ 60 φορές το δευτερόλεπτο

        self.state = "PLAYING" 

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

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if self.state == "PLAYING":
                    if event.key == pygame.K_SPACE or event.key == pygame.K_w or event.key == pygame.K_UP:
                        self.player.jump()
                elif self.state == "WIN":
                    if event.key == pygame.K_r: 
                        self.__init__() 
            
            if event.type == pygame.KEYUP:
                if self.state == "PLAYING":
                    if (event.key == pygame.K_SPACE or event.key == pygame.K_w or event.key == pygame.K_UP) and self.player.vel.y < 0:
                        self.player.vel.y *= 0.5 

    def update(self):
        if self.state == "PLAYING":
            for enemy in self.enemies:
                enemy.update()

            self.player.update(self.platforms, self.hazards, self.bounce_pads, self.enemies)
            
            for coin in self.coins[:]: 
                if self.player.rect.colliderect(coin.rect):
                    self.coins.remove(coin) 
                    self.score += 10        
            
            if self.player.rect.colliderect(self.door):
                self.state = "WIN" 
            
            self.scroll[0] += (self.player.rect.x - self.scroll[0] - WIDTH // 2) / 15
            self.scroll[1] += (self.player.rect.y - self.scroll[1] - HEIGHT // 2) / 15

        elif self.state == "WIN":
            # [NEW] Όταν κερδίζει, ελέγχει αν το σκορ είναι ρεκόρ και το σώζει στη βάση!
            if not self.score_saved:
                if self.score > self.high_score:
                    self.high_score = self.score
                    update_highscore_db(self.high_score)
                self.score_saved = True

    def draw(self):
        bg_x = -(self.scroll[0] * 0.3) % WIDTH
        self.win.blit(ASSETS["bg"], (bg_x, 0))
        self.win.blit(ASSETS["bg"], (bg_x - WIDTH, 0))
        
        render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

        door_draw_rect = (self.door.x - render_scroll[0], self.door.y - render_scroll[1], self.door.w, self.door.h)
        pygame.draw.rect(self.win, DOOR_COLOR, door_draw_rect)

        for pad in self.bounce_pads: pad.draw(self.win, render_scroll)
        for hazard in self.hazards: hazard.draw(self.win, render_scroll)
        
        for enemy in self.enemies: enemy.draw(self.win, render_scroll)
        for plat in self.platforms: plat.draw(self.win, render_scroll)
        for coin in self.coins: coin.draw(self.win, render_scroll)
            
        self.player.draw(self.win, render_scroll)

        # [NEW] Εμφάνιση του Current Score ΚΑΙ του High Score!
        score_text = FONT.render(f"SCORE: {self.score}", True, GOLD)
        hs_text = FONT.render(f"HIGH SCORE: {self.high_score}", True, WHITE)
        self.win.blit(score_text, (20, 20))
        self.win.blit(hs_text, (20, 50))

        if self.state == "WIN":
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(150)
            overlay.fill((0, 0, 0))
            self.win.blit(overlay, (0, 0))
            
            win_text = LARGE_FONT.render("EPIC VICTORY!", True, GREEN)
            sub_text = FONT.render(f"Final Score: {self.score} | Press 'R' to Restart", True, WHITE)
            self.win.blit(win_text, (WIDTH//2 - win_text.get_width()//2, HEIGHT//2 - 50))
            self.win.blit(sub_text, (WIDTH//2 - sub_text.get_width()//2, HEIGHT//2 + 30))

            # [NEW] Μήνυμα αν έκανε Νέο Ρεκόρ!
            if self.score >= self.high_score and self.score > 0:
                record_text = FONT.render("NEW HIGH SCORE!", True, GOLD)
                self.win.blit(record_text, (WIDTH//2 - record_text.get_width()//2, HEIGHT//2 + 70))

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
