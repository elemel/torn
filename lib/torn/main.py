from __future__ import division

from Box2D import *
import copy
from euclid import *
from itertools import *
from math import *
import cPickle as pickle
import pyglet
from pyglet.gl import *
import rabbyt
import random
import sys
from torn.geometry import *
from torn import ik

def rad_to_deg(angle_rad):
    return angle_rad * 180 / pi

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

def save_screenshot(name='screenshot.png', format='RGB'):
    image = pyglet.image.get_buffer_manager().get_color_buffer().image_data
    image.format = format
    image.save(name)

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
        rabbyt.set_default_attribs()
        glClearColor(1, 1, 1, 0)
        glColor3f(0, 0, 0)
        self.fps = fps
        self.fps_display = pyglet.clock.ClockDisplay()
        if '--animation-editor' in sys.argv:
            self.my_screen = AnimationEditor(self)
        elif '--skeleton-editor' in sys.argv:
            self.my_screen = SkeletonEditor(self)
        elif '--skin-editor' in sys.argv:
            self.my_screen = SkinEditor(self)
        else:
            self.my_screen = GameScreen(self)

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
        elif symbol == pyglet.window.key.F12:
            save_screenshot('torn-screenshot.png')
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

class Scrap(object):
    def __init__(self, name, position=None, scale=1, angle=0):
        if position is None:
            position = Point2()
        assert isinstance(position, Point2)
        assert type(scale) in (int, float)
        assert type(angle) in (int, float)
        self.name = name
        self.position = position
        self.scale = scale
        self.angle = angle

class Skin(object):
    def __init__(self):
        self.scraps = []

class View(object):
    pass

class ScrapView(View):
    def __init__(self, scrap):
        self.scrap = scrap
        self.sprite = rabbyt.Sprite(self.scrap.name, scale=self.scrap.scale,
                                    rot=rad_to_deg(self.scrap.angle))
        self.sprite.xy = self.scrap.position
        texture = self.sprite.texture
        self.texture_radius = (texture.width + texture.height) / 4
        self.radius = self.scrap.scale * self.texture_radius
        self.direction = Vector2(cos(self.scrap.angle), sin(self.scrap.angle))

    def _get_position(self):
        return self.scrap.position

    def _set_position(self, position):
        assert isinstance(position, Point2)
        self.scrap.position[:] = position
        self.sprite.xy = position

    position = property(_get_position, _set_position)

    def _get_transform(self):
        return self.scrap.position + self.radius * self.direction

    def _set_transform(self, transform):
        assert isinstance(transform, Point2)
        vector = transform - self.scrap.position
        self.radius = abs(vector)
        self.direction = vector.normalized()
        self.scrap.scale = self.radius / self.texture_radius
        self.scrap.angle = atan2(self.direction.y, self.direction.x)
        self.sprite.scale = self.scrap.scale
        self.sprite.rot = rad_to_deg(self.scrap.angle)

    transform = property(_get_transform, _set_transform)
    
    def draw(self, mouse_radius):
        self.sprite.render()
        glDisable(GL_TEXTURE_2D)
        glColor3f(0, 0, 0)
        glLineWidth(3)
        draw_circle(self.scrap.position, mouse_radius)
        draw_circle(self.scrap.position, self.radius)
        draw_circle(self.scrap.position + self.radius * self.direction,
                    mouse_radius)
        glColor3f(1, 1, 1)
        glLineWidth(1)
        draw_circle(self.scrap.position, mouse_radius)
        draw_circle(self.scrap.position, self.radius)
        draw_circle(self.scrap.position + self.radius * self.direction,
                    mouse_radius)

class SkinView(View):
    def __init__(self, skin):
        self.skin = skin
        self.scrap_views = [ScrapView(s) for s in self.skin.scraps]

    def draw(self, mouse_radius):
        for scrap_view in self.scrap_views:
            scrap_view.draw(mouse_radius)

class SkinEditor(Screen):
    def __init__(self, window):
        self.window = window
        translation = Vector2(self.window.width / 2, self.window.height / 2)
        scale = min(self.window.width, self.window.height) / 3.5
        self.camera = Camera(translation, scale)
        self.mouse_radius = 10
        try:
            self.skin = load_object('torn-skin.pickle')
        except:
            self.skin = Skin()
            self.skin.scraps.append(Scrap(name='torso.png', scale=0.005))
            self.skin.scraps.append(Scrap(name='head.png', scale=0.005))
        self.skin_view = SkinView(self.skin)

    def on_draw(self):
        self.window.clear()
        glPushMatrix()
        self.camera.transform_view()
        self.skin_view.draw(self.mouse_radius / self.camera.scale)
        glPopMatrix()

    def on_close(self):
        save_object(self.skin, 'torn-skin.pickle')

    def on_mouse_press(self, x, y, button, modifiers):
        mouse_point = self.camera.get_world_point(Vector2(x, y))
        mouse_radius = self.mouse_radius / self.camera.scale
        mouse_circle = Circle(mouse_point, mouse_radius)
        for scrap_view in self.skin_view.scrap_views:
            if mouse_circle.intersect(scrap_view.position):
                ScrapPositionController(self, scrap_view)
                break
            if mouse_circle.intersect(scrap_view.transform):
                ScrapTransformController(self, scrap_view)
                break

class Controller(object):
    pass

class ScrapPositionController(object):
    def __init__(self, editor, scrap_view):
        self.editor = editor
        self.scrap_view = scrap_view
        self.editor.window.push_handlers(self)

    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        position = self.editor.camera.get_world_point(Vector2(x, y))
        self.scrap_view.position = position
        return pyglet.event.EVENT_HANDLED

    def on_mouse_release(self, x, y, button, modifiers):
        self.editor.window.pop_handlers()
        return pyglet.event.EVENT_HANDLED

