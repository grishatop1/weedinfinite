import sys
import pygame
from pygame.locals import *
import threading
import time
import pickle
import os
from copy import copy
import json
from perlin import PerlinNoiseFactory
import random
import multiprocessing


class Camera:
	def __init__(self):
		self.x = 0
		self.y = 0
		self.vel = 3

	def move(self):
		self.x = game.p.x - (width/2) + game.p.w/2
		self.y = game.p.y - (height/2) + game.p.h/2

	def offset(self, x, y):
		return x-self.x, y-self.y

	def reOffset(self, x, y):
		return x+self.x, y+self.y

class Terrain:
	def __init__(self):
		self.loaded_chunks = {} #4
		self.selected_texture = 0

		self.noise_biomes = PerlinNoiseFactory(1, 1)

		self.noise_plane = PerlinNoiseFactory(1, 3)
		self.noise_desert = PerlinNoiseFactory(1, 1)
		self.noise_mountain = PerlinNoiseFactory(1, 2)
		
		self.noise_caves = PerlinNoiseFactory(2, 5)
		self.generator = Worker(self.generateChunk)

	def generateChunk(self, lockin, lockout):
		while True:
			cx,cy = lockin.get()
			chunks = {}
			chunks[(cx,cy)] = {}

			if cy == 0:

				biome_n = self.noise_biomes(cx/10)
				
				if biome_n < 0.2:
					#Planes
					for x in range(CHUNK_TILE):
						xo = x*TILE + cx*CHUNK
						n = self.noise_plane(xo/CHUNK)
						no = n * 1000
						yo = round(no/TILE)*TILE + cy*CHUNK

						#Place grass block
						yoc = yo//CHUNK
						if (cx,yoc) not in chunks:
							chunks[(cx,yoc)] = {}
						chunks[(cx,yoc)][(xo,yo)] = {"id": 2}

						#Place grass
						if random.randint(0,1):
							yos = yo-TILE
							yocs = yos//CHUNK
							if (cx,yocs) not in chunks:
								chunks[(cx,yocs)] = {}
							chunks[(cx,yocs)][(xo,yos)] = {"id": 5}


						#Place everything below grass block
						for i, y in enumerate(range(yo+TILE, CHUNK, TILE)):
							yoc = y//CHUNK
							if (cx,yoc) not in chunks:
								chunks[(cx,yoc)] = {}
							if i < random.randint(4,7):
								chunks[(cx,yoc)][(xo,y)] = {"id": 1}
							else:
								chunks[(cx,yoc)][(xo,y)] = {"id": 3}
						
						#Place below chunk
						yo = yo + CHUNK
						yoc = yo//CHUNK
						if yoc == 0:
							for y in range(yo, CHUNK, TILE):
								try:
									del chunks[(cx,yoc)][(xo,y)]
								except:
									pass


				elif biome_n < 0.4:
					#Desert
					for x in range(CHUNK_TILE):
						xo = x*TILE + cx*CHUNK
						n = self.noise_desert(xo/CHUNK)
						no = n * 500
						yo = -abs(round(no/TILE)*TILE + cy*CHUNK)

						#Place sand block
						yoc = yo//CHUNK
						if (cx,yoc) not in chunks:
							chunks[(cx,yoc)] = {}
						chunks[(cx,yoc)][(xo,yo)] = {"id": 6}

						#Place below sand
						for i, y in enumerate(range(yo+TILE, CHUNK, TILE)):
							yoc = y//CHUNK
							if (cx,yoc) not in chunks:
								chunks[(cx,yoc)] = {}
							if i < random.randint(9,11):
								chunks[(cx,yoc)][(xo,y)] = {"id": 6}
							else:
								chunks[(cx,yoc)][(xo,y)] = {"id": 3}
				elif biome_n < 1:
					#Mountains
					for x in range(CHUNK_TILE):
						xo = x*TILE + cx*CHUNK
						n = self.noise_desert(xo/CHUNK)
						no = n * 2000
						yo = -abs(round(no/TILE)*TILE + cy*CHUNK)

						#Place stone block
						yoc = yo//CHUNK
						if (cx,yoc) not in chunks:
							chunks[(cx,yoc)] = {}
						chunks[(cx,yoc)][(xo,yo)] = {"id": 3}

						#Place snow if height is bigger than 30 tiles
						if yo < -TILE*29:
							chunks[(cx,yoc)][(xo,yo-TILE)] = {"id": 7}

						#Place below stone
						for i, y in enumerate(range(yo+TILE, CHUNK, TILE)):
							yoc = y//CHUNK
							if (cx,yoc) not in chunks:
								chunks[(cx,yoc)] = {}
							chunks[(cx,yoc)][(xo,y)] = {"id": 3}

			elif cy > -1:
				for x in range(CHUNK_TILE):
					for y in range(CHUNK_TILE):
						xo = x*TILE + cx*CHUNK
						yo = y*TILE + cy*CHUNK
						n = self.noise_caves(xo/CHUNK, yo/CHUNK)
						if n > 0:
							chunks[(cx,cy)][(xo,yo)] = {"id": 3}

			lockout.put(chunks)
		

	def loadSpecificChunk(self, x, y):
		try:
			with open(f"world/{x}.{y}.region", "rb") as f:
				data = pickle.load(f)
				self.loaded_chunks[(x,y)] = data
		except:
			with open(f"world/{x}.{y}.region", "wb+") as f:
				pickle.dump({},f)
				self.loaded_chunks[(x,y)] = {}
				self.generator.write((x,y))

	def getTilesInScreen(self):
		tiles = []
		for x in range(0, width+TILE, TILE):
			for y in range(0, height+TILE, TILE):
				xg, yg = game.c.reOffset(x,y)
				xbg, ybg = xg//TILE*TILE, yg//TILE*TILE

				xbgc, ybgc = xbg//CHUNK, ybg//CHUNK
				if (xbg,ybg) in self.loaded_chunks[(xbgc, ybgc)]:
					tiles.append([xbg, ybg])

		return tiles


	def getChunksByPos(self, distance=2):
		output = []
		chunkX, chunkY = int(game.c.x//CHUNK), int(game.c.y//CHUNK)
		for dx in range(-1, distance):
			for dy in range(-1, distance):
				output.append([chunkX+dx, chunkY+dy])
		return output

	def loadChunks(self):
		chunks_pos = self.getChunksByPos()
		for x,y in chunks_pos:
			if (x,y) not in self.loaded_chunks:
				self.loadSpecificChunk(x,y)

		data = self.generator.read()
		if data:
			chunks = data
			self.loaded_chunks.update(chunks)
	
	def unloadChunks(self):
		chunks_pos = self.getChunksByPos()
		for x,y in copy(self.loaded_chunks):
			if [x,y] not in chunks_pos:
				with open(f"world/{x}.{y}.region", "wb+") as f:
					pickle.dump(self.loaded_chunks[(x,y)], f)
				del self.loaded_chunks[(x,y)]

	def place(self):

		mox, moy = game.c.reOffset(game.xm, game.ym)
		x_tile, y_tile = mox//TILE*TILE, moy//TILE*TILE
		pygame.draw.rect(game.win, BLACK, (*game.c.offset(x_tile, y_tile), TILE, TILE), 1)


		if game.click[0]:
			mox, moy = game.c.reOffset(game.xm, game.ym)
			x_tile, y_tile = mox//TILE*TILE, moy//TILE*TILE
			x_chunk, y_chunk = mox//CHUNK, moy//CHUNK
			if (x_tile, y_tile) not in self.loaded_chunks[(x_chunk, y_chunk)]:
				self.loaded_chunks[(x_chunk, y_chunk)][(x_tile, y_tile)] = {"id": self.selected_texture}
		if game.click[2]:	
			mox, moy = game.c.reOffset(game.xm, game.ym)
			x_tile, y_tile = mox//TILE*TILE, moy//TILE*TILE
			x_chunk, y_chunk = mox//CHUNK, moy//CHUNK
			if (x_tile, y_tile) in self.loaded_chunks[(x_chunk, y_chunk)]:
				del self.loaded_chunks[(x_chunk, y_chunk)][(x_tile, y_tile)]

	def draw(self):
		for cx, cy in self.loaded_chunks:
			pygame.draw.rect(game.win, BLACK, (*game.c.offset(cx*CHUNK, cy*CHUNK), CHUNK, CHUNK), 1)
			
		for x, y in self.getTilesInScreen():
			xo, yo = game.c.offset(x,y)
			cx,cy = x//CHUNK, y//CHUNK
			game.win.blit(game.tx.getTextureImage(self.loaded_chunks[(cx,cy)][(x,y)]["id"]), (xo,yo))

	def saveAll(self):
		for x, y in self.loaded_chunks:
			with open(f"world/{x}.{y}.region", "wb+") as f:
				pickle.dump(self.loaded_chunks[(x,y)], f)

	def update(self):
		self.loadChunks()
		self.draw()
		self.place()
		self.unloadChunks()

class Blocks:
	def __init__(self):
		self.blocks = None
		self.count = None
		self.load()
	
	def load(self):
		with open("blocks.json") as f:
			blocks = json.load(f)
		for block in blocks:
			image = pygame.image.load(blocks[block]["texture"]).convert_alpha()
			image = pygame.transform.scale(image, (TILE, TILE))
			blocks[block]["image"] = image

		self.blocks = blocks
		self.count = len(blocks)-1

	def getTextureImage(self, _id):
		return self.blocks[str(_id)]["image"]

	def isCollider(self, _id):
		return self.blocks[str(_id)]["collision"]

class Player:
	def __init__(self, x, y):
		self.x = x
		self.y = y
		self.xo = x
		self.yo = y
		self.w = 30
		self.h = 70
		self.color = pygame.Color("pink")
		self.velX = 0.3
		self.velY = 0
		self.acceleration = 0.5
		self.gravity = 0.02
		self.jumping = False
		self.facingLeft = False
		self.selected_texture = 0
		self.speed = 20

	def get_hits(self):
		hits = []
		for x,y in game.t.getTilesInScreen():
			cx,cy = x//CHUNK, y//CHUNK
			if not game.tx.isCollider(game.t.loaded_chunks[(cx,cy)][(x,y)]["id"]):
				continue
			xo, yo = x,y
			if self.x <= x+TILE and self.x+self.w >= x:
				if self.y < y+TILE and self.y+self.h > y:
					hits.append([x,y, xo, yo])

		return hits

	def checkCollisionX(self):
		collisions = self.get_hits()
		for x, y, xo, yo in collisions:
			if self.x + self.w >= x and self.xo + self.w < xo:
				self.x = x - self.w - 0.1
			elif self.x <= x + TILE and self.xo > xo + TILE:
				self.x = x + TILE + 0.1

	def checkCollisionY(self):
		collisions = self.get_hits()
		for x, y, xo, yo in collisions:
			if self.y + self.h >= y and self.yo + self.h < yo:
				self.y = y - self.h - 0.1
				self.velY = 0
				self.jumping = False
			elif self.y <= y + TILE and self.yo > yo + TILE:
				self.y = y + TILE + 0.1
				self.velY = 0

	def update(self):
		self.updateX()
		self.checkCollisionX()
		self.updateY()
		self.checkCollisionY()
		game.c.move()
		self.draw()

	def updateX(self):
		self.xo = self.x
		vel = self.velX
		if game.key[pygame.K_LSHIFT]:
			vel += 0.5
		if game.key[pygame.K_a]:
			self.x -= vel * max(game.d, 0.02)
			self.facingLeft = True
		if game.key[pygame.K_d]:
			self.x += vel * max(game.d, 0.02)
			self.facingLeft = False
		if game.key[pygame.K_r]:
			self.x = 0
			self.y = -400
	
	def updateY(self):
		self.yo = self.y
		if game.key[pygame.K_SPACE] and not self.jumping:
			self.jumping = True
			self.velY -= 7

		if self.velY < self.speed:
			self.velY += self.gravity * max(game.d, 0.02)
		
		self.y += self.velY

	def draw(self):
		pygame.draw.rect(game.win, self.color, (*game.c.offset(self.x, self.y),self.w,self.h))

class Worker:
	def __init__(self, func):
		self.func = func
		self.lockin = multiprocessing.Queue()
		self.lockout = multiprocessing.Queue()
		self.proc = multiprocessing.Process(target=self.func, daemon=True,
											args=(self.lockin, self.lockout))
		self.proc.start()

	def write(self, obj):
		self.lockin.put(obj)
	
	def read(self):
		try:
			return self.lockout.get_nowait()
		except:
			return

fps = 120
fpsClock = pygame.time.Clock()
 
width, height = 1270, 720

TILE = 40
CHUNK_TILE = 40
CHUNK = TILE*CHUNK_TILE

TILEX, TILEY = width//TILE, height//TILE

SEED = 69420
random.seed(SEED)


WHITE = (255,255,255)
BLACK = (0,0,0)
RED = pygame.Color("red")
GRAY = pygame.Color("gray")


def commander():
	while True:
		try:
			data = input()
			x, y = data.split(";")
			game.p.x, game.p.y = int(x)*TILE, int(y)*TILE
		except EOFError as e:
			print(end="")

threading.Thread(target=commander, daemon=True).start()

def autoDeleteWorld():
	dir = 'world/'
	for f in os.listdir(dir):
		os.remove(os.path.join(dir, f))

class Game:
	def __init__(self):
		pygame.init()
		self.win = pygame.display.set_mode((width, height))
		self.c = Camera()
		self.t = Terrain()
		self.tx = Blocks()
		self.p = Player(0,-400)

		self.key = None
		self.click = None
		self.xm, self.xy = 0, 0

		self.d = 0

	def main(self):
		small_font = pygame.font.SysFont("Arial", 7)
		font = pygame.font.SysFont("Arial", 25)

		run = True

		while run:
			self.d = fpsClock.tick(fps)
			self.win.fill((171, 244, 255))

			self.key = pygame.key.get_pressed()
			self.click = pygame.mouse.get_pressed()
			self.xm, self.ym = pygame.mouse.get_pos()
		
			for event in pygame.event.get():
				if event.type == QUIT:
					self.t.saveAll()
					run = False
				if event.type == KEYDOWN:
					pass
				if event.type == pygame.MOUSEBUTTONDOWN:
					if event.button == 4:
						self.t.selected_texture += 1
						if self.t.selected_texture > self.tx.count:
							self.t.selected_texture = 0
					elif event.button == 5:
						self.t.selected_texture -= 1
						if self.t.selected_texture < 0:
							self.t.selected_texture = self.tx.count


			#UPDATE AND RENDER
			self.t.update()
			self.p.update()

			fps_txt = font.render(str(int(fpsClock.get_fps())), True, BLACK)
			self.win.blit(fps_txt, (0, 0))
			pos_txt = font.render(f"Block X:{int(self.p.x//TILE)}  Y:{int(self.p.y//TILE)}", True, BLACK)
			self.win.blit(pos_txt, (0, 30))
			posc_txt = font.render(f"Chunk X:{int(self.p.x//CHUNK)}  Y:{int(self.p.y//CHUNK)}", True, BLACK)
			self.win.blit(posc_txt, (0, 60))
			tx_txt = font.render(f"Texture: {self.tx.blocks[str(self.t.selected_texture)]['name']}", True, BLACK)
			self.win.blit(tx_txt, (0, 90))


			pygame.display.flip()

if __name__ == "__main__":
	autoDeleteWorld()
	game = Game()
	game.main()
