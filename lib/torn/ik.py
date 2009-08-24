from euclid import *
from math import *

__all__ = 'solve'

def solve(polygon, end_point):
    if not polygon.closed:
        if len(polygon.vertices) == 2:
            _solve_one_edge(polygon, end_point)
        elif len(polygon.vertices) == 3:
            _solve_two_edges(polygon, end_point)

def _solve_one_edge(polygon, end_point):
    if end_point != polygon.starting_point:
        vector = end_point - polygon.starting_point
        vector.normalize()
        polygon.vertices[1] = (polygon.starting_point +
                               polygon.max_radius * vector)

def _solve_two_edges(polygon, end_point):
    v = end_point - polygon.starting_point
    d = abs(v)
    d1, d2 = polygon.lengths
    if d == 0:
        v = polygon.vertices[1] - polygon.vertices[0]
        v.normalize()
        polygon.vertices[2] = polygon.vertices[1] - d2 * v
    elif d >= polygon.max_radius:
        v.normalize()
        polygon.vertices[1] = polygon.vertices[0] + d1 * v
        polygon.vertices[2] = polygon.vertices[1] + d2 * v
    elif d <= polygon.min_radius:
        v.normalize()
        if d1 < d2:
            v = -v
        polygon.vertices[1] = polygon.vertices[0] + d1 * v
        polygon.vertices[2] = polygon.vertices[1] - d2 * v
    else:
        # Closed form solution 2 from "Oh My God, I Inverted Kine!" by
        # Jeff Lander.
        #
        # http://www.darwin3d.com/gamedev/articles/col0998.pdf
        a3 = atan2(v.y, v.x)
        a4 = acos((v.x ** 2 + v.y ** 2 + d1 ** 2 -
                   d2 ** 2) / (2 * d1 * d))

        # Don't mirror the polygon.
        v1 = polygon.vertices[1] - polygon.vertices[0]
        v2 = polygon.vertices[2] - polygon.vertices[1]
        z = v1.x * v2.y - v2.x * v1.y
        if z < 0:
            a = a3 + a4
        else:
            a = a3 - a4

        polygon.vertices[1] = polygon.vertices[0] + d1 * Vector2(cos(a), sin(a))
        polygon.vertices[2] = end_point.copy()
