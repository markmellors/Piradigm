import sgc
import pygame
from sgc.locals import *
from pygame import draw

class MyButton(sgc.Button):
    def _draw_base(self):
        # Frames around edge of button
        x = min(self.image.get_size()) / 8
        self._frame_lt = ((0,0), (self.rect.w,0), (self.rect.w-x,x),
                          (x,x), (x,self.rect.h-x), (0,self.rect.h))
        self._frame_rb = ((self.rect.w,self.rect.h),
                          (0,self.rect.h), (x,self.rect.h-x),
                          (self.rect.w-x,self.rect.h-x),
                          (self.rect.w-x,x), (self.rect.w,0))
        cols = {}
        cols["image"] = self._settings["col"]
        cols["over"] = [min(c*1.1, 255) for c in self._settings["col"]]
        cols["down"] = [c*0.6 for c in self._settings["col"]]
        for img in cols:
            self._images[img].fill(cols[img])
            # Draw a frame around the edges of the button
            frame_lt_c = [min(c*1.3, 255) for c in cols[img]]
            frame_rb_c = [c*0.6 for c in cols[img]]
            draw.polygon(self._images[img], frame_lt_c, self._frame_lt)
            draw.polygon(self._images[img], frame_rb_c, self._frame_rb)

    def _dotted_rect(self, col=(255,255,255)):
        """Draw a dotted rectangle to show keyboard focus."""
        self.image.lock()
        for i in range(0, self.rect.w, 1):
            # Draw horizontal lines
            self.image.set_at((i, 0), col)
            self.image.set_at((i, self.rect.h-1), col)
        for i in range(0, self.rect.h, 1):
            # Draw vertical lines
            self.image.set_at((0, i), col)
            self.image.set_at((self.rect.w-1, i), col)
        self.image.unlock()

    def _create_event(self, gui_type, **kwargs):
        """
        Returns a GUI `pygame.event.Event` object. The first argument must be
        the value for `gui_type` and should roughly describe the event.
        Optional keyword arguments can also be passed with additional
        attributes for the event.
              
        """
        return pygame.event.Event(
            GUI,
            dict(kwargs, **{"gui_type": gui_type, "widget_type": "Button",
                            "label": self._settings["label"][0],
                            "widget": self}))

class MyScale(sgc.Scale):
    _default_size = (100,40)
