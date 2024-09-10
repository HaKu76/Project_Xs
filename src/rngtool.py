"""Module for recording blinks from a video capture"""
from typing import List
from typing import Tuple
import time
import sys
import cv2
from xorshift import Xorshift
import calc

IDLE = 0xFF
SINGLE = 0xF0
DOUBLE = 0xF1

def randrange(rand,minimum,maximum):
    """Convert a random number into a range between two floats"""
    rand = (rand & 0x7fffff) / 8388607.0
    return rand * minimum + (1.0 - rand) * maximum

# pylint: disable=too-many-arguments,too-many-branches,too-many-locals,too-many-statements
# until made to accept a config directly, this many arguments is reasonable
# due to this function being responsible for controlling a video capture and detecting blinks,
# this many branches/local variables/statements are acceptable
def tracking_blink(img,
                   roi_x,
                   roi_y,
                   roi_w,
                   roi_h,
                   threshold = 0.9,
                   size = 40,
                   monitor_window = False,
                   window_prefix = "SysDVR-Client [PID ",
                   crop = None,
                   camera = 0,
                   tk_window = None)->Tuple[List[int],List[int],float]:
    """measuring the type and interval of player's blinks

    Returns:
        blinks:List[int], intervals:list[int], offset_time:float
    """

    eye = img
    last_frame_tk = None

    if monitor_window:
        # pylint: disable=import-outside-toplevel
        # we import here because otherwise it would throw an error on non windows platforms
        from windowcapture import WindowCapture
        video = WindowCapture(window_prefix,crop)
    else:
        if sys.platform.startswith('linux'): # all Linux
            backend = cv2.CAP_V4L
        else: # MS Windows/macOS/otherwise
            backend = cv2.CAP_ANY # auto-detect via OpenCV
        video = cv2.VideoCapture(camera,backend)
        video.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
        video.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
        video.set(cv2.CAP_PROP_BUFFERSIZE,1)

    state = IDLE
    blinks = []
    intervals = []
    prev_time = time.perf_counter()
    eye_width, eye_height = eye.shape[::-1]

    prev_roi = None
    offset_time = 0

    # observe blinks
    while len(blinks)<size or state!=IDLE:
        if tk_window is not None:
            if not tk_window.monitoring and not tk_window.reidentifying:
                tk_window.progress['text'] = "0/0"
                tk_window.monitor_tk_buffer = None
                tk_window.monitor_tk = None
                sys.exit()
        _, frame = video.read()
        time_counter = time.perf_counter()
        roi = cv2.cvtColor(frame[roi_y:roi_y+roi_h,roi_x:roi_x+roi_w],cv2.COLOR_RGB2GRAY)
        if (roi==prev_roi).all():
            continue

        prev_roi = roi
        res = cv2.matchTemplate(roi,eye,cv2.TM_CCOEFF_NORMED)
        _, match, _, max_loc = cv2.minMaxLoc(res)

        cv2.rectangle(frame,(roi_x,roi_y), (roi_x+roi_w,roi_y+roi_h), (0,0,255), 2)
        if 0.01<match<threshold:
            cv2.rectangle(frame,(roi_x,roi_y), (roi_x+roi_w,roi_y+roi_h), 255, 2)
            if state==IDLE:
                blinks.append(0)
                interval = (time_counter - prev_time)/1.017
                interval_round = round(interval)
                intervals.append(interval_round)
                print(f"Adv Since Last: {round((time_counter - prev_time)/1.018)} " \
                      f"{(time_counter - prev_time)/1.018}")
                print("记录下了单眨眼")
                print(f"时间间隔 {len(intervals)}/{size}")
                if tk_window is not None:
                    tk_window.progress['text'] = f"{len(intervals)}/{size}"

                if len(intervals)==size:
                    offset_time = time_counter

                state = SINGLE
                prev_time = time_counter
            elif state==SINGLE:
                #doubleの判定
                if time_counter - prev_time>0.3:
                    blinks[-1] = 1
                    state = DOUBLE
                    print("记录下了双眨眼")
            elif state==DOUBLE:
                pass
        else:
            max_loc = (max_loc[0] + roi_x,max_loc[1] + roi_y)
            bottom_right = (max_loc[0] + eye_width, max_loc[1] + eye_height)
            cv2.rectangle(frame,max_loc, bottom_right, 255, 2)
        if tk_window is None:
            cv2.imshow("view", frame)
            keypress = cv2.waitKey(1)
            if keypress == ord('q'):
                cv2.destroyAllWindows()
                sys.exit()
        else:
            if tk_window.config_json["display_percent"] != 100:
                _, frame_width, frame_height = frame.shape[::-1]
                frame = cv2.resize(
                    frame,
                    (round(frame_width*tk_window.config_json["display_percent"]/100),
                    round(frame_height*tk_window.config_json["display_percent"]/100)
                    ))
            frame_tk = tk_window.cv_image_to_tk(frame)
            tk_window.monitor_tk_buffer = last_frame_tk
            tk_window.monitor_display_buffer['image'] = tk_window.monitor_tk_buffer
            tk_window.monitor_tk = frame_tk
            tk_window.monitor_display['image'] = tk_window.monitor_tk
            last_frame_tk = frame_tk
        if state!=IDLE and time_counter - prev_time>0.7:
            state = IDLE
    if tk_window is None:
        cv2.destroyAllWindows()
    else:
        tk_window.progress['text'] = "0/0"
        frame_tk = None
        last_frame_tk = None
    video.release()
    return (blinks, intervals, offset_time)

