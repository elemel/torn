from __future__ import division

from Box2D import *
from euclid import *
from itertools import *
from math import *
import pyglet
from pyglet.gl import *
import sys

def draw_polygon(vertices, closed=True):
    vertices = list(vertices)
    if closed:
        vertices.append(vertices[0])
    vertices = zip(vertices[:-1], vertices[1:])
    vertices = tuple(chain(*chain(*vertices)))
    pyglet.graphics.draw(len(vertices) // 2, GL_LINES, ('v2f', vertices))

def draw_circle(center, radius, vertex_count=100):
    x, y = center
    vertices = []
    for i in xrange(vertex_count):
        angle = 2 * pi * i / vertex_count
        vertices.append((x + radius * cos(angle), y + radius * sin(angle)))
    draw_polygon(vertices)

class Camera(object):
    def __init__(self, **kwargs):
        self._position = Point2()
        self._scale = 1
        self._angle = 0
        self._world_to_screen = None
        self._screen_to_world = None
        for name, value in kwargs.iteritems():
            setattr(self, name, value)

    def _get_x(self):
        return self._position.x

    def _set_x(self, x):
        self._position.x = x
        self._world_to_screen = None
        self._screen_to_world = None

    x = property(_get_x, _set_x)

    def _get_y(self):
        return self._position.y

    def _set_y(self, y):
        self._position.y = y
        self._world_to_screen = None
        self._screen_to_world = None

    y = property(_get_y, _set_y)

    def _get_position(self):
        return self._position

    def _set_position(self, position):
        assert isinstance(position, Point2)
        self._position = position.copy()
        self._world_to_screen = None
        self._screen_to_world = None

    position = property(_get_position, _set_position)

    def _get_scale(self):
        return self._scale

    def _set_scale(self, scale):
        self._scale = scale
        self._world_to_screen = None
        self._screen_to_world = None

    scale = property(_get_scale, _set_scale)

    def _get_angle(self):
        return self._angle

    def _set_angle(self, angle):
        self._angle = angle
        self._world_to_screen = None
        self._screen_to_world = None

    angle = property(_get_angle, _set_angle)

    def get_screen_point(self, world_point):
        assert isinstance(world_point, Point2)
        screen_point = world_point * self.scale - self.position
        return Point2(*screen_point)

    def get_world_point(self, screen_point):
        assert isinstance(screen_point, Point2)
        world_point = (screen_point - self.position) / self.scale
        return Point2(*world_point)

    def transform_view(self):
        glTranslatef(self._position.x, self._position.y, 0)
        glScalef(self._scale, self._scale, self._scale)
        glRotatef(self._angle, 0, 0, 1)

class CameraController(object):
    def __init__(self, camera, pan_step=20, zoom_step=1.2):
        self.camera = camera
        self.pan_step = pan_step
        self.zoom_step = zoom_step

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.LEFT:
            self.camera.x += self.pan_step
        if symbol == pyglet.window.key.RIGHT:
            self.camera.x -= self.pan_step
        if symbol == pyglet.window.key.UP:
            self.camera.y -= self.pan_step
        if symbol == pyglet.window.key.DOWN:
            self.camera.y += self.pan_step
        if symbol == pyglet.window.key.PLUS:
            self.camera.scale *= self.zoom_step
        if symbol == pyglet.window.key.MINUS:
            self.camera.scale /= self.zoom_step

class Model(object):
    pass

class Polygon(object):
    def __init__(self, vertices, closed=True):
        self.vertices = list(v.copy() for v in vertices)
        assert len(self.vertices) >= 1
        assert all(isinstance(v, Point2) for v in self.vertices)
        assert type(closed) is bool
        self.closed = closed

    def copy(self):
        return Polygon(self.vertices, self.closed)

    @property
    def edges(self):
        edges = [LineSegment2(self.vertices[i], self.vertices[i + 1])
                 for i in xrange(len(self.vertices) - 1)]
        if self.closed and len(self.vertices) >= 3:
            edges.append(LineSegment2(self.vertices[-1], self.vertices[0]))
        return edges

    @property
    def lengths(self):
        return [e.length for e in self.edges]

    @property
    def starting_point(self):
        return self.vertices[0]

    @property
    def end_point(self):
        return self.vertices[0 if self.closed else -1]

    @property
    def max_radius(self):
        return 0 if self.closed else sum(self.lengths)

    @property
    def min_radius(self):
        if self.closed or len(self.vertices) <= 1:
            return 0
        lengths = [e.length for e in self.edges]
        lengths.sort()
        return max(0, lengths[-1] - sum(lengths[:-1]))

    @property
    def area(self):
        """
        http://local.wasp.uwa.edu.au/~pbourke/geometry/clockwise/
        """
        if not self.closed:
            return 0
        return sum(v1.x * v2.y - v2.x * v1.y
                   for v1, v2 in izip(self.vertices,
                                      self.vertices[1:] + self.vertices[:1]))

    @property
    def clockwise(self):
        return self.area < 0

    def reverse(self):
        self.vertices.reverse()

class Level(Model):
    def __init__(self):
        self.polygons = []
        
class Game(object):
    def __init__(self, level):
        self.world = self._create_world()
        for polygon in level.polygons:
            if len(polygon.vertices) >= 3:
                self._create_body(polygon)
        for polygon in level.polygons:
            if len(polygon.vertices) <= 2:
                for vertex in polygon.vertices:
                    self._create_joint(vertex)
        pyglet.clock.schedule_interval(self.step, 1 / 60)

    def _create_world(self):
        aabb = b2AABB()
        aabb.lowerBound = -100, -100
        aabb.upperBound = 100, 100
        return b2World(aabb, (0, -10), True)

    def _create_body(self, polygon):
        body_def = b2BodyDef()
        body = self.world.CreateBody(body_def)
        shape_def = b2PolygonDef()
        if polygon.clockwise:
            polygon = polygon.copy()
            polygon.reverse()
        shape_def.vertices = [tuple(v) for v in polygon.vertices]
        shape_def.density = 1
        body.CreateShape(shape_def)
        body.SetMassFromShapes()
        return body

    def _create_joint(self, point):
        aabb = b2AABB()
        aabb.lowerBound = tuple(point)
        aabb.upperBound = tuple(point)
        _, shapes = self.world.Query(aabb, 1000)
        bodies = [s.GetBody() for s in shapes]
        if len(bodies) == 1:
            joint_def = b2RevoluteJointDef()
            joint_def.Initialize(bodies[0], self.world.GetGroundBody(),
                                 tuple(point))
            self.world.CreateJoint(joint_def)
        elif len(bodies) == 2:
            joint_def = b2RevoluteJointDef()
            joint_def.Initialize(bodies[0], bodies[1], tuple(point))
            self.world.CreateJoint(joint_def)

    def delete(self):
        pyglet.clock.unschedule(self.step)

    def step(self, dt):
        self.world.Step(dt, 10, 10)

    def draw(self):
        for body in self.world.bodyList:
            glPushMatrix()
            glTranslatef(body.position.x, body.position.y, 0)
            angle = body.angle * 180 / pi
            glRotatef(angle, 0, 0, 1)
            for shape in body.shapeList:
                if isinstance(shape, b2PolygonShape):
                    draw_polygon(shape.vertices)
            glPopMatrix()
        for joint in self.world.jointList:
            draw_circle(joint.GetAnchor1().tuple(), 0.05)
            draw_circle(joint.GetAnchor2().tuple(), 0.05)

class Layer(object):
    def draw(self):
        pass

class GameLayer(Layer):
    def __init__(self, window, level):
        self.window = window
        self.level = level
        self.camera = Camera(x=(window.width / 2), y=(window.height / 2),
                             scale=(min(window.width, window.height) / 5))
        self.camera_controller = CameraController(self.camera)
        self.game = None

    def draw(self):
        glPushMatrix()
        self.camera.transform_view()
        if self.game is not None:
            self.game.draw()
        glPopMatrix()

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.ENTER:
            if self.game is None:
                self.game = Game(self.level)
            else:
                self.game.delete()
                self.game = None
            return pyglet.event.EVENT_HANDLED
        else:
            return self.camera_controller.on_key_press(symbol, modifiers)

class EditSkeletonLayer(Layer):
    def __init__(self, window, game_layer):
        self.window = window
        self.game_layer = game_layer
        self.level = self.game_layer.level
        self.camera = self.game_layer.camera
        self.mouse_radius = 10

    def draw(self):
        if self.game_layer.game is not None:
            return
        glPushMatrix()
        self.camera.transform_view()
        for polygon in self.level.polygons:
            draw_polygon(polygon.vertices, polygon.closed)
            for vertex in polygon.vertices:
                draw_circle(vertex, self.mouse_radius / self.camera.scale)
        glPopMatrix()

    def on_mouse_press(self, x, y, button, modifiers):
        mouse_point = self.camera.get_world_point(Point2(x, y))
        mouse_circle = Circle(mouse_point, self.mouse_radius / self.camera.scale)
        handled = self._drag_point(mouse_circle)
        if not handled:
            handled = self._drag_line(mouse_circle)
        if not handled:
            polygon = Polygon([mouse_point, mouse_point])
            self.level.polygons.append(polygon)
            DragPolygonLayer(self.window, self.camera, polygon,
                             polygon.vertices[-1])
        return pyglet.event.EVENT_HANDLED

    def _drag_point(self, mouse_circle):
        for polygon in self.level.polygons:
            for vertex in polygon.vertices:
                if mouse_circle.intersect(vertex):
                    DragPolygonLayer(self.window, self.camera, polygon, vertex)
                    return pyglet.event.EVENT_HANDLED
        return pyglet.event.EVENT_UNHANDLED

    def _drag_line(self, mouse_circle):
        for polygon in self.level.polygons:
            for i, edge in enumerate(polygon.edges):
                connection = mouse_circle.c.connect(edge)
                if connection.length < mouse_circle.r:
                    vertex = connection.p2.copy()
                    polygon.vertices[i + 1:i + 1] = [vertex]
                    DragPolygonLayer(self.window, self.camera, polygon, vertex)
                    return pyglet.event.EVENT_HANDLED
        return pyglet.event.EVENT_UNHANDLED

class DragPolygonLayer(Layer):
    def __init__(self, window, camera, polygon, vertex):
        self.window = window
        self.camera = camera
        self.polygon = polygon
        self.vertex = vertex
        self.window.push_layer(self)

    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        self.vertex[:] = self.camera.get_world_point(Point2(x, y))
        return pyglet.event.EVENT_HANDLED

    def on_mouse_release(self, x, y, button, modifiers):
        self.polygon.vertices = list(k for k, _
                                     in groupby(self.polygon.vertices))
        self.window.pop_layer(self)
        return pyglet.event.EVENT_HANDLED

class TornWindow(pyglet.window.Window):
    def __init__(self, fps=False, **kwargs):
        super(TornWindow, self).__init__(**kwargs)
        self.fps = fps
        self.clock_display = pyglet.clock.ClockDisplay()
        self.layers = []

    def push_layer(self, layer):
        self.layers.append(layer)
        self.push_handlers(layer)

    def pop_layer(self, layer):
        if layer in self.layers:
            while self.layers[-1] is not layer:
                self.layers.pop()
            self.layers.pop()

    def on_draw(self):
        self.clear()
        for layer in self.layers:
            layer.draw()
        if self.fps:
            self.clock_display.draw()
        return pyglet.event.EVENT_HANDLED

def main():
    fps = '--fps' in sys.argv
    fullscreen = '--fullscreen' in sys.argv
    window = TornWindow(fps=fps, fullscreen=fullscreen)
    level = Level()
    level.polygons.append(Polygon([Point2(), Point2(1, 1), Point2(1, 0)]))
    window.push_layer(GameLayer(window, level))
    window.push_layer(EditSkeletonLayer(window, window.layers[-1]))
    pyglet.app.run()

if __name__ == '__main__':
    main()
