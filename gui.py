import pygame
from settings import *

class GUIManager:
	def __init__(self, game):
		self.game = game
		self.widgets = []
		self.small_font = pygame.font.SysFont("Arial", 7)
		self.font = pygame.font.SysFont("Arial", 25)

	def event(self):
		for widget in self.widgets:
			if widget.checkClick():
				return True

	def draw(self):
		for widget in self.widgets:
			widget.draw()

	def addButton(self, x, y, w, h, text, color, command):
		self.widgets.append(Button(self, x, y, w, h, text, color, command))

class Widget:
	def __init__(self, manager, x, y, w, h):
		self.manager = manager
		self.x, self.y = x,y
		self.w, self.h = w,h

	def click(self):
		xm, ym = self.manager.game.xm, self.manager.game.ym
		if xm > self.x and xm < self.x+self.w and ym > self.y and ym < self.y+self.h:
			pygame.mouse.set_cursor(*pygame.cursors.diamond)
			if self.manager.game.L_click:
				return "click"
			else:
				return "hover"
		else:
			pygame.mouse.set_cursor(*pygame.cursors.arrow)

#ELEMENTS
class Button(Widget):
	def __init__(self, manager, x, y, w, h, text, color, command):
		Widget.__init__(self, manager, x, y, w, h)
		self.text = text
		self.color = color
		self.command = command

	def checkClick(self):
		if self.click() == "click":
			self.command()
			return True
		else:
			return False

	def changeText(self, new_text):
		self.text = new_text

	def changeColor(self, new_color):
		self.color = new_color

	def draw(self):
		text_txt = self.manager.font.render(self.text, True, self.color)
		text_x, text_y = text_txt.get_width(), text_txt.get_height()
		pygame.draw.rect(self.manager.game.win, (255,255,255), (self.x,self.y,self.w,self.h))
		pygame.draw.rect(self.manager.game.win, (0,0,0), (self.x,self.y,self.w,self.h), 1)
		self.manager.game.win.blit(text_txt, (self.x+self.w/2-text_x/2, self.y+self.h/2-text_y/2))