def tracking_blink_manual(size = 40, reidentify = False)->Tuple[List[int],List[int],float]:
    """measuring the type and interval of player's blinks manually

    Returns:
        blinks:List[int],intervals:list[int],offset_time:float: [description]
    """
    blinks = []
    intervals = []
    prev_time = 0
    offset_time = 0
    while len(blinks)<size:
        if not reidentify:
            input()
            time_counter = time.perf_counter()
            print(f"Adv Since Last: {round((time_counter - prev_time)/1.018)} " \
                  f"{(time_counter - prev_time)}")

            if prev_time != 0 and time_counter - prev_time<0.7:
                blinks[-1] = 1
                print("记录下了双眨眼")
            else:
                blinks.append(0)
                interval = (time_counter - prev_time)/1.018
                interval_round = round(interval)
                intervals.append(interval_round)
                print("记录下了单眨眼")
                print(f"时间间隔 {len(intervals)}/{size}")

                if len(intervals)==size:
                    offset_time = time_counter
                prev_time = time_counter
        else:
            blinks.append(int(input("Blink Type (0 = single, 1 = double): ")))
            print(f"眨眼类型 {len(blinks)}/{size}")
            time_counter = time.perf_counter()
            if len(intervals)==size:
                offset_time = time_counter

    return (blinks, intervals, offset_time)

def tracking_poke_blink(img,
                        roi_x,
                        roi_y,
                        roi_w,
                        roi_h,
                        size = 64,
                        threshold = 0.85,
                        monitor_window = False,
                        window_prefix = "SysDVR-Client [PID ",
                        crop = None,
                        tk_window = None,
                        camera = 0)->Tuple[List[int],List[int],float]:
    """measuring the type and interval of pokemon's blinks

    Returns:
        intervals:list[int],offset_time:float: [description]
    """

    eye = img
    last_frame_tk = None

    if monitor_window:
        # pylint: disable=import-outside-toplevel
        # we import here because otherwise it would throw an error on non windows platforms
        from windowcapture import WindowCapture
        video = WindowCapture(window_prefix, crop)
    else:
        if sys.platform.startswith('linux'): # all Linux
            backend = cv2.CAP_V4L
        else: # MS Windows/macOS/otherwise
            backend = cv2.CAP_ANY # auto-detect via OpenCV
        video = cv2.VideoCapture(camera,backend)
        video.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
        video.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
        video.set(cv2.CAP_PROP_BUFFERSIZE,1)

    state = IDLE
    intervals = []
    prev_roi = None
    prev_time = time.perf_counter()
    eye_width, eye_height = eye.shape[::-1]

    # observe blinks
    while len(intervals)<size:
        if tk_window is not None:
            if not tk_window.tidsiding:
                tk_window.progress['text'] = "0/0"
                tk_window.monitor_tk_buffer = None
                tk_window.monitor_tk = None
                sys.exit()
        _, frame = video.read()
        time_counter = time.perf_counter()

        roi = cv2.cvtColor(frame[roi_y:roi_y+roi_h,roi_x:roi_x+roi_w],cv2.COLOR_RGB2GRAY)
        if (roi==prev_roi).all():
            continue
        prev_roi = roi

        res = cv2.matchTemplate(roi,eye,cv2.TM_CCOEFF_NORMED)
        _, match, _, max_loc = cv2.minMaxLoc(res)

        cv2.rectangle(frame,(roi_x,roi_y), (roi_x+roi_w,roi_y+roi_h), (0,0,255), 2)
        if 0.4<match<threshold:
            cv2.rectangle(frame,(roi_x,roi_y), (roi_x+roi_w,roi_y+roi_h), 255, 2)
            if state==IDLE:
                interval = (time_counter - prev_time)
                intervals.append(interval)
                print(f"时间间隔 {len(intervals)}/{size}")
                if tk_window is not None:
                    tk_window.progress['text'] = f"{len(intervals)}/{size}"
                state = SINGLE
                prev_time = time_counter
            elif state==SINGLE:
                pass
        else:
            max_loc = (max_loc[0] + roi_x,max_loc[1] + roi_y)
            bottom_right = (max_loc[0] + eye_width, max_loc[1] + eye_height)
            cv2.rectangle(frame,max_loc, bottom_right, 255, 2)
        if state!=IDLE and time_counter - prev_time>0.7:
            state = IDLE

        if tk_window is None:
            cv2.imshow("view", frame)
            keypress = cv2.waitKey(1)
            if keypress == ord('q'):
                cv2.destroyAllWindows()
                sys.exit()
        else:
            if tk_window.config_json["display_percent"] != 100:
                _, frame_width, frame_height = frame.shape[::-1]
                frame = cv2.resize(
                    frame,
                    (round(frame_width*tk_window.config_json["display_percent"]/100),
                    round(frame_height*tk_window.config_json["display_percent"]/100)
                    ))
            frame_tk = tk_window.cv_image_to_tk(frame)
            tk_window.monitor_tk_buffer = last_frame_tk
            tk_window.monitor_display_buffer['image'] = tk_window.monitor_tk_buffer
            tk_window.monitor_tk = frame_tk
            tk_window.monitor_display['image'] = tk_window.monitor_tk
            last_frame_tk = frame_tk
    if tk_window is None:
        cv2.destroyAllWindows()
    else:
        tk_window.progress['text'] = "0/0"
        frame_tk = None
        last_frame_tk = None
    video.release()
    return intervals

