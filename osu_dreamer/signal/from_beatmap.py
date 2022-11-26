
import numpy as np

from osu_dreamer.osu.hit_objects import Circle, Slider, Spinner

from .util import smooth_hit

MAP_SIGNAL_DIM = 6
    
def timing_signal(beatmap, frame_times: "L,") -> ",L":
    pass


def hit_signal(beatmap, frame_times: "L,") -> "4,L":
    """
    returns an array encoding the hits occurring at the times represented by `frames`
    - [0] represents hits
    - [1] represents slider holds
    - [2] represents spinner holds
    - [3] represents new combos

    - `frame_times`: array of times at each frame in ms
    """

    sig = np.zeros((4, len(frame_times)))
    for ho in beatmap.hit_objects:
        if isinstance(ho, Circle):
            sig[0] += smooth_hit(frame_times, ho.t)
        elif isinstance(ho, Slider):
            sig[1] += smooth_hit(frame_times, (ho.t, ho.end_time()))
        else: # Spinner
            sig[2] += smooth_hit(frame_times, (ho.t, ho.end_time()))

        if ho.new_combo:
            sig[3] += smooth_hit(frame_times, ho.t)

    return sig

def cursor_signal(beatmap, frame_times: "L,") -> "2,L":
    """
    return [2,L] where [{0,1},i] is the {x,y} position at the times represented by `frames`

    - `frame_times`: array of times at each frame in ms
    """
    
    def hit_object_pair_gen():
        """generator that yields the latest pair of adjacent hit objects that surround `t`"""
        cur_t = yield
        for a,b in zip([None] + beatmap.hit_objects, beatmap.hit_objects + [None]):
            while b is None or b.t > cur_t:
                cur_t = yield a,b
    hit_object_pair_gen = hit_object_pair_gen()
    next(hit_object_pair_gen)
    
    pos = []
    for t in frame_times:
        a, b = hit_object_pair_gen.send(t)
        if a is None:
            # before first hit object
            pos.append(b.start_pos())
        elif t < a.end_time():
            # hitting current hit object
            if isinstance(a, (Circle, Spinner)):
                pos.append(a.start_pos())
            elif isinstance(a, Slider):
                single_slide = a.slide_duration / a.slides

                ts = (t - a.t) % (single_slide * 2)
                if ts < single_slide:  # start -> end
                    pos.append(a.lerp(ts / single_slide))
                else:  # end -> start
                    pos.append(a.lerp(2 - ts / single_slide))
        elif b is None:
            # after last hit object
            pos.append(a.end_pos())
        else:
            # moving to next hit object
            f = (t - a.end_time()) / (b.t - a.end_time())
            pos.append((1 - f) * a.end_pos() + f * b.start_pos())
            
    return np.array(pos).T
        
            

def from_beatmap(beatmap, frame_times: "L,") -> "6,L":
    """
    returns a [6,L] scaled to [-1,1]

    - `frame_times`: array of times at each frame in ms
    """
    hits: "4,L" = hit_signal(beatmap, frame_times)
    cursor: "2,L" = cursor_signal(beatmap, frame_times) / np.array([[512],[384]])

    return np.concatenate([hits, cursor], axis=0) * 2 - 1
    