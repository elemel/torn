from __future__ import division

from Box2D import *
import copy
from euclid import *
from itertools import *
from math import *
import cPickle as pickle
import pyglet
from pyglet.gl import *
import random
import sys

def create_aabb(lower_bound=(-1, -1), upper_bound=(1, 1)):
    aabb = b2AABB()
    aabb.lowerBound = lower_bound
    aabb.upperBound = upper_bound
    return aabb

def create_world(lower_bound=(-100, -100), upper_bound=(100, 100),
                 gravity=(0, -10), do_sleep=True):
    aabb = create_aabb(lower_bound, upper_bound)
    return b2World(aabb, gravity, do_sleep)

def draw_polygon(points, closed=True):
    if closed:
        points = points + points[:1]
    vertices = zip(points[:-1], points[1:])
    vertices = tuple(chain(*chain(*vertices)))
    pyglet.graphics.draw(len(vertices) // 2, GL_LINES, ('v2f', vertices))

def draw_circle(center=(0, 0), radius=1, vertex_count=100):
    x, y = center
    vertices = []
    for i in xrange(vertex_count):
        angle = 2 * pi * i / vertex_count
        vertices.append((x + radius * cos(angle), y + radius * sin(angle)))
    draw_polygon(vertices)

def get_bounding_box(points):
    x1 = min(x for x, y in points)
    y1 = min(y for x, y in points)
    x2 = max(x for x, y in points)
    y2 = max(y for x, y in points)
    return (x1, y1), (x2, y2)

def get_point_distance(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def get_closest_point_on_segment(p, segment):
    """
    http://local.wasp.uwa.edu.au/~pbourke/geometry/pointline/
    """
    p1, p2 = segment
    if p1 == p2:
        return p1
    x, y = p
    x1, y1 = p1
    x2, y2 = p2
    dx = x2 - x1
    dy = y2 - y1
    u = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
    u = max(u, 0)
    u = min(u, 1)
    return x1 + u * dx, y1 + u * dy

class Camera(object):
    def __init__(self, translation=None, scale=1):
        if translation is None:
            self.translation = Vector2()
        else:
            assert isinstance(translation, Vector2)
            self.translation = translation
        assert scale > 0
        self.scale = scale

    def get_screen_point(self, world_point):
        assert isinstance(world_point, Point2)
        screen_point = world_point * self.scale - self.translation
        return Point2(*screen_point)

    def get_world_point(self, screen_point):
        assert isinstance(screen_point, Point2)
        world_point = (screen_point - self.translation) / self.scale
        return Point2(*world_point)

    def transform_view(self):
        glTranslatef(self.translation.x, self.translation.y, 0)
        glScalef(self.scale, self.scale, self.scale)

def load_object(path):
    file_ = open(path, 'rb')
    return pickle.load(file_)

def save_object(obj, path):
    file_ = open(path, 'wb')
    pickle.dump(obj, file_, pickle.HIGHEST_PROTOCOL)

class Polygon(object):
    def __init__(self, vertices, closed=True):
        self.vertices = list(vertices)
        assert all(isinstance(v, Point2) for v in self.vertices)
        self.closed = closed

    @property
    def edges(self):
        edges = [LineSegment2(self.vertices[i], self.vertices[i + 1])
                 for i in xrange(len(self.vertices) - 1)]
        if self.closed:
            edges.append(LineSegment2(self.vertices[-1], self.vertices[0]))
        return edges

class Skeleton(object):
    def __init__(self):
        self.torso = Polygon([Point2(-0.5, -0.5), Point2(0.5, -0.5),
                              Point2(0.5, 0.5), Point2(-0.5, 0.5)])
        self.limbs = []

    @property
    def polygons(self):
        return [self.torso] + self.limbs

    @property
    def vertices(self):
        vertices = list(self.torso.vertices)
        for limb in self.limbs:
            vertices.extend(limb.vertices)
        return vertices

    @property
    def edges(self):
        edges = list(self.torso.edges)
        for limb in self.limbs:
            edges.extend(limb.edges)
        return edges

class MyWindow(pyglet.window.Window):
    def __init__(self, fps=False, **kwargs):
        super(MyWindow, self).__init__(**kwargs)
        self.fps = fps
        self.fps_display = pyglet.clock.ClockDisplay()
        self.my_screen = SkeletonEditor(self)

    def on_draw(self):
        self.my_screen.on_draw()
        if self.fps:
            self.fps_display.draw()

    def on_close(self):
        self.my_screen.on_close()
        super(MyWindow, self).on_close()

    def on_mouse_press(self, x, y, button, modifiers):
        self.my_screen.on_mouse_press(x, y, button, modifiers)

    def on_mouse_release(self, x, y, button, modifiers):
        self.my_screen.on_mouse_release(x, y, button, modifiers)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.my_screen.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.ESCAPE:
            self.on_close()
        else:
            self.my_screen.on_key_press(symbol, modifiers)

    def on_key_release(self, symbol, modifiers):
        self.my_screen.on_key_release(symbol, modifiers)

class Screen(object):
    def on_close(self):
        pass

    def on_draw(self):
        pass

    def on_mouse_press(self, x, y, button, modifiers):
        pass

    def on_mouse_release(self, x, y, button, modifiers):
        pass

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        pass

    def on_key_press(self, symbol, modifiers):
        pass

    def on_key_release(self, symbol, modifiers):
        pass

class GameScreen(Screen):
    def __init__(self, window):
        self.window = window
        self.time = 0
        self.dt = 1 / 60
        self.level = Level()
        pyglet.clock.schedule_interval(self.step, self.dt)

    def on_close(self):
        pyglet.clock.unschedule(self.step)

    def on_draw(self):
        self.window.clear()

    def step(self, dt):
        self.time += dt
        while self.level.time + self.dt < self.time:
            self.level.step(self.dt)

class SkeletonEditor(Screen):
    def __init__(self, window):
        self.window = window
        translation = Vector2(self.window.width / 2, self.window.height / 2)
        scale = min(self.window.width, self.window.height) / 3.5
        self.camera = Camera(translation, scale)
        try:
            self.skeleton = load_object('torn-skeleton.pickle')
        except:
            self.skeleton = Skeleton()

        self.drag_vertex = None
        self.history = []
        self.screen_epsilon = 10
        self.pan_step = 20
        self.zoom_step = 1.2

    def on_close(self):
        save_object(self.skeleton, 'torn-skeleton.pickle')

    def on_draw(self):
        self.window.clear()
        glPushMatrix()
        self.camera.transform_view()
        self.draw_skeleton()
        glPopMatrix()

    def draw_skeleton(self):
        for polygon in self.skeleton.polygons:
            draw_polygon(polygon.vertices, polygon.closed)
        for vertex in self.skeleton.vertices:
            draw_circle(vertex, self.screen_epsilon / self.camera.scale)

    def on_mouse_press(self, x, y, button, modifiers):
        self.history.append(copy.deepcopy(self.skeleton))
        self.drag_vertex = None
        point = self.camera.get_world_point(Point2(x, y))
        epsilon = self.screen_epsilon / self.camera.scale

        # First option, drag an existing vertex.
        vertices = filter(Circle(point, epsilon).intersect,
                          self.skeleton.vertices)
        if vertices:
            self.drag_vertex = random.choice(vertices)

        # Second option, split an existing edge and drag the new vertex.
        if self.drag_vertex is None:
            self.drag_vertex = self.drag_edge(point, epsilon)

        # Last option, create a new limb.
        if self.drag_vertex is None:
            self.drag_vertex = point.copy()
            limb = Polygon([point.copy(), self.drag_vertex], closed=False)
            self.skeleton.limbs.append(limb)

    def drag_edge(self, point, epsilon):
        assert isinstance(point, Point2)
        for polygon in self.skeleton.polygons:
            for i, edge in enumerate(polygon.edges):
                connection = point.connect(edge)
                if connection.length < epsilon:
                    vertex = connection.p2.copy()
                    polygon.vertices[i + 1:i + 1] = [vertex]
                    return vertex
        return None

    def on_mouse_release(self, x, y, button, modifiers):
        epsilon = 2 * self.screen_epsilon / self.camera.scale
        vertices = filter(Circle(self.drag_vertex, epsilon).intersect,
                          self.skeleton.vertices)
        if len(vertices) >= 2:
            self.delete_skeleton_vertex(self.drag_vertex)

    def delete_skeleton_vertex(self, vertex):
        for polygon in self.skeleton.polygons:
            if vertex in polygon.vertices:
                polygon.vertices.remove(vertex)
                if (len(polygon.vertices) < 2 and
                    polygon in self.skeleton.limbs):
                    self.skeleton.limbs.remove(polygon)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.drag_vertex[:] = self.camera.get_world_point(Point2(x, y))

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.BACKSPACE:
            if self.history:
                self.skeleton = self.history.pop()
        if symbol == pyglet.window.key.LEFT:
            self.camera.translation.x += self.pan_step
        if symbol == pyglet.window.key.RIGHT:
            self.camera.translation.x -= self.pan_step
        if symbol == pyglet.window.key.UP:
            self.camera.translation.y -= self.pan_step
        if symbol == pyglet.window.key.DOWN:
            self.camera.translation.y += self.pan_step
        if symbol == pyglet.window.key.PLUS:
            self.camera.scale *= self.zoom_step
        if symbol == pyglet.window.key.MINUS:
            self.camera.scale /= self.zoom_step

class Level(object):
    def __init__(self):
        self.time = 0
        self.world = create_world()

    def step(self, dt):
        self.time += dt
        self.world.Step(dt, 10, 10)

def main():
    fps = '--fps' in sys.argv
    fullscreen = '--fullscreen' in sys.argv
    window = MyWindow(fps=fps, fullscreen=fullscreen)
    pyglet.app.run()

if __name__ == '__main__':
    main()