def simultaneous_tracking(plimg,
                          plroi:Tuple[int,int,int,int],
                          pkimg,
                          pkroi:Tuple[int,int,int,int],
                          plth=0.88,
                          pkth=0.999185,
                          size=8)->Tuple[List[int],List[int],float]:
    """measuring type/intervals of player's blinks  and the interval of pokemon's blinks
        note: this methods is very unstable. it not recommended to use.
    Returns:
        intervals:list[int],offset_time:float: [description]
    """
    video = cv2.VideoCapture(0,cv2.CAP_DSHOW)
    video.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
    video.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
    video.set(cv2.CAP_PROP_BUFFERSIZE,1)

    pl_state = IDLE
    pk_state = IDLE
    blinks = []
    intervals = []
    pl_prev = time.perf_counter()
    pk_prev = time.perf_counter()

    prev_roi = None

    offset_time = 0

    blinkcounter = 0

    # observe blinks
    while len(blinks)<size or pl_state!=IDLE:
        _, frame = video.read()
        time_counter = time.perf_counter()

        #player eye
        roi_x,roi_y,roi_w,roi_h = plroi
        roi = cv2.cvtColor(frame[roi_y:roi_y+roi_h,roi_x:roi_x+roi_w],cv2.COLOR_RGB2GRAY)
        if (roi==prev_roi).all():
            continue

        prev_roi = roi
        res = cv2.matchTemplate(roi,plimg,cv2.TM_CCOEFF_NORMED)
        _, match, _, _ = cv2.minMaxLoc(res)

        #cv2.imshow("pl",roi)

        if 0.01<match<plth:
            if pl_state==IDLE:
                blinks.append(0)
                interval = (time_counter - pl_prev)/1.017
                interval_round = round(interval)
                interval_corrected = interval_round + blinkcounter
                blinkcounter = 0#reset blinkcounter
                intervals.append(interval_corrected)

                if len(intervals)==size:
                    offset_time = time_counter

                #check interval
                pl_state = SINGLE
                pl_prev = time_counter
            elif pl_state==SINGLE:
                #double
                if time_counter - pl_prev>0.3:
                    blinks[-1] = 1
                    pl_state = DOUBLE
            elif pl_state==DOUBLE:
                pass

        if pl_state!=IDLE and time_counter - pl_prev>0.7:
            pl_state = IDLE

        if pk_state==IDLE:
            #poke eye
            roi_x,roi_y,roi_w,roi_h = pkroi
            roi = cv2.cvtColor(frame[roi_y:roi_y+roi_h,roi_x:roi_x+roi_w],cv2.COLOR_RGB2GRAY)

            res = cv2.matchTemplate(roi,pkimg,cv2.TM_CCORR_NORMED)#CCORR might be better?
            _, match, _, _ = cv2.minMaxLoc(res)
            cv2.imshow("pk",roi)
            cv2.waitKey(1)
            if 0.4<match<pkth:
                #print("poke blinked!")
                blinkcounter += 1
                pk_prev = time_counter
                pk_state = SINGLE

        if pk_state!=IDLE and time_counter - pk_prev>0.7:
            pk_state = IDLE

    cv2.destroyAllWindows()
    print(intervals)
    return (blinks, intervals, offset_time)