class ScrapTransformController(object):
    def __init__(self, editor, scrap_view):
        self.editor = editor
        self.scrap_view = scrap_view
        self.editor.window.push_handlers(self)

    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        transform = self.editor.camera.get_world_point(Vector2(x, y))
        self.scrap_view.transform = transform
        return pyglet.event.EVENT_HANDLED

    def on_mouse_release(self, x, y, button, modifiers):
        self.editor.window.pop_handlers()
        return pyglet.event.EVENT_HANDLED

class Pose(object):
    def __init__(self, skeleton):
        assert isinstance(skeleton, Skeleton)
        self.targets = [l.vertices[-1].copy() for l in skeleton.limbs]

class Animation(object):
    def __init__(self, skeleton, looped=True):
        assert isinstance(skeleton, Skeleton)
        assert type(looped) is bool
        self.poses = [Pose(skeleton)]
        self.looped = looped

class AnimationEditor(Screen):
    def __init__(self, window):
        self.window = window
        translation = Vector2(self.window.width / 2, self.window.height / 2)
        scale = min(self.window.width, self.window.height) / 3.5
        self.camera = Camera(translation, scale)
        self.screen_epsilon = 10
        self.skeleton = load_object('torn-skeleton.pickle')
        try:
            self.animation = load_object('torn-animation.pickle')
        except:
            self.animation = Animation(self.skeleton)
        self.pose_index = 0
        self.history = []
        self.drag_limbs = self.get_drag_limbs()
        self.limb_index = None
        self.pan_step = 20
        self.zoom_step = 1.2

    def get_drag_limbs(self):
        limbs = []
        pose = self.animation.poses[self.pose_index]
        for i, limb in enumerate(self.skeleton.limbs):
            vertices = ik.solve(limb.vertices, pose.targets[i])
            limbs.append(Polygon(vertices, closed=False))
        return limbs

    def on_close(self):
        save_object(self.animation, 'torn-animation.pickle')

    def on_draw(self):
        self.window.clear()
        glPushMatrix()
        self.camera.transform_view()
        self.draw_pose()
        glPopMatrix()
        self.draw_timeline()

    def draw_pose(self):
        glColor3f(0, 0, 0)
        draw_polygon(self.skeleton.torso.vertices, True)
        for i, limb in enumerate(self.drag_limbs):
            glColor3f(0, 0, 0)
            draw_polygon(limb.vertices, limb.closed)
            draw_circle(limb.vertices[-1],
                        self.screen_epsilon / self.camera.scale)

    def draw_timeline(self):
        point_count = len(self.animation.poses)
        if point_count >= 2 and self.animation.looped:
            point_count += 1
        width = self.window.width / point_count
        y = 2 * self.screen_epsilon
        glColor3f(0.5, 0.5, 0.5)
        draw_polygon([(width / 2, y), (self.window.width - width / 2, y)],
                     closed=False)
        for i in xrange(point_count):
            current = (i % len(self.animation.poses)) == self.pose_index
            color = 0 if current else 0.5
            glColor3f(color, color, color)
            x = width / 2 + i * width
            draw_circle((x, y), self.screen_epsilon)

    def on_mouse_press(self, x, y, button, modifiers):
        self.history.append((self.pose_index, copy.deepcopy(self.animation)))
        self.drag_vertex = None
        mouse_point = self.camera.get_world_point(Point2(x, y))
        epsilon = self.screen_epsilon / self.camera.scale
        mouse_circle = Circle(mouse_point, epsilon)
        for i, limb in enumerate(self.drag_limbs):
            if mouse_circle.intersect(limb.vertices[-1]):
                self.limb_index = i
                break

    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        if self.limb_index is None:
            return
        mouse_point = self.camera.get_world_point(Point2(x, y))
        limb = self.skeleton.limbs[self.limb_index]
        vertices = ik.solve(limb.vertices, mouse_point)
        self.drag_limbs[self.limb_index] = Polygon(vertices, closed=False)
        pose = self.animation.poses[self.pose_index]
        pose.targets[self.limb_index] = vertices[-1].copy()

    def on_mouse_release(self, x, y, button, modifiers):
        self.limb_index = None

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.BACKSPACE:
            if self.history:
                self.pose_index, self.animation = self.history.pop()
                self.drag_limbs = self.get_drag_limbs()
        if symbol == pyglet.window.key.INSERT:
            pose = copy.deepcopy(self.animation.poses[self.pose_index])
            self.animation.poses[self.pose_index:self.pose_index] = [pose]
        if symbol == pyglet.window.key.DELETE:
            if len(self.animation.poses) >= 2:
                del self.animation.poses[self.pose_index]
                self.pose_index = min(self.pose_index,
                                      len(self.animation.poses) - 1)
        if symbol == pyglet.window.key.PAGEUP:
            self.pose_index -= 1
            self.pose_index %= len(self.animation.poses)
            self.drag_limbs = self.get_drag_limbs()
        if symbol == pyglet.window.key.PAGEDOWN:
            self.pose_index += 1
            self.pose_index %= len(self.animation.poses)
            self.drag_limbs = self.get_drag_limbs()
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
    if '-h' in sys.argv or '--help' in sys.argv:
        print """
Options:
  --animation-editor    Start the animation editor.
  --fullscreen          Enable fullscreen mode.
  -h, --help            You're looking at it.
  --skeleton-editor     Start the skeleton editor.
  --skin-editor         Start the skin editor.
""".strip()
        return

    fps = '--fps' in sys.argv
    fullscreen = '--fullscreen' in sys.argv
    window = MyWindow(fps=fps, fullscreen=fullscreen)
    pyglet.app.run()

if __name__ == '__main__':
    main()
