from euclid import *
from itertools import *
from math import *

def solve(vertices, target):
    if len(vertices) == 2:
        return _solve_one_edge(vertices, target)
    elif len(vertices) == 3:
        return _solve_two_edges(vertices, target)
    else:
        return vertices

def _solve_one_edge(vertices, target):
    v1, v2 = vertices
    if v1 == target:
        return vertices
    return v1, v1 + abs(v2 - v1) * (target - v1).normalize()

def _solve_two_edges(vertices, target):
    v1, v2, v3 = vertices
    u = target - v1
    d = abs(u)
    u1 = v2 - v1
    u2 = v3 - v2
    d1 = abs(u1)
    d2 = abs(u2)
    if d == 0:
        v3 = v2 - (d2 / d1) * u1
    elif d >= d1 + d2:
        v2 = v1 + (d1 / d) * u
        v3 = v2 + (d2 / d) * u
    elif d <= d1 - d2:
        v2 = v1 + (d1 / d) * u
        v3 = v2 - (d2 / d) * u
    elif d <= d2 - d1:
        v2 = v1 - (d1 / d) * u
        v3 = v2 + (d2 / d) * u
    else:
        # Closed form solution 2 from "Oh My God, I Inverted Kine!" by
        # Jeff Lander.
        #
        # http://www.darwin3d.com/gamedev/articles/col0998.pdf
        a1 = atan2(u.y, u.x)
        a2 = acos((u.x ** 2 + u.y ** 2 + d1 ** 2 -
                   d2 ** 2) / (2 * d1 * d))

        # Maintain winding.
        if u1.x * u2.y - u2.x * u1.y < 0:
            a = a1 + a2
        else:
            a = a1 - a2

        v2 = v1 + d1 * Vector2(cos(a), sin(a))
        v3 = target
    return v1, v2, v3