def recov(blinks:List[int],rawintervals:List[int],npc:int=0)->Xorshift:
    """
    Recover the xorshift from the type and interval of blinks.

    Args:
        blinks (List[int]):
        intervals (List[int]):
        npc (int):

    Returns:
        List[int]: internalstate
    """
    intervals = rawintervals[1:]
    if npc != 0:
        intervals = [x*(npc+1) for x in intervals]
    advanced_frame = sum(intervals)
    states = calc.reverse_states(blinks, intervals)
    # pylint: disable=no-value-for-parameter
    prng = Xorshift(*states)
    states = prng.get_state()

    #validation check
    if npc == 0:
        expected_blinks = \
            [r&0xF for r in \
                prng.get_next_rand_sequence(advanced_frame) if r&0b1110==0]
        paired = list(zip(blinks,expected_blinks))
        print(blinks)
        print(expected_blinks)
        assert all(o==e for o,e in paired)
    else:
        raise_error = True
        for distance in range(npc+1):
            expected_blinks = \
                [r&0xF for r in
                    prng.get_next_rand_sequence(advanced_frame*npc)[distance::npc+1] if r&0b1110==0]
            paired = list(zip(blinks,expected_blinks))
            if all(o==e for o,e in paired):
                advanced_frame += distance
                raise_error = False
                break
        print(blinks)
        print(expected_blinks)
        if raise_error:
            assert all(o==e for o,e in paired)
    result = Xorshift(*states)
    result.get_next_rand_sequence(advanced_frame)
    return result

def reidentiy_by_blinks(rng:Xorshift,
                       observed_blinks:List[int],
                       npc = 0,
                       search_max=10**6,
                       search_min=0,
                       return_advance=False)->Xorshift:
    """reidentify Xorshift state by type of observed blinks.

    Args:
        rng (Xorshift): identified rng
        observed_blinks (List[int]):
        npc (int, optional): num of npcs. Defaults to 0.
        search_max (int, optional): . Defaults to 10**6.
        search_min (int, optional): . Defaults to 0.

    Returns:
        Xorshift: reidentified rng
    """

    if search_max<search_min:
        search_min, search_max = search_max, search_min
    search_range = search_max - search_min
    observed_len = len(observed_blinks)
    if 2**observed_len < search_range:
        return None

    for distance in range(1+npc):
        identify_rng = Xorshift(*rng.get_state())
        rands = \
            [(i, r&0xF) for i,r in
                list(enumerate(identify_rng.get_next_rand_sequence(search_max)))[distance::1+npc]]
        blinkrands = [(i, r) for i,r in rands if r&0b1110==0]

        #prepare
        expected_blinks_lst = []
        expected_blinks = 0
        lastblink_idx = -1
        mask = (1<<observed_len)-1
        for idx, rand in blinkrands[:observed_len]:
            lastblink_idx = idx

            expected_blinks <<= 1
            expected_blinks |= rand

        expected_blinks_lst.append((lastblink_idx, expected_blinks))

        for idx, rand in blinkrands[observed_len:]:
            lastblink_idx = idx

            expected_blinks <<= 1
            expected_blinks |= rand
            expected_blinks &= mask

            expected_blinks_lst.append((lastblink_idx, expected_blinks))

        #search
        search_blinks = calc.list2bitvec(observed_blinks)
        result = Xorshift(*rng.get_state())
        for idx, blinks in expected_blinks_lst:
            if search_blinks==blinks and search_min <= idx:
                print(f"found  at advances:{idx}, distance={distance}")
                result.get_next_rand_sequence(idx)
                if return_advance:
                    return result, idx
                return result

    return None

def reidentiy_by_intervals(rng:Xorshift,
                          rawintervals:List[int],
                          npc = 0,
                          search_max=10**6,
                          search_min=0,
                          return_advance=False)->Xorshift:
    """reidentify Xorshift state by intervals of observed blinks.
    This method is faster than "reidentiy_by_blinks" in most cases
    since it can be reidentified by less blinking.
    Args:
        rng (Xorshift): [description]
        rawintervals (List[int]): list of intervals of blinks. 7 or more are recommended.
        npc (int, optional): [description]. Defaults to 0.
        search_max ([type], optional): [description]. Defaults to 10**6.
        search_min (int, optional): [description]. Defaults to 0.
    Returns:
        Xorshift: [description]
    """
    intervals = rawintervals[1:]
    if search_max<search_min:
        search_min, search_max = search_max, search_min
    observed_len = sum(intervals)+1

    for distance in range(1+npc):
        identify_rng = Xorshift(*rng.get_state())
        blinkrands = \
            [(i, int((r&0b1110)==0)) for i,r in
                list(enumerate(identify_rng.get_next_rand_sequence(search_max)))[distance::1+npc]]

        #prepare
        expected_blinks_lst = []
        expected_blinks = 0
        lastblink_idx = -1
        mask = (1<<observed_len)-1
        for idx, rand in blinkrands[:observed_len]:
            lastblink_idx = idx

            expected_blinks <<= 1
            expected_blinks |= rand

        expected_blinks_lst.append((lastblink_idx, expected_blinks))

        for idx, rand in blinkrands[observed_len:]:
            lastblink_idx = idx

            expected_blinks <<= 1
            expected_blinks |= rand
            expected_blinks &= mask

            expected_blinks_lst.append((lastblink_idx, expected_blinks))

        #search preparation
        search_blinks = 1
        for i in intervals:
            search_blinks <<= i
            search_blinks |= 1

        #search
        result = Xorshift(*rng.get_state())
        for idx, blinks in expected_blinks_lst:
            if search_blinks==blinks and search_min <= idx:
                print(f"found  at advances:{idx}, distance={distance}")
                result.get_next_rand_sequence(idx)
                if return_advance:
                    return result, idx
                return result

    return None

def reidentiy_by_intervals_noisy(rng:Xorshift,
                               rawintervals:List[int],
                               search_max=10**5,
                               search_min=0)->Xorshift:
    """Reidentify Xorshift state via intervals with noise in the background"""
    intervals = rawintervals[1:]
    blink_bools = [True]
    for interval in intervals:
        blink_bools.extend([False]*(interval-1))
        blink_bools.append(True)
    reident_time = len(blink_bools)
    possible_length = int(reident_time*4//3)

    possible_advances = []
    temp_rng = Xorshift(*rng.get_state())
    temp_rng.get_next_rand_sequence(search_min)
    blink_rands = [int((r&0b1110)==0) for r in temp_rng.get_next_rand_sequence(search_max)]
    for advance in range(search_max-possible_length):
        blinks = blink_rands[advance:advance+possible_length]
        i = 0
        j = 0
        differences = []
        try:
            while i < reident_time:
                diff = 0
                while blink_bools[i] != blinks[j]:
                    diff += 1
                    j += 1
                if diff != 0:
                    differences.append(diff)
                j += 1
                i += 1
        except IndexError:
            continue
        pokemon_blink_count = sum(differences)
        possible_advances.append((pokemon_blink_count,advance))
    correct = min(possible_advances)
    rng.advance(search_min+sum(correct)+reident_time)
    return rng, search_min+sum(correct)+reident_time

def recov_by_munchlax(rawintervals:List[float])->Xorshift:
    """Recover the xorshift from the interval of Munchlax blinks.

    Args:
        rawintervals (List[float]): [description]

    Returns:
        Xorshift: [description]
    """
    advances = len(rawintervals)
    # correct for delays in observation
    intervals = [interval+0.048 for interval in rawintervals]
    # ignore the first interval as its not based on a blink
    intervals = intervals[1:]
    states = calc.reverse_states_by_munchlax(intervals)

    # pylint: disable=no-value-for-parameter
    prng = Xorshift(*states)
    states = prng.get_state()

    #validation check
    expected_intervals = [randrange(r,100,370)/30 for r in prng.get_next_rand_sequence(advances)]

    paired = list(zip(intervals,expected_intervals))

    assert all(abs(o-e)<0.1 for o,e in paired)
    result = Xorshift(*states)
    result.get_next_rand_sequence(len(intervals))
    return result
